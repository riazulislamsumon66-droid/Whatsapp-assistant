"""
WhatsApp Assistant - Main App (Flet Framework)
Android APK installable application
"""
import flet as ft
import json
import os
import threading
import time
import requests

# --- App Configuration ---
APP_NAME = "WhatsApp Assistant"
APP_VERSION = "1.0.0"

CONFIG_DIR = "/data/data/com.termux/files/home/whatsapp-assistant-app"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DB_FILE = os.path.join(CONFIG_DIR, "messages.json")

def ensure_dirs():
    os.makedirs(CONFIG_DIR, exist_ok=True)

def load_settings():
    ensure_dirs()
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "ai_api_key": "",
        "ai_provider": "openrouter",
        "ai_model": "google/gemini-2.0-flash-free",
        "website_url": "",
        "backend_api": "",
        "bot_name": "Assistant",
        "reply_tone": "friendly_professional",
        "whatsapp_connected": False,
        "bridge_url": "http://localhost:3000"
    }

def save_settings(settings):
    ensure_dirs()
    with open(CONFIG_FILE, "w") as f:
        json.dump(settings, f, indent=2)

def load_messages():
    ensure_dirs()
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return []

def save_messages(messages):
    ensure_dirs()
    with open(DB_FILE, "w") as f:
        json.dump(messages, f, indent=2)

# --- WhatsApp Functions ---
def check_bridge(bridge_url="http://localhost:3000"):
    try:
        r = requests.get(f"{bridge_url}/health", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get("status") == "connected"
    except:
        pass
    return False

def send_whatsapp_message(to, message, bridge_url="http://localhost:3000"):
    try:
        r = requests.post(
            f"{bridge_url}/send",
            json={"chatId": to, "message": message},
            timeout=10
        )
        return r.status_code == 200
    except:
        return False

def get_recent_messages(bridge_url="http://localhost:3000"):
    try:
        r = requests.get(f"{bridge_url}/messages?limit=50", timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

def generate_ai_reply(message, website_data=None, settings=None):
    """Generate AI reply via OpenRouter"""
    if not settings:
        settings = load_settings()
    
    api_key = settings.get("ai_api_key", "")
    model = settings.get("ai_model", "google/gemini-2.0-flash-free")
    tone = settings.get("reply_tone", "friendly_professional")
    bot_name = settings.get("bot_name", "Assistant")
    
    if not api_key:
        return f"Thank you for your message! {bot_name} will get back to you shortly."
    
    system_prompt = f"""You are {bot_name}, a helpful WhatsApp assistant. 
Reply in the SAME LANGUAGE the customer used.
Tone: {tone}. Keep replies concise (under 300 words).
Never mention you are an AI or bot. Be natural and human-like."""
    
    if website_data:
        system_prompt += f"\n\nBusiness Information:\n{website_data}"
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                "max_tokens": 500,
                "temperature": 0.7
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except:
        pass
    
    return f"Thank you for your message! I'll get back to you shortly."

def scrape_website_simple(url):
    """Simple website text extraction"""
    if not url:
        return None
    if not url.startswith("http"):
        url = "https://" + url
    try:
        r = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0"
        })
        if r.status_code == 200:
            import re
            text = re.sub(r'<[^>]+>', ' ', r.text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:3000]
    except:
        pass
    return None


