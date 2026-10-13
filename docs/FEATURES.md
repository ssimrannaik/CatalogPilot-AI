# CatalogPilot AI — Feature Guide

## Core catalog management
- SQLite-backed demo catalog that persists after restart.
- Product editor and individual save workflow.
- CSV import/export with JSON-compatible columns for categories, attributes and images.
- Bulk field updates for selected products.
- Product health scores and catalog audit for descriptions, SKU, categories, attributes, images and price.
- Duplicate-name and duplicate-SKU checks.
- Change history with restore for locally stored demo products.

## AI-assisted content
- Content suggestions for product name, description, short description, SEO title, meta description, keywords, suggested category and image alt text.
- Built-in safe generator works without API credentials.
- Optional OpenAI-compatible chat completions endpoint via `.env` for enhanced generation and translations.
- Translation preview clearly identifies when no translation provider is configured.
- Suggestions are never automatically published.

## Catalog Intelligence Lab
- Catalog Copilot with rule-based intents for incomplete products, duplicate candidates, stock alerts, SEO guidance and pricing guidance.
- Catalog insight cards: average health, critical/healthy products, missing descriptions/images, low-stock alerts and invalid prices.
- Configurable validation rules editable in the dashboard and saved locally in `catalog_rules.json`.
- Gross margin analysis for products with both selling price and `cost_price`.
- Create draft products in local demo mode.
- Download a JSON audit/insights report.

## Integrations
- Optional WooCommerce product listing and update integration using REST API keys.
- Live WooCommerce credentials are required for store integration. Never commit real credentials.
- Product creation is intentionally disabled for live WooCommerce in this prototype to reduce accidental live-store changes.

## Current boundaries
- No authentication or multi-user permissions.
- No production-grade queue/retry service, webhook processing or scheduled sync.
- Image checking currently detects missing images; it does not certify image quality or copyright.
- Rule-based copilot is not an unrestricted autonomous agent and does not make changes on its own.
- Gross margin is not net profit and excludes fees, taxes, shipping, discounts and overhead.
