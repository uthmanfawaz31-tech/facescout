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
        os.makedirs(self.user_data_dir, exist_ok=True)
        self.is_running = False

    def log(self, message: str):
        if self.log_callback:
            self.log_callback(message)

    def extract_group_id_or_name(self, group_url: str) -> Optional[str]:
        """Extracts group slug or numerical ID from Facebook URL."""
        match = re.search(r"facebook\.com\/groups\/([^\/\?]+)", group_url)
        if match:
            return match.group(1)
        return None

    def build_group_search_urls(self, group_url: str, keywords: List[str]) -> List[Dict[str, str]]:
        """Builds in-group search URLs for all stealth keywords."""
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
        """Launches a visible browser so the user can log into Facebook once. Session is saved."""
        self.log("Launching visible Chrome browser for Facebook login...")
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
            self.log("Browser opened. Please log into your Facebook account in the browser.")
            self.log("Once logged in, you can close the browser window. Session will be saved automatically.")
            
            # Keep open until user closes or navigates to feed
            try:
                while len(context.pages) > 0:
                    await asyncio.sleep(2)
            except Exception:
                pass
            await context.close()
            self.log("Facebook login session saved successfully!")

    async def scrape_group(
        self,
        group_url: str,
        keywords: Optional[List[str]] = None,
        max_posts: int = 30,
        scan_comments: bool = True,
        deep_profile_scan: bool = False,
        headless: bool = True,
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
            self.log(f"Invalid Facebook group URL: {group_url}")
            self.is_running = False
            return []

        self.log(f"Starting scouting on group: {group_id}")
        self.log(f"Keywords to scout: {', '.join(active_keywords[:8])}...")

        async with async_playwright() as p:
            launch_args = ["--disable-blink-features=AutomationControlled"]
            if not headless:
                launch_args.append("--start-maximized")

            context = await p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                executable_path=CHROME_PATH if CHROME_PATH and os.path.exists(CHROME_PATH) else None,
                headless=headless,
                args=launch_args,
                viewport=None if not headless else {"width": 1280, "height": 800}
            )

            page = await context.new_page()
            
            # Use stealth tweaks
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)

            # Try navigating to search first for top keywords (most targeted results)
            # Pick primary keywords: "firestick", "m3u", "tivimate", "smart tv", "xtream"
            search_targets = [kw for kw in active_keywords if kw in [
                "firestick", "m3u", "tivimate", "xtream", "smart tv", "live tv", "smarters"
            ]]
            if not search_targets:
                search_targets = active_keywords[:3]

            for search_kw in search_targets:
                if not self.is_running or len(found_leads) >= max_posts:
                    break

                target_url = f"https://www.facebook.com/groups/{group_id}/search/?q={search_kw.replace(' ', '%20')}"
                self.log(f"Navigating to in-group search: '{search_kw}' -> {target_url}")
                
                try:
                    await page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
                    await asyncio.sleep(random.uniform(3.0, 5.0))

                    # Check for login checkpoint or redirect
                    if "login" in page.url or "checkpoint" in page.url:
                        self.log("NOTICE: Facebook requires login to view this group. Use the 'Login with Browser' button to sign in once.")
                        break

                    # Scroll down several times to load posts
                    scroll_cycles = 4
                    for sc in range(scroll_cycles):
                        if not self.is_running or len(found_leads) >= max_posts:
                            break
                        
                        self.log(f"Scanning search results for '{search_kw}' (scroll {sc+1}/{scroll_cycles})...")
                        await page.mouse.wheel(0, 1400)
                        await asyncio.sleep(random.uniform(2.5, 4.0))

                        # Extract visible post elements
                        posts_data = await page.evaluate("""
                            () => {
                                const results = [];
                                const postElements = document.querySelectorAll('div[role="feed"] > div, div[role="article"]');
                                
                                postElements.forEach((el, index) => {
                                    // Text content
                                    const text = el.innerText || '';
                                    if (text.length < 20) return;

                                    // Author info
                                    let authorName = 'Unknown User';
                                    let authorUrl = '';
                                    const authorEl = el.querySelector('h2 a, h3 a, strong a, a[role="link"]');
                                    if (authorEl) {
                                        authorName = authorEl.innerText.trim();
                                        authorUrl = authorEl.href || '';
                                    }

                                    // Post link / permalink
                                    let postUrl = '';
                                    const links = el.querySelectorAll('a[href*="/posts/"], a[href*="/permalink/"], a[href*="multi_permalinks"]');
                                    if (links.length > 0) {
                                        postUrl = links[0].href;
                                    }

                                    results.push({
                                        id: 'fb_post_' + index + '_' + Date.now(),
                                        authorName: authorName,
                                        authorUrl: authorUrl,
                                        postUrl: postUrl,
                                        text: text
                                    });
                                });
                                return results;
                            }
                        """)

                        for item in posts_data:
                            raw_text = item.get("text", "")
                            if not raw_text or raw_text in seen_texts:
                                continue
                            seen_texts.add(raw_text)

                            matched_kw = self.extractor.matches_keywords(raw_text)
                            if not matched_kw:
                                continue

                            intent, confidence = self.extractor.classify_intent(raw_text)
                            contacts = self.extractor.extract_contacts(raw_text)

                            author_url = item.get("authorUrl", "")
                            author_name = item.get("authorName", "Group Member")

                            # Deep scan bio if requested and no direct contact found in text
                            if deep_profile_scan and author_url and "facebook.com" in author_url and not (contacts.whatsapp or contacts.telegram):
                                try:
                                    contacts = await self._deep_scan_profile(context, author_url, contacts)
                                except Exception as e:
                                    self.log(f"Profile scan error for {author_name}: {e}")

                            lead = Lead(
                                id=f"lead_{len(found_leads)+1}_{random.randint(1000, 9999)}",
                                author_name=author_name,
                                author_profile_url=author_url,
                                post_url=item.get("postUrl", target_url),
                                source_type="post",
                                raw_text=raw_text[:800],
                                matched_keywords=matched_kw,
                                intent=intent,
                                intent_confidence=confidence,
                                contacts=contacts,
                                group_url=group_url
                            )

                            found_leads.append(lead)
                            self.log(f"Found [{intent}] Lead: {author_name} | Keywords: {', '.join(matched_kw)} | Contacts: WA:{len(contacts.whatsapp)} TG:{len(contacts.telegram)}")
                            
                            if on_lead_found:
                                on_lead_found(lead)

                            if len(found_leads) >= max_posts:
                                break

                except Exception as e:
                    self.log(f"Error querying '{search_kw}': {e}")
                    await asyncio.sleep(2)

            await context.close()

        self.is_running = False
        self.log(f"Scouting completed! Total leads found: {len(found_leads)}")
        return found_leads

    async def _deep_scan_profile(self, context: BrowserContext, profile_url: str, contacts: ContactInfo) -> ContactInfo:
        """Visits user profile to extract public intro/bio and contact links."""
        try:
            p_page = await context.new_page()
            # Clean profile url
            clean_url = profile_url.split("?")[0]
            await p_page.goto(clean_url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(random.uniform(1.5, 2.5))

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
        # Split by likely post/comment boundaries
        blocks = re.split(r"\n\s*\n\s*\n|(?<=\n)(?=[A-Z][a-z]+ [A-Z][a-z]+(?:\s+·|\s+Shared|\s+wrote|\s+commented))", text_or_html)
        if len(blocks) <= 1:
            blocks = text_or_html.split("\n\n")

        for idx, block in enumerate(blocks):
            clean_block = block.strip()
            if len(clean_block) < 15:
                continue

            matched_kw = self.extractor.matches_keywords(clean_block)
            if not matched_kw:
                # If the block has explicit contacts and streaming words, still match
                contacts = self.extractor.extract_contacts(clean_block)
                if not (contacts.whatsapp or contacts.telegram or contacts.discord):
                    continue

            contacts = self.extractor.extract_contacts(clean_block)
            intent, confidence = self.extractor.classify_intent(clean_block)

            # Try to infer author name from first line
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
