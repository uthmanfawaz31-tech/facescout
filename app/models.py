from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal
from datetime import datetime

class ContactInfo(BaseModel):
    whatsapp: List[str] = Field(default_factory=list)
    whatsapp_links: List[str] = Field(default_factory=list)
    telegram: List[str] = Field(default_factory=list)
    telegram_links: List[str] = Field(default_factory=list)
    discord: List[str] = Field(default_factory=list)
    phone_numbers: List[str] = Field(default_factory=list)
    emails: List[str] = Field(default_factory=list)
    other_socials: Dict[str, str] = Field(default_factory=dict)

class Lead(BaseModel):
    id: str
    author_name: str
    author_profile_url: Optional[str] = None
    post_url: Optional[str] = None
    source_type: Literal["post", "comment", "profile_bio", "pasted_text"] = "post"
    raw_text: str
    matched_keywords: List[str] = Field(default_factory=list)
    intent: Literal["REQUESTING", "DISCUSSING", "SELLER"] = "DISCUSSING"
    intent_confidence: float = 0.5
    contacts: ContactInfo = Field(default_factory=ContactInfo)
    scouted_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    group_url: Optional[str] = None

class ScrapeRequest(BaseModel):
    group_url: str
    keywords: Optional[List[str]] = None
    max_posts: int = 40
    scan_comments: bool = True
    deep_profile_scan: bool = False
    headless: bool = True

class PasteScoutRequest(BaseModel):
    text_or_html: str
    group_url: Optional[str] = None
    keywords: Optional[List[str]] = None

class ScoutStatus(BaseModel):
    is_active: bool = False
    current_action: str = "Idle"
    posts_scanned: int = 0
    comments_scanned: int = 0
    leads_count: int = 0
    logs: List[str] = Field(default_factory=list)
