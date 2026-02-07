from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

URLS = {
    "gold": "https://canlidoviz.com/altin-fiyatlari/kapali-carsi/gram-altin",
    "ceyrekaltin":"https://canlidoviz.com/altin-fiyatlari/ceyrek-altin",
    "gumus": "https://canlidoviz.com/altin-fiyatlari/kapali-carsi/gumus",
    "usd": "https://canlidoviz.com/doviz-kurlari/dolar",
    "eur": "https://canlidoviz.com/doviz-kurlari/euro",
    "gbp":"https://canlidoviz.com/doviz-kurlari/ingiliz-sterlini",
    "bilezik": "https://canlidoviz.com/altin-fiyatlari/kapali-carsi/22-ayar-bilezik"
}

ALTINKAYNAK_URLS = {
    "gold": "https://static.altinkaynak.com/Gold",
    "doviz": "https://static.altinkaynak.com/Currency"
}

ALTINKAYNAK_MAPPING = {
    # Original Mappings
    "gold": {"code": "GA", "type": "altin", "chart_id": 20, "history_id": 35},
    "ceyrekaltin": {"code": "C", "type": "altin", "chart_id": 28, "history_id": 28},
    "gumus": {"code": "AG1000", "type": "altin", "chart_id": 50, "history_id": 24},
    "usd": {"code": "USD", "type": "doviz", "chart_id": 1, "history_id": 1},
    "eur": {"code": "EUR", "type": "doviz", "chart_id": 3, "history_id": 3},
    "gbp": {"code": "GBP", "type": "doviz", "chart_id": 4, "history_id": 5},
    "bilezik": {"code": "B", "type": "altin", "chart_id": 22, "history_id": 25}, # Updated code to B based on list

    # New Currencies
    "chf": {"code": "CHF", "type": "doviz", "chart_id": 4, "history_id": 4}, # Guessing chart_id
    "jpy": {"code": "JPY", "type": "doviz", "chart_id": 9, "history_id": 9},
    "sar": {"code": "SAR", "type": "doviz", "chart_id": 10, "history_id": 10},
    "aud": {"code": "AUD", "type": "doviz", "chart_id": 11, "history_id": 11},
    "cad": {"code": "CAD", "type": "doviz", "chart_id": 12, "history_id": 12},
    "rub": {"code": "RUB", "type": "doviz", "chart_id": 13, "history_id": 13},
    "azn": {"code": "AZN", "type": "doviz", "chart_id": 14, "history_id": 14},
    "cny": {"code": "CNY", "type": "doviz", "chart_id": 15, "history_id": 15},
    "ron": {"code": "RON", "type": "doviz", "chart_id": 16, "history_id": 16},
    "aed": {"code": "AED", "type": "doviz", "chart_id": 17, "history_id": 17},
    "bgn": {"code": "BGN", "type": "doviz", "chart_id": 18, "history_id": 18},
    "kwd": {"code": "KWD", "type": "doviz", "chart_id": 19, "history_id": 19},

    # New Gold/Metals
    "has_altin": {"code": "HH", "type": "altin", "chart_id": 20, "history_id": 20},
    "kulce_altin": {"code": "CH", "type": "altin", "chart_id": 21, "history_id": 21},
    "ata_cumhuriyet": {"code": "A", "type": "altin", "chart_id": 32, "history_id": 32},
    "yarim_altin": {"code": "Y", "type": "altin", "chart_id": 29, "history_id": 29},
    "teklik_altin": {"code": "T", "type": "altin", "chart_id": 30, "history_id": 30},
    "gremse_altin": {"code": "G", "type": "altin", "chart_id": 31, "history_id": 31},
    "resat_altin": {"code": "R", "type": "altin", "chart_id": 33, "history_id": 33},
    "hamit_altin": {"code": "H", "type": "altin", "chart_id": 34, "history_id": 34},
    "18_ayar": {"code": "18", "type": "altin", "chart_id": 26, "history_id": 26},
    "14_ayar": {"code": "14", "type": "altin", "chart_id": 27, "history_id": 27},
    "ata_besli": {"code": "A5", "type": "altin", "chart_id": 41, "history_id": 41}
}

