"""Deterministic catalog intelligence features; no external AI key required."""
from __future__ import annotations
import re
from urllib.parse import urlparse

DEFAULT_RULES = [
    {"id":"description_minimum", "name":"Useful product description", "enabled":True, "severity":"Medium", "field":"description", "kind":"min_length", "value":50, "message":"Description should contain at least 50 characters."},
    {"id":"sku_required", "name":"SKU required", "enabled":True, "severity":"Low", "field":"sku", "kind":"required", "value":True, "message":"Add a unique SKU to simplify inventory tracking."},
    {"id":"image_required", "name":"Product image required", "enabled":True, "severity":"Medium", "field":"images", "kind":"required_list", "value":True, "message":"Add at least one product image."},
    {"id":"category_required", "name":"Category required", "enabled":True, "severity":"Low", "field":"categories", "kind":"required_list", "value":True, "message":"Assign a category so customers can browse products."},
    {"id":"price_positive", "name":"Price must be positive", "enabled":True, "severity":"High", "field":"regular_price", "kind":"positive_number", "value":True, "message":"Price should be a positive number."},
]

def plain(value):
    return re.sub(r"<[^>]*>", "", str(value or "")).strip()

CHANNEL_PROFILES = {
    "amazon": {
        "name": "Amazon Marketplace",
        "description": "Illustrative marketplace checklist; actual requirements vary by category and seller account.",
        "requirements": [
            {"field": "name", "label": "Product title", "guidance": "Add a clear customer-facing product title."},
            {"field": "description", "label": "Product description (120+ characters)", "minimum": 120, "guidance": "Use Content Studio to draft a fuller, factual description."},
            {"field": "sku", "label": "Seller SKU", "guidance": "Add a unique seller SKU for catalog tracking."},
            {"field": "regular_price", "label": "Positive selling price", "guidance": "Set a valid price greater than zero."},
            {"field": "category", "label": "Product category", "guidance": "Map the product to the most relevant marketplace category."},
            {"field": "image", "label": "At least one product image", "guidance": "Add a clear, accurate product image."},
            {"field": "attributes", "label": "Product attributes", "guidance": "Add relevant attributes such as size, color, or material where applicable."},
        ],
    },
    "shopify": {
        "name": "Shopify Storefront",
        "description": "Illustrative storefront checklist; this is not a Shopify publishing or policy validation.",
        "requirements": [
            {"field": "name", "label": "Product title", "guidance": "Add a clear customer-facing product title."},
            {"field": "description", "label": "Product description (50+ characters)", "minimum": 50, "guidance": "Use Content Studio to draft a useful, factual description."},
            {"field": "regular_price", "label": "Positive selling price", "guidance": "Set a valid price greater than zero."},
            {"field": "category", "label": "Product category", "guidance": "Choose an appropriate product category or product type."},
            {"field": "image", "label": "At least one product image", "guidance": "Add a clear, accurate product image."},
        ],
    },
}


def channel_readiness(products, channel):
    """Score products against a transparent demo checklist for a sales channel."""
    profile = CHANNEL_PROFILES.get(channel)
    if profile is None:
        raise ValueError(f"Unsupported channel '{channel}'. Choose one of: {', '.join(CHANNEL_PROFILES)}.")

    results = []
    requirements = profile["requirements"]
    for product in products:
        issues = []
        for requirement in requirements:
            field = requirement["field"]
            value = product.get(field)
            missing = False
            if field == "name":
                missing = not plain(value)
            elif field == "description":
                missing = len(plain(value)) < requirement["minimum"]
            elif field == "sku":
                missing = not plain(value)
            elif field == "regular_price":
                try:
                    price = float(value)
                    missing = not (price > 0 and price < float("inf"))
                except (TypeError, ValueError):
                    missing = True
            elif field == "category":
                categories = product.get("categories") or []
                missing = not any(
                    plain(category.get("name") if isinstance(category, dict) else category)
                    for category in categories
                )
            elif field == "image":
                missing = not any(
                    isinstance(image, dict) and (plain(image.get("src")) or plain(image.get("id")))
                    for image in product.get("images") or []
                )
            elif field == "attributes":
                missing = not any(
                    isinstance(attribute, dict)
                    and plain(attribute.get("name"))
                    and bool(attribute.get("options"))
                    for attribute in product.get("attributes") or []
                )
            if missing:
                issues.append({
                    "field": field,
                    "label": requirement["label"],
                    "guidance": requirement["guidance"],
                })

        score = round((len(requirements) - len(issues)) / len(requirements) * 100)
        results.append({
            "product_id": product.get("id"),
            "name": plain(product.get("name")) or "Unnamed product",
            "score": score,
            "ready": not issues,
            "issues": issues,
        })

    ready_count = sum(result["ready"] for result in results)
    return {
        "channel": channel,
        "name": profile["name"],
        "description": profile["description"],
        "requirements": [
            {"field": item["field"], "label": item["label"]}
            for item in requirements
        ],
        "products_checked": len(results),
        "ready_count": ready_count,
        "needs_work_count": len(results) - ready_count,
        "average_score": round(sum(result["score"] for result in results) / len(results)) if results else 0,
        "results": results,
    }


