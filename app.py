import os
import re
import json
from typing import Optional, Any
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from catalogpilot.intelligence import catalog_insights, channel_readiness, copilot_answer, margin_analysis

load_dotenv()

app = FastAPI(title="CatalogPilot AI", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

WC_URL = os.getenv("WOOCOMMERCE_URL", "").rstrip("/")
WC_KEY = os.getenv("WOOCOMMERCE_CONSUMER_KEY", "")
WC_SECRET = os.getenv("WOOCOMMERCE_CONSUMER_SECRET", "")
AI_KEY = os.getenv("OPENAI_API_KEY", "")
AI_BASE = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
AI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# In-memory demo data: changes reset when the server restarts.
PRODUCTS: list[dict[str, Any]] = [
    {"id": 101, "name": "Cotton T-Shirt", "type": "simple", "regular_price": "499", "cost_price": "245", "description": "", "short_description": "", "categories": [], "attributes": [{"name": "Color", "options": ["Blue"]}], "sku": "TS-BLU-01", "stock_quantity": 42, "manage_stock": True, "images": [{"src": "demo"}], "status": "publish", "source": "Demo"},
    {"id": 102, "name": "Stainless Steel Water Bottle", "type": "simple", "regular_price": "699", "cost_price": "310", "description": "Reusable bottle for everyday use.", "short_description": "", "categories": [{"id": 4, "name": "Accessories"}], "attributes": [], "sku": "WB-700", "stock_quantity": 4, "manage_stock": True, "images": [{"src": "demo"}], "status": "publish", "source": "Demo"},
    {"id": 103, "name": "Running Shoes", "type": "simple", "regular_price": "2499", "cost_price": "1680", "description": "Comfortable shoes for daily runs.", "short_description": "Running shoes", "categories": [{"id": 7, "name": "Footwear"}], "attributes": [{"name": "Size", "options": ["8"]}, {"name": "Color", "options": ["Black"]}], "sku": "", "stock_quantity": 18, "manage_stock": True, "images": [{"src": "demo"}], "status": "publish", "source": "Demo"},
    {"id": 104, "name": "Ceramic Coffee Mug", "type": "simple", "regular_price": "299", "cost_price": "145", "description": "A ceramic mug for hot drinks.", "short_description": "Coffee mug", "categories": [{"id": 5, "name": "Home"}], "attributes": [{"name": "Capacity", "options": ["300 ml"]}], "sku": "MUG-300", "stock_quantity": 0, "manage_stock": True, "images": [{"src": "demo"}], "status": "publish", "source": "Demo"},
    {"id": 105, "name": "Yoga Mat", "type": "simple", "regular_price": "899", "cost_price": "520", "description": "", "short_description": "Yoga mat", "categories": [{"id": 6, "name": "Fitness"}], "attributes": [], "sku": "YM-01", "stock_quantity": 7, "manage_stock": True, "images": [{"src": "demo"}], "status": "publish", "source": "Demo"},
    {"id": 106, "name": "Everyday Canvas Tote", "type": "simple", "regular_price": "549", "cost_price": "210", "description": "A versatile canvas tote for daily errands, commuting, and carrying your everyday essentials.", "short_description": "A carry-all for everyday plans.", "categories": [{"id": 4, "name": "Accessories"}], "attributes": [{"name": "Color", "options": ["Natural"]}], "sku": "BAG-CNV-06", "stock_quantity": 36, "manage_stock": True, "images": [{"src": "demo"}], "status": "publish", "source": "Demo"},
    {"id": 107, "name": "Wireless Desk Lamp", "type": "simple", "regular_price": "1899", "cost_price": "1120", "description": "A clean-lined desk lamp for focused work and reading. Its compact profile fits neatly on a nightstand or work surface.", "short_description": "A compact lamp for desks and bedside tables.", "categories": [{"id": 5, "name": "Home"}], "attributes": [{"name": "Color", "options": ["Warm white"]}], "sku": "LMP-107", "stock_quantity": 12, "manage_stock": True, "images": [{"src": "demo"}], "status": "publish", "source": "Demo"},
    {"id": 108, "name": "Classic Denim Jacket", "type": "simple", "regular_price": "2299", "cost_price": "1540", "description": "A classic denim jacket designed for easy layering through changing seasons.", "short_description": "Classic denim jacket.", "categories": [{"id": 2, "name": "Clothing"}], "attributes": [{"name": "Size", "options": ["M"]}, {"name": "Color", "options": ["Indigo"]}], "sku": "JKT-DNM-08", "stock_quantity": 3, "manage_stock": True, "images": [], "status": "publish", "source": "Demo"},
    {"id": 109, "name": "Insulated Lunch Bag", "type": "simple", "regular_price": "799", "cost_price": "425", "description": "A lightweight lunch bag for packing meals and snacks for work, school, or a day out.", "short_description": "", "categories": [{"id": 4, "name": "Accessories"}], "attributes": [{"name": "Color", "options": ["Sage"]}], "sku": "LCH-109", "stock_quantity": 21, "manage_stock": True, "images": [{"src": "demo"}], "status": "publish", "source": "Demo"},
    {"id": 110, "name": "Adjustable Dumbbell", "type": "simple", "regular_price": "3499", "cost_price": "2890", "description": "A versatile training essential for home workouts and strength routines.", "short_description": "Dumbbell for home training.", "categories": [{"id": 6, "name": "Fitness"}], "attributes": [{"name": "Weight", "options": ["Adjustable"]}], "sku": "FIT-DB-10", "stock_quantity": 9, "manage_stock": True, "images": [{"src": "demo"}], "status": "publish", "source": "Demo"},
    {"id": 111, "name": "Linen Cushion Cover", "type": "simple", "regular_price": "649", "cost_price": "280", "description": "Refresh your living space with a textured cushion cover in a versatile neutral shade.", "short_description": "Textured cushion cover for a quick room refresh.", "categories": [{"id": 5, "name": "Home"}], "attributes": [{"name": "Size", "options": ["45 x 45 cm"]}], "sku": "HOM-CUS-11", "stock_quantity": 27, "manage_stock": True, "images": [{"src": "demo"}], "status": "publish", "source": "Demo"},
    {"id": 112, "name": "Trail Running Cap", "type": "simple", "regular_price": "449", "cost_price": "205", "description": "A lightweight cap for training sessions, weekend walks, and outdoor routines.", "short_description": "Lightweight cap for outdoor routines.", "categories": [{"id": 7, "name": "Footwear"}], "attributes": [{"name": "Color", "options": ["Charcoal"]}], "sku": "CAP-TR-12", "stock_quantity": 2, "manage_stock": True, "images": [{"src": "demo"}], "status": "publish", "source": "Demo"},
    {"id": 113, "name": "Glass Food Storage Set", "type": "simple", "regular_price": "1199", "cost_price": "690", "description": "A reusable storage set for keeping pantry staples and leftovers organized.", "short_description": "Reusable food storage set.", "categories": [{"id": 5, "name": "Home"}], "attributes": [{"name": "Pieces", "options": ["3"]}], "sku": "KIT-GLS-13", "stock_quantity": 15, "manage_stock": True, "images": [{"src": "demo"}], "status": "publish", "source": "Demo"},
    {"id": 114, "name": "Everyday Crew Socks", "type": "simple", "regular_price": "249", "cost_price": "115", "description": "A simple everyday essential designed to pair with casual and active outfits.", "short_description": "Everyday crew socks.", "categories": [{"id": 2, "name": "Clothing"}], "attributes": [{"name": "Size", "options": ["One size"]}], "sku": "SOC-CR-14", "stock_quantity": 64, "manage_stock": True, "images": [{"src": "demo"}], "status": "publish", "source": "Demo"},
    {"id": 115, "name": "Travel Neck Pillow", "type": "simple", "regular_price": "999", "cost_price": "510", "description": "A compact travel pillow for added comfort on commutes and longer journeys.", "short_description": "Compact pillow for travel days.", "categories": [{"id": 4, "name": "Accessories"}], "attributes": [], "sku": "TRV-PIL-15", "stock_quantity": 5, "manage_stock": True, "images": [{"src": "demo"}], "status": "publish", "source": "Demo"},
    {"id": 116, "name": "Minimal Wall Clock", "type": "simple", "regular_price": "1399", "cost_price": "1045", "description": "A minimal wall clock that brings a practical finishing touch to a home office or living space.", "short_description": "Minimal clock for home spaces.", "categories": [{"id": 5, "name": "Home"}], "attributes": [{"name": "Color", "options": ["Sand"]}], "sku": "HOM-CLK-16", "stock_quantity": 14, "manage_stock": True, "images": [{"src": "demo"}], "status": "publish", "source": "Demo"},
    {"id": 117, "name": "Performance Training Shorts", "type": "simple", "regular_price": "849", "cost_price": "430", "description": "Training shorts for gym sessions, warm-ups, and active weekends.", "short_description": "Shorts for training and active days.", "categories": [{"id": 2, "name": "Clothing"}], "attributes": [{"name": "Size", "options": ["L"]}, {"name": "Color", "options": ["Navy"]}], "sku": "CLT-SHT-17", "stock_quantity": 22, "manage_stock": True, "images": [{"src": "demo"}], "status": "publish", "source": "Demo"},
    {"id": 118, "name": "Pour Over Coffee Dripper", "type": "simple", "regular_price": "599", "cost_price": "295", "description": "A straightforward coffee dripper for a measured, hands-on morning brew.", "short_description": "A simple pour-over coffee dripper.", "categories": [{"id": 5, "name": "Home"}], "attributes": [{"name": "Material", "options": ["Ceramic"]}], "sku": "KIT-COF-18", "stock_quantity": 8, "manage_stock": True, "images": [{"src": "demo"}], "status": "publish", "source": "Demo"},
    {"id": 119, "name": "Foldable Laptop Stand", "type": "simple", "regular_price": "1299", "cost_price": "990", "description": "A foldable laptop stand for creating a more adaptable home or office workspace.", "short_description": "Portable stand for your workspace.", "categories": [{"id": 4, "name": "Accessories"}], "attributes": [{"name": "Color", "options": ["Silver"]}], "sku": "ACC-LAP-19", "stock_quantity": 0, "manage_stock": True, "images": [{"src": "demo"}], "status": "publish", "source": "Demo"},
    {"id": 120, "name": "Resistance Band Set", "type": "simple", "regular_price": "699", "cost_price": "305", "description": "A compact resistance band set for warm-ups and varied at-home movement routines.", "short_description": "Resistance bands for home routines.", "categories": [{"id": 6, "name": "Fitness"}], "attributes": [{"name": "Pieces", "options": ["5"]}], "sku": "FIT-BND-20", "stock_quantity": 31, "manage_stock": True, "images": [{"src": "demo"}], "status": "publish", "source": "Demo"},
]

class GenerateRequest(BaseModel):
    product_id: int
    keywords: str = ""

class UpdateRequest(BaseModel):
    product_id: int
    fields: dict[str, Any] = Field(default_factory=dict)

class SyncRequest(BaseModel):
    product_id: int

class CopilotRequest(BaseModel):
    message: str

def wc_configured() -> bool:
    return bool(WC_URL and WC_KEY and WC_SECRET and urlparse(WC_URL).scheme in ("http", "https"))

def wc_request(method: str, path: str, **kwargs):
    if not wc_configured():
        raise HTTPException(status_code=400, detail="WooCommerce is not configured. Use demo mode or set credentials in .env.")
    try:
        response = requests.request(
            method, f"{WC_URL}/wp-json/wc/v3/{path.lstrip('/')}",
            auth=(WC_KEY, WC_SECRET), timeout=15, **kwargs
        )
        response.raise_for_status()
        return response.json() if response.content else {}
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"WooCommerce request failed: {exc}")

