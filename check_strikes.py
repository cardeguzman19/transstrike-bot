# check_strikes.py
# Requirements: requests, beautifulsoup4
# Save seen URLs to seen.txt (created automatically)

import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# CONFIG (use environment variables in GitHub Actions)
TELEGRAM_TOKEN = os.getenv("8289486284:AAF9kdkEhK1wS1e0CS3dR3vQKLLQSeLD5cs")
TELEGRAM_CHAT_ID = os.getenv("7135433123")
BASE = "https://newsinfo.inquirer.net"

KEYWORDS = ["strike", "transport", "transpo", "piston", "manibela", "jeepney", "bus", "drivers", "operators", "nationwide"]
NCR_CITIES = [
    "Manila","Quezon City","Caloocan","Las Piñas","Makati","Malabon","Mandaluyong",
    "Marikina","Muntinlupa","Navotas","Parañaque","Pasay","Pasig","San Juan","Taguig",
    "Valenzuela","Pateros"
]

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
SEEN_FILE = "seen.txt"

def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        for u in sorted(seen):
            f.write(u + "\n")

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID in env")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode":"HTML", "disable_web_page_preview": False}
    r = requests.post(url, data=payload, timeout=20)
    return r.ok

def fetch_page(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print("fetch error:", e)
        return ""

def find_articles_on_pages():
    paths = ["", "/category/latest-stories", "/category/inquirer-headlines"]
    urls = [BASE + p for p in paths]
    found = set()
    for u in urls:
        html = fetch_page(u)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/"):
                href = BASE + href
            # basic article heuristics
            if href.startswith(BASE) and ("/news" in href or "/210" in href or "/20" in href):
                found.add(href.split("?")[0])
    return found

def article_matches(html_text):
    txt = html_text.lower()
    if not any(k.lower() in txt for k in KEYWORDS):
        return False
    if "metro manila" in txt or "ncr" in txt:
        return True
    if any(city.lower() in txt for city in NCR_CITIES):
        return True
    return False

def extract_title(soup):
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    if soup.title:
        return soup.title.get_text(strip=True)
    return "No title found"

def main():
    seen = load_seen()
    urls = find_articles_on_pages()
    new_found = []
    for u in sorted(urls):
        if u in seen:
            continue
        html = fetch_page(u)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        page_text = soup.get_text(separator=" ", strip=True)
        if article_matches(page_text):
            title = extract_title(soup)
            pub = ""
            time_tag = soup.find("time")
            if time_tag and time_tag.get("datetime"):
                pub = time_tag.get("datetime")
            message = f"⚠️ <b>{title}</b>\n\n{u}\n\nFound: {datetime.utcnow().isoformat()} UTC"
            if pub:
                message += f"\nPublished: {pub}"
            ok = send_telegram(message)
            print("Sent:", ok, title)
            new_found.append(u)
        seen.add(u)
    save_seen(seen)
    if not new_found:
        print("No new matching articles found.")

if __name__ == "__main__":
    main()
