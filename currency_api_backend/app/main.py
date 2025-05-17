
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CANLIDOVIZ_URL = "https://api.canlidoviz.com/web/items?marketId=1&type=0"

@app.get("/api/rates")
def get_rates():
    try:
        response = requests.get(CANLIDOVIZ_URL, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except Exception as e:
        return {"status": "error", "message": str(e)}
