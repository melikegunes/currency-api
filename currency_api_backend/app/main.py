
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup

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

def parse_currency_data(html):
    soup = BeautifulSoup(html, "html.parser")
    table_body = soup.find('tbody')
    currency_data = []

    for row in table_body.find_all('tr'):
        columns = row.find_all("td")
        if columns:
            bank_name = columns[0].text.strip().split('\n')[0]
            buying_price = columns[1].text.strip()
            selling_price = columns[2].text.strip().split('\n')[0]
            bank_name=(bank_name.replace('İ','I')
                                .replace('Ş','S')
                                .replace('Ü','U')
                                .replace('Ç','C'))

            currency_data.append({
                "bank": bank_name,
                "buy": float(buying_price),
                "sell": float(selling_price)
            })
    return currency_data

@app.get("/api/rates")
def get_rates():
    result = {}
    for label, url in URLS.items():
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            response.encoding = "utf-8"
            response.raise_for_status()
            result[label] = parse_currency_data(response.text)
        except Exception as e:
            result[label] = {"error": str(e)}
    return {"status": "success", "data": result}

@app.get("/api/rates/{asset}")
def get_asset_rates(asset: str):
    asset = asset.lower()
    try:
        response = requests.get(URLS[asset], headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        data = parse_currency_data(response.text)
        return {"status": "success", "asset": asset, "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

