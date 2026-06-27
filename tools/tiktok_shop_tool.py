import os
import httpx
import hashlib
import hmac
import time
import json
from dotenv import load_dotenv

load_dotenv()

APP_KEY = os.getenv("TIKTOK_SHOP_APP_KEY")
APP_SECRET = os.getenv("TIKTOK_SHOP_APP_SECRET")
ACCESS_TOKEN = os.getenv("TIKTOK_SHOP_ACCESS_TOKEN")
BASE_URL = "https://open-api.tiktokglobalshop.com"

def is_available() -> bool:
    return bool(APP_KEY and APP_SECRET and ACCESS_TOKEN)

async def get_product_performance(product_ids: list[str]) -> list[dict]:
    """
    Hamare TikTok Shop products ki performance lo.
    Ye feedback loop ke liye hai - konsa product kitna bika.
    """
    if not is_available():
        return []

    results = []
    for pid in product_ids[:10]:
        data = await _api_call("GET", "/api/products/details", {"product_id": pid})
        if data:
            results.append({
                "product_id": pid,
                "name": data.get("product_name", ""),
                "sales": data.get("sales_count", 0),
                "revenue": data.get("gmv", 0),
                "stock": data.get("stock", 0),
            })
    return results

async def get_order_analytics(days: int = 7) -> dict:
    """
    Last N days ke orders aur sales data lo.
    Video performance se sales correlation samjhne ke liye.
    """
    if not is_available():
        return {}

    end_time = int(time.time())
    start_time = end_time - (days * 86400)

    data = await _api_call("GET", "/api/orders/search", {
        "create_time_ge": start_time,
        "create_time_lt": end_time,
        "page_size": 100,
    })

    if not data:
        return {}

    orders = data.get("orders", [])
    total_revenue = sum(float(o.get("payment_info", {}).get("total_amount", 0)) for o in orders)
    total_orders = len(orders)

    product_sales = {}
    for order in orders:
        for item in order.get("line_items", []):
            pid = item.get("product_id", "")
            if pid:
                product_sales[pid] = product_sales.get(pid, 0) + item.get("quantity", 0)

    return {
        "period_days": days,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "top_products": sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:5],
    }

async def get_trending_products_in_shop(niche: str) -> list[dict]:
    """
    Hamare shop ke best selling products lo - content ideas ke liye.
    """
    if not is_available():
        return []

    data = await _api_call("GET", "/api/products/search", {
        "page_size": 20,
        "sort_field": "sales",
        "sort_order": "DESC",
    })

    if not data:
        return []

    products = data.get("products", [])
    return [{
        "id": p.get("id", ""),
        "name": p.get("title", ""),
        "price": p.get("skus", [{}])[0].get("price", {}).get("sale_price", ""),
        "sales": p.get("sales", 0),
        "category": p.get("category_list", [{}])[0].get("name", ""),
    } for p in products[:10]]

async def _api_call(method: str, path: str, params: dict = None) -> dict:
    """TikTok Shop API call with signature."""
    if not is_available():
        return {}

    timestamp = str(int(time.time()))
    params = params or {}
    params.update({
        "app_key": APP_KEY,
        "timestamp": timestamp,
        "access_token": ACCESS_TOKEN,
    })

    sign = _generate_sign(path, params)
    params["sign"] = sign

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                resp = await client.get(f"{BASE_URL}{path}", params=params)
            else:
                resp = await client.post(f"{BASE_URL}{path}", json=params)
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") == 0:
                return result.get("data", {})
            return {}
    except Exception as e:
        print(f"[TikTok Shop API] Error: {e}")
        return {}

def _generate_sign(path: str, params: dict) -> str:
    """TikTok Shop API signature generate karo."""
    sorted_params = sorted(params.items())
    param_str = "".join([f"{k}{v}" for k, v in sorted_params if k != "sign"])
    sign_str = f"{APP_SECRET}{path}{param_str}{APP_SECRET}"
    return hmac.new(
        APP_SECRET.encode("utf-8"),
        sign_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest().upper()
