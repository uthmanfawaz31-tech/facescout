import os
import re
import json
import asyncio
import random
from typing import List, Dict, Optional, Callable
from playwright.async_api import async_playwright, BrowserContext, Page
from app.config import COOKIES_DIR, CHROME_PATH, BASE_DIR
from app.models import Lead, ContactInfo
from app.extractor import LeadExtractor

class FacebookGroupScraper:
    def __init__(self, extractor: Optional[LeadExtractor] = None, log_callback: Optional[Callable[[str], None]] = None):
        self.extractor = extractor or LeadExtractor()
        self.log_callback = log_callback or (lambda msg: print(f"[FB Scraper] {msg}"))
        self.user_data_dir = os.path.join(COOKIES_DIR, "browser_profile")
        self.cookies_file = os.path.join(COOKIES_DIR, "cookies.json")
        os.makedirs(self.user_data_dir, exist_ok=True)
        self.is_running = False

    def log(self, message: str):
        if self.log_callback:
            self.log_callback(message)

    def is_session_saved(self) -> bool:
        """Checks if a saved browser session or cookies.json exists."""
        if os.path.exists(self.cookies_file) and os.path.getsize(self.cookies_file) > 10:
            return True
        # Check if browser profile contains Default or session files
        profile_default = os.path.join(self.user_data_dir, "Default")
        if os.path.exists(profile_default) and len(os.listdir(profile_default)) > 2:
            return True
        return False

    def save_raw_cookies(self, cookie_text_or_json: str) -> bool:
        """Saves cookie string or EditThisCookie JSON into cookies.json."""
        try:
            cookies = []
            trimmed = cookie_text_or_json.strip()
            
            # Format 1: JSON array from EditThisCookie / Cookie-Editor
            if trimmed.startswith("[") and trimmed.endswith("]"):
                parsed = json.loads(trimmed)
                for c in parsed:
                    cookies.append({
                        "name": c.get("name"),
                        "value": c.get("value"),
                        "domain": c.get("domain", ".facebook.com"),
                        "path": c.get("path", "/"),
                        "secure": c.get("secure", True),
                        "httpOnly": c.get("httpOnly", False),
                        "sameSite": c.get("sameSite", "Lax") if c.get("sameSite") in ["Strict", "Lax", "None"] else "Lax"
                    })
            else:
                # Format 2: Header string e.g. "c_user=1000123; xs=2%3Aabc..."
                pairs = trimmed.split(";")
                for p in pairs:
                    if "=" in p:
                        k, v = p.strip().split("=", 1)
                        cookies.append({
                            "name": k.strip(),
                            "value": v.strip(),
                            "domain": ".facebook.com",
                            "path": "/",
                            "secure": True
                        })

            if not cookies:
                return False

            with open(self.cookies_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2)

            self.log(f"Successfully saved {len(cookies)} Facebook session cookies!")
            return True
        except Exception as e:
            self.log(f"Error saving cookies: {e}")
            return False

    def extract_group_id_or_name(self, group_url: str) -> Optional[str]:
        """Extracts group slug or numerical ID from Facebook URL."""
        clean = group_url.strip()
        # Handles: facebook.com/groups/12345/
        match = re.search(r"facebook\.com\/groups\/([^\/\?#]+)", clean, re.IGNORECASE)
        if match:
            return match.group(1)
        # If user just pasted the group ID or slug
        if clean.isalnum() or "-" in clean or "_" in clean:
            return clean
        return None

    def build_group_search_urls(self, group_url: str, keywords: List[str]) -> List[Dict[str, str]]:
        """Builds in-group search URLs for stealth keywords."""
        group_id = self.extract_group_id_or_name(group_url)
        if not group_id:
            return []
        
        urls = []
        for kw in keywords:
            encoded_kw = kw.replace(" ", "%20")
            search_url = f"https://www.facebook.com/groups/{group_id}/search/?q={encoded_kw}"
            urls.append({"keyword": kw, "url": search_url})
        return urls

    async def open_login_browser(self):
        """Launches a visible browser so the user can log into Facebook once."""
        self.log("🚀 Launching visible Chrome browser for Facebook login...")
        async with async_playwright() as p:
            launch_args = ["--disable-blink-features=AutomationControlled", "--start-maximized"]
            context = await p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                executable_path=CHROME_PATH if CHROME_PATH and os.path.exists(CHROME_PATH) else None,
                headless=False,
                args=launch_args,
                viewport=None
            )
            page = await context.new_page()
            await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
            self.log("Browser opened! Please log into Facebook in that window.")
            self.log("Once logged in to your account, you can close the browser window. Session will be saved automatically.")
            
            # Wait for user to log in or close
            try:
                while len(context.pages) > 0:
                    # Check if cookies now include c_user
                    cookies = await context.cookies()
                    has_cuser = any(c.get("name") == "c_user" for c in cookies)
                    if has_cuser:
                        with open(self.cookies_file, "w", encoding="utf-8") as f:
                            json.dump(cookies, f, indent=2)
                        self.log("✅ Facebook login detected! Session cookies captured and saved.")
                    await asyncio.sleep(2)
            except Exception:
                pass
            await context.close()
            self.log("Facebook session saved successfully!")

    async def _dismiss_facebook_popups(self, page: Page):
        """Dismisses cookie banners, login modals, and closeable overlays."""
        try:
            # 1. Send Escape key
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.5)

            # 2. Click standard dismiss / close / not now buttons if present
            await page.evaluate("""
                () => {
                    // Click close on dialogs
                    const closeSelectors = [
                        'div[aria-label="Close"]',
                        'div[aria-label="Decline optional cookies"]',
                        'div[aria-label="Allow all cookies"]',
                        'div[aria-label="Only allow essential cookies"]',
                        '[data-testid="cookie-policy-manage-dialog-accept-button"]',
                        'div[role="button"][tabindex="0"]'
                    ];

                    // Remove blocking modal overlays if present
                    const dialogs = document.querySelectorAll('div[role="dialog"], [data-pagelet="Consent"]');
                    dialogs.forEach(d => {
                        const txt = (d.innerText || '').toLowerCase();
                        if (txt.includes('log in') || txt.includes('cookie') || txt.includes('see more on facebook')) {
                            d.remove();
                        }
                    });

                    // Restore body scrolling
                    document.body.style.overflow = 'auto';
                    document.documentElement.style.overflow = 'auto';
                    document.querySelectorAll('div[style*="overflow: hidden"]').forEach(el => {
                        el.style.overflow = 'auto';
                    });
                }
            """)
        except Exception:
            pass

    async def scrape_group(
        self,
        group_url: str,
        keywords: Optional[List[str]] = None,
        max_posts: int = 30,
        scan_comments: bool = True,
        deep_profile_scan: bool = False,
        headless: bool = False,
        on_lead_found: Optional[Callable[[Lead], None]] = None
    ) -> List[Lead]:
        """
        Scrapes a Facebook group for IPTV/streaming queries, extracting posts, comments,
        and alternative contact details (WhatsApp, Telegram, Discord, etc.).
        """
        self.is_running = True
        found_leads: List[Lead] = []
        seen_texts = set()

        if keywords:
            self.extractor = LeadExtractor(keywords)

        active_keywords = self.extractor.keywords
        group_id = self.extract_group_id_or_name(group_url)
        if not group_id:
            self.log(f"❌ Invalid Facebook group URL or ID: '{group_url}'")
            self.is_running = False
            return []

        self.log(f"🔎 Target Group Identified: {group_id}")
        self.log(f"Active Stealth Keywords ({len(active_keywords)}): {', '.join(active_keywords[:6])}...")

        async with async_playwright() as p:
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--disable-notifications"
            ]
            if not headless:
                launch_args.append("--start-maximized")

            # Check if Chrome executable is available
            exec_path = CHROME_PATH if (CHROME_PATH and os.path.exists(CHROME_PATH)) else None

            context = await p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                executable_path=exec_path,
                headless=headless,
                args=launch_args,
                viewport=None if not headless else {"width": 1280, "height": 900}
            )

            # Load cookies.json if present
            if os.path.exists(self.cookies_file):
                try:
                    with open(self.cookies_file, "r", encoding="utf-8") as f:
                        saved_cookies = json.load(f)
                    if isinstance(saved_cookies, list) and len(saved_cookies) > 0:
                        await context.add_cookies(saved_cookies)
                        self.log(f"Loaded {len(saved_cookies)} session cookies into browser.")
                except Exception as e:
                    self.log(f"Notice: Could not load cookies file: {e}")

            page = await context.new_page()
            
            # Stealth script overrides
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
            """)

            # Step 1: Navigate to the Group Feed first
            base_group_url = f"https://www.facebook.com/groups/{group_id}/"
            self.log(f"Navigating to group feed: {base_group_url}")
            
            try:
                await page.goto(base_group_url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(3.0)
                await self._dismiss_facebook_popups(page)

                # Check if redirected to login
                current_url = page.url.lower()
                if "login" in current_url or "checkpoint" in current_url:
                    self.log("⚠️ FACEBOOK LOGIN REQUIRED:")
                    self.log("Facebook has locked this group behind a login wall.")
                    self.log("👉 ACTION: Use the 'FB Session Login' button in the dashboard to sign in once, or paste your cookies.")
                    if not headless:
                        self.log("Browser window is visible! You may log in directly now...")
                        # Wait up to 60s for user to log in if window is visible
                        for _ in range(30):
                            if "login" not in page.url.lower():
                                self.log("Login detected! Proceeding with scraping...")
                                await asyncio.sleep(2)
                                break
                            await asyncio.sleep(2)
                
                # Scroll group feed to gather recent discussions
                self.log(f"Scanning main group feed discussions...")
                for scroll_step in range(4):
                    if not self.is_running or len(found_leads) >= max_posts:
                        break
                    
                    await self._dismiss_facebook_popups(page)
                    await page.mouse.wheel(0, 1200)
                    await asyncio.sleep(random.uniform(2.0, 3.5))

                    leads_from_page = await self._extract_posts_and_comments_from_dom(page, group_url, seen_texts)
                    for lead in leads_from_page:
                        found_leads.append(lead)
                        self.log(f"🎯 LEAD FOUND: {lead.author_name} ({lead.intent}) | Keywords: {', '.join(lead.matched_keywords)}")
                        if on_lead_found:
                            on_lead_found(lead)
                        if len(found_leads) >= max_posts:
                            break

            except Exception as e:
                self.log(f"Notice during feed navigation: {e}")

            # Step 2: In-Group Targeted Keyword Searches
            # If still have capacity, query targeted keywords in the group search
            priority_keywords = ["firestick", "m3u", "tivimate", "xtream", "smart tv", "live tv", "smarters"]
            search_keywords = [k for k in active_keywords if k in priority_keywords]
            if not search_keywords:
                search_keywords = active_keywords[:3]

            for kw in search_keywords:
                if not self.is_running or len(found_leads) >= max_posts:
                    break

                search_url = f"https://www.facebook.com/groups/{group_id}/search/?q={kw.replace(' ', '%20')}"
                self.log(f"Searching in-group for '{kw}' -> {search_url}")

                try:
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=35000)
                    await asyncio.sleep(random.uniform(2.5, 4.0))
                    await self._dismiss_facebook_popups(page)

                    if "login" in page.url.lower():
                        self.log(f"In-group search requires active Facebook login. Skipping search query.")
                        break

                    # Scroll search results
                    for sc in range(3):
                        if not self.is_running or len(found_leads) >= max_posts:
                            break

                        await self._dismiss_facebook_popups(page)
                        await page.mouse.wheel(0, 1400)
                        await asyncio.sleep(random.uniform(2.0, 3.5))

                        leads_from_page = await self._extract_posts_and_comments_from_dom(page, group_url, seen_texts)
                        for lead in leads_from_page:
                            found_leads.append(lead)
                            self.log(f"🎯 LEAD FOUND: {lead.author_name} ({lead.intent}) | Keywords: {', '.join(lead.matched_keywords)}")
                            if on_lead_found:
                                on_lead_found(lead)
                            if len(found_leads) >= max_posts:
                                break

                except Exception as e:
                    self.log(f"Notice querying '{kw}': {e}")
                    await asyncio.sleep(2)

            # Deep profile scan if requested
            if deep_profile_scan:
                for lead in found_leads:
                    if not self.is_running:
                        break
                    if lead.author_profile_url and not (lead.contacts.whatsapp or lead.contacts.telegram):
                        self.log(f"Deep scanning profile bio for: {lead.author_name}...")
                        lead.contacts = await self._deep_scan_profile(context, lead.author_profile_url, lead.contacts)

            await context.close()

        self.is_running = False
        self.log(f"✅ Scouting completed! Total leads captured: {len(found_leads)}")
        return found_leads

    async def _extract_posts_and_comments_from_dom(self, page: Page, group_url: str, seen_texts: set) -> List[Lead]:
        """
        Extracts posts and comments from current page using multi-strategy DOM inspection.
        Resilient against Facebook's frequent CSS obfuscations.
        """
        results: List[Lead] = []

        try:
            raw_elements = await page.evaluate("""
                () => {
                    const extracted = [];
                    
                    // Strategy 1: Post text blocks
                    const textNodes = document.querySelectorAll('div[dir="auto"], span[dir="auto"], div[data-ad-preview="message"]');
                    
                    textNodes.forEach(node => {
                        const text = (node.innerText || '').trim();
                        if (text.length < 15 || text.length > 2500) return;
                        
                        // Ignore UI buttons and labels
                        const lower = text.toLowerCase();
                        if (['like', 'comment', 'share', 'write a comment...', 'view more comments', 'most relevant', 'all comments'].includes(lower)) {
                            return;
                        }

                        // Traverse up to find container card
                        let container = node;
                        for (let i = 0; i < 6; i++) {
                            if (container.parentElement) {
                                container = container.parentElement;
                                if (container.getAttribute('role') === 'article' || container.querySelector('a[role="link"]')) {
                                    break;
                                }
                            }
                        }

                        // Extract author name and profile URL
                        let authorName = 'Facebook User';
                        let authorUrl = '';
                        const authorLink = container.querySelector('h2 a, h3 a, strong a, a[role="link"][tabindex="0"], a[href*="/user/"], a[href*="facebook.com/"]');
                        if (authorLink) {
                            authorName = (authorLink.innerText || '').trim() || 'Facebook User';
                            authorUrl = authorLink.href || '';
                        }

                        // Extract post link
                        let postUrl = '';
                        const permalink = container.querySelector('a[href*="/posts/"], a[href*="/permalink/"], a[href*="multi_permalinks"]');
                        if (permalink) {
                            postUrl = permalink.href || '';
                        }

                        extracted.push({
                            text: text,
                            authorName: authorName,
                            authorUrl: authorUrl,
                            postUrl: postUrl
                        });
                    });

                    return extracted;
                }
            """)

            for item in raw_elements:
                text = item.get("text", "")
                if not text or text in seen_texts:
                    continue
                seen_texts.add(text)

                matched_kw = self.extractor.matches_keywords(text)
                contacts = self.extractor.extract_contacts(text)

                # Include if matches keywords OR has explicit direct social contacts
                if not matched_kw and not (contacts.whatsapp or contacts.telegram or contacts.discord):
                    continue

                intent, confidence = self.extractor.classify_intent(text)

                lead = Lead(
                    id=f"fb_lead_{len(results)+1}_{random.randint(1000, 9999)}",
                    author_name=item.get("authorName") or "Facebook Member",
                    author_profile_url=item.get("authorUrl"),
                    post_url=item.get("postUrl") or group_url,
                    source_type="post",
                    raw_text=text[:900],
                    matched_keywords=matched_kw,
                    intent=intent,
                    intent_confidence=confidence,
                    contacts=contacts,
                    group_url=group_url
                )
                results.append(lead)

        except Exception as e:
            self.log(f"DOM extraction notice: {e}")

        return results

    async def _deep_scan_profile(self, context: BrowserContext, profile_url: str, contacts: ContactInfo) -> ContactInfo:
        """Visits user profile to extract public intro/bio and contact links."""
        try:
            p_page = await context.new_page()
            clean_url = profile_url.split("?")[0]
            await p_page.goto(clean_url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(random.uniform(1.5, 2.5))
            await self._dismiss_facebook_popups(p_page)

            bio_text = await p_page.evaluate("""
                () => {
                    const bioEl = document.querySelector('div[data-pagelet="ProfileTilesFeed_0"], div[role="main"]');
                    return bioEl ? bioEl.innerText : document.body.innerText;
                }
            """)

            if bio_text:
                bio_contacts = self.extractor.extract_contacts(bio_text)
                for wa in bio_contacts.whatsapp:
                    if wa not in contacts.whatsapp:
                        contacts.whatsapp.append(wa)
                        contacts.whatsapp_links.append(f"https://wa.me/{wa}")
                for tg in bio_contacts.telegram:
                    if tg not in contacts.telegram:
                        contacts.telegram.append(tg)
                        contacts.telegram_links.append(f"https://t.me/{tg}")
                for dc in bio_contacts.discord:
                    if dc not in contacts.discord:
                        contacts.discord.append(dc)
                for em in bio_contacts.emails:
                    if em not in contacts.emails:
                        contacts.emails.append(em)
                for k, v in bio_contacts.other_socials.items():
                    contacts.other_socials[k] = v

            await p_page.close()
        except Exception:
            pass
        return contacts

    def parse_pasted_content(self, text_or_html: str, group_url: Optional[str] = None) -> List[Lead]:
        """
        Instantly parses copied text or HTML from Facebook groups.
        Zero browser automation required. 100% ban-proof.
        """
        leads: List[Lead] = []
        blocks = re.split(r"\n\s*\n\s*\n|(?<=\n)(?=[A-Z][a-z]+ [A-Z][a-z]+(?:\s+·|\s+Shared|\s+wrote|\s+commented))", text_or_html)
        if len(blocks) <= 1:
            blocks = text_or_html.split("\n\n")

        for idx, block in enumerate(blocks):
            clean_block = block.strip()
            if len(clean_block) < 15:
                continue

            matched_kw = self.extractor.matches_keywords(clean_block)
            contacts = self.extractor.extract_contacts(clean_block)
            if not matched_kw and not (contacts.whatsapp or contacts.telegram or contacts.discord):
                continue

            intent, confidence = self.extractor.classify_intent(clean_block)

            lines = clean_block.splitlines()
            first_line = lines[0].strip()
            author_name = "Facebook User"
            if len(first_line) < 35 and not any(p in first_line.lower() for p in ["http", "looking", "need", "dm", "wa.me"]):
                author_name = first_line

            lead = Lead(
                id=f"pasted_lead_{idx+1}_{random.randint(100, 999)}",
                author_name=author_name,
                source_type="pasted_text",
                raw_text=clean_block[:900],
                matched_keywords=matched_kw,
                intent=intent,
                intent_confidence=confidence,
                contacts=contacts,
                group_url=group_url
            )
            leads.append(lead)

        return leads
