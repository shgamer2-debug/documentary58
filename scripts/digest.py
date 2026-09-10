#!/usr/bin/env python3
"""Утренний дайджест 58 ПСЧ"""
import os, json, imaplib, email, io, requests
from email.header import decode_header
from datetime import datetime

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "-1004320702729")
MAIL_PASS = os.environ.get("MAIL_PASS", "")
MAIL_HOST = "imap.mail.ru"
MAIL_USER = "pch-58@mail.ru"
BASE = f"https://api.telegram.org/bot{TOKEN}"

def send(text):
    r = requests.post(f"{BASE}/sendMessage", json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=30)
    ok = r.json().get("ok", False)
    print(f"{'✅' if ok else '❌'} Digest: {r.json().get('description', 'sent')}")
    return ok

def decode(s):
    parts = decode_header(s or "")
    r = ""
    for p, c in parts:
        if isinstance(p, bytes): r += p.decode(c or "utf-8", errors="replace")
        else: r += p
    return r

def main():
    today = datetime.now()
    date_str = today.strftime("%d.%m.%Y")
    
    # Shift calc
    start = datetime(2026, 9, 9)
    days = (today - start).days
    shift_on = ((3 - 1 + days) % 4) + 1
    shift_off = ((shift_on - 2) % 4) + 1
    
    # Sick data
    sick = ""
    try:
        mail = imaplib.IMAP4_SSL(MAIL_HOST, 993, timeout=20)
        mail.login(MAIL_USER, MAIL_PASS)
        mail.select("INBOX")
        s, ids = mail.search(None, "ALL")
        all_ids = ids[0].split() if ids[0] else []
        for mid in all_ids[-3:]:
            s, d = mail.fetch(mid, "(RFC822)")
            if s != "OK": continue
            msg = email.message_from_bytes(d[0][1])
            for part in msg.walk():
                if part.get_content_maintype() == "multipart": continue
                if part.get("Content-Disposition") is None: continue
                fn = part.get_filename()
                if not fn: continue
                fn = decode(fn)
                if "заболев" in fn.lower():
                    p = part.get_payload(decode=True)
                    import docx
                    doc = docx.Document(io.BytesIO(p))
                    for table in doc.tables[:2]:
                        for row in table.rows[1:]:
                            cells = [c.text.strip().replace('\n',' ') for c in row.cells]
                            if cells[0] and cells[0][0].isdigit():
                                n = cells[3][:25] if len(cells)>3 else ""
                                dg = cells[6][:20] if len(cells)>6 else ""
                                sd = cells[4][:12] if len(cells)>4 else ""
                                ed = cells[5][:12] if len(cells)>5 else ""
                                sick += f"- {n} — {dg}, с {sd} на приём {ed}\n"
                    break
            break
        mail.logout()
    except Exception as e:
        sick = f"(ошибка получения данных)"
    
    if not sick.strip():
        sick = "- Данные не получены"
    
    # Weather
    weather = "—"
    try:
        r = requests.get("https://wttr.in/Kumertau?format=%C+%t&lang=ru", timeout=10)
        if r.status_code == 200: weather = r.text.strip()
    except: pass
    
    # Currency
    usd, cny = "?", "?"
    try:
        r = requests.get("https://www.cbr-xml-daily.ru/latest.js", timeout=10)
        if r.status_code == 200:
            d = r.json()
            if 'USD' in d.get('rates',{}): usd = str(round(1/d['rates']['USD'], 2))
            if 'CNY' in d.get('rates',{}): cny = str(round(1/d['rates']['CNY'], 2))
    except: pass
    
    msg = (
        f"Сегодня {date_str}. На смене {shift_on} караул (сменяет {shift_off}).\n\n"
        f"На больничном:\n{sick}\n\n"
        f"На контроле:\n"
        f"- нет активных задач\n\n"
        f"На развод:\n"
        f"проверить готовность техники, инструктаж по ПДД, "
        f"смотр-конкурс по ОТ — подготовка\n\n"
        f"Погода: {weather}\n"
        f"Доллар: {usd}, Юань: {cny}"
    )
    
    send(msg)

if __name__ == "__main__":
    main()