---
name: wine-import-assistant
description: "Manage GranMonte Thai wine import operations for the US market. Track Florida Thai restaurant prospects and their order commitments, calculate landed import costs (container shipping, TTB fees, COLA applications, state licensing), generate wholesale price quotes for restaurant buyers, manage wine inventory by SKU (Spring Chenin Blanc, Heritage Syrah, Sakuna Rosé, The Orient Syrah), and produce monthly sales reports. Use this skill whenever the user mentions wine importing, GranMonte, Thai wine, restaurant prospects, wholesale pricing, wine inventory, COLA applications, TTB compliance, distributor licensing, wine cost calculations, landed cost, container shipping for wine, restaurant order tracking, or wine sales reports — even if they don't say 'wine-import-assistant' explicitly. Also trigger when the user asks about Thai restaurant outreach in Florida, wine markup calculations, or needs to prepare quotes or reports for the wine business."
---

# Wine Import Assistant

Manages the full operational lifecycle of importing GranMonte Thai wine into the Florida market, selling to Thai restaurants through direct distribution.

## Context

**Brand:** GranMonte — Thailand's premier vineyard in Khao Yai, producing award-winning wines from Thai terroir.

**Market:** Thai restaurants in Florida (Miami, Orlando, Tampa, Fort Lauderdale, Jacksonville, Gainesville metro areas).

**Business model:** Import Thai wine → Distribute directly to FL Thai restaurants → Build volume to qualify for or bypass traditional distributor requirements.

**Regulatory status:**
- TTB federal import permit: ✅ Done
- Federal import license: ✅ Secured
- FL JDBW distributor license: ❌ Pending (bottleneck — requires $20K/month consecutive sales for 6 months through existing distributor, or alternative path via LibDib)

**Product catalog (4 SKUs):**

| SKU Code | Wine | Varietal | Vintage | FOB Price (THB) | Case Pack |
|----------|------|----------|---------|-----------------|-----------|
| GM-SCB | Spring Chenin Blanc | Chenin Blanc | 2023 | ฿3,200 | 12 |
| GM-HS | Heritage Syrah | Syrah | 2022 | ฿4,800 | 12 |
| GM-SR | Sakuna Rosé | Rosé blend | 2023 | ฿2,800 | 12 |
| GM-TOS | The Orient Syrah | Syrah | 2021 | ฿5,600 | 12 |

## Workflow

When the user asks for anything wine-import related, follow these steps:

### 1. Identify the task type

Classify what the user needs into one of these categories:

- **Prospect tracking** — Add, update, or review restaurant prospect pipeline
- **Cost calculation** — Calculate landed cost per bottle/case for a specific shipment scenario
- **Price quoting** — Generate a wholesale price sheet or custom quote for a restaurant
- **Inventory management** — Check stock levels, update inventory after shipments/sales, track by SKU
- **Sales reporting** — Generate monthly or custom-period sales summary with revenue, volume, margins

### 2. Load or initialize data

The skill uses a JSON data store. Check if `scripts/wine_data.json` exists in the workspace:
- If yes, read it to get current state
- If no, run `python scripts/wine_manager.py init` to create a fresh data store with the 4 SKUs pre-loaded

The data store schema is documented in `references/data-schema.md`.

### 3. Execute the task

Run the appropriate command via the Python script:

```bash
# Prospect management
python scripts/wine_manager.py prospect add --name "Thai Basil" --city "Miami" --contact "Somchai" --phone "305-555-1234" --commitment 5
python scripts/wine_manager.py prospect list
python scripts/wine_manager.py prospect update --id P001 --status "quoted"
python scripts/wine_manager.py prospect pipeline

# Cost calculation
python scripts/wine_manager.py cost calculate --cases 100 --shipping-method "LCL" --exchange-rate 36.5
python scripts/wine_manager.py cost calculate --cases 500 --shipping-method "FCL" --exchange-rate 36.5
python scripts/wine_manager.py cost breakdown --sku GM-SCB --cases 50

# Price quoting
python scripts/wine_manager.py quote generate --restaurant "Thai Basil" --skus GM-SCB,GM-HS --cases 10,5 --margin 35
python scripts/wine_manager.py quote list

# Inventory
python scripts/wine_manager.py inventory status
python scripts/wine_manager.py inventory receive --sku GM-SCB --cases 50 --date "2026-04-01"
python scripts/wine_manager.py inventory sell --sku GM-SCB --cases 5 --restaurant "Thai Basil" --date "2026-04-02"

# Sales reporting
python scripts/wine_manager.py report monthly --month 2026-03
python scripts/wine_manager.py report summary --start 2026-01-01 --end 2026-03-31
python scripts/wine_manager.py report top-restaurants --limit 10
```

### 4. Present results

Format output based on the task:

- **Prospect list** → Table with columns: ID, Name, City, Contact, Commitment (cases/mo), Status, Last Contact
- **Cost calculation** → Itemized breakdown table showing FOB, freight, insurance, customs, TTB, COLA, state fees, total landed cost per bottle and per case
- **Price quote** → Professional quote document with restaurant name, date, line items, suggested retail, payment terms
- **Inventory** → Dashboard-style table with SKU, wine name, cases on hand, cases committed, cases available, last movement date
- **Sales report** → Summary with total revenue, cases sold, margin, breakdown by SKU and by restaurant, comparison to previous period if data exists

### 5. Cost calculation reference

These are the standard cost components for calculating landed cost. The script uses these defaults but they can be overridden:

| Cost Component | Default Value | Notes |
|----------------|---------------|-------|
| Ocean freight (LCL) | $180/CBM | Less-than-container load |
| Ocean freight (FCL) | $3,500/20ft | Full container (~1,200 cases) |
| Marine insurance | 1.1% of CIF | Standard cargo insurance |
| US Customs duty (wine) | $0.21/liter | Still wine under 14% ABV |
| TTB excise tax | $1.07/gallon | Federal excise for table wine |
| COLA application | $0/label | Free to file, but ~45 day lead time |
| FL state excise | $2.25/gallon | Florida wine excise tax |
| Customs broker fee | $175/shipment | Entry processing |
| Drayage | $350-600 | Port to warehouse |
| Warehouse (monthly) | $0.50/case | Cold storage |
| THB→USD exchange | Variable | Check current rate; ~36.5 default |

### 6. Margin guidelines

| Channel | Target Markup | Notes |
|---------|--------------|-------|
| Restaurant wholesale | 30-40% | Over landed cost |
| Distributor (if using) | 25-30% | Their margin on top of yours |
| Suggested retail (restaurant) | 200-300% | Over wholesale, standard for wine |

## Important business rules

- **Never auto-send quotes or commitments** — always draft and let the user review before any customer-facing output
- **Exchange rate sensitivity** — always show the exchange rate used in any cost calculation, and flag if it's stale (>7 days)
- **COLA tracking** — each wine label needs an approved COLA before it can be sold. Track COLA status per SKU.
- **FL license status** — until the JDBW license is resolved, flag any operations that assume direct distribution capability
- **Payment terms** — default NET 30 for restaurant accounts; flag any restaurant requesting longer terms

## File locations

- `scripts/wine_manager.py` — Main operational script (run directly)
- `scripts/wine_data.json` — Data store (created on first run)
- `references/data-schema.md` — Full JSON schema documentation