def date_to_ticks(date_str: str):
    """Converts YYYY-MM-DD to .NET Ticks."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        unix_epoch_ticks = 621355968000000000
        ticks = int(dt.timestamp() * 10000000) + unix_epoch_ticks
        return ticks
    except ValueError:
        return None

def clean_price(p):
    """Cleans Altinkaynak price strings into floats."""
    if not p: return 0.0
    p = str(p).strip()
    # If there's a dot AND a comma, dot is thousand, comma is decimal
    if '.' in p and ',' in p:
        return float(p.replace('.', '').replace(',', '.'))
    # If only comma, it's likely the decimal separator
    if ',' in p:
        return float(p.replace(',', '.'))
    # If only dot, it could be decimal (currency 43.500) or thousand (gold 7.300)
    # Check if dot is followed by exactly 3 digits (thousand separator case)
    if '.' in p:
        parts = p.split('.')
        if len(parts[-1]) == 3 and len(parts) > 1:
            # Check context or just treat as thousand if not currency
            # For simplicity, we assume thousand if exactly 3 digits follow
            return float(p.replace('.', ''))
        return float(p)
    return float(p)

def parse_currency_data(html):
    soup = BeautifulSoup(html, "html.parser")
    table_body = soup.find('tbody')
    currency_data = []

    if not table_body:
        return currency_data

    for row in table_body.find_all('tr'):
        columns = row.find_all("td")
        if columns:
            bank_name = columns[0].text.strip().split('\n')[0]
            buy_text = columns[1].text.strip().split('\n')[0]
            sell_text = columns[2].text.strip().split('\n')[0]
            
            bank_name=(bank_name.replace('İ','I')
                                .replace('Ş','S')
                                .replace('Ü','U')
                                .replace('Ç','C'))

            try:
                # Robust cleaning function
                def parse_price(text):
                    # Remove currency symbols and whitespace
                    text = text.replace('TL', '').replace('$', '').replace('€', '').strip()
                    if ',' in text and '.' in text:
                        # If both present, assume last one is decimal
                        if text.rfind(',') > text.rfind('.'):
                            # 1.234,56 -> remove dot, replace comma with dot
                            text = text.replace('.', '').replace(',', '.')
                        else:
                            # 1,234.56 -> remove comma
                            text = text.replace(',', '')
                    elif ',' in text:
                        # 43,5120 -> 43.5120 (Turkey standard)
                        text = text.replace(',', '.')
                    # If only dots, leaving it might be risky if it's 1.200 (1200) vs 1.200 (1.2).
                    # But usually canlidoviz uses comma for decimal. 
                    # If it was 43.5290 and we got 435290, it means we stripped the dot.
                    # So if only dot is present, we should KEEP it if it looks like a decimal (small number)
                    # or strip it if thousands. 
                    # However, safer to assume it's a decimal if the resulting number is massive otherwise?
                    # Let's trust that clean float conversion works on "43.5290".
                    
                    return float(text)

                currency_data.append({
                    "bank": bank_name,
                    "buy": parse_price(buy_text),
                    "sell": parse_price(sell_text)
                })
            except ValueError:
                continue
    return currency_data

def fetch_altinkaynak_data():
    results = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": "https://www.altinkaynak.com/",
        "Origin": "https://www.altinkaynak.com"
    }
    
    for category, url in ALTINKAYNAK_URLS.items():
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            for item in data:
                kod = item.get("Kod")
                buy_raw = item.get("Alis", "0")
                sell_raw = item.get("Satis", "0")
                
                try:
                    buy_price = clean_price(buy_raw)
                    sell_price = clean_price(sell_raw)

                    # Normalize Silver (AG1000) from KG to Gram
                    if kod == "AG1000" or kod == "AG_T":
                         buy_price /= 1000.0
                         sell_price /= 1000.0

                    results[kod] = {
                        "bank": "Altinkaynak",
                        "buy": buy_price,
                        "sell": sell_price
                    }
                except (ValueError, TypeError):
                    continue
        except Exception as e:
            print(f"Error fetching Altinkaynak {category}: {e}")
            
    return results

@app.get("/api/rates")
def get_rates():
    result = {}
    altinkaynak_all = fetch_altinkaynak_data()
    
    # Process existing URLS (canlidoviz + Altinkaynak)
    for label, url in URLS.items():
        try:
            # Fetch from canlidoviz.com
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            response.encoding = "utf-8"
            # response.raise_for_status() # Optional: handle canlidoviz failures gracefully
            if response.status_code == 200:
                data = parse_currency_data(response.text)
            else:
                data = []
            
            # Inject Altinkaynak if mapped
            if label in ALTINKAYNAK_MAPPING:
                mapping = ALTINKAYNAK_MAPPING[label]
                altin_code = mapping["code"]
                if altin_code in altinkaynak_all:
                    data.append(altinkaynak_all[altin_code])
            
            result[label] = data
        except Exception as e:
            result[label] = {"error": str(e)}

    # Add Altinkaynak-only assets
    for label, mapping in ALTINKAYNAK_MAPPING.items():
        if label not in result: # Only add if not already covered by URLS loop
            altin_code = mapping["code"]
            if altin_code in altinkaynak_all:
                result[label] = [altinkaynak_all[altin_code]]
            else:
                result[label] = [] # Or omit if no data

    return {"status": "success", "data": result}

@app.get("/api/rates/{asset}")
def get_asset_rates(asset: str):
    asset = asset.lower()
    # Check if asset exists in either source
    if asset not in URLS and asset not in ALTINKAYNAK_MAPPING:
        return {"status": "error", "message": "Asset not found"}
        
    try:
        data = []
        # Fetch from canlidoviz.com if available
        if asset in URLS:
            response = requests.get(URLS[asset], headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            response.encoding = "utf-8"
            if response.status_code == 200:
                data = parse_currency_data(response.text)
        
        # Inject Altinkaynak if mapped
        altinkaynak_all = fetch_altinkaynak_data()
        if asset in ALTINKAYNAK_MAPPING:
            mapping = ALTINKAYNAK_MAPPING[asset]
            altin_code = mapping["code"]
            if altin_code in altinkaynak_all:
                data.append(altinkaynak_all[altin_code])
                
        return {"status": "success", "asset": asset, "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/history/{asset}")
def get_historical_rates(asset: str, date: str = Query(..., description="Date in YYYY-MM-DD format")):
    asset = asset.lower()
    if asset not in ALTINKAYNAK_MAPPING:
        return {"status": "error", "message": "Asset mapping for Altinkaynak not found"}
    
    mapping = ALTINKAYNAK_MAPPING[asset]
    start_ticks = date_to_ticks(date)
    # Next day ticks for the range end
    end_ticks = start_ticks + 864000000000
    
    if not start_ticks:
        return {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD"}
        
    url = f"https://api.altinkaynak.com/kur/getrange/{mapping['type']}/{mapping.get('history_id', 0)}/start/{start_ticks}/end/{end_ticks}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": "https://www.altinkaynak.com/",
        "Origin": "https://www.altinkaynak.com",
        "Accept": "application/json, text/plain, */*",
        "x-token": "f5f4a6ac-c1b3-11f0-8de9-0242ac120002_mobil"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # response.raise_for_status() # The API might return 404 or empty list if no data, which we handle
        data_list = response.json()
        
        # We might get multiple entries or empty list
        if not data_list or "error" in data_list:
             return {"status": "error", "message": f"Data for {asset} not found for this date (API)"}

        # Take the first entry
        asset_data = data_list[0]
            
        return {
            "status": "success",
            "asset": asset,
            "date": date,
            "data": {
                "buy": clean_price(asset_data.get("Alis")),
                "sell": clean_price(asset_data.get("Satis")),
                "time": asset_data.get("GuncellenmeZamani")
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/chart/{asset}")
def get_chart_data(asset: str):
    asset = asset.lower()
    if asset not in ALTINKAYNAK_MAPPING or "chart_id" not in ALTINKAYNAK_MAPPING[asset]:
        return {"status": "error", "message": "Chart ID not found for this asset"}
        
    chart_id = ALTINKAYNAK_MAPPING[asset]["chart_id"]
    url = f"https://static.altinkaynak.com/chart/Store_{chart_id}_1"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Original format is often [[timestamp, price], ...]
        # Or a list of objects depending on the specific Store file
        return {"status": "success", "asset": asset, "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/history/{asset}/range")
def get_historical_range(
    asset: str, 
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format")
):
    asset = asset.lower()
    if asset not in ALTINKAYNAK_MAPPING:
        return {"status": "error", "message": "Asset mapping for Altinkaynak not found"}

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD"}

    if start_dt > end_dt:
        return {"status": "error", "message": "start_date cannot be after end_date"}

    # Limit range to prevent excessive requests (e.g., 31 days)
    delta = (end_dt - start_dt).days
    if delta > 31:
        return {"status": "error", "message": "Range too large. Maximum 31 days allowed."}

    mapping = ALTINKAYNAK_MAPPING[asset]
    start_ticks = date_to_ticks(start_date)
    # End date + 1 day to cover the full end date
    end_dt_plus_one = end_dt + timedelta(days=1)
    end_ticks_calculated = date_to_ticks(end_dt_plus_one.strftime("%Y-%m-%d"))

    url = f"https://api.altinkaynak.com/kur/getrange/{mapping['type']}/{mapping.get('history_id', 0)}/start/{start_ticks}/end/{end_ticks_calculated}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": "https://www.altinkaynak.com/",
        "Origin": "https://www.altinkaynak.com",
        "x-token": "f5f4a6ac-c1b3-11f0-8de9-0242ac120002_mobil"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        data_list = response.json()
        
        if not isinstance(data_list, list):
             return {"status": "error", "message": "Upstream API returned invalid format"}

        results = []
        # The API returns a list of objects with "GuncellenmeZamani": "DD.MM.YYYY HH:MM:SS"
        # We need to map them back to YYYY-MM-DD
        
        for item in data_list:
            raw_time = item.get("GuncellenmeZamani", "")
            # Simple date extraction
            date_str = raw_time.split(" ")[0] # "01.01.2024"
            if "." in date_str:
                parts = date_str.split(".")
                if len(parts) == 3:
                    iso_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
                    results.append({
                        "date": iso_date,
                        "buy": clean_price(item.get("Alis")),
                        "sell": clean_price(item.get("Satis"))
                    })
        
        return {
            "status": "success",
            "asset": asset,
            "start_date": start_date,
            "end_date": end_date,
            "data": results
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