def rule_issues(product, rules):
    found=[]
    for rule in rules:
        if not rule.get('enabled', True): continue
        field=rule.get('field',''); value=product.get(field)
        kind=rule.get('kind'); failed=False
        if kind=='required': failed=not plain(value)
        elif kind=='required_list': failed=not isinstance(value,list) or len(value)==0
        elif kind=='min_length': failed=len(plain(value)) < int(rule.get('value',0))
        elif kind=='positive_number':
            try: failed=float(value)<=0
            except (ValueError,TypeError): failed=True
        elif kind=='url': failed=not urlparse(plain(value)).scheme in ('http','https')
        if failed: found.append({"rule_id":rule.get('id'),"rule":rule.get('name'),"severity":rule.get('severity','Medium'),"field":field,"message":rule.get('message','Rule failed.')})
    return found

def catalog_insights(products, audit_results):
    by_id={int(a['product_id']):a for a in audit_results}
    scores=[by_id.get(int(p.get('id',-1)),{}).get('score',100) for p in products]
    categories={}
    for p in products:
        for c in p.get('categories') or []:
            name=c.get('name','Uncategorized') if isinstance(c,dict) else str(c)
            categories[name]=categories.get(name,0)+1
    low_stock=[]; out_of_stock=[]; no_image=[]; no_description=[]; invalid_price=[]
    for p in products:
        qty=p.get('stock_quantity')
        if p.get('manage_stock') and qty is not None:
            try:
                quantity=int(qty)
                if quantity<=0: out_of_stock.append({"id":p.get('id'),"name":p.get('name'),"stock_quantity":quantity})
                elif quantity<=5: low_stock.append({"id":p.get('id'),"name":p.get('name'),"stock_quantity":quantity})
            except (ValueError,TypeError): pass
        elif p.get('stock_status')=='outofstock':
            out_of_stock.append({"id":p.get('id'),"name":p.get('name'),"stock_quantity":qty})
        if not p.get('images'): no_image.append({"id":p.get('id'),"name":p.get('name')})
        if not plain(p.get('description')): no_description.append({"id":p.get('id'),"name":p.get('name')})
        try:
            if float(p.get('regular_price') or 0)<=0: invalid_price.append({"id":p.get('id'),"name":p.get('name')})
        except (ValueError,TypeError): invalid_price.append({"id":p.get('id'),"name":p.get('name')})
    return {
      "catalog_size":len(products),"average_health":round(sum(scores)/len(scores)) if scores else 0,
      "healthy_products":sum(1 for s in scores if s>=80),"critical_products":sum(1 for s in scores if s<50),
      "category_distribution":[{"category":k,"count":v} for k,v in sorted(categories.items(),key=lambda x:(-x[1],x[0]))],
      "alerts":{"low_stock":low_stock,"out_of_stock":out_of_stock,"missing_images":no_image,"missing_descriptions":no_description,"invalid_prices":invalid_price},
      "top_priority_products":sorted([{"id":p.get('id'),"name":p.get('name'),"score":by_id.get(int(p.get('id',-1)),{}).get('score',100)} for p in products],key=lambda x:x['score'])[:8]
    }