# --- Main App ---
def main(page: ft.Page):
    page.title = APP_NAME
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.window.width = 400
    page.window.height = 700
    page.bgcolor = "#0f1419"
    
    settings = load_settings()
    messages_store = load_messages()
    
    # --- Navigation State ---
    current_tab = "dashboard"
    
    # ==================== DASHBOARD TAB ====================
    
    # Connection Status
    conn_indicator = ft.Container(
        width=12, height=12,
        border_radius=6,
        bgcolor="#f4212e"
    )
    conn_text = ft.Text("Disconnected", size=12, color="#8b98a5")
    
    def update_connection_status():
        connected = check_bridge(settings.get("bridge_url", "http://localhost:3000"))
        conn_indicator.bgcolor = "#00ba7c" if connected else "#f4212e"
        conn_text.value = "Connected" if connected else "Disconnected"
        conn_text.color = "#00ba7c" if connected else "#8b98a5"
        page.update()
    
    # Stats
    total_msgs = ft.Text("0", size=28, weight=ft.FontWeight.BOLD, color="#1d9bf0")
    total_contacts = ft.Text("0", size=28, weight=ft.FontWeight.BOLD, color="#1d9bf0")
    ai_replies = ft.Text("0", size=28, weight=ft.FontWeight.BOLD, color="#1d9bf0")
    today_msgs = ft.Text("0", size=28, weight=ft.FontWeight.BOLD, color="#1d9bf0")
    
    def refresh_stats():
        msgs = load_messages()
        total_msgs.value = str(len(msgs))
        contacts = set(m.get("sender", "") for m in msgs)
        total_contacts.value = str(len(contacts))
        ai_count = sum(1 for m in msgs if m.get("ai_used"))
        ai_replies.value = str(ai_count)
        today_msgs.value = str(len(msgs))  # simplified
        page.update()
    
    # Recent Messages List
    messages_list = ft.ListView(spacing=8, padding=16, auto_scroll=False)
    
    def refresh_messages():
        messages_list.controls.clear()
        msgs = load_messages()[-20:]  # Last 20
        for m in reversed(msgs):
            msg_item = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(m.get("sender", "Unknown"), size=13, weight=ft.FontWeight.BOLD, color="#1d9bf0"),
                        ft.Text(m.get("time", ""), size=11, color="#8b98a5"),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text(m.get("message", "")[:120], size=13, color="#e1e8ed"),
                    ft.Container(
                        content=ft.Text(f"↳ {m.get('reply', '')[:100]}", size=12, color="#00ba7c", italic=True),
                        padding=ft.padding.only(left=16, top=4)
                    ) if m.get("reply") else ft.Container(),
                ]),
                bgcolor="#1a2332",
                border_radius=8,
                padding=12,
            )
            messages_list.controls.append(msg_item)
        page.update()
    
    def on_refresh_click(e):
        update_connection_status()
        refresh_stats()
        refresh_messages()
    
    # Auto-reply toggle
    auto_reply_switch = ft.Switch(
        value=True,
        active_color="#1d9bf0",
        label="Auto Reply",
        label_style=ft.TextStyle(size=13, color="#8b98a5")
    )
    
    dashboard_view = ft.Container(
        content=ft.Column([
            # Header
            ft.Container(
                content=ft.Row([
                    ft.Text("📱 WhatsApp Assistant", size=18, weight=ft.FontWeight.BOLD, color="#1d9bf0"),
                    ft.Row([
                        conn_indicator,
                        conn_text,
                    ], spacing=6),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=16,
                bgcolor="#1a2332",
            ),
            
            # Controls Row
            ft.Container(
                content=ft.Row([
                    auto_reply_switch,
                    ft.ElevatedButton(
                        "↻ Refresh",
                        icon=ft.Icons.REFRESH,
                        on_click=on_refresh_click,
                        bgcolor="#1d9bf0",
                        color="white",
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=ft.padding.symmetric(horizontal=16, vertical=8),
            ),
            
            # Stats Grid
            ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Messages", size=11, color="#8b98a5"),
                            total_msgs,
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        expand=True, bgcolor="#1a2332", border_radius=10, padding=12
                    ),
                    ft.Container(width=8),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Contacts", size=11, color="#8b98a5"),
                            total_contacts,
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        expand=True, bgcolor="#1a2332", border_radius=10, padding=12
                    ),
                    ft.Container(width=8),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("AI Replies", size=11, color="#8b98a5"),
                            ai_replies,
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        expand=True, bgcolor="#1a2332", border_radius=10, padding=12
                    ),
                ]),
                padding=16,
            ),
            
            # Messages Header
            ft.Container(
                content=ft.Text("💬 Recent Messages", size=15, weight=ft.FontWeight.BOLD),
                padding=ft.padding.symmetric(horizontal=16),
            ),
            
            # Messages List
            ft.Container(
                content=messages_list,
                expand=True,
            ),
        ], spacing=0),
        expand=True,
    )
    
    
    # ==================== CONNECTION TAB ====================
    
    bridge_url_field = ft.TextField(
        label="Bridge URL",
        value=settings.get("bridge_url", "http://localhost:3000"),
        border_color="#2f3336",
        color="#e1e8ed",
        text_size=14,
    )
    
    connection_result = ft.Text("", size=13, color="#00ba7c")
    qr_image = ft.Image(visible=False, width=200, height=200)
    
    def on_connect_click(e):
        url = bridge_url_field.value.strip()
        settings["bridge_url"] = url
        save_settings(settings)
        
        connection_result.color = "#8b98a5"
        connection_result.value = "Connecting..."
        page.update()
        
        def connect_bg():
            time.sleep(1)
            connected = check_bridge(url)
            if connected:
                connection_result.value = "✅ Connected to WhatsApp!"
                connection_result.color = "#00ba7c"
                settings["whatsapp_connected"] = True
            else:
                connection_result.value = "❌ Could not connect. Make sure bridge is running on port 3000"
                connection_result.color = "#f4212e"
                settings["whatsapp_connected"] = False
            save_settings(settings)
            update_connection_status()
            page.update()
        
        threading.Thread(target=connect_bg, daemon=True).start()
    
    connection_view = ft.Container(
        content=ft.Column([
            ft.Text("🔗 Connect WhatsApp", size=18, weight=ft.FontWeight.BOLD, padding=16),
            
            ft.Container(
                content=ft.Column([
                    ft.Text("Connect via Baileys Bridge", size=15, weight=ft.FontWeight.W_500, color="#e1e8ed"),
                    ft.Text("Run your Baileys bridge on port 3000, then connect.", size=12, color="#8b98a5"),
                    
                    bridge_url_field,
                    
                    ft.ElevatedButton(
                        "Connect",
                        icon=ft.Icons.LINK,
                        on_click=on_connect_click,
                        bgcolor="#00ba7c",
                        color="white",
                        width=200,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                    ),
                    
                    connection_result,
                    
                    ft.Divider(color="#2f3336"),
                    
                    ft.Text("📋 How to setup bridge:", size=14, weight=ft.FontWeight.W_500, color="#e1e8ed"),
                    ft.Text(
                        "1. Install Node.js on your server/VPS\n"
                        "2. Install @whiskeysockets/baileys\n"
                        "3. Run bridge on port 3000\n"
                        "4. Enter the URL and click Connect",
                        size=12, color="#8b98a5"
                    ),
                ], spacing=12),
                padding=16,
                bgcolor="#1a2332",
                border_radius=12,
                margin=16,
            ),
        ]),
        expand=True,
        bgcolor="#0f1419",
    )
    
    
    # ==================== SETTINGS TAB ====================
    
    api_key_field = ft.TextField(
        label="AI API Key",
        value=settings.get("ai_api_key", ""),
        password=True,
        can_reveal_password=True,
        border_color="#2f3336",
        color="#e1e8ed",
        text_size=14,
    )
    
    provider_dropdown = ft.Dropdown(
        label="AI Provider",
        value=settings.get("ai_provider", "openrouter"),
        options=[
            ft.dropdown.Option("openrouter", "OpenRouter"),
            ft.dropdown.Option("openai", "OpenAI"),
            ft.dropdown.Option("custom", "Custom API"),
        ],
        border_color="#2f3336",
        color="#e1e8ed",
        text_size=14,
    )
    
    model_field = ft.TextField(
        label="AI Model",
        value=settings.get("ai_model", "google/gemini-2.0-flash-free"),
        border_color="#2f3336",
        color="#e1e8ed",
        text_size=14,
    )
    
    website_url_field = ft.TextField(
        label="Website URL",
        value=settings.get("website_url", ""),
        border_color="#2f3336",
        color="#e1e8ed",
        text_size=14,
        hint_text="https://yourbusiness.com"
    )
    
    backend_api_field = ft.TextField(
        label="Backend API URL",
        value=settings.get("backend_api", ""),
        border_color="#2f3336",
        color="#e1e8ed",
        text_size=14,
        hint_text="https://yourbusiness.com/api/data"
    )
    
    bot_name_field = ft.TextField(
        label="Bot Name",
        value=settings.get("bot_name", "Assistant"),
        border_color="#2f3336",
        color="#e1e8ed",
        text_size=14,
    )
    
    tone_dropdown = ft.Dropdown(
        label="Reply Tone",
        value=settings.get("reply_tone", "friendly_professional"),
        options=[
            ft.dropdown.Option("friendly_professional", "Friendly Professional"),
            ft.dropdown.Option("formal", "Formal"),
            ft.dropdown.Option("casual", "Casual"),
            ft.dropdown.Option("warm", "Warm & Friendly"),
        ],
        border_color="#2f3336",
        color="#e1e8ed",
        text_size=14,
    )
    
    save_result = ft.Text("", size=13)
    
    def on_save_click(e):
        settings["ai_api_key"] = api_key_field.value.strip()
        settings["ai_provider"] = provider_dropdown.value
        settings["ai_model"] = model_field.value.strip()
        settings["website_url"] = website_url_field.value.strip()
        settings["backend_api"] = backend_api_field.value.strip()
        settings["bot_name"] = bot_name_field.value.strip() or "Assistant"
        settings["reply_tone"] = tone_dropdown.value
        save_settings(settings)
        
        save_result.value = "✅ Settings saved successfully!"
        save_result.color = "#00ba7c"
        page.update()
    
    def on_test_api_click(e):
        save_result.value = "Testing API..."
        save_result.color = "#8b98a5"
        page.update()
        
        def test_bg():
            api_key = api_key_field.value.strip()
            model = model_field.value.strip() or "google/gemini-2.0-flash-free"
            
            if not api_key:
                save_result.value = "❌ Please enter API key first"
                save_result.color = "#f4212e"
                page.update()
                return
            
            try:
                r = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": "Say hello in one sentence"}],
                        "max_tokens": 100
                    },
                    timeout=15
                )
                if r.status_code == 200:
                    reply = r.json()["choices"][0]["message"]["content"]
                    save_result.value = f"✅ API working! Test reply: {reply[:50]}"
                    save_result.color = "#00ba7c"
                else:
                    save_result.value = f"❌ API error: {r.status_code}"
                    save_result.color = "#f4212e"
            except Exception as ex:
                save_result.value = f"❌ Connection failed: {str(ex)[:50]}"
                save_result.color = "#f4212e"
            page.update()
        
        threading.Thread(target=test_bg, daemon=True).start()
    
    settings_view = ft.Container(
        content=ft.Column([
            ft.Text("⚙️ Settings", size=18, weight=ft.FontWeight.BOLD, padding=16),
            
            ft.Container(
                content=ft.Column([
                    ft.Text("🤖 AI Configuration", size=15, weight=ft.FontWeight.W_500, color="#e1e8ed"),
                    provider_dropdown,
                    api_key_field,
                    model_field,
                    ft.Row([
                        ft.ElevatedButton("Save Settings", icon=ft.Icons.SAVE, on_click=on_save_click, bgcolor="#1d9bf0", color="white"),
                        ft.ElevatedButton("Test API", icon=ft.Icons.PLAY_ARROW, on_click=on_test_api_click, bgcolor="#7c3aed", color="white"),
                    ], spacing=8),
                    save_result,
                ], spacing=10),
                padding=16, bgcolor="#1a2332", border_radius=12, margin=16,
            ),
            
            ft.Container(
                content=ft.Column([
                    ft.Text("🌐 Website & Backend", size=15, weight=ft.FontWeight.W_500, color="#e1e8ed"),
                    website_url_field,
                    backend_api_field,
                ], spacing=10),
                padding=16, bgcolor="#1a2332", border_radius=12, margin=16,
            ),
            
            ft.Container(
                content=ft.Column([
                    ft.Text("💬 Reply Settings", size=15, weight=ft.FontWeight.W_500, color="#e1e8ed"),
                    bot_name_field,
                    tone_dropdown,
                ], spacing=10),
                padding=16, bgcolor="#1a2332", border_radius=12, margin=16,
            ),
        ], scroll=ft.ScrollMode.AUTO),
        expand=True,
        bgcolor="#0f1419",
    )
    
    
    # ==================== MESSAGES TAB ====================
    
    all_messages_list = ft.ListView(spacing=8, padding=16)
    
    def refresh_all_messages():
        all_messages_list.controls.clear()
        msgs = load_messages()
        for m in reversed(msgs[-50:]):
            all_messages_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(m.get("sender", "?"), size=13, weight=ft.FontWeight.BOLD, color="#1d9bf0"),
                            ft.Text(m.get("time", ""), size=11, color="#8b98a5"),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Text(m.get("message", ""), size=13, color="#e1e8ed"),
                        ft.Text(f"↳ {m.get('reply', 'No reply')}", size=12, color="#00ba7c", italic=True) if m.get("reply") else ft.Container(),
                    ]),
                    bgcolor="#1a2332", border_radius=8, padding=12,
                )
            )
        page.update()
    
    def on_send_manual(e):
        to = manual_to_field.value.strip()
        msg = manual_msg_field.value.strip()
        if not to or not msg:
            return
        
        bridge = settings.get("bridge_url", "http://localhost:3000")
        success = send_whatsapp_message(to, msg, bridge)
        
        if success:
            msgs = load_messages()
            msgs.append({
                "sender": to,
                "message": msg,
                "reply": "",
                "time": time.strftime("%Y-%m-%d %H:%M"),
                "direction": "outgoing"
            })
            save_messages(msgs)
            manual_msg_field.value = ""
            refresh_all_messages()
    
    manual_to_field = ft.TextField(
        label="To (phone@s.whatsapp.net)",
        border_color="#2f3336",
        color="#e1e8ed",
        text_size=14,
    )
    manual_msg_field = ft.TextField(
        label="Message",
        border_color="#2f3336",
        color="#e1e8ed",
        text_size=14,
        multiline=True,
        min_lines=2,
        max_lines=4,
    )
    
    messages_view = ft.Container(
        content=ft.Column([
            ft.Text("💬 All Messages", size=18, weight=ft.FontWeight.BOLD, padding=16),
            
            # Manual send
            ft.Container(
                content=ft.Column([
                    ft.Text("📤 Send Manual Message", size=14, weight=ft.FontWeight.W_500),
                    manual_to_field,
                    manual_msg_field,
                    ft.ElevatedButton("Send", icon=ft.Icons.SEND, on_click=on_send_manual, bgcolor="#1d9bf0", color="white"),
                ], spacing=8),
                padding=16, bgcolor="#1a2332", border_radius=12, margin=16,
            ),
            
            ft.Text("📋 Message History", size=14, weight=ft.FontWeight.W_500, padding=ft.padding.symmetric(horizontal=16)),
            
            ft.Container(content=all_messages_list, expand=True),
        ], spacing=0),
        expand=True,
        bgcolor="#0f1419",
    )
    
    
    # ==================== BOTTOM NAVIGATION ====================
    
    def on_nav_change(e):
        idx = e.control.selected_index
        if idx == 0:
            content_container.content = dashboard_view
            refresh_stats()
            refresh_messages()
        elif idx == 1:
            content_container.content = connection_view
        elif idx == 2:
            content_container.content = settings_view
        elif idx == 3:
            content_container.content = messages_view
            refresh_all_messages()
        page.update()
    
    nav_bar = ft.NavigationBar(
        selected_index=0,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.DASHBOARD, label="Dashboard"),
            ft.NavigationBarDestination(icon=ft.Icons.LINK, label="Connect"),
            ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="Settings"),
            ft.NavigationBarDestination(icon=ft.Icons.CHAT, label="Messages"),
        ],
        on_change=on_nav_change,
        bgcolor="#1a2332",
        indicator_color="#1d9bf0",
    )
    
    # Content container
    content_container = ft.Container(content=dashboard_view, expand=True)
    
    # Main layout
    page.add(
        content_container,
        nav_bar,
    )
    
    # Initial load
    update_connection_status()
    refresh_stats()
    refresh_messages()
    
    # --- Background auto-reply listener ---
    def auto_reply_loop():
        processed = set()
        while True:
            try:
                if auto_reply_switch.value and check_bridge(settings.get("bridge_url", "http://localhost:3000")):
                    recent = get_recent_messages(settings.get("bridge_url", "http://localhost:3000"))
                    if isinstance(recent, list):
                        for msg in recent:
                            msg_id = msg.get("id", str(hash(msg.get("body", ""))))
                            if msg_id in processed:
                                continue
                            processed.add(msg_id)
                            
                            sender = msg.get("from", "")
                            body = msg.get("body", "")
                            
                            if not sender or not body:
                                continue
                            
                            # Get website data
                            web_data = None
                            if settings.get("website_url"):
                                web_data = scrape_website_simple(settings["website_url"])
                            
                            # Generate and send reply
                            reply = generate_ai_reply(body, web_data, settings)
                            send_whatsapp_message(sender, reply, settings.get("bridge_url", "http://localhost:3000"))
                            
                            # Log
                            msgs = load_messages()
                            msgs.append({
                                "sender": sender,
                                "message": body,
                                "reply": reply,
                                "time": time.strftime("%Y-%m-%d %H:%M"),
                                "ai_used": bool(settings.get("ai_api_key")),
                                "direction": "incoming"
                            })
                            save_messages(msgs)
                    
                    # Limit processed set
                    if len(processed) > 500:
                        processed = set(list(processed)[-250:])
            except:
                pass
            time.sleep(5)
    
    # Start background thread
    bg_thread = threading.Thread(target=auto_reply_loop, daemon=True)
    bg_thread.start()


# --- Run ---
if __name__ == "__main__":
    ft.app(target=main)
