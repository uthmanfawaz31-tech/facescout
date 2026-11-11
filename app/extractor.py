import re
from typing import Tuple, List, Dict, Optional
from app.models import ContactInfo
from app.config import DEFAULT_KEYWORDS, REQUEST_PATTERNS, SELLER_PATTERNS

class LeadExtractor:
    def __init__(self, keywords: Optional[List[str]] = None):
        self.keywords = [k.strip().lower() for k in (keywords or DEFAULT_KEYWORDS) if k.strip()]

    def matches_keywords(self, text: str) -> List[str]:
        """Check which target IPTV/streaming stealth keywords exist in text."""
        matched = []
        lowered = text.lower()
        for kw in self.keywords:
            pattern = r'(?<![a-z0-9])' + re.escape(kw) + r'(?![a-z0-9])'
            if re.search(pattern, lowered):
                matched.append(kw)
        return list(dict.fromkeys(matched))

    def classify_intent(self, text: str) -> Tuple[str, float]:
        """
        Classifies whether the user is:
        - REQUESTING (High priority prospective buyer looking for service/m3u/recommendation)
        - SELLER (Competitor / spammer promoting their service)
        - DISCUSSING (General setup, device talk, app issues)
        """
        lowered = text.lower()
        request_matches = 0
        for pat in REQUEST_PATTERNS:
            if re.search(pat, lowered):
                request_matches += 1

        seller_matches = 0
        for pat in SELLER_PATTERNS:
            if re.search(pat, lowered):
                seller_matches += 1

        if seller_matches > request_matches and seller_matches > 0:
            return "SELLER", min(0.95, 0.6 + seller_matches * 0.15)
        elif request_matches > 0:
            return "REQUESTING", min(0.98, 0.6 + request_matches * 0.18)
        else:
            return "DISCUSSING", 0.50

    def extract_contacts(self, text: str) -> ContactInfo:
        """
        Extracts WhatsApp numbers/links, Telegram handles/links, Discord, emails, and phone numbers.
        """
        contacts = ContactInfo()
        clean_text = text.replace("\r", " ")

        # 1. WhatsApp Links (wa.me / api.whatsapp.com / chat.whatsapp.com)
        wa_link_pattern = r"(?:https?:\/\/)?wa\.me\/(?:\+?(\d{7,15}))"
        for match in re.finditer(wa_link_pattern, clean_text, re.IGNORECASE):
            num = match.group(1).lstrip("+")
            if num not in contacts.whatsapp:
                contacts.whatsapp.append(num)
                contacts.whatsapp_links.append(f"https://wa.me/{num}")

        wa_api_pattern = r"(?:https?:\/\/)?api\.whatsapp\.com\/send\?phone=(?:\+?(\d{7,15}))"
        for match in re.finditer(wa_api_pattern, clean_text, re.IGNORECASE):
            num = match.group(1).lstrip("+")
            if num not in contacts.whatsapp:
                contacts.whatsapp.append(num)
                contacts.whatsapp_links.append(f"https://wa.me/{num}")

        wa_group_pattern = r"((?:https?:\/\/)?chat\.whatsapp\.com\/[a-zA-Z0-9]{15,28})"
        for match in re.finditer(wa_group_pattern, clean_text, re.IGNORECASE):
            link = match.group(1)
            if not link.startswith("http"):
                link = "https://" + link
            if link not in contacts.whatsapp_links:
                contacts.whatsapp_links.append(link)

        # 2. WhatsApp Explicit Mention with Phone Number
        # e.g., "WhatsApp: +1 (555) 019-2834" or "wa: 447123456789"
        wa_text_pattern = r"(?:whatsapp|wa|watsapp|wapp|what's\s*app)[:\s\-]+(?:\+?(\d[\d\s\-().]{6,16}\d))"
        for match in re.finditer(wa_text_pattern, clean_text, re.IGNORECASE):
            raw_num = match.group(1)
            digits = re.sub(r"\D", "", raw_num)
            if len(digits) >= 8 and len(digits) <= 15:
                if digits not in contacts.whatsapp:
                    contacts.whatsapp.append(digits)
                    contacts.whatsapp_links.append(f"https://wa.me/{digits}")

        # 3. Telegram Links and Handles
        # t.me/username or telegram.me/username
        tg_link_pattern = r"(?:https?:\/\/)?(?:t\.me|telegram\.me)\/([a-zA-Z0-9_]{4,32})"
        for match in re.finditer(tg_link_pattern, clean_text, re.IGNORECASE):
            handle = match.group(1)
            # Skip generic paths
            if handle.lower() not in ["joinchat", "share", "addstickers", "c"]:
                if handle not in contacts.telegram:
                    contacts.telegram.append(handle)
                    contacts.telegram_links.append(f"https://t.me/{handle}")

        # Explicit Telegram mention e.g. "telegram: @username" or "tg @username"
        tg_text_pattern = r"(?:telegram|tg|tele|t\.g)[:\s\-]+@?([a-zA-Z0-9_]{4,32})"
        for match in re.finditer(tg_text_pattern, clean_text, re.IGNORECASE):
            handle = match.group(1).lstrip("@")
            if handle not in contacts.telegram and len(handle) >= 4:
                contacts.telegram.append(handle)
                contacts.telegram_links.append(f"https://t.me/{handle}")

        # Standalone @handle if nearby social words or in short responses
        at_pattern = r"(?<![a-zA-Z0-9_])@([a-zA-Z0-9_]{5,30})\b"
        for match in re.finditer(at_pattern, clean_text):
            candidate = match.group(1)
            # Ignore common non-handles
            if candidate.lower() not in ["everyone", "here", "channel", "admin", "all", "highlight"]:
                # Check if text mentions tg, telegram, dm, contact
                context_window = clean_text[max(0, match.start() - 30):min(len(clean_text), match.end() + 30)].lower()
                if any(w in context_window for w in ["tg", "tele", "telegram", "reach", "dm", "message", "contact"]):
                    if candidate not in contacts.telegram:
                        contacts.telegram.append(candidate)
                        contacts.telegram_links.append(f"https://t.me/{candidate}")

        # 4. Discord Users & Invites
        # Username#1234
        disc_tag_pattern = r"\b([a-zA-Z0-9_.-]{2,32})#(\d{4})\b"
        for match in re.finditer(disc_tag_pattern, clean_text):
            tag = f"{match.group(1)}#{match.group(2)}"
            if tag not in contacts.discord:
                contacts.discord.append(tag)

        # Discord mention e.g. "discord: username"
        disc_text_pattern = r"(?:discord|dc)[:\s\-]+@?([a-zA-Z0-9_.-]{3,32})"
        for match in re.finditer(disc_text_pattern, clean_text, re.IGNORECASE):
            d_user = match.group(1).lstrip("@")
            if d_user not in contacts.discord:
                contacts.discord.append(d_user)

        # Discord invite links
        disc_link_pattern = r"((?:https?:\/\/)?(?:discord\.gg|discord\.com\/invite)\/[a-zA-Z0-9_-]+)"
        for match in re.finditer(disc_link_pattern, clean_text, re.IGNORECASE):
            inv = match.group(1)
            if not inv.startswith("http"):
                inv = "https://" + inv
            if inv not in contacts.discord:
                contacts.discord.append(inv)

        # 5. Generic Phone Numbers with Country Codes
        phone_pattern = r"(?:\+|00)[1-9]\d{0,3}[-.\s]?(?:\(?\d{1,4}\)?[-.\s]?)?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}"
        for match in re.finditer(phone_pattern, clean_text):
            raw_ph = match.group(0).strip()
            # Clean digits
            cleaned_digits = re.sub(r"\D", "", raw_ph)
            # Filter reasonable phone lengths and skip dates like 2026-11-11
            if 8 <= len(cleaned_digits) <= 15:
                if cleaned_digits not in contacts.phone_numbers:
                    contacts.phone_numbers.append(cleaned_digits)
                    # If no whatsapp link yet, add as probable WhatsApp
                    if cleaned_digits not in contacts.whatsapp:
                        contacts.whatsapp.append(cleaned_digits)
                        contacts.whatsapp_links.append(f"https://wa.me/{cleaned_digits}")

        # 6. Emails
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        for match in re.finditer(email_pattern, clean_text):
            email = match.group(0).lower()
            if email not in contacts.emails:
                contacts.emails.append(email)

        # 7. Other Socials & Portals (Instagram, Twitter, Linktree)
        ig_pattern = r"(?:https?:\/\/)?(?:www\.)?instagram\.com\/([a-zA-Z0-9_.-]{3,30})"
        for match in re.finditer(ig_pattern, clean_text, re.IGNORECASE):
            contacts.other_socials["Instagram"] = f"https://instagram.com/{match.group(1)}"

        x_pattern = r"(?:https?:\/\/)?(?:www\.)?(?:twitter\.com|x\.com)\/([a-zA-Z0-9_]{1,15})"
        for match in re.finditer(x_pattern, clean_text, re.IGNORECASE):
            contacts.other_socials["Twitter/X"] = f"https://x.com/{match.group(1)}"

        linktree_pattern = r"((?:https?:\/\/)?(?:www\.)?linktr\.ee\/[a-zA-Z0-9_.-]+)"
        for match in re.finditer(linktree_pattern, clean_text, re.IGNORECASE):
            link = match.group(1)
            if not link.startswith("http"):
                link = "https://" + link
            contacts.other_socials["Linktree"] = link

        return contacts
