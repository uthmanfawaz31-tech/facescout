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

## 🔑 Facebook Session & Authentication (Important!)

Facebook strictly locks group discussions and in-group searches behind login. If you start a scan without an active session, Facebook redirects to the login screen and 0 leads will be captured.

StreamScout gives you **3 easy ways** to authenticate or bypass this:

### 1. In-Browser Console Grabber (Easiest & 100% Ban-Proof)
If you already browse Facebook in your daily browser (Chrome, Edge, Brave), you are already logged in!
1. Open any Facebook group in your browser and scroll down a few times.
2. Press `F12` on your keyboard (or Right Click → Inspect → Click "Console").
3. Copy the 1-line snippet from the **"In-Browser Grabber"** tab on StreamScout and paste it into the console.
4. Press Enter. All leads from your current screen immediately send to your StreamScout dashboard!

### 2. Fast Cookie Paste (5 Seconds)
1. On the dashboard header, click **"Connect FB Cookies"**.
2. Paste your Facebook cookie string (`c_user=...; xs=...`) or export from the "EditThisCookie" / "Cookie-Editor" extension.
3. Click Save. The engine is authenticated permanently on your machine.

### 3. Log In via Real Chrome
1. Click **"Log In via Visible Chrome"** in the top warning banner.
2. A visible Chrome window will launch.
3. Log into Facebook. Once logged in, close the window. Your session cookies are automatically captured and saved.

---

## 🚀 How to Run

In the project folder, start the platform:

```powershell
python run.py
```

Open your browser at:
```
http://127.0.0.1:8000
```
