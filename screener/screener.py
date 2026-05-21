from services.asx_api import ASXAPI
from fastapi import APIRouter
from screener.screener import get_stock_data

asx = ASXAPI()
router = APIRouter()

@router.get("/stock/{ticker}")
def stock(ticker: str, market: str = "AUTO"):
    data = get_stock_data(ticker, market)
    if not data:
        return {"error": "Ticker not found"}
    return data

def get_asx_stock_data(ticker: str):
    try:
        share = asx.get_share(ticker)
        company = asx.get_company(ticker)

        return {
            "ticker": ticker,
            "price": share.get("last_price"),
            "open": share.get("open_price"),
            "high": share.get("day_high_price"),
            "low": share.get("day_low_price"),
            "volume": share.get("volume"),
            "market_cap": company.get("market_cap"),
            "sector": company.get("sector_name"),
            "industry": company.get("industry_group_name"),
        }

    except Exception as e:
        print(f"ASX fetch failed for {ticker}: {e}")
        return None
