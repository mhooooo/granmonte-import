# Data Schema — wine_data.json

The wine_manager.py script uses a single JSON file as its data store. This document describes the full schema.

## Top-level structure

```json
{
  "metadata": {
    "created": "2026-04-01T00:00:00Z",
    "last_modified": "2026-04-02T12:30:00Z",
    "version": "1.0",
    "business": "GranMonte Thai Wine — FL Distribution",
    "exchange_rate": 36.5,
    "exchange_rate_date": "2026-04-01"
  },
  "catalog": [ ...SKU objects... ],
  "prospects": [ ...prospect objects... ],
  "inventory": [ ...inventory records... ],
  "sales": [ ...sale transaction objects... ],
  "quotes": [ ...quote objects... ],
  "cola_status": [ ...COLA tracking objects... ]
}
```

## Catalog (SKU definitions)

```json
{
  "sku": "GM-SCB",
  "name": "Spring Chenin Blanc",
  "varietal": "Chenin Blanc",
  "vintage": 2023,
  "fob_thb": 3200,
  "case_pack": 12,
  "bottle_ml": 750,
  "abv": 12.5,
  "description": "Crisp white with tropical fruit notes, Khao Yai terroir"
}
```

## Prospects

```json
{
  "id": "P001",
  "name": "Thai Basil Restaurant",
  "city": "Miami",
  "metro": "Miami",
  "address": "123 Main St, Miami, FL 33101",
  "contact_name": "Somchai",
  "contact_phone": "305-555-1234",
  "contact_email": "somchai@thaibasil.com",
  "commitment_cases_monthly": 5,
  "status": "lead",
  "notes": "",
  "created_date": "2026-04-01",
  "last_contact_date": "2026-04-01",
  "quoted": false,
  "quote_id": null
}
```

**Status values:** `lead` → `contacted` → `quoted` → `sampling` → `committed` → `active` → `churned`

## Inventory

```json
{
  "sku": "GM-SCB",
  "cases_on_hand": 50,
  "cases_committed": 15,
  "cases_available": 35,
  "last_received_date": "2026-04-01",
  "last_sold_date": null,
  "movements": [
    {
      "date": "2026-04-01",
      "type": "receive",
      "cases": 50,
      "reference": "Shipment #001"
    }
  ]
}
```

## Sales

```json
{
  "id": "S001",
  "date": "2026-04-02",
  "restaurant_id": "P001",
  "restaurant_name": "Thai Basil Restaurant",
  "items": [
    {
      "sku": "GM-SCB",
      "cases": 5,
      "price_per_case": 120.00,
      "total": 600.00
    }
  ],
  "subtotal": 600.00,
  "tax": 0,
  "total": 600.00,
  "payment_terms": "NET30",
  "payment_status": "pending",
  "invoice_number": "INV-2026-001"
}
```

## Quotes

```json
{
  "id": "Q001",
  "date": "2026-04-01",
  "restaurant_id": "P001",
  "restaurant_name": "Thai Basil Restaurant",
  "valid_until": "2026-04-30",
  "items": [
    {
      "sku": "GM-SCB",
      "name": "Spring Chenin Blanc",
      "cases": 10,
      "bottles": 120,
      "price_per_bottle": 10.00,
      "price_per_case": 120.00,
      "line_total": 1200.00
    }
  ],
  "subtotal": 1200.00,
  "payment_terms": "NET30",
  "notes": "",
  "status": "draft",
  "margin_pct": 35
}
```

## COLA Status

```json
{
  "sku": "GM-SCB",
  "wine_name": "Spring Chenin Blanc",
  "cola_id": null,
  "status": "not_submitted",
  "submitted_date": null,
  "approved_date": null,
  "expiry_date": null,
  "notes": ""
}
```

**Status values:** `not_submitted` → `submitted` → `under_review` → `approved` → `expired`
