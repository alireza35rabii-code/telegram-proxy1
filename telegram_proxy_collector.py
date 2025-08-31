import os, re, requests, concurrent.futures

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# منابع SOCKS5 (می‌تونی بعداً زیادشون کنی)
SOURCES = [
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://www.proxy-list.download/api/v1/get?type=socks5",
]

def fetch_source(url):
    try:
        r = requests.get(url, timeout=12)
        if r.ok:
            return r.text
    except Exception:
        pass
    return ""

def collect_proxies():
    combined = "\n".join(fetch_source(u) for u in SOURCES)
    # ip:port
    found = set()
    for ip, port in re.findall(r"(\d+\.\d+\.\d+\.\d+):(\d+)", combined):
        p = int(port)
        if 1 <= p <= 65535:
            found.add(f"{ip}:{p}")
    return list(found)

def is_alive_socks5(proxy, timeout=6):
    """تست واقعی از طریق SOCKS5 برای دسترسی به api.telegram.org"""
    try:
        proxies = {
            "http":  f"socks5h://{proxy}",
            "https": f"socks5h://{proxy}",
        }
        # توکن جعلی؛ اگر reachable باشد معمولاً 401/404 برمی‌گردد (<=499 را موفق می‌گیریم)
        resp = requests.get(
            "https://api.telegram.org/botINVALIDTOKEN/getMe",
            proxies=proxies,
            timeout=timeout,
        )
        return resp.status_code < 500
    except Exception:
        return False

def send_to_telegram(lines):
    if not BOT_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    # پیام‌ها را تیکه‌تیکه بفرست تا طول پیام زیاد نشود
    chunk = []
    total = 0
    for p in lines:
        chunk.append(p)
        # حدوداً 50 خطی بفرست
        if len(chunk) >= 50:
            requests.post(url, data={"chat_id": CHAT_ID, "text": "\n".join(chunk)})
            total += len(chunk)
            chunk = []
    if chunk:
        requests.post(url, data={"chat_id": CHAT_ID, "text": "\n".join(chunk)})
        total += len(chunk)
    # گزارش تعداد
    requests.post(url, data={"chat_id": CHAT_ID, "text": f"✅ {total} پروکسی سالم ارسال شد."})

def main():
    candidates = collect_proxies()
    if not candidates:
        if BOT_TOKEN and CHAT_ID:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                data={"chat_id": CHAT_ID, "text": "❌ پروکسی‌ای پیدا نشد."},
            )
        return

    alive = []
    # تست موازی با ThreadPool (سریع‌تر)
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as ex:
        for proxy, ok in zip(candidates, ex.map(is_alive_socks5, candidates)):
            if ok:
                alive.append(proxy)

    if alive:
        send_to_telegram(alive)
    else:
        if BOT_TOKEN and CHAT_ID:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                data={"chat_id": CHAT_ID, "text": "❌ پروکسی سالم پیدا نشد."},
            )

if __name__ == "__main__":
    main()
