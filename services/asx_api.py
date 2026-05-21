import httpx

BASE_URL = "https://www.asx.com.au/asx/1"

class ASXAPI:
    def __init__(self, timeout=10):
        self.client = httpx.Client(timeout=timeout)

    def get_share(self, ticker: str) -> dict:
        """Fetch ASX share data (delayed)."""
        url = f"{BASE_URL}/share/{ticker.upper()}"
        r = self.client.get(url)
        r.raise_for_status()
        return r.json()

    def get_company(self, ticker: str) -> dict:
        """Fetch company metadata."""
        url = f"{BASE_URL}/company/{ticker.upper()}"
        r = self.client.get(url)
        r.raise_for_status()
        return r.json()

    def get_price(self, ticker: str) -> float:
        """Convenience wrapper for last price."""
        data = self.get_share(ticker)
        return data.get("last_price")
