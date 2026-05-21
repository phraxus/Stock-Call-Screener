from fastapi import APIRouter
from screener.screener import get_asx_stock_data

router = APIRouter()

@router.get("/asx/{ticker}")
def asx_stock(ticker: str):
    data = get_asx_stock_data(ticker)
    if not data:
        return {"error": "Ticker not found or ASX API unavailable"}
    return data