def get_products() -> list[dict]:
    if wc_configured():
        try:
            data = wc_request("GET", "products", params={"per_page": 100})
            for p in data:
                p["source"] = "WooCommerce"
            return data
        except HTTPException:
            # Keep demo visible if store is temporarily unreachable.
            return PRODUCTS
    return PRODUCTS

def audit_product(p: dict) -> list[dict]:
    issues = []
    desc = re.sub(r"<[^>]*>", "", str(p.get("description") or "")).strip()
    short = re.sub(r"<[^>]*>", "", str(p.get("short_description") or "")).strip()
    categories = p.get("categories") or []
    attrs = p.get("attributes") or []
    sku = str(p.get("sku") or "").strip()
    if not desc:
        issues.append({"severity": "High", "field": "description", "message": "Full description is missing."})
    elif len(desc) < 35:
        issues.append({"severity": "Medium", "field": "description", "message": "Description may be too short."})
    if not short:
        issues.append({"severity": "Medium", "field": "short_description", "message": "Short description is missing."})
    if not categories:
        issues.append({"severity": "Medium", "field": "categories", "message": "No product category is assigned."})
    if not attrs:
        issues.append({"severity": "Medium", "field": "attributes", "message": "No product attributes are defined."})
    if not sku:
        issues.append({"severity": "Low", "field": "sku", "message": "SKU is missing."})
    if not p.get("images"):
        issues.append({"severity": "Medium", "field": "images", "message": "No product image is available."})
    try:
        if float(p.get("regular_price") or 0) <= 0:
            issues.append({"severity": "High", "field": "regular_price", "message": "Price should be a positive number."})
    except (ValueError, TypeError):
        issues.append({"severity": "High", "field": "regular_price", "message": "Price should be a positive number."})
    return issues

