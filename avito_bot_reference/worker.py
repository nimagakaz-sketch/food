import asyncio
import html as html_lib
import json
import logging
import os
import re
import urllib.parse
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession
from aiogram import Bot, Dispatcher, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

BOT_TOKEN = "8593240850:AAGqei6Qv-DQnx5IZurU9VEriw84zKwrXYg"
CHAT_ID = 374188835

BASE_DIR = os.getenv("AVITO_DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
TASKS_FILE = os.path.join(BASE_DIR, "tasks.json")
PRICE_CACHE_FILE = os.path.join(BASE_DIR, "price_cache.json")
ITEMS_STORE_FILE = os.path.join(BASE_DIR, "items_store.json")
DEALS_FILE = os.path.join(BASE_DIR, "deals.json")
FAVORITES_FILE = os.path.join(BASE_DIR, "favorites.json")
BLACKLIST_FILE = os.path.join(BASE_DIR, "blacklist.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
PROXIES_FILE = os.path.join(BASE_DIR, "proxies.txt")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [WORKER] %(message)s")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
    "Accept": "application/json, text/html, application/xhtml+xml, */*",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Referer": "https://www.avito.ru/"
}

KNOWN_CITIES = {
    "кемерово": 631270,
    "новосибирск": 641780,
    "москва": 637640,
    "санкт-петербург": 653240,
    "питер": 653240,
    "екатеринбург": 651470,
    "казань": 646390,
    "нижний новгород": 641570,
    "красноярск": 633350,
    "самара": 648170,
    "омск": 642450,
    "ростов-на-дону": 647030,
    "уфа": 622830,
    "краснодар": 632660,
    "тюмень": 655450,
    "томск": 657310,
    "барнаул": 621540,
    "владивосток": 644560,
    "иркутск": 630130,
    "хабаровск": 657150,
    "сочи": 634450
}

ACCESSORY_STOP_WORDS = [
    "чехол", "стекло", "коробка", "запчаст", "ремонт", "кабель", "блок",
    "зарядк", "аккумулятор", "дисплей", "пленка", "ремешок", "корпус", "плата",
    "watch", "часы", "airpods", "наушник", "переходник", "адаптер", "шнур"
]

MODEL_MIN_THRESHOLDS = {
    "11": 10500,
    "11 pro": 15000,
    "11 pro max": 19000,
    "12": 17000,
    "12 mini": 14000,
    "12 pro": 26000,
    "12 pro max": 36000,
    "13": 28000,
    "13 mini": 23000,
    "13 pro": 38000,
    "13 pro max": 45000,
    "14": 38000,
    "14 plus": 41000,
    "14 pro": 52000,
    "14 pro max": 59000,
    "15": 48000,
    "15 pro": 65000,
    "15 pro max": 75000,
    "16": 62000,
    "16 pro": 85000,
    "16 pro max": 99000
}

current_proxy_index = 0

def load_proxies():
    if not os.path.exists(PROXIES_FILE):
        return []
    try:
        with open(PROXIES_FILE, "r", encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
    except Exception:
        return []

def get_next_proxy():
    global current_proxy_index
    proxies = load_proxies()
    if not proxies:
        return None
    proxy = proxies[current_proxy_index % len(proxies)]
    current_proxy_index = (current_proxy_index + 1) % len(proxies)
    return proxy

def get_dynamic_min_price(model_name: str, fallback_min: int = 3000) -> int:
    name = (model_name or "").lower().strip()
    for m_key in sorted(MODEL_MIN_THRESHOLDS.keys(), key=len, reverse=True):
        if m_key in name:
            return MODEL_MIN_THRESHOLDS[m_key]
    return fallback_min

def load_tasks():
    if not os.path.exists(TASKS_FILE): return []
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return []

def save_tasks(tasks):
    try:
        with open(TASKS_FILE, "w", encoding="utf-8") as f: json.dump(tasks, f, ensure_ascii=False, indent=2)
    except Exception: pass

def load_json(fpath, default=None):
    if default is None: default = {}
    if not os.path.exists(fpath): return default
    try:
        with open(fpath, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return default

def save_json(fpath, data):
    try:
        with open(fpath, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception: pass

def calculate_trimmed_mean(prices, trim_percent: float = 0.20):
    if not prices: return 0
    valid_p = sorted([p for p in prices if p > 0])
    n = len(valid_p)
    if n < 4: return int(sum(valid_p) / n)
    k = max(1, int(n * trim_percent))
    core = valid_p[k:-k] if (n - 2 * k) > 0 else valid_p
    return int(sum(core) / len(core))

def extract_memory_from_text(text):
    if not text: return None
    m = re.search(r"\b(64|128|256|512|1024)\s*(?:gb|гб|тб|tb)?\b", text.lower())
    if m:
        val = m.group(1)
        return "1 ТБ" if val == "1024" else f"{val} ГБ"
    return None

def analyze_condition_and_defects(title: str, text: str = "") -> dict:
    full_text = f"{title} {text}".lower()
    defects = []
    conditions = []
    
    # 1. Face ID / Touch ID
    if any(k in full_text for k in ["без face id", "не работает face", "face id off", "фейс не работает", "без фейс", "face id не", "не работает touch", "без touch id"]):
        defects.append("⚠️ Не работает Face ID")
    elif "face id работает" in full_text or "face id ok" in full_text:
        conditions.append("✅ Face ID работает")
        
    # 2. True Tone
    if any(k in full_text for k in ["без true tone", "нет true tone", "трутон не работает", "без трутон", "true tone off"]):
        defects.append("⚠️ Без True Tone")
    elif "true tone" in full_text and "работает" in full_text:
        conditions.append("✅ True Tone")
        
    # 3. Screen / Body condition
    if any(k in full_text for k in ["разбит", "трещина", "треснут", "скол на экране", "битый экран", "паутинка", "полосы на экране", "пятно на матрице", "полоса"]):
        defects.append("💥 Разбит / Трещины")
    elif any(k in full_text for k in ["идеал", "в идеале", "как новый", "состояние нового", "без сколов", "без царапин"]):
        conditions.append("✨ Идеальное состояние")
        
    # 4. Screen Replacement
    if any(k in full_text for k in ["менялся дисплей", "заменен экран", "экран меняли", "копия дисплея", "ошибка экрана"]):
        defects.append("🔧 Менян экран")
        
    # 5. Lock / iCloud / MDM / R-Sim
    if any(k in full_text for k in ["icloud", "айклауд", "пароль на экране", "mdm", "обход", "заблокирован", "r-sim", "р-сим", "демо", "demo"]):
        defects.append("🚫 Блокировка / iCloud / R-Sim")
        
    # 6. Battery Health
    m_bat = re.search(r"\b(?:акб|батаре[яеи]|емкость|состояние|battery|health)[:\s]*(\d{2,3})\s*%", full_text)
    if m_bat:
        pct = int(m_bat.group(1))
        if 50 <= pct <= 100:
            if pct >= 85:
                conditions.append(f"🔋 АКБ {pct}%")
            elif pct >= 75:
                conditions.append(f"🟡 АКБ {pct}%")
            else:
                defects.append(f"🪫 АКБ {pct}% (сервис)")
                
    # 7. Bundle / Box / Warranty
    if any(k in full_text for k in ["полный комплект", "родная коробка", "с коробкой", "коробка чек"]):
        conditions.append("📦 Полный комплект")
    if any(k in full_text for k in ["есть чек", "с чеком", "чек из магазина"]):
        conditions.append("🧾 Есть чек")
    if any(k in full_text for k in ["на гарантии", "гарантия apple", "гарантия до"]):
        conditions.append("🛡 На гарантии")
        
    is_critical = any("🚫" in d or "💥" in d for d in defects)
    return {
        "defects": defects,
        "conditions": conditions,
        "is_critical": is_critical
    }

def extract_image_url(raw_item: dict) -> str:
    images = raw_item.get("images") or []
    if isinstance(images, list) and images:
        first = images[0]
        if isinstance(first, dict):
            for res_key in ["1280x960", "864x648", "640x480", "432x324"]:
                if res_key in first and first[res_key]:
                    return first[res_key]
            for v in first.values():
                if isinstance(v, str) and v.startswith("http"):
                    return v
        elif isinstance(first, str) and first.startswith("http"):
            return first
    img = raw_item.get("image")
    if isinstance(img, dict):
        for res_key in ["1280x960", "640x480", "432x324"]:
            if res_key in img and img[res_key]:
                return img[res_key]
        for v in img.values():
            if isinstance(v, str) and v.startswith("http"):
                return v
    elif isinstance(img, str) and img.startswith("http"):
        return img
    return ""

def get_iphone_series(text: str):
    t = text.lower()
    m = re.search(r"\b(?:iphone|айфон)\s*(?:apple)?\s*(se(?:\s*\d{4})?|xr|xs|x|1[1-7]|[6-8])\b", t)
    if m:
        val = m.group(1).replace(" ", "")
        if val.startswith("se"): return "se"
        return val
    m2 = re.search(r"\b(se|xr|xs|x|1[1-7]|[6-8])\s*(?:pro\s*max|promax|pro|plus|mini|макс|про)\b", t)
    if m2:
        return m2.group(1)
    return None

def get_iphone_modifier(text: str) -> str:
    t = text.lower().replace("-", " ").replace("_", " ")
    if "pro max" in t or "про макс" in t or "promax" in t:
        return "pro_max"
    if "max" in t or "макс" in t:
        return "max"
    if "pro" in t or "про" in t:
        return "pro"
    if "plus" in t or "плюс" in t:
        return "plus"
    if "mini" in t or "мини" in t:
        return "mini"
    return "base"

def is_matching_model(target_model: str, title: str, url_path: str = "") -> bool:
    if not target_model or not title:
        return False
        
    t = title.lower()
    u = (url_path or "").lower().replace("_", " ")
    combined = f"{t} {u}"
    
    # 1. Reject accessories and parts
    if any(sw in combined for sw in ACCESSORY_STOP_WORDS):
        return False
        
    m = target_model.lower().strip()
    
    # 2. iPhone specific strict matching
    if "iphone" in m or "айфон" in m:
        if "iphone" not in combined and "айфон" not in combined:
            return False
            
        target_series = get_iphone_series(m)
        title_series = get_iphone_series(t)
        
        if target_series and title_series and target_series != title_series:
            return False
        if target_series and not title_series:
            return False
            
        target_mod = get_iphone_modifier(m)
        title_mod = get_iphone_modifier(t)
        if target_mod != title_mod:
            return False
            
        if url_path:
            url_series = get_iphone_series(u)
            if target_series and url_series and target_series != url_series:
                return False
            url_mod = get_iphone_modifier(u)
            if target_mod != url_mod:
                return False
            
        # Check memory if explicitly requested in target
        target_mem = extract_memory_from_text(m)
        title_mem = extract_memory_from_text(t) or extract_memory_from_text(u)
        if target_mem and title_mem and target_mem != title_mem:
            return False
            
        return True
        
    # Non-iPhone matching (Samsung, Xiaomi, etc.)
    words = [w for w in re.split(r"\s+", m) if len(w) > 1]
    return all(w in combined for w in words)

async def resolve_city_location_id(city_name: str, session: AsyncSession, proxy: str = None) -> int:
    cleaned = (city_name or "").strip().lower()
    for k, v in KNOWN_CITIES.items():
        if k in cleaned or cleaned in k:
            return v
    try:
        url = f"https://www.avito.ru/web/1/slocations?q={urllib.parse.quote(city_name)}"
        req_kw = {"headers": HEADERS, "impersonate": "safari15_5", "timeout": 8}
        if proxy: req_kw["proxy"] = proxy
        r = await session.get(url, **req_kw)
        if r.status_code == 200:
            data = r.json()
            locations = data.get("result", {}).get("locations", [])
            for loc in locations:
                names = loc.get("names", {})
                for n in names.values():
                    if cleaned in n.lower():
                        return loc.get("id")
            if locations:
                return locations[-1].get("id")
    except Exception as e:
        logging.warning(f"Location resolve error for {city_name}: {e}")
    return 637640  # Default to Moscow if not found

async def fetch_avito_items(model_query: str, city_name: str, min_p: int, max_p: int):
    items = []
    seen_ids = set()
    b_list = load_json(BLACKLIST_FILE, [])
    blacklisted_ids = {str(b.get("id")) for b in b_list}
    blacklisted_names = {b.get("name", "").lower() for b in b_list if b.get("name")}
    
    cfg = load_json(SETTINGS_FILE, {})
    filter_critical_defects = cfg.get("filter_defects", True)

    queries = [model_query]
    if "apple" not in model_query.lower() and "iphone" in model_query.lower():
        queries.append(f"Apple {model_query}")
    
    proxy = get_next_proxy()
    if proxy:
        logging.info(f"Используется прокси: {proxy}")
        
    async with AsyncSession() as s:
        loc_id = await resolve_city_location_id(city_name, s, proxy)
        
        for q_text in queries:
            q_encoded = urllib.parse.quote(q_text)
            url = f"https://www.avito.ru/web/1/main/items?locationId={loc_id}&categoryId=84&q={q_encoded}"
            
            try:
                req_kw = {"headers": HEADERS, "impersonate": "safari15_5", "timeout": 12}
                if proxy: req_kw["proxy"] = proxy
                
                r = await s.get(url, **req_kw)
                if r.status_code == 429:
                    logging.warning(f"Avito 429 на {q_text}. Ротация прокси...")
                    proxy = get_next_proxy()
                    await asyncio.sleep(2.0)
                    continue
                elif r.status_code == 200:
                    data = r.json()
                    raw_items = data.get("items", [])
                    for raw in raw_items:
                        iid = str(raw.get("id", ""))
                        if not iid or iid == "0" or iid in seen_ids or iid in blacklisted_ids:
                            continue
                        
                        seller_info = raw.get("seller") or {}
                        seller_name = (seller_info.get("name") or "").lower()
                        if seller_name and any(bn in seller_name for bn in blacklisted_names):
                            continue

                        title = raw.get("title", "").strip()
                        if not title: continue
                        
                        raw_url = raw.get("urlPath") or ""
                        clean_path = raw_url.split("?")[0] if raw_url else ""

                        # STRICT MODEL VALIDATION
                        if not is_matching_model(model_query, title, clean_path):
                            continue
                        
                        # Defect & Condition Analysis
                        inspect_res = analyze_condition_and_defects(title, clean_path)
                        if filter_critical_defects and inspect_res["is_critical"]:
                            logging.info(f"Пропущен дефектный товар: {title} ({', '.join(inspect_res['defects'])})")
                            continue

                        # Extract price
                        price_dict = raw.get("priceDetailed", {})
                        p_str = price_dict.get("string", "")
                        raw_nums = re.findall(r"\d+", p_str.replace("\xa0", "").replace(" ", ""))
                        if not raw_nums: continue
                        price_val = int(raw_nums[0])
                        
                        if not (min_p <= price_val <= max_p):
                            continue
                        
                        seen_ids.add(iid)
                        if clean_path:
                            full_url = f"https://www.avito.ru{clean_path}" if clean_path.startswith("/") else f"https://www.avito.ru/{clean_path}"
                        else:
                            full_url = f"https://www.avito.ru/{iid}"
                            
                        memory = extract_memory_from_text(title) or extract_memory_from_text(clean_path)
                        img_url = extract_image_url(raw)
                        
                        items.append({
                            "id": iid,
                            "title": title,
                            "price": price_val,
                            "url": full_url,
                            "image": img_url,
                            "memory": memory,
                            "city": city_name,
                            "defects": inspect_res["defects"],
                            "conditions": inspect_res["conditions"],
                            "seller": seller_info.get("name", "Частное лицо")
                        })
            except Exception as e:
                logging.warning(f"Error fetching Avito items for {q_text}: {e}")
            
    return items

async def send_deal_notification(it: dict, task_name: str, price_num: int, prev_price: int, avg_p: int, thread_id: int = None, is_drop: bool = False):
    iid = it["id"]
    cfg = load_json(SETTINGS_FILE, {})
    send_photo_enabled = cfg.get("send_photos", True)
    
    diff = avg_p - price_num if avg_p > 0 else 0
    diff_pct = int((diff / avg_p) * 100) if avg_p > 0 else 0

    if is_drop:
        drop_pct = int(((prev_price - price_num) / prev_price) * 100) if prev_price > 0 else 0
        badge = f"📉 <b>СНИЖЕНИЕ ЦЕНЫ НА {drop_pct}%!</b>"
        price_line = f"💵 <b>Цена: <s>{prev_price:,} ₽</s> ➔ {price_num:,} ₽</b>".replace(",", " ")
    elif diff > 0 and diff_pct >= 8:
        badge = f"🔥 <b>ВЫГОДА +{diff:,} ₽ (-{diff_pct}%)</b>".replace(",", " ")
        price_line = f"💵 <b>Цена: {price_num:,} ₽</b>".replace(",", " ")
    else:
        badge = "⚡️ <b>НОВОЕ ПРЕДЛОЖЕНИЕ</b>"
        price_line = f"💵 <b>Цена: {price_num:,} ₽</b>".replace(",", " ")

    msg = f"{badge}\n\n"
    msg += f"📱 <b>{html_lib.escape(it['title'])}</b>\n"
    msg += f"{price_line}\n"
    if avg_p > 0 and diff > 0:
        msg += f"📊 Рыночная: ~{avg_p:,} ₽ | Профит: <b>+{diff:,} ₽</b>\n".replace(",", " ")
    elif avg_p > 0:
        msg += f"📊 Рыночная: ~{avg_p:,} ₽\n".replace(",", " ")
    if it.get("city"):
        msg += f"📍 Город: {html_lib.escape(it['city'])}\n"
    if it.get("seller"):
        msg += f"👤 Продавец: {html_lib.escape(it['seller'])}\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="↗️ На Авито", url=it["url"]),
            InlineKeyboardButton(text="⭐ В избранное", callback_data=f"fav_{iid}"),
            InlineKeyboardButton(text="🧮 Маржа", callback_data=f"calc_{iid}")
        ]
    ])

    img_url = it.get("image")
    sent = False
    
    # 1. Try sending with photo if available and enabled
    if send_photo_enabled and img_url and img_url.startswith("http"):
        try:
            send_kw = {
                "chat_id": CHAT_ID,
                "photo": img_url,
                "caption": msg,
                "parse_mode": "HTML",
                "reply_markup": kb
            }
            if thread_id: send_kw["message_thread_id"] = thread_id
            await bot.send_photo(**send_kw)
            sent = True
        except Exception as e:
            logging.warning(f"send_photo failed, falling back to send_message: {e}")
            sent = False
            
    # 2. Fallback to regular text message
    if not sent:
        try:
            send_kw = {
                "chat_id": CHAT_ID,
                "text": msg,
                "parse_mode": "HTML",
                "reply_markup": kb
            }
            if thread_id: send_kw["message_thread_id"] = thread_id
            await bot.send_message(**send_kw)
        except Exception as e:
            logging.warning(f"Telegram notification error: {e}")

async def process_task(task, first_run, price_cache, store):
    model = task.get("model", "")
    city = task.get("city", "Кемерово")
    thread_id = task.get("thread_id")
    task_name = f"{model} ({city})"
    
    custom_min = task.get("min_price")
    min_p = custom_min if (custom_min and custom_min > 3000) else get_dynamic_min_price(model)
    max_p = task.get("max_price", 150000)
    
    logging.info(f"Сканирование Avito: {task_name} [Мин: {min_p} ₽, Макс: {max_p} ₽]")
    items = await fetch_avito_items(model, city, min_p, max_p)
    
    if not items:
        logging.info(f"Объявлений не найдено для {task_name}")
        return
    
    logging.info(f"Найдено {len(items)} объявлений для {task_name}")
    
    valid_prices = [it["price"] for it in items if it["price"] >= min_p]
    if len(valid_prices) >= 3:
        computed_avg = calculate_trimmed_mean(valid_prices, 0.20)
        if computed_avg > 0:
            task["avg_price"] = computed_avg
    
    avg_p = task.get("avg_price", 0)
    if avg_p == 0 and valid_prices:
        avg_p = int(sum(valid_prices) / len(valid_prices))
        task["avg_price"] = avg_p

    # Enrich all items with task_name, city, and market evaluation
    for it in items:
        it["task_name"] = task_name
        it["city"] = city
        it["avg_price"] = avg_p
        if avg_p > 0 and it["price"] < avg_p:
            it["profit"] = avg_p - it["price"]
        else:
            it["profit"] = 0

    store[task_name] = items
    save_json(ITEMS_STORE_FILE, store)

    # Update deals list
    try:
        all_deals = load_json(DEALS_FILE, [])
        if not isinstance(all_deals, list): all_deals = []
        filtered_deals = [d for d in all_deals if d.get("task_name") != task_name]
        
        for it in items:
            if avg_p > 0 and it["price"] < avg_p:
                diff = avg_p - it["price"]
                diff_pct = int((diff / avg_p) * 100)
                if diff_pct >= 6:
                    filtered_deals.append({
                        "id": it["id"],
                        "task_name": task_name,
                        "title": it["title"],
                        "city": city,
                        "price": it["price"],
                        "avg_price": avg_p,
                        "profit": diff,
                        "url": it["url"],
                        "image": it.get("image", ""),
                        "memory": it.get("memory", ""),
                        "seller": it.get("seller", "")
                    })
        
        filtered_deals.sort(key=lambda x: x["profit"], reverse=True)
        save_json(DEALS_FILE, filtered_deals[:50])
    except Exception as e:
        logging.warning(f"Deals update error: {e}")
    
    if first_run:
        for it in items: price_cache[it["id"]] = it["price"]
        save_json(PRICE_CACHE_FILE, price_cache)
        return
        
    # Check for price drops and new items
    for it in reversed(items):
        iid = it["id"]
        price_num = it["price"]
        prev_price = price_cache.get(iid)
        
        if prev_price and (prev_price - price_num) >= 500 and int(((prev_price - price_num) / prev_price) * 100) >= 3:
            price_cache[iid] = price_num
            save_json(PRICE_CACHE_FILE, price_cache)
            await send_deal_notification(it, task_name, price_num, prev_price, avg_p, thread_id, is_drop=True)
            await asyncio.sleep(0.5)
            
        elif iid not in price_cache:
            price_cache[iid] = price_num
            save_json(PRICE_CACHE_FILE, price_cache)
            diff = avg_p - price_num if avg_p > 0 else 0
            diff_pct = int((diff / avg_p) * 100) if avg_p > 0 else 0
            
            # Notify only if item is below market or initial task baseline
            if avg_p == 0 or diff_pct >= 5:
                await send_deal_notification(it, task_name, price_num, prev_price or price_num, avg_p, thread_id, is_drop=False)
                await asyncio.sleep(0.5)

# ==============================================================================
# Telegram Bot Callback Query Handlers (Favorites & Blacklist)
# ==============================================================================
@dp.callback_query(F.data.startswith("fav_"))
async def handle_callback_favorite(callback: CallbackQuery):
    iid = callback.data.replace("fav_", "").strip()
    favs = load_json(FAVORITES_FILE, [])
    
    # Check if already in favorites
    if any(str(f.get("id")) == iid for f in favs):
        await callback.answer("⭐ Уже в Избранном!", show_alert=False)
        return
        
    # Find item from deals or items store
    all_deals = load_json(DEALS_FILE, [])
    item = next((d for d in all_deals if str(d.get("id")) == iid), None)
    
    if not item:
        items_store = load_json(ITEMS_STORE_FILE, {})
        for t_items in items_store.values():
            for it in t_items:
                if str(it.get("id")) == iid:
                    item = it
                    break
            if item: break

    if item:
        fav_entry = {
            "id": iid,
            "title": item.get("title", "iPhone"),
            "price": item.get("price", 0),
            "avg_price": item.get("avg_price", 0),
            "profit": item.get("profit", 0),
            "url": item.get("url", f"https://www.avito.ru/{iid}"),
            "image": item.get("image", ""),
            "city": item.get("city", ""),
            "memory": item.get("memory", ""),
            "conditions": item.get("conditions", []),
            "defects": item.get("defects", []),
            "status": "saved",
            "note": "",
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        favs.insert(0, fav_entry)
        save_json(FAVORITES_FILE, favs)
        await callback.answer("⭐ Сохранено в Избранное!", show_alert=False)
    else:
        await callback.answer("⭐ Товар добавлен в Избранное!", show_alert=False)

@dp.callback_query(F.data.startswith("bl_"))
async def handle_callback_blacklist(callback: CallbackQuery):
    iid = callback.data.replace("bl_", "").strip()
    b_list = load_json(BLACKLIST_FILE, [])
    
    # Remove from deals immediately
    deals = load_json(DEALS_FILE, [])
    item = next((d for d in deals if str(d.get("id")) == iid), None)
    seller_name = item.get("seller", "") if item else ""
    
    deals = [d for d in deals if str(d.get("id")) != iid]
    save_json(DEALS_FILE, deals)
    
    entry = {
        "id": iid,
        "name": seller_name,
        "title": item.get("title", "") if item else f"Лот #{iid}",
        "reason": "Заблокирован пользователем через Telegram",
        "added_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    b_list.insert(0, entry)
    save_json(BLACKLIST_FILE, b_list)
    await callback.answer(f"🚫 Добавлено в Чёрный список!", show_alert=True)

@dp.callback_query(F.data.startswith("calc_"))
async def handle_callback_calculator(callback: CallbackQuery):
    iid = callback.data.replace("calc_", "").strip()
    all_deals = load_json(DEALS_FILE, [])
    item = next((d for d in all_deals if str(d.get("id")) == iid), None)
    if item:
        p = item.get("price", 0)
        avg = item.get("avg_price", 0)
        profit = avg - p if avg > p else 0
        roi = int((profit / p) * 100) if p > 0 else 0
        txt = f"🧮 <b>Расчёт маржинальности:</b>\n\n"
        txt += f"• Покупка: {p:,} ₽\n".replace(",", " ")
        txt += f"• Рыночная цена: ~{avg:,} ₽\n".replace(",", " ")
        txt += f"• Чистая прибыль: +{profit:,} ₽ ({roi}% ROI)\n\n".replace(",", " ")
        txt += f"Подробный калькулятор расходов доступен в Mini App!"
        await callback.answer(f"Прибыль: +{profit:,} ₽ ({roi}% ROI)".replace(",", " "), show_alert=True)
    else:
        await callback.answer("Откройте калькулятор маржи в Mini App!", show_alert=True)

async def start_telegram_polling():
    try:
        logging.info("Telegram Dispatcher polling запущен для кнопок Избранного и ЧС.")
        await dp.start_polling(bot, allowed_updates=["callback_query", "message"])
    except Exception as e:
        logging.warning(f"Telegram polling warning: {e}")

async def main(once: bool = False):
    first_run = True
    price_cache = load_json(PRICE_CACHE_FILE, {})
    store = load_json(ITEMS_STORE_FILE, {})
    logging.info(f"Фоновый парсер Avito запущен {'(однократный скан)' if once else ''}!")
    
    # Start telegram callback polling in background
    if not once:
        asyncio.create_task(start_telegram_polling())
    
    while True:
        tasks = load_tasks()
        for t in tasks:
            try:
                await process_task(t, first_run, price_cache, store)
            except Exception as e:
                logging.error(f"Ошибка в задаче: {e}")
            await asyncio.sleep(2.5)
            
        if first_run:
            save_tasks(tasks)
            first_run = False
            lines = [f"• {t.get('model')} ({t.get('city')}): ~{t.get('avg_price', 0):,} ₽".replace(",", " ") for t in tasks]
            msg = "🟢 <b>Мониторинг Avito запущен!</b>\n\n" + "\n".join(lines)
            try: await bot.send_message(CHAT_ID, msg, parse_mode="HTML")
            except Exception: pass
            
        if once:
            logging.info("Однократное сканирование успешно завершено.")
            break
            
        await asyncio.sleep(12.0)

if __name__ == "__main__":
    import sys
    is_once = "--once" in sys.argv or "-o" in sys.argv
    asyncio.run(main(once=is_once))
