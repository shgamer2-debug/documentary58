#!/usr/bin/env python3
"""Напоминания 58 ПСЧ"""
import os, requests
from datetime import datetime

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "-1004320702729")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

hour = datetime.now().hour
if hour == 8:
    msg = "🔔 **Доброе утро!** Напоминаю о задачах на сегодня:\n- Проверить сроки исполнения документов\n- Подготовить смену"
elif hour == 12:
    msg = "🔔 **Обеденное напоминание:**\nНе забудьте про контроль исполнения указаний."
else:
    msg = "🔔 **Вечернее напоминание:**\nПроверьте что задачи на сегодня выполнены."

r = requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=30)
print("✅ OK" if r.json().get("ok") else f"❌ {r.json()}")