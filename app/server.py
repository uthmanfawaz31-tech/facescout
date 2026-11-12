import os
import csv
import io
import json
import asyncio
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import DEFAULT_KEYWORDS, STATIC_DIR, DATA_DIR, COOKIES_DIR
from app.models import Lead, ScrapeRequest, PasteScoutRequest, ScoutStatus
from app.extractor import LeadExtractor
from app.fb_scraper import FacebookGroupScraper
from app.telegram_bot import TelegramScoutBot

app = FastAPI(title="StreamScout - Facebook IPTV & Streaming Lead Engine", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session state
state = {
    "is_active": False,
    "current_action": "Idle",
    "last_error": None,
    "posts_scanned": 0,
    "comments_scanned": 0,
    "logs": ["StreamScout Engine Ready."],
    "leads": [],
    "keywords": list(DEFAULT_KEYWORDS),
    "telegram_bot": None,
    "scraper": None
}

def add_log(msg: str):
    state["logs"].append(msg)
    if len(state["logs"]) > 250:
        state["logs"].pop(0)

# Mount directories
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(COOKIES_DIR, exist_ok=True)

@app.get("/api/session/status")
async def get_session_status():
    scraper = FacebookGroupScraper()
    is_saved = scraper.is_session_saved()
    return {
        "is_authenticated": is_saved,
        "status_label": "Authenticated & Ready" if is_saved else "Not Authenticated (Login Recommended)"
    }

@app.post("/api/session/cookies")
async def save_cookies_endpoint(payload: dict):
    raw_cookies = payload.get("cookies", "").strip()
    if not raw_cookies:
        raise HTTPException(status_code=400, detail="Cookie content is empty.")
    
    scraper = FacebookGroupScraper(log_callback=add_log)
    success = scraper.save_raw_cookies(raw_cookies)
    if success:
        add_log("Facebook session cookies saved successfully via dashboard.")
        return {"status": "success", "message": "Cookies saved successfully!"}
    else:
        raise HTTPException(status_code=400, detail="Invalid cookie format. Provide 'c_user=...; xs=...' or JSON array.")

@app.get("/api/keywords")
async def get_keywords():
    return {"keywords": state["keywords"]}

@app.post("/api/keywords")
async def update_keywords(payload: dict):
    new_kw = payload.get("keywords")
    if isinstance(new_kw, list):
        state["keywords"] = [k.strip().lower() for k in new_kw if k.strip()]
        add_log(f"Updated keywords list ({len(state['keywords'])} keywords).")
        return {"status": "success", "keywords": state["keywords"]}
    raise HTTPException(status_code=400, detail="Expected list of keywords")

@app.post("/api/scout/generate-search-links")
async def generate_search_links(payload: dict):
    group_url = payload.get("group_url", "")
    scraper = FacebookGroupScraper()
    group_id = scraper.extract_group_id_or_name(group_url)
    if not group_id:
        raise HTTPException(status_code=400, detail="Invalid Facebook Group URL or ID")
    
    links = scraper.build_group_search_urls(group_url, state["keywords"])
    return {"group_id": group_id, "links": links}

@app.post("/api/scout/paste")
async def scout_pasted_content(req: PasteScoutRequest):
    extractor = LeadExtractor(state["keywords"])
    scraper = FacebookGroupScraper(extractor=extractor)
    leads = scraper.parse_pasted_content(req.text_or_html, group_url=req.group_url)
    
    for lead in leads:
        if not any(l.raw_text == lead.raw_text for l in state["leads"]):
            state["leads"].insert(0, lead)
            
    add_log(f"Parsed pasted content: found {len(leads)} leads/contacts.")
    return {"status": "success", "leads_found": len(leads), "leads": leads}

async def run_browser_scout_task(req: ScrapeRequest):
    state["is_active"] = True
    state["current_action"] = "Initializing browser..."
    state["last_error"] = None
    add_log(f"🚀 Starting group scout: {req.group_url}")

    def on_lead(lead: Lead):
        state["leads"].insert(0, lead)
        add_log(f"🎯 NEW LEAD: {lead.author_name} ({lead.intent}) - WA:{len(lead.contacts.whatsapp)} TG:{len(lead.contacts.telegram)}")

    extractor = LeadExtractor(req.keywords or state["keywords"])
    scraper = FacebookGroupScraper(extractor=extractor, log_callback=add_log)
    state["scraper"] = scraper

    try:
        leads = await scraper.scrape_group(
            group_url=req.group_url,
            keywords=req.keywords or state["keywords"],
            max_posts=req.max_posts,
            scan_comments=req.scan_comments,
            deep_profile_scan=req.deep_profile_scan,
            headless=req.headless,
            on_lead_found=on_lead
        )
        if len(leads) == 0:
            state["current_action"] = "Completed (0 leads found - Check logs if login was required)"
            add_log("Scan finished with 0 leads. If Facebook prompted for login, please use 'FB Session Login' or paste your cookies.")
        else:
            state["current_action"] = f"Completed ({len(leads)} leads captured)"
            add_log(f"🎉 Scout session finished! Total new leads: {len(leads)}")
    except Exception as e:
        state["last_error"] = str(e)
        state["current_action"] = f"Error: {str(e)[:40]}"
        add_log(f"❌ Scout session failed with error: {str(e)}")
    finally:
        state["is_active"] = False

@app.post("/api/scout/start")
async def start_scout(req: ScrapeRequest, background_tasks: BackgroundTasks):
    if state["is_active"]:
        raise HTTPException(status_code=400, detail="A scouting session is already running.")
    
    background_tasks.add_task(run_browser_scout_task, req)
    return {"status": "started", "message": "Scouting session initiated in background"}

@app.post("/api/scout/stop")
async def stop_scout():
    if state["scraper"]:
        state["scraper"].is_running = False
    state["is_active"] = False
    state["current_action"] = "Stopped"
    add_log("Scouting session stopped by user.")
    return {"status": "stopped"}

@app.get("/api/scout/status")
async def get_status():
    scraper = FacebookGroupScraper()
    is_saved = scraper.is_session_saved()
    return {
        "is_active": state["is_active"],
        "current_action": state["current_action"],
        "last_error": state["last_error"],
        "is_authenticated": is_saved,
        "leads_count": len(state["leads"]),
        "logs": state["logs"][-40:],
        "leads": state["leads"]
    }

@app.post("/api/browser/login")
async def trigger_browser_login(background_tasks: BackgroundTasks):
    scraper = FacebookGroupScraper(log_callback=add_log)
    background_tasks.add_task(scraper.open_login_browser)
    return {"status": "success", "message": "Visible Chrome launched! Please log in to Facebook in that window."}

@app.post("/api/telegram/start")
async def start_telegram_bot(payload: dict, background_tasks: BackgroundTasks):
    bot_token = payload.get("bot_token", "").strip()
    if not bot_token:
        raise HTTPException(status_code=400, detail="Bot token is required.")

    if state["telegram_bot"] and state["telegram_bot"].is_running:
        state["telegram_bot"].stop()

    bot = TelegramScoutBot(bot_token=bot_token, on_log=add_log)
    state["telegram_bot"] = bot
    background_tasks.add_task(bot.start_polling)
    return {"status": "started", "message": "Telegram bot connected and polling!"}

@app.post("/api/telegram/stop")
async def stop_telegram_bot():
    if state["telegram_bot"]:
        state["telegram_bot"].stop()
        state["telegram_bot"] = None
        return {"status": "stopped", "message": "Telegram bot stopped."}
    return {"status": "not_running", "message": "Telegram bot was not running."}

@app.post("/api/leads/clear")
async def clear_leads():
    state["leads"] = []
    add_log("Cleared all leads from session.")
    return {"status": "cleared"}

@app.get("/api/export/csv")
async def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Author Name", "Intent", "Matched Keywords",
        "WhatsApp Numbers", "WhatsApp Chat Links",
        "Telegram Handles", "Telegram Links",
        "Discord", "Emails", "Author Profile URL", "Post URL", "Text Snippet", "Scouted At"
    ])
    
    for lead in state["leads"]:
        writer.writerow([
            lead.id,
            lead.author_name,
            lead.intent,
            "; ".join(lead.matched_keywords),
            "; ".join(lead.contacts.whatsapp),
            "; ".join(lead.contacts.whatsapp_links),
            "; ".join(lead.contacts.telegram),
            "; ".join(lead.contacts.telegram_links),
            "; ".join(lead.contacts.discord),
            "; ".join(lead.contacts.emails),
            lead.author_profile_url or "",
            lead.post_url or "",
            lead.raw_text.replace("\n", " ")[:300],
            lead.scouted_at
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=facebook_iptv_leads.csv"}
    )

@app.get("/api/export/json")
async def export_json():
    leads_dict = [l.model_dump() for l in state["leads"]]
    return StreamingResponse(
        iter([json.dumps(leads_dict, indent=2)]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=facebook_iptv_leads.json"}
    )

# Static file serving
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>StreamScout: static/index.html not found</h1>"