def copilot_answer(message, products, audit_results):
    q=plain(message).lower(); audit_by_id={int(a['product_id']):a for a in audit_results}
    if not q: return {"intent":"help","answer":"Ask me to find incomplete products, show duplicate candidates, review catalog health, find low-stock items, or explain how to improve SEO.","items":[]}
    if any(k in q for k in ['duplicate','same product','repeated']):
        seen={}; dup=[]
        for p in products:
            name=re.sub(r'[^a-z0-9]+',' ',plain(p.get('name')).lower()).strip()
            sku=plain(p.get('sku')).lower()
            key=('sku',sku) if sku else ('name',name)
            if key[1] and key in seen: dup.append({"id":p.get('id'),"name":p.get('name'),"possible_match":seen[key].get('name'),"match_by":key[0]})
            elif key[1]: seen[key]=p
        return {"intent":"duplicates","answer":f"Found {len(dup)} possible duplicate candidate(s). Verify before merging or deleting anything.","items":dup}
    if any(k in q for k in ['stock','inventory','out of stock','low stock']) :
        items=[]
        for p in products:
            qty=p.get('stock_quantity')
            if p.get('stock_status')=='outofstock' or (p.get('manage_stock') and qty is not None and str(qty).lstrip('-').isdigit() and int(qty)<=5):
                items.append({"id":p.get('id'),"name":p.get('name'),"stock_quantity":qty,"stock_status":p.get('stock_status','unknown')})
        return {"intent":"stock_alerts","answer":f"Found {len(items)} product(s) that are out of stock or at/below the 5-unit alert threshold. Demo products without inventory data cannot be assessed.","items":items}
    if any(k in q for k in ['incomplete','missing','fix','attention','audit','quality','health']):
        items=[]
        for p in products:
            a=audit_by_id.get(int(p.get('id',-1)),{})
            if a.get('issue_count',0): items.append({"id":p.get('id'),"name":p.get('name'),"score":a.get('score',0),"issue_count":a.get('issue_count',0),"issues":a.get('issues',[])})
        items.sort(key=lambda x:(x['score'],-x['issue_count']))
        return {"intent":"catalog_audit","answer":f"{len(items)} product(s) need attention. Start with the lowest health score; review every proposed change before publishing.","items":items[:30]}
    if any(k in q for k in ['seo','search engine','keyword','google']):
        return {"intent":"seo_guidance","answer":"SEO checklist: use a specific readable product title; write a unique factual description; include relevant search terms naturally; add useful image alt text; fill category and product attributes; avoid keyword stuffing and unsupported claims. Use the Content Studio to prepare suggestions, then review them.","items":[]}
    if any(k in q for k in ['price','margin','profit','cost']):
        return {"intent":"pricing_guidance","answer":"For a margin review, add each product's unit cost. Gross margin = (selling price − unit cost) ÷ selling price × 100. This excludes shipping, tax, platform fees, discounts and other operating costs, so it is not net profit.","items":[]}
    return {"intent":"help","answer":"I can audit product completeness, list possible duplicates, check available stock fields, explain SEO improvements, and guide pricing/margin analysis. Try: ‘Find incomplete products’ or ‘Show low stock items’. I prepare insights only; I do not publish changes automatically.","items":[]}

def margin_analysis(products):
    rows=[]
    for p in products:
        if p.get('cost_price') in (None, ''): continue
        try: price=float(p.get('regular_price') or 0); cost=float(p.get('cost_price'))
        except (ValueError,TypeError): continue
        if price<=0 or cost<0: continue
        profit=price-cost; margin=round(profit/price*100,2)
        rows.append({"id":p.get('id'),"name":p.get('name'),"price":price,"cost":cost,"gross_profit_per_unit":round(profit,2),"gross_margin_percent":margin,"flag":"Review margin" if margin<20 else "Healthy margin"})
    return {"products_analyzed":len(rows),"rows":sorted(rows,key=lambda x:x['gross_margin_percent'])}
