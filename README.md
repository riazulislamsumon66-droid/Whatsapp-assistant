# 📱 WhatsApp Assistant - Android APK

A powerful WhatsApp auto-reply assistant Android app with AI + website integration.

## 🎯 For Users (How to Use)

### Download & Install
1. Download the APK from the latest GitHub Actions build
2. Install on your Android phone (allow "Install from unknown sources")
3. Open the app
4. Go to **Settings** → Enter your AI API key
5. Go to **Connect** → Enter your bridge URL → Connect
6. Go to **Dashboard** → Enable Auto Reply
7. That's it! 🎉

## 🛠️ For Developers (How to Build)

### Option 1: GitHub Actions (Recommended)
1. Fork this repository
2. Push to GitHub
3. The workflow automatically builds the APK
4. Download from Actions → Artifacts

### Option 2: Local Build (Termux/Linux)
```bash
pip install buildozer
buildozer android debug
```

### Option 3: Flet Build (Easiest)
```bash
pip install flet
flet build apk main.py
```

## Features

- 🔗 **WhatsApp Connect** — Connect via Baileys bridge
- 🤖 **AI Auto Reply** — Uses OpenRouter, OpenAI, or any compatible API
- 🌐 **Website Scraping** — Auto-scrapes your website for context
- ⚙️ **Backend API** — Connect your own API for data-driven replies
- 📱 **Native Android** — Beautiful dark UI with bottom navigation
- 💾 **Local Storage** — All data stored on device
- 📤 **Manual Messages** — Send messages manually from the app
- 🔔 **Background Service** — Auto-reply runs in background

## Screens

1. **Dashboard** — Stats, connection status, recent messages
2. **Connect** — WhatsApp bridge connection
3. **Settings** — AI API key, website URL, bot config
4. **Messages** — Full message history + manual send

## Requirements

- AI API Key (OpenRouter recommended — free tier available)
- Baileys bridge running on a server (port 3000)
- Android 5.0+
