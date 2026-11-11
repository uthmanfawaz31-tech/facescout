import os
import sys
import uvicorn

if __name__ == "__main__":
    print("=" * 65)
    print(" 🚀 StreamScout - Facebook Stealth IPTV & Streaming Lead Platform")
    print("=" * 65)
    print(" • Dashboard URL    : http://127.0.0.1:8000")
    print(" • Mode             : Auto-Browser Scout + Ban-Proof Paste + Telegram")
    print(" • Stealth Filter   : m3u, firestick, xtream codes, tivimate, etc.")
    print(" • Contact Channels : WhatsApp, Telegram, Discord, Email, Phone")
    print("=" * 65)
    print("Starting StreamScout web dashboard server...")
    
    uvicorn.run("app.server:app", host="127.0.0.1", port=8000, log_level="info")
