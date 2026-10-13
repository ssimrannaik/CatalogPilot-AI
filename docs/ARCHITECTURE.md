# Architecture

- `app.py`: FastAPI routes, request validation, SQLite persistence, CSV import/export, optional WooCommerce REST integration.
- `catalogpilot/intelligence.py`: isolated deterministic business rules, catalog insight aggregation, Catalog Copilot intent handling and margin calculations.
- `static/index.html`: single-page dashboard layout.
- `static/styles.css`: responsive visual design.
- `static/app.js`: browser-side API integration and user interactions.
- `catalogpilot.db`: created automatically at runtime; persistent local demo data.
- `catalog_rules.json`: created when rules are saved; do not commit business-specific production rules without review.

## Safety principles
1. AI text is a suggestion, not verified product truth.
2. Product updates require explicit user action.
3. Live WooCommerce changes require API credentials and should be tested on staging first.
4. Reports describe fields available in the source; missing data is not guessed.
