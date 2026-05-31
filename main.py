# WhatsApp Assistant - Python source (keep as-is)
# This is the main app entry point for buildozer/p4a

import json
import os
import threading
import time
import requests

# Simple Kivy-based UI for Android APK
import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.utils import platform

Window.clearcolor = (0.06, 0.08, 0.1, 1)

CONFIG_DIR = "/data/data/com.termux/files/home" if platform == "android" else "."
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
        r = requests.post(f"{bridge_url}/send", json={"chatId": to, "message": message}, timeout=10)
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
    prompt = f"You are {bot_name}, a helpful WhatsApp assistant. Tone: {tone}. Reply in the SAME language as the customer. Keep reply concise (under 300 words). Never mention being an AI. Be warm and professional."
    if website_data:
        prompt += f"\n\nBusiness Info:\n{website_data}"
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": message}], "max_tokens": 500, "temperature": 0.7},
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
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            import re
            text = re.sub(r'<[^>]+>', ' ', r.text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:3000]
    except:
        pass
    return None

class DashboardTab(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = "vertical"
        self.padding = 10
        self.spacing = 8

        self.add_widget(Label(text="Maya Assistant", font_size=24, size_hint_y=0.1, color=(0.11, 0.6, 0.94, 1)))

        status_box = BoxLayout(size_hint_y=0.1)
        self.status_label = Label(text="● Disconnected", color=(0.96, 0.13, 0.18, 1), font_size=14)
        status_box.add_widget(self.status_label)
        self.add_widget(status_box)

        # Stats
        stats = GridLayout(cols=2, size_hint_y=0.2, spacing=5)
        self.stat_messages = Label(text="Messages: 0", font_size=13)
        self.stat_contacts = Label(text="Contacts: 0", font_size=13)
        self.stat_ai = Label(text="AI Replies: 0", font_size=13)
        self.stat_today = Label(text="Today: 0", font_size=13)
        stats.add_widget(self.stat_messages)
        stats.add_widget(self.stat_contacts)
        stats.add_widget(self.stat_ai)
        stats.add_widget(self.stat_today)
        self.add_widget(stats)

        self.add_widget(Label(text="Auto Reply", font_size=14, size_hint_y=0.05))
        self.auto_switch = Button(text="Auto Reply: ON", background_color=(0.11, 0.6, 0.94, 1), size_hint_y=0.08)
        self.auto_switch.bind(on_press=self.toggle_auto)
        self.auto_switch.state = "down"
        self.add_widget(self.auto_switch)

        btn_box = BoxLayout(size_hint_y=0.1, spacing=5)
        refresh_btn = Button(text="Refresh", background_color=(0, 0.73, 0.49, 1))
        refresh_btn.bind(on_press=self.refresh)
        scrape_btn = Button(text="Scrape Website", background_color=(0.49, 0.23, 0.93, 1))
        scrape_btn.bind(on_press=self.scrape_now)
        btn_box.add_widget(refresh_btn)
        btn_box.add_widget(scrape_btn)
        self.add_widget(btn_box)

        self.msg_label = Label(text="Recent activity will appear here...", font_size=12, size_hint_y=0.3, color=(0.55, 0.6, 0.65, 1), halign="center", valign="top")
        self.msg_label.bind(size=self.msg_label.setter("text_size"))
        self.add_widget(self.msg_label)
        Clock.schedule_interval(self.auto_refresh, 10)

    def toggle_auto(self, instance):
        if instance.state == "down":
            instance.text = "Auto Reply: ON"
            instance.background_color = (0.11, 0.6, 0.94, 1)
        else:
            instance.text = "Auto Reply: OFF"
            instance.background_color = (0.5, 0.5, 0.5, 1)

    def refresh(self, instance=None):
        cfg = load_config()
        if check_bridge(cfg.get("bridge_url", "http://localhost:3000")):
            self.status_label.text = "● Connected"
            self.status_label.color = (0, 0.73, 0.49, 1)
        else:
            self.status_label.text = "● Disconnected"
            self.status_label.color = (0.96, 0.13, 0.18, 1)

    def scrape_now(self, instance):
        cfg = load_config()
        url = cfg.get("website_url", "")
        if url:
            data = scrape_website(url)
            self.msg_label.text = f"Scraped {len(data) if data else 0} chars from {url}"
        else:
            self.msg_label.text = "Set website URL in Settings first"

    def auto_refresh(self, dt):
        if self.auto_switch.state == "down":
            self.refresh()

class SettingsTab(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = "vertical"
        self.padding = 10
        self.spacing = 6
        cfg = load_config()

        self.add_widget(Label(text="AI Settings", font_size=16, size_hint_y=0.06, color=(0.11, 0.6, 0.94, 1)))

        self.add_widget(Label(text="API Key:", font_size=13, size_hint_y=0.04))
        self.api_key = TextInput(text=cfg.get("ai_api_key", ""), password=True, multiline=False, size_hint_y=0.07)
        self.add_widget(self.api_key)

        self.add_widget(Label(text="Model:", font_size=13, size_hint_y=0.04))
        self.model = TextInput(text=cfg.get("ai_model", "google/gemini-2.0-flash-free"), multiline=False, size_hint_y=0.07)
        self.add_widget(self.model)

        self.add_widget(Label(text="Website URL:", font_size=13, size_hint_y=0.04))
        self.website = TextInput(text=cfg.get("website_url", ""), multiline=False, size_hint_y=0.07)
        self.add_widget(self.website)

        self.add_widget(Label(text="Backend API:", font_size=13, size_hint_y=0.04))
        self.backend = TextInput(text=cfg.get("backend_api", ""), multiline=False, size_hint_y=0.07)
        self.add_widget(self.backend)

        self.add_widget(Label(text="Bot Name:", font_size=13, size_hint_y=0.04))
        self.bot_name = TextInput(text=cfg.get("bot_name", "Maya"), multiline=False, size_hint_y=0.07)
        self.add_widget(self.bot_name)

        self.add_widget(Label(text="Bridge URL:", font_size=13, size_hint_y=0.04))
        self.bridge = TextInput(text=cfg.get("bridge_url", "http://localhost:3000"), multiline=False, size_hint_y=0.07)
        self.add_widget(self.bridge)

        btn_box = BoxLayout(size_hint_y=0.1, spacing=8)
        save_btn = Button(text="Save Settings", background_color=(0.11, 0.6, 0.94, 1))
        save_btn.bind(on_press=self.save)
        test_btn = Button(text="Test API", background_color=(0.49, 0.23, 0.93, 1))
        test_btn.bind(on_press=self.test_api)
        btn_box.add_widget(save_btn)
        btn_box.add_widget(test_btn)
        self.add_widget(btn_box)

        self.result_label = Label(text="", font_size=12, size_hint_y=0.08, color=(0, 0.73, 0.49, 1))
        self.add_widget(self.result_label)

    def save(self, instance):
        cfg = load_config()
        cfg["ai_api_key"] = self.api_key.text
        cfg["ai_model"] = self.model.text
        cfg["website_url"] = self.website.text
        cfg["backend_api"] = self.backend.text
        cfg["bot_name"] = self.bot_name.text
        cfg["bridge_url"] = self.bridge.text
        save_config(cfg)
        self.result_label.text = "Saved!"
        self.result_label.color = (0, 0.73, 0.49, 1)

    def test_api(self, instance):
        key = self.api_key.text.strip()
        if not key:
            self.result_label.text = "Enter API key first"
            self.result_label.color = (0.96, 0.13, 0.18, 1)
            return
        self.result_label.text = "Testing..."
        self.result_label.color = (0.55, 0.6, 0.65, 1)
        def test():
            try:
                r = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model": self.model.text or "google/gemini-2.0-flash-free", "messages": [{"role": "user", "content": "Say hi"}], "max_tokens": 50},
                    timeout=15
                )
                if r.status_code == 200:
                    Clock.schedule_once(lambda dt: setattr(self.result_label, "text", "API working!"))
                    Clock.schedule_once(lambda dt: setattr(self.result_label, "color", (0, 0.73, 0.49, 1)))
                else:
                    Clock.schedule_once(lambda dt: setattr(self.result_label, "text", f"Error: {r.status_code}"))
                    Clock.schedule_once(lambda dt: setattr(self.result_label, "color", (0.96, 0.13, 0.18, 1)))
            except Exception as e:
                Clock.schedule_once(lambda dt: setattr(self.result_label, "text", f"Failed: {str(e)[:40]}"))
                Clock.schedule_once(lambda dt: setattr(self.result_label, "color", (0.96, 0.13, 0.18, 1)))
        threading.Thread(target=test, daemon=True).start()

class MayaApp(App):
    def build(self):
        self.title = "Maya Assistant"
        tabs = TabbedPanel(do_default_tab=False, background_color=(0.06, 0.08, 0.1, 1))

        dash_tab = TabbedPanelItem(text="Dashboard")
        dash_tab.add_widget(DashboardTab(self))
        tabs.add_widget(dash_tab)

        settings_tab = TabbedPanelItem(text="Settings")
        settings_tab.add_widget(SettingsTab(self))
        tabs.add_widget(settings_tab)

        return tabs

if __name__ == "__main__":
    MayaApp().run()
