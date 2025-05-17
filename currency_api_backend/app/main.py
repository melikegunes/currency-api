
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
    "Gold": "https://canlidoviz.com/altin-fiyatlari/kapali-carsi/gram-altin",
    "Gumus": "https://canlidoviz.com/altin-fiyatlari/kapali-carsi/gumus",
    "USD": "https://canlidoviz.com/doviz-kurlari/dolar",
    "EUR": "https://canlidoviz.com/doviz-kurlari/euro",
    "Bilezik": "https://canlidoviz.com/altin-fiyatlari/kapali-carsi/22-ayar-bilezik"
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
            currency_data.append({
                "Bank": bank_name,
                "Buying Price": float(buying_price),
                "Selling Price": float(selling_price)
            })
    return currency_data

@app.get("/api/rates")
def get_rates():
    result = {}
    for label, url in URLS.items():
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            result[label] = parse_currency_data(response.text)
        except Exception as e:
            result[label] = {"error": str(e)}
    return {"status": "success", "data": result}
