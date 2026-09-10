#!/usr/bin/env python3
"""Проверка почты 58 ПСЧ — запускается GitHub Actions"""
import os, re, json, imaplib, email, tempfile, io
from email.header import decode_header
from datetime import datetime
from PIL import Image
import requests

# === CONFIG ===
MAIL_HOST = "imap.mail.ru"
MAIL_USER = "pch-58@mail.ru"
MAIL_PASS = os.environ.get("MAIL_PASS", "")
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "-1004320702729")

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

def tg_send(text, buttons=None):
    data = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    if buttons:
        data["reply_markup"] = json.dumps({"inline_keyboard": buttons})
    try:
        r = requests.post(f"{BASE_URL}/sendMessage", json=data, timeout=30)
        return r.json()
    except: return None

def tg_answer(callback_id, text):
    try:
        requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": callback_id, "text": text}, timeout=10)
    except: pass

def tg_delete(chat_id, msg_id):
    try:
        requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id}, timeout=10)
    except: pass

def tg_pin(chat_id, msg_id):
    try:
        requests.post(f"{BASE_URL}/pinChatMessage", json={"chat_id": chat_id, "message_id": msg_id}, timeout=10)
    except: pass

def decode_str(s):
    if not s: return ""
    parts = decode_header(s)
    r = ""
    for part, charset in parts:
        if isinstance(part, bytes):
            r += part.decode(charset or 'utf-8', errors='replace')
        else:
            r += part
    return r

def ocr_pdf(data):
    try:
        import pymupdf
        doc = pymupdf.open(stream=data, filetype="pdf")
        text = ""
        for page in doc[:3]:
            t = page.get_text().strip()
            if t:
                text += t + "\n"
            else:
                pix = page.get_pixmap(dpi=150)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                try:
                    import pytesseract
                    text += pytesseract.image_to_string(img, lang="rus") + "\n"
                except: pass
        doc.close()
        return re.sub(r'МЧС РОССИИ.*?Башкортостан', '', text, flags=re.DOTALL).strip()
    except: return ""

def classify(subj, text):
    c = (subj + " " + text).lower()[:200]
    if "рапорт" in c or "рапорт" in c: return "Кадры/Рапорты"
    if "протокол приема зачета" in c: return "Кадры/Протоколы зачетов"
    if "протокол" in c[:200]: return "Протоколы"
    if "договор" in c: return "Договоры"
    if "служебная записка" in c or "сз-" in c: return "Служебные записки"
    if "табель" in c: return "Отчёты/Табели учёта"
    if "заболеваем" in c: return "Отчёты/Заболеваемость"
    if "приказ" in c[:200]: return "Приказы"
    if "спт" in c or "подготовк" in c or "пту" in c: return "Обучение"
    if "сведени" in c or "отчет" in c or "отчёт" in c: return "Отчёты/Прочие"
    return "Указания"

def process_callbacks():
    try:
        r = requests.get(f"{BASE_URL}/getUpdates", timeout=25)
        updates = r.json()
    except: return
    
    for u in updates.get("result", []):
        if "callback_query" not in u: continue
        cb = u["callback_query"]
        action = cb["data"]
        msg = cb.get("message", {})
        msg_id = msg.get("message_id", 0)
        chat_id = str(msg.get("chat", {}).get("id", CHAT_ID))
        msg_text = msg.get("text", "")[:200]
        
        if action == "archive":
            tg_answer(cb["id"], "✅ В архиве")
        elif action == "important":
            tg_answer(cb["id"], "⭐ Закреплено!")
            tg_pin(chat_id, msg_id)
        elif action == "schedule":
            tg_answer(cb["id"], "📅 В расписании")
        elif action == "remind":
            tg_answer(cb["id"], "🔔 Буду напоминать")
        elif action == "report":
            tg_answer(cb["id"], "📊 Ищу данные...")
        elif action == "search":
            tg_answer(cb["id"], "🔍 Ищу похожие...")
        elif action == "ignore":
            tg_answer(cb["id"], "❌ Удалено")
            tg_delete(chat_id, msg_id)
        else:
            tg_answer(cb["id"], f"✅ {action}")

def main():
    print(f"🔍 Проверка почты {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    
    # Connect to mail
    mail = imaplib.IMAP4_SSL(MAIL_HOST, 993, timeout=30)
    mail.login(MAIL_USER, MAIL_PASS)
    mail.select("INBOX")
    
    status, ids = mail.search(None, "UNSEEN")
    unseen = ids[0].split() if ids[0] else []
    print(f"Непрочитанных: {len(unseen)}")
    
    for mid in unseen[:5]:
        status, data = mail.fetch(mid, "(RFC822)")
        if status != "OK": continue
        msg = email.message_from_bytes(data[0][1])
        
        subject = decode_str(msg["Subject"] or "")
        from_ = decode_str(msg["From"] or "")
        print(f"\n📧 {subject[:60]}")
        
        doc_text = ""
        for part in msg.walk():
            if part.get_content_maintype() == "multipart": continue
            if part.get("Content-Disposition") is None: continue
            fn = part.get_filename()
            if not fn: continue
            fname = decode_str(fn)
            payload = part.get_payload(decode=True)
            if not payload: continue
            
            _, ext = os.path.splitext(fname)
            if ext.lower() == ".pdf":
                doc_text = ocr_pdf(payload)
            elif ext.lower() == ".docx":
                try:
                    import docx
                    d = docx.Document(io.BytesIO(payload))
                    doc_text = " ".join([p.text for p in d.paragraphs[:15]])
                except: pass
        
        doc_text = re.sub(r'МЧС РОССИИ.*?Башкортостан', '', doc_text, flags=re.DOTALL).strip()
        cat = classify(subject, doc_text)
        
        msg_text = (
            f"📩 **Новый документ**\n\n"
            f"**Категория:** {cat}\n"
            f"**Документ:** {subject[:80]}\n"
            f"**От:** {from_[:50]}\n"
            f"**Суть:** {doc_text[:200]}\n"
            f"**Сохранён:** {cat}"
        )
        
        buttons = [
            [{"text": "✅ Архив", "callback_data": "archive"}, {"text": "⭐ Важное", "callback_data": "important"}],
            [{"text": "📅 Расписание", "callback_data": "schedule"}, {"text": "🔔 Напомнить", "callback_data": "remind"}],
            [{"text": "📊 Отчёт", "callback_data": "report"}, {"text": "🔍 Поиск", "callback_data": "search"}],
            [{"text": "❌ Удалить", "callback_data": "ignore"}],
        ]
        
        result = tg_send(msg_text, buttons)
        if result and result.get("ok"):
            print(f"  ✅ Пост отправлен")
        else:
            print(f"  ❌ Ошибка: {result}")
    
    mail.logout()
    
    # Always send test message on manual run
    try:
        r = requests.post(f"{BASE_URL}/sendMessage", json={
            "chat_id": CHAT_ID,
            "text": "✅ GitHub Actions: проверка почты работает!"
        }, timeout=15)
        if r.json().get("ok"):
            print("✅ Тестовое сообщение отправлено")
        else:
            print(f"❌ Ошибка TG: {r.json()}")
    except Exception as e:
        print(f"❌ Ошибка соединения: {e}")
    
    # Process callbacks
    process_callbacks()
    print("\n✅ Готово")

if __name__ == "__main__":
    main()