def local_suggestions(p: dict, keywords: str = "") -> dict:
    name = str(p.get("name") or "Product").strip()
    name_clean = re.sub(r"<[^>]*>", "", name)
    words = keywords.strip()
    desc = (
        f"Discover the {name_clean}, designed for everyday use. "
        f"It combines practical functionality with a simple, versatile design. "
        f"Review the product specifications to make sure it suits your needs."
    )
    short = f"{name_clean} for everyday use."
    seo = f"{name_clean} | Shop Online"
    tags = [w.strip() for w in re.split(r"[,;]", words) if w.strip()]
    if not tags:
        tags = [w.lower() for w in re.findall(r"[A-Za-z0-9]+", name_clean) if len(w) > 2][:5]
    category = "Accessories"
    low = name_clean.lower()
    if any(x in low for x in ["shoe", "sneaker", "boot"]): category = "Footwear"
    elif any(x in low for x in ["shirt", "t-shirt", "jeans", "dress"]): category = "Clothing"
    elif any(x in low for x in ["mug", "bottle", "mat", "lamp"]): category = "Home & Lifestyle"
    elif any(x in low for x in ["yoga", "fitness", "dumbbell"]): category = "Fitness"
    return {"description": desc, "short_description": short, "seo_title": seo, "keywords": tags, "suggested_category": category}

