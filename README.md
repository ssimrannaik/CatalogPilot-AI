# CatalogPilot AI — PIM System Integration Hackathon Project

CatalogPilot AI is a working starter project for a Product Information Management (PIM) challenge. It audits product data, generates suggested product content, and can update a WooCommerce store after a human reviews the changes.

## Features
- Commerce operations dashboard with product health, category mix, priority alerts, and current inventory insights
- Product catalog search and category/stock filters with CSV export
- Dedicated inventory, content studio, pricing, analytics, data quality, AI Copilot, and store connection portals
- Inventory stock updates and product content edits with human approval
- Gross-margin analysis when unit cost data is available (excludes taxes, shipping, fees, and operating costs)
- Product data quality audit: missing descriptions, short descriptions, categories, attributes and SKUs
- Channel readiness checks for illustrative Amazon Marketplace and Shopify Storefront catalog checklists
- AI content suggestions (built-in local generator works without an API key)
- Catalog Copilot for incomplete product, duplicate-candidate, stock, SEO, and pricing questions
- Optional OpenAI-compatible chat-completions API support
- Human review before saving changes
- Demo mode with 20 sample products across five categories, including stock and unit-cost data
- Optional WooCommerce REST API connection
- Responsive interface

## Requirements
- Python 3.10 or newer
- VS Code
- Internet only for installing packages or connecting a real WooCommerce/API service

## Run in VS Code (Windows)

1. Extract the ZIP.
2. Open the `CatalogPilot_AI` folder in VS Code (`File > Open Folder`).
3. Open Terminal > New Terminal.
4. Create a virtual environment:

   ```powershell
   py -m venv .venv
   ```

5. Activate it:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, run this in the current terminal only:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\.venv\Scripts\Activate.ps1
   ```

6. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

7. Start the app:

   ```powershell
   uvicorn app:app --reload
   ```

8. Open this address in your browser:

   `http://127.0.0.1:8000`

Demo mode works without WooCommerce credentials and without an AI API key.

## Optional: use an AI API
1. Copy `.env.example` to a new file named `.env`.
2. Add your provider's API key to `OPENAI_API_KEY`.
3. Set `OPENAI_BASE_URL` and `OPENAI_MODEL` if using a compatible provider.
4. Stop and restart the server.

Never commit `.env` or expose API keys in frontend JavaScript. If the AI API fails or returns unexpected data, the app falls back to its local generator.

## Optional: connect WooCommerce
1. Use a test/staging WooCommerce store first.
2. In WordPress, create REST API credentials with the minimum permissions needed.
3. Copy `.env.example` to `.env`.
4. Set `WOOCOMMERCE_URL`, `WOOCOMMERCE_CONSUMER_KEY`, and `WOOCOMMERCE_CONSUMER_SECRET`.
5. Restart the server.

The backend requests product data from `/wp-json/wc/v3/products`. Saving approved descriptions, short descriptions, SKU, or price uses the WooCommerce product update endpoint. Ensure your store uses HTTPS and never share the credentials. Demo mode is used when credentials are missing.

## Demo script for judges
1. Open the dashboard and show the product count.
2. Click **Run audit** and explain the missing product information.
3. Select **Review** beside Cotton T-Shirt.
4. Click **Generate AI suggestions**.
5. Review and edit the suggested description and short description.
6. Click **Approve & save**.
7. Show the refreshed issue count and explain that live WooCommerce updates require valid credentials.

## API endpoints
- `GET /api/status` — current mode and API configuration
- `GET /api/products` — product catalog
- `GET /api/audit` — audit summary and issues
- `GET /api/channel-readiness?channel=amazon` or `?channel=shopify` — product readiness scores and checklist guidance
- `POST /api/generate` — generate content suggestions
- `POST /api/update` — save approved fields
- `POST /api/sync` — check that a product is reachable in a configured WooCommerce store

## Important prototype notes
- Demo changes are stored in memory and reset when the server restarts.
- Channel readiness profiles are illustrative guidance, not official channel requirements, listing approval, or publishing integrations. Requirements vary by product category and seller account; verify them with each channel before publishing.
- SEO title, keywords and suggested category are shown as recommendations; this starter does not write them into custom WooCommerce SEO fields.
- This is a hackathon prototype, not production software. Before production use, add authentication, role-based access, persistent database storage, request rate limiting, audit-log persistence, and stronger input validation.
