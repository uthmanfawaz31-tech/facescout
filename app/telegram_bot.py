import asyncio
import httpx
import json
from typing import Optional, Callable
from app.fb_scraper import FacebookGroupScraper
from app.extractor import LeadExtractor
from app.config import DEFAULT_KEYWORDS

class TelegramScoutBot:
    def __init__(self, bot_token: str, on_log: Optional[Callable[[str], None]] = None):
        self.bot_token = bot_token
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        self.is_running = False
        self.scraper = FacebookGroupScraper()
        self.on_log = on_log or (lambda msg: print(f"[TG Bot] {msg}"))

    def log(self, message: str):
        if self.on_log:
            self.on_log(message)

    async def send_message(self, chat_id: int, text: str, reply_markup: Optional[dict] = None):
        """Sends a message to a Telegram chat."""
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                res = await client.post(f"{self.api_url}/sendMessage", json=payload)
                return res.json()
            except Exception as e:
                self.log(f"Error sending message to {chat_id}: {e}")
                return None

    async def start_polling(self):
        """Polls for new messages from Telegram users."""
        self.is_running = True
        offset = 0
        self.log("Telegram Scout Bot started polling...")

        async with httpx.AsyncClient(timeout=35.0) as client:
            while self.is_running:
                try:
                    res = await client.get(f"{self.api_url}/getUpdates", params={"offset": offset, "timeout": 20})
                    if res.status_code == 200:
                        data = res.json()
                        if data.get("ok"):
                            for update in data.get("result", []):
                                offset = update["update_id"] + 1
                                await self.handle_update(update)
                    else:
                        await asyncio.sleep(3)
                except httpx.RequestError as e:
                    self.log(f"Telegram polling connection error: {e}")
                    await asyncio.sleep(4)
                except Exception as e:
                    self.log(f"Telegram polling error: {e}")
                    await asyncio.sleep(2)

    def stop(self):
        self.is_running = False
        self.log("Telegram Scout Bot stopped.")

    async def handle_update(self, update: dict):
        message = update.get("message")
        if not message or "text" not in message:
            return

        chat_id = message["chat"]["id"]
        text = message["text"].strip()

        if text.startswith("/start"):
            welcome_text = (
                "🎯 <b>Facebook IPTV / Live TV Scout Bot</b>\n\n"
                "I scout Facebook groups for people talking about or requesting IPTV, "
                "live streaming, m3u playlists, and firesticks — and find their "
                "<b>WhatsApp, Telegram, or Discord</b> so you bypass Facebook DM limits!\n\n"
                "<b>Commands & Usage:</b>\n"
                "• Send any <b>Facebook Group Link</b> to generate instant keyword search links or scout it\n"
                "• <b>Paste any post/comment text</b> to extract WhatsApp/Telegram instantly\n"
                "• <code>/keywords</code> - View stealth keywords used"
            )
            await self.send_message(chat_id, welcome_text)

        elif text.startswith("/keywords"):
            kw_list = "\n".join([f"• <code>{k}</code>" for k in DEFAULT_KEYWORDS[:20]])
            msg = f"🔍 <b>Active Stealth Keywords ({len(DEFAULT_KEYWORDS)}):</b>\n\n{kw_list}\n<i>...and more</i>"
            await self.send_message(chat_id, msg)

        elif "facebook.com/groups/" in text:
            group_id = self.scraper.extract_group_id_or_name(text)
            if not group_id:
                await self.send_message(chat_id, "⚠️ Invalid Facebook Group link. Please send a valid group link.")
                return

            # Generate stealth search links
            search_items = self.scraper.build_group_search_urls(text, [
                "firestick", "m3u", "tivimate", "xtream", "smart tv", "live tv"
            ])
            links_markup = {
                "inline_keyboard": [
                    [{"text": f"🔎 Search '{item['keyword']}'", "url": item["url"]}]
                    for item in search_items[:5]
                ]
            }

            msg = (
                f"🎯 <b>Facebook Group Detected:</b> <code>{group_id}</code>\n\n"
                f"Generated direct in-group search links for stealth keywords.\n"
                f"Click below to browse targeted requests, or paste posts/comments here for instant contact extraction!"
            )
            await self.send_message(chat_id, msg, reply_markup=links_markup)

        else:
            # User pasted text or post content
            leads = self.scraper.parse_pasted_content(text)
            if not leads:
                await self.send_message(
                    chat_id,
                    "ℹ️ No relevant streaming keywords or social contacts found in that snippet.\n"
                    "Try pasting a post or comment discussing firestick, m3u, live tv, or containing a phone number / @handle."
                )
                return

            for lead in leads:
                badge = "🔥 <b>[HIGH PRIORITY LEAD - REQUESTING]</b>" if lead.intent == "REQUESTING" else f"ℹ️ [{lead.intent}]"
                wa_info = f"📱 WhatsApp: <code>{', '.join(lead.contacts.whatsapp)}</code>" if lead.contacts.whatsapp else "📱 WhatsApp: None"
                tg_info = f"✈️ Telegram: <code>@{', '.join(lead.contacts.telegram)}</code>" if lead.contacts.telegram else "✈️ Telegram: None"
                dc_info = f"🎮 Discord: <code>{', '.join(lead.contacts.discord)}</code>" if lead.contacts.discord else ""

                buttons = []
                for wa_link in lead.contacts.whatsapp_links[:2]:
                    buttons.append([{"text": "💬 Chat on WhatsApp", "url": wa_link}])
                for tg_link in lead.contacts.telegram_links[:2]:
                    buttons.append([{"text": "✈️ Open in Telegram", "url": tg_link}])

                card_text = (
                    f"{badge}\n\n"
                    f"👤 <b>Author:</b> {lead.author_name}\n"
                    f"🏷️ <b>Keywords:</b> <code>{', '.join(lead.matched_keywords)}</code>\n"
                    f"{wa_info}\n"
                    f"{tg_info}\n"
                    f"{dc_info}\n\n"
                    f"📝 <b>Text Snippet:</b>\n<i>\"{lead.raw_text[:280]}...\"</i>"
                )

                reply_markup = {"inline_keyboard": buttons} if buttons else None
                await self.send_message(chat_id, card_text, reply_markup=reply_markup)