def ai_suggestions(p: dict, keywords: str = "") -> Optional[dict]:
    if not AI_KEY:
        return None
    prompt = (
        "You improve e-commerce product information. Return ONLY valid JSON with keys "
        "description, short_description, seo_title, keywords (array of strings), suggested_category. "
        "Do not invent technical specifications, materials, certifications, health benefits, or guarantees. "
        "Use cautious generic wording when product details are limited. "
        f"Product name: {p.get('name','')}; current description: {p.get('description','')}; "
        f"current attributes: {json.dumps(p.get('attributes') or [])}; extra keywords: {keywords}"
    )
    try:
        r = requests.post(
            f"{AI_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {AI_KEY}", "Content-Type": "application/json"},
            json={"model": AI_MODEL, "temperature": 0.3, "messages": [{"role": "system", "content": "Return valid JSON only."}, {"role": "user", "content": prompt}]},
            timeout=25,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
        result = json.loads(content)
        for key in ["description", "short_description", "seo_title", "keywords", "suggested_category"]:
            if key not in result:
                raise ValueError(f"Missing {key}")
        return result
    except Exception:
        return None

@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.get("/api/status")
def status():
    return {"app": "CatalogPilot AI", "mode": "WooCommerce" if wc_configured() else "Demo", "woocommerce_configured": wc_configured(), "ai_configured": bool(AI_KEY)}

