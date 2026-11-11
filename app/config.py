import os

# Default Stealth Keywords for IPTV / Live TV Streaming
DEFAULT_KEYWORDS = [
    # Protocols & Formats
    "m3u",
    "m3u8",
    "xtream codes",
    "xtream",
    "xtreme code",
    "stalker portal",
    "mac address",
    "epg",
    "playlist",

    # Streaming Devices & Hardware
    "firestick",
    "fire stick",
    "android tv",
    "smart tv",
    "samsung tv",
    "lg tv",
    "formuler",
    "shield tv",
    "mag box",
    "chromecast",
    "apple tv",
    "mi box",

    # IPTV Apps & Players
    "iptv",
    "tivimate",
    "smarters pro",
    "iptv smarters",
    "smarters",
    "xcip tv",
    "xcip",
    "implayer",
    "ibo player",
    "net iptv",
    "smart stb",
    "ss iptv",
    "ott navigator",

    # Streaming Terms (Avoid direct flagged words)
    "live tv",
    "live streams",
    "ppv",
    "sports channels",
    "sky sports",
    "tnt sports",
    "channels list",
    "catch up",
    "cut the cord",
    "buffer free"
]

# Patterns signaling someone is looking to BUY or requesting a service (High Priority Leads)
REQUEST_PATTERNS = [
    r"\blooking for\b",
    r"\bneed a (provider|service|recommendation|m3u|playlist|sub)\b",
    r"\brecommend(ations?)?\b",
    r"\bany good (service|provider|player|app|streams?)\b",
    r"\bwho (has|uses|is) the best\b",
    r"\btest line\b",
    r"\bfree trial\b",
    r"\bpricing\b",
    r"\bwhere (can|do) i get\b",
    r"\banyone (selling|have|know of)\b",
    r"\bmy (provider|service) (stopped|went down|buffering|is dead)\b",
    r"\bwant to cut the cord\b",
    r"\blooking to switch\b",
    r"\bpm me details\b",
    r"\bdm me info\b"
]

# Patterns signaling competitor sellers or promoters
SELLER_PATTERNS = [
    r"\bdm (me )?for (a )?(test|trial|free trial|link)\b",
    r"\bmessage me (on|for)\b",
    r"\bwhatsapp me\b",
    r"\bwe offer\b",
    r"\bcheck (out )?my\b",
    r"\breseller\b",
    r"\b\d+k?\+?\s*channels\b",
    r"\banti-?freeze\b",
    r"\b99\.9% uptime\b",
    r"\binstant delivery\b",
    r"\baffordable price\b"
]

# System Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
COOKIES_DIR = os.path.join(BASE_DIR, "cookies")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Default Chrome executable location on Windows
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_PATH):
    CHROME_PATH = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(CHROME_PATH):
        CHROME_PATH = None
