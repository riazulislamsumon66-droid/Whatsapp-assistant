# WhatsApp Assistant - Flet version for Android APK
# Same functionality as Kivy version but uses Flet (Flutter-based)

import json
import os
import threading
import time
import requests

import flet as ft

CONFIG_DIR = "."
CONFIG_FILE = os.path.join(CONFIG_DIR, "maya_config.json")


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {
        "ai_api_key": "",
        "ai_provider": "openrouter",
        "ai_model": "google/gemini-2.0-flash-free",
        "website_url": "",
        "backend_api": "",
        "bot_name": "Maya",
        "reply_tone": "friendly_professional",
        "bridge_url": "http://localhost:3000"
    }


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def check_bridge(url="http://localhost:3000"):
    try:
        r = requests.get(f"{url}/health", timeout=5)
        return r.status_code == 200 and r.json().get("status") == "connected"
    except:
        return False


def send_message(to, message, bridge_url="http://localhost:3000"):
    try:
        r = requests.post(f"{bridge_url}/send",
                         json={"chatId": to, "message": message},
                         timeout=10)
        return r.status_code == 200
    except:
        return False


def generate_ai_reply(message, website_data=None, config=None):
    if not config:
        config = load_config()
    api_key = config.get("ai_api_key", "")
    model = config.get("ai_model", "google/gemini-2.0-flash-free")
    tone = config.get("reply_tone", "friendly_professional")
    bot_name = config.get("bot_name", "Maya")
    if not api_key:
        return f"Thank you for your message! {bot_name} will respond shortly."
    prompt = (f"You are {bot_name}, a helpful WhatsApp assistant. Tone: {tone}. "
              f"Reply in the SAME language as the customer. Keep reply concise (under 300 words). "
              f"Never mention being an AI. Be warm and professional.")
    if website_data:
        prompt += f"\n\nBusiness Info:\n{website_data}"
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": message}
            ], "max_tokens": 500, "temperature": 0.7},
            timeout=30
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except:
        pass
    return "Thank you for your message! I'll respond shortly."


