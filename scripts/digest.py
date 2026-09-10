#!/usr/bin/env python3
"""Утренний дайджест 58 ПСЧ"""
import os, re, json, imaplib, email, io
from email.header import decode_header
from datetime import datetime
import requests

MAIL_HOST = "imap.mail.ru"
MAIL_USER = "pch-58@mail.ru"
MAIL_PASS = os.environ.get("MAIL_PASS", "")
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "-1004320702729")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

def decode_str(s):
    if not s: return ""
    r = ""
    for part, ch in decode_header(s):
        if isinstance(part, bytes): r += part.decode(ch or 'utf-8', errors='replace')
        else: r += part
    return r

def main():
    today = datetime.now()
    date_str = today.strftime("%d.%m.%Y")
    
    # Shift calculation (09.09.2026 = shift 3)
    start = datetime(2026, 9, 9)
    days = (today - start).days
    shift_on = ((3 - 1 + days) % 4) + 1
    shift_off = ((shift_on - 2) % 4) + 1
    
    # Get sick data from email
    sick_lines = []
    try:
        mail = imaplib.IMAP4_SSL(MAIL_HOST, 993, timeout=30)
        mail.login(MAIL_USER, MAIL_PASS)
        mail.select("INBOX")
        status, ids = mail.search(None, "ALL")
        all_ids = ids[0].split() if ids[0] else []
        
        for mid in all_ids[-3:]:
            status, data = mail.fetch(mid, "(RFC822)")
            if status != "OK": continue
            msg = email.message_from_bytes(data[0][1])
            for part in msg.walk():
                if part.get_content_maintype() == "multipart": continue
                if part.get("Content-Disposition") is None: continue
                fn = part.get_filename()
                if not fn: continue
                fname = decode_str(fn)
                if "заболев" in fname.lower():
                    payload = part.get_payload(decode=True)
                    import docx
                    d = docx.Document(io.BytesIO(payload))
                    for table in d.tables[:2]:
                        for row in table.rows[1:]:
                            cells = [c.text.strip().replace('\n', ' ') for c in row.cells]
                            if cells[0] and cells[0][0].isdigit():
                                name = cells[3] if len(cells) > 3 else ""
                                diag = cells[6] if len(cells) > 6 else ""
                                start_d = cells[4] if len(cells) > 4 else ""
                                end_d = cells[5] if len(cells) > 5 else ""
                                sick_lines.append(f"- {name[:25]} — {diag[:20]}, с {start_d[:12]} на приём {end_d[:12]}")
                    break
            break
        mail.logout()
    except Exception as e:
        sick_lines.append(f"(ошибка: {e})")
    
    sick_text = "\n".join(sick_lines) if sick_lines else "- Данные не получены"
    
    # Weather
    weather = "Нет данных"
    try:
        r = requests.get("https://wttr.in/Kumertau?format=%C+%t&lang=ru", timeout=10)
        if r.status_code == 200:
            weather = r.text.strip()
    except: pass
    
    # Currency
    usd = "?"
    cny = "?"
    try:
        r = requests.get("https://www.cbr-xml-daily.ru/latest.js", timeout=10)
        if r.status_code == 200:
            data = r.json()
            usd = str(round(1 / data['rates']['USD'], 2)) if 'USD' in data['rates'] else "?"
            cny = str(round(1 / data['rates']['CNY'], 2)) if 'CNY' in data['rates'] else "?"
    except: pass
    
    msg = (
        f"Сегодня {date_str}. На смене {shift_on} караул (сменяет {shift_off}).\n\n"
        f"На больничном:\n{sick_text}\n\n"
        f"На контроле:\n- (из docs_db.json при следующей реализации)\n\n"
        f"На развод:\n"
        f"проверить готовность техники, инструктаж по ПДД, "
        f"смотр-конкурс по ОТ — подготовка\n\n"
        f"Погода: {weather}\n"
        f"Доллар: {usd}, Юань: {cny}"
    )
    
    r = requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": CHAT_ID, "text": msg}, timeout=30)
    if r.json().get("ok"):
        print("✅ Дайджест отправлен!")
    else:
        print(f"❌ Ошибка: {r.json()}")

if __name__ == "__main__":
    main()