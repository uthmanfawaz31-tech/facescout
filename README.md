# 🎯 StreamScout — Facebook IPTV & Streaming Lead Extractor Platform

A specialized scouting platform designed to bypass Facebook's 1-message-per-24h outreach restriction by extracting **WhatsApp numbers**, **Telegram handles**, **Discord tags**, and direct contact channels from Facebook group members talking about or requesting IPTV & live TV streaming.

---

## ⚡ The Facebook Outreach Limitation Problem & Solution

> **The Problem:** Facebook limits outbound direct messaging (DM) to stranger profiles (often allowing only 1 message per 24 hours before triggering anti-spam flags or rate limits).
>
> **The Solution:** StreamScout identifies high-intent leads requesting streaming setups and extracts their **WhatsApp (`wa.me`)**, **Telegram (`t.me`)**, **Discord**, or phone numbers from comments, posts, and public profile bios — allowing you to reach out directly via external channels with **zero Facebook restrictions**.
>
> **Stealth Keyword Architecture:** Because Facebook shadows and restricts the direct keyword `"iptv"`, StreamScout scans for high-volume stealth terms and hardware/app alternatives:
> - **Protocols & Formats:** `m3u`, `m3u8`, `xtream codes`, `xtream`, `xtreme code`, `stalker portal`, `mac address`, `epg`, `playlist`
> - **Devices & Hardware:** `firestick`, `fire stick`, `android tv`, `smart tv`, `samsung tv`, `lg tv`, `webos`, `formuler`, `shield tv`, `mag box`, `chromecast`
> - **Players & Apps:** `tivimate`, `smarters pro`, `iptv smarters`, `xcip tv`, `implayer`, `ibo player`, `net iptv`, `smart stb`, `ss iptv`
> - **Live Terms:** `live tv`, `live streams`, `sports channels`, `ppv`, `sky sports`, `tnt sports`, `cut the cord`, `buffer free`

---

## 🚀 Key Features

1. **Multi-Mode Lead Discovery:**
   - **Mode 1: Automated Browser Scouting:** Playwright-powered stealth browser logs into Facebook groups, searches targeted keywords, scrolls discussion feeds, and extracts leads in real time.
   - **Mode 2: In-Group Stealth Search Generator:** Generates 1-click search URLs for any group, letting you browse keyword-filtered posts directly in your browser.
   - **Mode 3: Ban-Proof Quick Paste Ingest:** Copy posts or comment sections from your mobile phone or PC and paste them into the dashboard for instantaneous contact & intent extraction.
   - **Mode 4: Mobile Telegram Bot:** Connect your own Telegram bot token to control StreamScout and receive lead notifications directly on your phone.
2. **AI Intent Classification:**
   - 🔥 **`REQUESTING` (Hot Buyer Leads):** People asking for recommendations, providers, playlists, test lines, or free trials.
   - 💬 **`DISCUSSING`:** People troubleshooting devices (Firestick buffering, Smart TV apps, audio sync).
   - 📢 **`SELLER`:** Competitors and sellers (automatically flagged so you don't waste time outreach).
3. **1-Click Outreach Generator:**
   - Generates personalized pitches tailored to what the lead asked for.
   - Direct `Chat on WhatsApp` (`https://wa.me/...`) and `Open in Telegram` (`https://t.me/...`) buttons.
4. **Export to CSV / JSON:**
   - One-click export with full contact lists ready for CRM or bulk outreach.

---

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.10+
- Google Chrome installed (optional, for visible browser login)

### 1. Launch the Platform
In the project directory, run:

```bash
python run.py
```

Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## 📖 How to Use

### Step 1: Facebook Session Login (Optional but Recommended)
1. On the dashboard header, click **"FB Session Login"**.
2. A visible Chrome window will open.
3. Log into your Facebook account once.
4. Close the browser window. Your session cookies are securely saved in `cookies/browser_profile` and will be reused for all future scans.

### Step 2: Scout a Facebook Group
1. Copy any Facebook Group link (e.g., `https://www.facebook.com/groups/firestickstreamers/`).
2. Paste it into the **"Facebook Group URL"** field.
3. Choose post scan count (e.g. 30).
4. Click **"Start Group Scouting"**.
5. StreamScout will scan in-group search results for each stealth keyword, extract posts and comments, classify intent, and display discovered leads.

### Step 3: Direct Outreach
1. For any discovered lead, check their direct contact badge:
   - Green badge: **WhatsApp (`+...`)**
   - Blue badge: **Telegram (`@username`)**
   - Purple badge: **Discord**
2. Click **"Generate Outreach Pitch"** to copy a tailored message or click **"Chat on WhatsApp"** to open a direct chat instantly!

### Step 4: Mobile Telegram Bot (Optional)
1. Message `@BotFather` on Telegram and create a bot (`/newbot`) to get a token.
2. Go to the **Mobile Telegram Bot** tab in StreamScout and paste your token.
3. Click **"Connect Telegram Bot"**.
4. Now you can forward group links or paste comments in Telegram, and the bot will reply with rich lead cards on your phone.

---

## 📁 Project Architecture

```
facebook scouting/
├── app/
│   ├── __init__.py
│   ├── config.py           # Stealth keywords, regex patterns, device lists
│   ├── models.py           # Pydantic schemas (Lead, ContactInfo, Status)
│   ├── extractor.py        # Contact parser (WA, TG, Discord, Email, Phone) + Intent classifier
│   ├── fb_scraper.py       # Playwright browser automation & stealth scraping
│   ├── telegram_bot.py     # Telegram Bot integration for mobile use
│   └── server.py           # FastAPI REST API + Live dashboard endpoints
├── static/
│   ├── index.html          # Modern dark-mode responsive dashboard
│   └── app.js              # Real-time state management, filters, modal handlers
├── cookies/                # Persistent Chrome user profiles & session cookies
├── data/                   # Scanned leads storage & exports
├── requirements.txt        # Python package dependencies
├── run.py                  # One-command server runner
└── README.md               # Documentation & usage manual
```