def scrape_website(url):
    if not url:
        return None
    if not url.startswith("http"):
        url = "https://" + url
    try:
        r = requests.get(url, timeout=10,
                        headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            import re
            text = re.sub(r'<[^>]+>', ' ', r.text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:3000]
    except:
        pass
    return None


def main(page: ft.Page):
    page.title = "Maya Assistant"
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0F1419"

    cfg = load_config()
    auto_reply_enabled = True

    # ─── Status ───
    status_icon = ft.Icon(name=ft.Icons.RADIO_BUTTON_OFF, color=ft.Colors.RED)
    status_text = ft.Text("Disconnected", color=ft.Colors.RED, size=14, weight=ft.FontWeight.BOLD)

    # ─── Stats ───
    stat_msgs = ft.Text("Messages: 0", size=12)
    stat_contacts = ft.Text("Contacts: 0", size=12)
    stat_ai = ft.Text("AI Replies: 0", size=12)
    stat_today = ft.Text("Today: 0", size=12)

    # ─── Auto Reply Toggle ───
    auto_btn = ft.ElevatedButton(
        "Auto Reply: ON",
        icon=ft.Icons.PLAY_ARROW,
        color=ft.Colors.ONE,
        bgcolor=ft.Colors.BLUE_700,
    )

    activity_log = ft.Text("Recent activity will appear here...",
                           size=11, color=ft.Colors.GREY_500)

    # ─── Settings fields ───
    api_key_field = ft.TextField(label="API Key", value=cfg.get("ai_api_key", ""),
                                 password=True, can_reveal_password=True)
    model_field = ft.TextField(label="Model", value=cfg.get("ai_model", "google/gemini-2.0-flash-free"))
    website_field = ft.TextField(label="Website URL", value=cfg.get("website_url", ""))
    backend_field = ft.TextField(label="Backend API", value=cfg.get("backend_api", ""))
    bot_name_field = ft.TextField(label="Bot Name", value=cfg.get("bot_name", "Maya"))
    bridge_field = ft.TextField(label="Bridge URL", value=cfg.get("bridge_url", "http://localhost:3000"))
    save_result = ft.Text("", size=12)

    def refresh_status(e=None):
        bridge = bridge_field.value or "http://localhost:3000"
        if check_bridge(bridge):
            status_icon.name = ft.Icons.RADIO_BUTTON_CHECKED
            status_icon.color = ft.Colors.GREEN
            status_text.value = "Connected"
            status_text.color = ft.Colors.GREEN
        else:
            status_icon.name = ft.Icons.RADIO_BUTTON_OFF
            status_icon.color = ft.Colors.RED
            status_text.value = "Disconnected"
            status_text.color = ft.Colors.RED
        page.update()

    def toggle_auto(e):
        nonlocal auto_reply_enabled
        auto_reply_enabled = not auto_reply_enabled
        if auto_reply_enabled:
            auto_btn.text = "Auto Reply: ON"
            auto_btn.bgcolor = ft.Colors.BLUE_700
            auto_btn.icon = ft.Icons.PLAY_ARROW
        else:
            auto_btn.text = "Auto Reply: OFF"
            auto_btn.bgcolor = ft.Colors.GREY_700
            auto_btn.icon = ft.Icons.PAUSE
        page.update()

    def scrape_now(e):
        url = website_field.value.strip()
        if url:
            data = scrape_website(url)
            activity_log.value = f"Scraped {len(data) if data else 0} chars from {url}"
        else:
            activity_log.value = "Set website URL in Settings first"
        page.update()

    def save_settings(e):
        cfg = load_config()
        cfg["ai_api_key"] = api_key_field.value
        cfg["ai_model"] = model_field.value
        cfg["website_url"] = website_field.value
        cfg["backend_api"] = backend_field.value
        cfg["bot_name"] = bot_name_field.value
        cfg["bridge_url"] = bridge_field.value
        save_config(cfg)
        save_result.value = "Saved!"
        save_result.color = ft.Colors.GREEN
        page.update()

    def test_api(e):
        key = api_key_field.value.strip()
        if not key:
            save_result.value = "Enter API key first"
            save_result.color = ft.Colors.RED
            page.update()
            return
        save_result.value = "Testing..."
        save_result.color = ft.Colors.GREY_400
        page.update()

        def _test():
            try:
                r = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model": model_field.value or "google/gemini-2.0-flash-free",
                          "messages": [{"role": "user", "content": "Say hi"}],
                          "max_tokens": 50},
                    timeout=15
                )
                if r.status_code == 200:
                    save_result.value = "API working!"
                    save_result.color = ft.Colors.GREEN
                else:
                    save_result.value = f"Error: {r.status_code}"
                    save_result.color = ft.Colors.RED
            except Exception as ex:
                save_result.value = f"Failed: {str(ex)[:40]}"
                save_result.color = ft.Colors.RED
            page.update()

        threading.Thread(target=_test, daemon=True).start()

    # ─── Dashboard Tab ───
    dashboard = ft.Column([
        ft.Text("Maya Assistant", size=24, weight=ft.FontWeight.BOLD,
                color=ft.Colors.BLUE_400),
        ft.Row([status_icon, status_text], spacing=5),
        ft.Divider(height=1),
        ft.Row([
            ft.Column([stat_msgs, stat_ai], expand=1),
            ft.Column([stat_contacts, stat_today], expand=1),
        ]),
        ft.Divider(height=1),
        auto_btn,
        ft.Row([
            ft.ElevatedButton("Refresh", icon=ft.Icons.REFRESH,
                             bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE,
                             on_click=refresh_status),
            ft.ElevatedButton("Scrape Website", icon=ft.Icons.LINK,
                             bgcolor=ft.Colors.PURPLE_700, color=ft.Colors.WHITE,
                             on_click=scrape_now),
        ], wrap=True),
        activity_log,
    ], spacing=10, expand=True)

    # ─── Settings Tab ───
    settings = ft.Column([
        ft.Text("AI Settings", size=18, weight=ft.FontWeight.BOLD,
                color=ft.Colors.BLUE_400),
        api_key_field,
        model_field,
        website_field,
        backend_field,
        bot_name_field,
        bridge_field,
        ft.Row([
            ft.ElevatedButton("Save Settings", icon=ft.Icons.SAVE,
                             bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE,
                             on_click=save_settings),
            ft.ElevatedButton("Test API", icon=ft.Icons.SCIENCE,
                             bgcolor=ft.Colors.PURPLE_700, color=ft.Colors.WHITE,
                             on_click=test_api),
        ], wrap=True),
        save_result,
    ], spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

    # ─── Tabs ───
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=200,
        expand=True,
        tabs=[
            ft.Tab(text="Dashboard", icon=ft.Icons.DASHBOARD, content=dashboard),
            ft.Tab(text="Settings", icon=ft.Icons.SETTINGS, content=settings),
        ],
    )

    page.add(tabs)
    auto_btn.on_click = toggle_auto

    # Auto-refresh timer
    def auto_refresh_loop():
        while True:
            time.sleep(10)
            if auto_reply_enabled:
                refresh_status()

    threading.Thread(target=auto_refresh_loop, daemon=True).start()


ft.app(target=main)