@app.get("/api/products")
def products():
    return get_products()

@app.get("/api/audit")
def audit():
    data = get_products()
    results = []
    for p in data:
        issues = audit_product(p)
        penalty = sum({"High": 25, "Medium": 12, "Low": 5}.get(x["severity"], 5) for x in issues)
        results.append({"product_id": p.get("id"), "name": p.get("name"), "issue_count": len(issues), "score": max(0, 100 - penalty), "issues": issues})
    return {"products_checked": len(data), "issues_total": sum(x["issue_count"] for x in results), "results": results}

@app.get("/api/insights")
def insights():
    data = get_products()
    audit_data = audit()
    return {
        **catalog_insights(data, audit_data["results"]),
        "margins": margin_analysis(data),
    }

@app.get("/api/channel-readiness")
def channel_readiness_report(channel: str = "amazon"):
    try:
        return channel_readiness(get_products(), channel)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/api/copilot")
def copilot(req: CopilotRequest):
    data = get_products()
    audit_data = audit()
    return copilot_answer(req.message, data, audit_data["results"])

@app.post("/api/generate")
def generate(req: GenerateRequest):
    p = next((x for x in get_products() if int(x.get("id", -1)) == req.product_id), None)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    suggestion = ai_suggestions(p, req.keywords)
    mode = "AI API" if suggestion is not None else "Local generator"
    if suggestion is None:
        suggestion = local_suggestions(p, req.keywords)
    return {"product_id": req.product_id, "suggestion": suggestion, "mode": mode, "note": "Review all suggestions before publishing."}

@app.post("/api/update")
def update(req: UpdateRequest):
    allowed = {"name", "description", "short_description", "sku", "regular_price", "stock_quantity"}
    if not req.fields or any(k not in allowed for k in req.fields):
        raise HTTPException(status_code=400, detail=f"Allowed fields: {', '.join(sorted(allowed))}")
    fields = dict(req.fields)
    if "stock_quantity" in fields:
        quantity = fields["stock_quantity"]
        if isinstance(quantity, bool):
            raise HTTPException(status_code=400, detail="Stock quantity must be a non-negative whole number.")
        try:
            numeric_quantity = float(quantity)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Stock quantity must be a non-negative whole number.")
        if not numeric_quantity.is_integer() or numeric_quantity < 0:
            raise HTTPException(status_code=400, detail="Stock quantity must be a non-negative whole number.")
        fields["stock_quantity"] = int(numeric_quantity)
    if wc_configured():
        payload = {**fields, **({"manage_stock": True} if "stock_quantity" in fields else {})}
        result = wc_request("PUT", f"products/{req.product_id}", json=payload)
        return {"ok": True, "product": result, "message": "Updated in WooCommerce."}
    p = next((x for x in PRODUCTS if int(x.get("id", -1)) == req.product_id), None)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    p.update(fields)
    if "stock_quantity" in fields:
        p["manage_stock"] = True
    return {"ok": True, "product": p, "message": "Updated in demo memory. Changes reset when the server restarts."}

@app.post("/api/sync")
def sync(req: SyncRequest):
    if not wc_configured():
        raise HTTPException(status_code=400, detail="Live sync needs WooCommerce credentials in .env. In demo mode, use Save Changes to update sample data.")
    # Confirm the product exists in the connected store.
    product = wc_request("GET", f"products/{req.product_id}")
    return {"ok": True, "product_id": req.product_id, "name": product.get("name"), "status": "Connected", "message": "Product is reachable in WooCommerce. Use Save Changes to push approved field updates."}
