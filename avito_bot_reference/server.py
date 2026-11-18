import json
import logging
import os
import signal
import subprocess
import sys
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
TASKS_FILE = os.path.join(BASE_DIR, "tasks.json")
DEALS_FILE = os.path.join(BASE_DIR, "deals.json")
ITEMS_STORE_FILE = os.path.join(BASE_DIR, "items_store.json")
PRICE_CACHE_FILE = os.path.join(BASE_DIR, "price_cache.json")
FAVORITES_FILE = os.path.join(BASE_DIR, "favorites.json")
BLACKLIST_FILE = os.path.join(BASE_DIR, "blacklist.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
PROXIES_FILE = os.path.join(BASE_DIR, "proxies.txt")
LOG_FILE = os.path.join(BASE_DIR, "bot.log")
WORKER_SCRIPT = os.path.join(BASE_DIR, "worker.py")
VENV_PYTHON = os.path.join(BASE_DIR, "venv", "bin", "python3")
PYTHON_BIN = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable

logging.basicConfig(level=logging.INFO, format="%(asctime)s [HOST] %(message)s")

worker_proc = None
worker_start_time = None
last_scan_time = None

def load_json(filepath, default):
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading {filepath}: {e}")
        return default

def save_json(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"Error saving {filepath}: {e}")
        return False

def append_log(message):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            t = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"{t} [SERVER] {message}\n")
    except Exception:
        pass

def is_worker_running():
    global worker_proc
    if worker_proc is None:
        return False
    ret = worker_proc.poll()
    return ret is None

def start_worker():
    global worker_proc, worker_start_time
    if is_worker_running():
        return False, "Воркер уже работает"

    cmd = [PYTHON_BIN, WORKER_SCRIPT]
    try:
        log_f = open(LOG_FILE, "a", encoding="utf-8")
        worker_proc = subprocess.Popen(cmd, cwd=BASE_DIR, stdout=log_f, stderr=subprocess.STDOUT)
        worker_start_time = time.time()
        append_log(f"Фоновый парсер запущен (PID {worker_proc.pid})")
        return True, f"Запущен (PID {worker_proc.pid})"
    except Exception as e:
        append_log(f"Ошибка запуска воркера: {e}")
        return False, f"Ошибка запуска: {e}"

def stop_worker():
    global worker_proc, worker_start_time
    if not is_worker_running():
        return False, "Воркер не был запущен"

    try:
        worker_proc.terminate()
        try:
            worker_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            worker_proc.kill()
    except Exception as e:
        append_log(f"Ошибка остановки: {e}")

    try:
        res = subprocess.run(["pgrep", "-f", "worker.py"], capture_output=True, text=True)
        for line in res.stdout.strip().splitlines():
            pid = int(line.strip())
            if pid != os.getpid():
                os.kill(pid, signal.SIGKILL)
    except Exception:
        pass
    
    worker_proc = None
    worker_start_time = None
    append_log(f"Фоновый парсер остановлен")
    return True, "Воркер успешно остановлен"

class AvitoBotHostHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.OK)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def send_json(self, data, status=HTTPStatus.OK):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def read_post_json(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/"):
            return self.handle_api_get(path, parse_qs(parsed.query))

        if path == "/" or not os.path.exists(os.path.join(WEB_DIR, path.lstrip("/"))):
            self.path = "/index.html"
            return super().do_GET()

        return super().do_GET()

    def handle_api_get(self, path, query):
        global worker_proc, worker_start_time

        if path == "/api/status":
            running = is_worker_running()
            uptime_str = ""
            if running and worker_start_time:
                s = int(time.time() - worker_start_time)
                uptime_str = f"{s // 60}м {s % 60}с"
            
            tasks = load_json(TASKS_FILE, [])
            deals = load_json(DEALS_FILE, [])
            favs = load_json(FAVORITES_FILE, [])
            b_list = load_json(BLACKLIST_FILE, [])
            items_store = load_json(ITEMS_STORE_FILE, {})
            total_items = sum(len(v) for v in items_store.values()) if isinstance(items_store, dict) else 0

            return self.send_json({
                "running": running,
                "pid": worker_proc.pid if running else None,
                "uptime": uptime_str,
                "tasks_count": len(tasks),
                "deals_count": len(deals),
                "ads_count": total_items,
                "favorites_count": len(favs),
                "blacklist_count": len(b_list),
                "items_count": total_items,
                "last_scan": time.strftime("%H:%M:%S")
            })

        elif path == "/api/tasks":
            tasks = load_json(TASKS_FILE, [])
            return self.send_json(tasks)

        elif path == "/api/deals":
            deals = load_json(DEALS_FILE, [])
            return self.send_json(deals)

        elif path in ("/api/ads", "/api/items/flat"):
            store = load_json(ITEMS_STORE_FILE, {})
            all_ads = []
            seen_ids = set()
            for t_name, it_list in store.items():
                if isinstance(it_list, list):
                    for it in it_list:
                        iid = str(it.get("id"))
                        if iid and iid not in seen_ids:
                            seen_ids.add(iid)
                            item_copy = dict(it)
                            if "task_name" not in item_copy:
                                item_copy["task_name"] = t_name
                            all_ads.append(item_copy)
            all_ads.sort(key=lambda x: (x.get("profit", 0) > 0, x.get("profit", 0), x.get("id", "")), reverse=True)
            return self.send_json(all_ads)

        elif path == "/api/favorites":
            favs = load_json(FAVORITES_FILE, [])
            return self.send_json(favs)

        elif path == "/api/blacklist":
            b_list = load_json(BLACKLIST_FILE, [])
            return self.send_json(b_list)

        elif path == "/api/proxies":
            proxies_list = []
            if os.path.exists(PROXIES_FILE):
                try:
                    with open(PROXIES_FILE, "r", encoding="utf-8") as f:
                        proxies_list = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
                except Exception:
                    pass
            return self.send_json({"proxies": proxies_list})

        elif path == "/api/items":
            items = load_json(ITEMS_STORE_FILE, {})
            return self.send_json(items)

        elif path == "/api/logs":
            lines_to_read = 150
            if os.path.exists(LOG_FILE):
                try:
                    with open(LOG_FILE, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        return self.send_json({"logs": lines[-lines_to_read:]})
                except Exception as e:
                    return self.send_json({"logs": [f"Ошибка чтения логов: {e}"]})
            return self.send_json({"logs": ["Логов пока нет. Запустите воркер или выполните сканирование."]})

        elif path == "/api/settings":
            cfg = load_json(SETTINGS_FILE, {})
            bot_token = cfg.get("bot_token")
            chat_id = cfg.get("chat_id")
            
            # Fallback to reading from worker.py if not in settings.json
            if not bot_token and os.path.exists(WORKER_SCRIPT):
                with open(WORKER_SCRIPT, "r", encoding="utf-8") as f:
                    content = f.read()
                    import re
                    m_token = re.search(r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']', content)
                    if m_token: bot_token = m_token.group(1)
                    m_chat = re.search(r'CHAT_ID\s*=\s*([0-9\-]+)', content)
                    if m_chat: chat_id = m_chat.group(1)

            proxies_count = 0
            if os.path.exists(PROXIES_FILE):
                try:
                    with open(PROXIES_FILE, "r", encoding="utf-8") as pf:
                        proxies_count = len([l for l in pf if l.strip() and not l.strip().startswith("#")])
                except Exception: pass

            return self.send_json({
                "bot_token": bot_token or "",
                "chat_id": chat_id or "",
                "thread_id": cfg.get("thread_id", ""),
                "filter_defects": cfg.get("filter_defects", True),
                "send_photos": cfg.get("send_photos", True),
                "scan_interval": cfg.get("scan_interval", 12),
                "profit_threshold": cfg.get("profit_threshold", 6),
                "proxies_count": proxies_count
            })

        self.send_json({"error": "Endpoint not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/"):
            return self.handle_api_post(path)

        self.send_json({"error": "Endpoint not found"}, HTTPStatus.NOT_FOUND)

    def handle_api_post(self, path):
        data = self.read_post_json()

        if path == "/api/worker/start":
            success, msg = start_worker()
            return self.send_json({"success": success, "message": msg})

        elif path == "/api/worker/stop":
            success, msg = stop_worker()
            return self.send_json({"success": success, "message": msg})

        elif path == "/api/worker/run-once":
            append_log("Запрос ручного сканирования через панель")
            try:
                cmd = [PYTHON_BIN, WORKER_SCRIPT, "--once"]
                log_f = open(LOG_FILE, "a", encoding="utf-8")
                proc = subprocess.Popen(cmd, cwd=BASE_DIR, stdout=log_f, stderr=subprocess.STDOUT)
                return self.send_json({"success": True, "message": "Сканирование запущено в фоне", "pid": proc.pid})
            except Exception as e:
                return self.send_json({"success": False, "error": str(e)})

        elif path == "/api/tasks":
            tasks = load_json(TASKS_FILE, [])
            new_task = data
            if not new_task.get("id"):
                import uuid
                new_task["id"] = f"task_{uuid.uuid4().hex[:8]}"
            if not new_task.get("title"):
                new_task["title"] = f"{new_task.get('model', 'Товар')} ({new_task.get('city', 'Город')})"
            
            existing_idx = next((i for i, t in enumerate(tasks) if t.get("id") == new_task["id"]), None)
            if existing_idx is not None:
                tasks[existing_idx] = new_task
            else:
                tasks.append(new_task)

            save_json(TASKS_FILE, tasks)
            append_log(f"Задача сохранена: {new_task['title']}")
            return self.send_json({"success": True, "task": new_task, "tasks": tasks})

        elif path == "/api/deals/delete":
            deal_id = str(data.get("id"))
            deals = load_json(DEALS_FILE, [])
            deals = [d for d in deals if str(d.get("id")) != deal_id]
            save_json(DEALS_FILE, deals)
            return self.send_json({"success": True, "deals": deals})

        elif path == "/api/deals/clear":
            save_json(DEALS_FILE, [])
            append_log("Список сделок очищен через интерфейс")
            return self.send_json({"success": True})

        elif path == "/api/ads/delete":
            ad_id = str(data.get("id"))
            store = load_json(ITEMS_STORE_FILE, {})
            for t_name in list(store.keys()):
                if isinstance(store[t_name], list):
                    store[t_name] = [it for it in store[t_name] if str(it.get("id")) != ad_id]
            save_json(ITEMS_STORE_FILE, store)
            return self.send_json({"success": True})

        elif path == "/api/ads/clear":
            save_json(ITEMS_STORE_FILE, {})
            append_log("Лента объявлений очищена через панель")
            return self.send_json({"success": True})

        elif path == "/api/favorites":
            favs = load_json(FAVORITES_FILE, [])
            new_fav = data
            if not new_fav.get("id"):
                return self.send_json({"success": False, "error": "ID is required"}, HTTPStatus.BAD_REQUEST)
            
            new_fav["saved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            if "status" not in new_fav:
                new_fav["status"] = "saved"  # saved | inspecting | bought | resold
            if "note" not in new_fav:
                new_fav["note"] = ""

            idx = next((i for i, f in enumerate(favs) if str(f.get("id")) == str(new_fav["id"])), None)
            if idx is not None:
                favs[idx].update(new_fav)
            else:
                favs.insert(0, new_fav)

            save_json(FAVORITES_FILE, favs)
            append_log(f"Товар добавлен/обновлен в Избранном: {new_fav.get('title')}")
            return self.send_json({"success": True, "favorites": favs})

        elif path == "/api/favorites/delete":
            fav_id = str(data.get("id"))
            favs = load_json(FAVORITES_FILE, [])
            favs = [f for f in favs if str(f.get("id")) != fav_id]
            save_json(FAVORITES_FILE, favs)
            append_log(f"Товар удален из Избранного: {fav_id}")
            return self.send_json({"success": True, "favorites": favs})

        elif path == "/api/favorites/status":
            fav_id = str(data.get("id"))
            favs = load_json(FAVORITES_FILE, [])
            idx = next((i for i, f in enumerate(favs) if str(f.get("id")) == fav_id), None)
            if idx is not None:
                if "status" in data: favs[idx]["status"] = data["status"]
                if "note" in data: favs[idx]["note"] = data["note"]
                save_json(FAVORITES_FILE, favs)
                return self.send_json({"success": True, "item": favs[idx]})
            return self.send_json({"success": False, "error": "Not found"}, HTTPStatus.NOT_FOUND)

        elif path == "/api/blacklist":
            b_list = load_json(BLACKLIST_FILE, [])
            entry = data
            entry_id = str(entry.get("id") or entry.get("seller_id") or time.time())
            entry["id"] = entry_id
            entry["added_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

            if not any(str(b.get("id")) == entry_id for b in b_list):
                b_list.insert(0, entry)
                save_json(BLACKLIST_FILE, b_list)
                append_log(f"Добавлено в ЧС: {entry.get('title') or entry_id}")
            return self.send_json({"success": True, "blacklist": b_list})

        elif path == "/api/blacklist/delete":
            bid = str(data.get("id"))
            b_list = load_json(BLACKLIST_FILE, [])
            b_list = [b for b in b_list if str(b.get("id")) != bid]
            save_json(BLACKLIST_FILE, b_list)
            append_log(f"Удалено из ЧС: {bid}")
            return self.send_json({"success": True, "blacklist": b_list})

        elif path == "/api/proxies":
            raw_text = data.get("proxies_text", "")
            lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
            try:
                with open(PROXIES_FILE, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n" if lines else "")
                append_log(f"Сохранен список прокси: {len(lines)} шт.")
                return self.send_json({"success": True, "count": len(lines)})
            except Exception as e:
                return self.send_json({"success": False, "error": str(e)})

        elif path == "/api/settings":
            cfg = load_json(SETTINGS_FILE, {})
            for k in ["bot_token", "chat_id", "thread_id", "filter_defects", "send_photos", "scan_interval", "profit_threshold"]:
                if k in data:
                    cfg[k] = data[k]
            save_json(SETTINGS_FILE, cfg)
            append_log("Настройки сохранены в settings.json")
            return self.send_json({"success": True, "settings": cfg})

        elif path == "/api/test-telegram":
            cmd = [PYTHON_BIN, "-c", f"""
import asyncio, sys
sys.path.insert(0, {repr(BASE_DIR)})
import worker

async def test_tg():
    try:
        sample_deal = {{
            "id": "demo_123456",
            "title": "Apple iPhone 14 128Gb (Midnight)",
            "price": 48000,
            "url": "https://www.avito.ru",
            "image": "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=600&auto=format&fit=crop",
            "city": "Кемерово",
            "seller": "Частное лицо"
        }}
        await worker.send_deal_notification(sample_deal, "iPhone 14 (Кемерово)", 48000, 48000, 58000, None, is_drop=False)
        print("Success")
    except Exception as e:
        print(f"Error: {{e}}", file=sys.stderr)
        sys.exit(1)

asyncio.run(test_tg())
"""]
            res = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
            if res.returncode == 0:
                append_log("Тестовое предложение успешно отправлено в Telegram")
                return self.send_json({"success": True, "message": "Тестовое предложение отправлено в Telegram!"})
            else:
                append_log(f"Ошибка отправки Telegram: {res.stderr}")
                return self.send_json({"success": False, "error": res.stderr.strip() or "Ошибка отправки"})

        self.send_json({"error": "Endpoint not found"}, HTTPStatus.NOT_FOUND)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/tasks/"):
            task_id = path.replace("/api/tasks/", "").strip()
            tasks = load_json(TASKS_FILE, [])
            filtered = [t for t in tasks if str(t.get("id")) != task_id]
            save_json(TASKS_FILE, filtered)
            append_log(f"Задача удалена: {task_id}")
            return self.send_json({"success": True, "tasks": filtered})

        self.send_json({"error": "Endpoint not found"}, HTTPStatus.NOT_FOUND)

def run(port=8088):
    os.makedirs(WEB_DIR, exist_ok=True)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"=== Avito Bot Host Server Initialized at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")

    server_address = ("127.0.0.1", port)
    httpd = ThreadingHTTPServer(server_address, AvitoBotHostHandler)
    logging.info(f"Avito Bot Host запущен на http://127.0.0.1:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_worker()
        httpd.server_close()
        logging.info("Сервер остановлен.")

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8088
    run(port)
