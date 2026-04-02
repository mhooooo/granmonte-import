#!/usr/bin/env python3
"""
GranMonte Thai Wine Import Manager
===================================
CLI tool for managing wine import operations: prospects, costs, quotes, inventory, and sales.
Data persists in wine_data.json alongside this script.

Usage:
    python wine_manager.py <command> <subcommand> [options]

Commands:
    init                          Initialize fresh data store
    prospect  add|list|update|pipeline   Manage restaurant prospects
    cost      calculate|breakdown        Calculate landed import costs
    quote     generate|list              Generate wholesale price quotes
    inventory status|receive|sell        Track wine inventory by SKU
    report    monthly|summary|top-restaurants   Generate sales reports
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ── Constants ────────────────────────────────────────────────────────────────

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wine_data.json")

DEFAULT_CATALOG = [
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
    },
    {
        "sku": "GM-HS",
        "name": "Heritage Syrah",
        "varietal": "Syrah",
        "vintage": 2022,
        "fob_thb": 4800,
        "case_pack": 12,
        "bottle_ml": 750,
        "abv": 14.0,
        "description": "Full-bodied red with dark fruit and spice, flagship varietal"
    },
    {
        "sku": "GM-SR",
        "name": "Sakuna Rosé",
        "varietal": "Rosé blend",
        "vintage": 2023,
        "fob_thb": 2800,
        "case_pack": 12,
        "bottle_ml": 750,
        "abv": 12.0,
        "description": "Light and refreshing rosé, perfect with Thai cuisine"
    },
    {
        "sku": "GM-TOS",
        "name": "The Orient Syrah",
        "varietal": "Syrah",
        "vintage": 2021,
        "fob_thb": 5600,
        "case_pack": 12,
        "bottle_ml": 750,
        "abv": 14.5,
        "description": "Premium reserve Syrah, oak-aged, limited production"
    }
]

# Standard import cost defaults
COST_DEFAULTS = {
    "ocean_freight_lcl_per_cbm": 180.00,      # USD per cubic meter
    "ocean_freight_fcl_20ft": 3500.00,          # USD for full 20ft container
    "fcl_capacity_cases": 1200,                 # approx cases per 20ft container
    "marine_insurance_pct": 0.011,              # 1.1% of CIF value
    "us_customs_duty_per_liter": 0.21,          # still wine <14% ABV
    "ttb_excise_per_gallon": 1.07,              # federal excise table wine
    "fl_state_excise_per_gallon": 2.25,         # Florida excise
    "cola_fee": 0.00,                           # free to file
    "customs_broker_fee": 175.00,               # per shipment
    "drayage_low": 350.00,                      # port to warehouse low
    "drayage_high": 600.00,                     # port to warehouse high
    "warehouse_per_case_monthly": 0.50,         # cold storage
    "case_volume_cbm": 0.018,                   # approx CBM per case of 12x750ml
    "bottles_per_case": 12,
    "ml_per_bottle": 750,
    "liters_per_gallon": 3.78541,
    "default_exchange_rate": 36.5               # THB per USD
}


# ── Data Store ───────────────────────────────────────────────────────────────

def load_data() -> dict:
    """Load data from JSON file or return None if not found."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return None


def save_data(data: dict):
    """Save data to JSON file."""
    data["metadata"]["last_modified"] = datetime.utcnow().isoformat() + "Z"
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def init_data() -> dict:
    """Create a fresh data store with default catalog."""
    now = datetime.utcnow().isoformat() + "Z"
    data = {
        "metadata": {
            "created": now,
            "last_modified": now,
            "version": "1.0",
            "business": "GranMonte Thai Wine — FL Distribution",
            "exchange_rate": COST_DEFAULTS["default_exchange_rate"],
            "exchange_rate_date": datetime.utcnow().strftime("%Y-%m-%d")
        },
        "catalog": DEFAULT_CATALOG,
        "prospects": [],
        "inventory": [
            {
                "sku": item["sku"],
                "cases_on_hand": 0,
                "cases_committed": 0,
                "cases_available": 0,
                "last_received_date": None,
                "last_sold_date": None,
                "movements": []
            }
            for item in DEFAULT_CATALOG
        ],
        "sales": [],
        "quotes": [],
        "cola_status": [
            {
                "sku": item["sku"],
                "wine_name": item["name"],
                "cola_id": None,
                "status": "not_submitted",
                "submitted_date": None,
                "approved_date": None,
                "expiry_date": None,
                "notes": ""
            }
            for item in DEFAULT_CATALOG
        ]
    }
    save_data(data)
    return data


def ensure_data() -> dict:
    """Load existing data or initialize fresh."""
    data = load_data()
    if data is None:
        print("📦 No data store found. Initializing fresh database...")
        data = init_data()
        print(f"✅ Data store created at {DATA_FILE}")
        print(f"   - {len(data['catalog'])} SKUs loaded")
        print(f"   - {len(data['inventory'])} inventory records initialized")
        print(f"   - {len(data['cola_status'])} COLA tracking records created")
    return data


# ── Prospect Management ─────────────────────────────────────────────────────

def prospect_add(args):
    """Add a new restaurant prospect."""
    data = ensure_data()
    
    # Generate next ID
    existing_ids = [int(p["id"][1:]) for p in data["prospects"] if p["id"].startswith("P")]
    next_id = max(existing_ids, default=0) + 1
    pid = f"P{next_id:03d}"
    
    prospect = {
        "id": pid,
        "name": args.name,
        "city": args.city or "",
        "metro": args.metro or args.city or "",
        "address": args.address or "",
        "contact_name": args.contact or "",
        "contact_phone": args.phone or "",
        "contact_email": args.email or "",
        "commitment_cases_monthly": args.commitment or 0,
        "status": "lead",
        "notes": args.notes or "",
        "created_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "last_contact_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "quoted": False,
        "quote_id": None
    }
    
    data["prospects"].append(prospect)
    save_data(data)
    
    print(f"✅ Prospect added: {pid} — {args.name}")
    print(f"   City: {prospect['city']}")
    print(f"   Contact: {prospect['contact_name']} ({prospect['contact_phone']})")
    print(f"   Commitment: {prospect['commitment_cases_monthly']} cases/month")
    print(f"   Status: {prospect['status']}")


def prospect_list(args):
    """List all prospects in a table."""
    data = ensure_data()
    prospects = data["prospects"]
    
    if not prospects:
        print("📋 No prospects yet. Add one with: prospect add --name 'Restaurant Name'")
        return
    
    # Filter by status if specified
    if hasattr(args, 'status') and args.status:
        prospects = [p for p in prospects if p["status"] == args.status]
    
    # Print table header
    print(f"\n{'ID':<6} {'Name':<28} {'City':<14} {'Contact':<16} {'Cases/Mo':<10} {'Status':<12} {'Last Contact':<12}")
    print("─" * 100)
    
    for p in prospects:
        print(f"{p['id']:<6} {p['name'][:26]:<28} {p['city'][:12]:<14} {p['contact_name'][:14]:<16} "
              f"{p['commitment_cases_monthly']:<10} {p['status']:<12} {p['last_contact_date']:<12}")
    
    print(f"\nTotal: {len(prospects)} prospects")
    total_commitment = sum(p["commitment_cases_monthly"] for p in prospects)
    print(f"Total monthly commitment: {total_commitment} cases")


def prospect_update(args):
    """Update a prospect's status or details."""
    data = ensure_data()
    
    prospect = next((p for p in data["prospects"] if p["id"] == args.id), None)
    if not prospect:
        print(f"❌ Prospect {args.id} not found")
        return
    
    if args.status:
        old_status = prospect["status"]
        prospect["status"] = args.status
        print(f"   Status: {old_status} → {args.status}")
    if args.commitment:
        prospect["commitment_cases_monthly"] = args.commitment
        print(f"   Commitment: {args.commitment} cases/month")
    if args.notes:
        prospect["notes"] = args.notes
    if args.contact:
        prospect["contact_name"] = args.contact
    if args.phone:
        prospect["contact_phone"] = args.phone
    if args.email:
        prospect["contact_email"] = args.email
    
    prospect["last_contact_date"] = datetime.utcnow().strftime("%Y-%m-%d")
    save_data(data)
    print(f"✅ Prospect {args.id} ({prospect['name']}) updated")


def prospect_pipeline(args):
    """Show prospect pipeline summary by status."""
    data = ensure_data()
    prospects = data["prospects"]
    
    if not prospects:
        print("📋 No prospects in pipeline yet.")
        return
    
    statuses = ["lead", "contacted", "quoted", "sampling", "committed", "active", "churned"]
    pipeline = {s: [] for s in statuses}
    
    for p in prospects:
        if p["status"] in pipeline:
            pipeline[p["status"]].append(p)
    
    print("\n🍷 GranMonte FL — Prospect Pipeline")
    print("=" * 60)
    
    for status in statuses:
        items = pipeline[status]
        if items:
            cases = sum(p["commitment_cases_monthly"] for p in items)
            print(f"\n  {status.upper()} ({len(items)} restaurants, {cases} cases/mo)")
            for p in items:
                print(f"    • {p['name']} ({p['city']}) — {p['commitment_cases_monthly']} cases/mo")
    
    total = len(prospects)
    active = len([p for p in prospects if p["status"] in ("committed", "active")])
    total_cases = sum(p["commitment_cases_monthly"] for p in prospects if p["status"] in ("committed", "active"))
    
    print(f"\n{'─' * 60}")
    print(f"  Total prospects: {total}")
    print(f"  Active/committed: {active}")
    print(f"  Committed cases/month: {total_cases}")
    
    # Revenue projection
    if total_cases > 0:
        avg_case_revenue = 120  # rough average wholesale per case
        monthly_rev = total_cases * avg_case_revenue
        print(f"  Est. monthly revenue: ${monthly_rev:,.0f}")


# ── Cost Calculation ─────────────────────────────────────────────────────────

def cost_calculate(args):
    """Calculate total landed cost for a shipment."""
    data = ensure_data()
    
    cases = args.cases
    exchange_rate = args.exchange_rate or data["metadata"]["exchange_rate"]
    shipping_method = args.shipping_method or "LCL"
    
    catalog = {item["sku"]: item for item in data["catalog"]}
    
    # Average FOB across all SKUs if no specific SKU given
    if hasattr(args, 'sku') and args.sku and args.sku in catalog:
        skus = [catalog[args.sku]]
    else:
        skus = list(catalog.values())
    
    avg_fob_thb = sum(s["fob_thb"] for s in skus) / len(skus)
    avg_fob_usd = avg_fob_thb / exchange_rate
    total_fob_usd = avg_fob_usd * cases
    
    # Shipping
    if shipping_method.upper() == "FCL":
        freight = COST_DEFAULTS["ocean_freight_fcl_20ft"]
        freight_per_case = freight / min(cases, COST_DEFAULTS["fcl_capacity_cases"])
    else:  # LCL
        volume_cbm = cases * COST_DEFAULTS["case_volume_cbm"]
        freight = volume_cbm * COST_DEFAULTS["ocean_freight_lcl_per_cbm"]
        freight_per_case = freight / cases
    
    # Insurance (1.1% of CIF)
    insurance = (total_fob_usd + freight) * COST_DEFAULTS["marine_insurance_pct"]
    
    # Total liters and gallons
    total_bottles = cases * COST_DEFAULTS["bottles_per_case"]
    total_liters = total_bottles * COST_DEFAULTS["ml_per_bottle"] / 1000
    total_gallons = total_liters / COST_DEFAULTS["liters_per_gallon"]
    
    # Duties and taxes
    customs_duty = total_liters * COST_DEFAULTS["us_customs_duty_per_liter"]
    ttb_excise = total_gallons * COST_DEFAULTS["ttb_excise_per_gallon"]
    fl_excise = total_gallons * COST_DEFAULTS["fl_state_excise_per_gallon"]
    
    # Fees
    customs_broker = COST_DEFAULTS["customs_broker_fee"]
    drayage = (COST_DEFAULTS["drayage_low"] + COST_DEFAULTS["drayage_high"]) / 2
    
    # Total landed
    total_landed = (total_fob_usd + freight + insurance + customs_duty +
                    ttb_excise + fl_excise + customs_broker + drayage)
    
    landed_per_case = total_landed / cases
    landed_per_bottle = landed_per_case / COST_DEFAULTS["bottles_per_case"]
    
    # Print breakdown
    print(f"\n🍷 GranMonte Import — Landed Cost Calculation")
    print(f"{'=' * 55}")
    print(f"  Shipment: {cases} cases ({total_bottles} bottles)")
    print(f"  Shipping: {shipping_method.upper()}")
    print(f"  Exchange rate: ฿{exchange_rate} / $1 USD")
    print(f"  Avg FOB per case: ฿{avg_fob_thb:,.0f} (${avg_fob_usd:,.2f})")
    print(f"{'─' * 55}")
    
    print(f"\n  {'Cost Component':<30} {'Total':>12} {'Per Case':>10}")
    print(f"  {'─' * 52}")
    print(f"  {'FOB (ex-works Thailand)':<30} ${total_fob_usd:>11,.2f} ${total_fob_usd/cases:>9,.2f}")
    print(f"  {'Ocean freight (' + shipping_method.upper() + ')':<30} ${freight:>11,.2f} ${freight_per_case:>9,.2f}")
    print(f"  {'Marine insurance (1.1%)':<30} ${insurance:>11,.2f} ${insurance/cases:>9,.2f}")
    print(f"  {'US customs duty':<30} ${customs_duty:>11,.2f} ${customs_duty/cases:>9,.2f}")
    print(f"  {'TTB federal excise':<30} ${ttb_excise:>11,.2f} ${ttb_excise/cases:>9,.2f}")
    print(f"  {'FL state excise':<30} ${fl_excise:>11,.2f} ${fl_excise/cases:>9,.2f}")
    print(f"  {'Customs broker':<30} ${customs_broker:>11,.2f} ${customs_broker/cases:>9,.2f}")
    print(f"  {'Drayage (avg)':<30} ${drayage:>11,.2f} ${drayage/cases:>9,.2f}")
    print(f"  {'─' * 52}")
    print(f"  {'TOTAL LANDED':<30} ${total_landed:>11,.2f} ${landed_per_case:>9,.2f}")
    print(f"\n  Landed cost per bottle: ${landed_per_bottle:.2f}")
    
    # Margin analysis
    print(f"\n  {'Margin Analysis':<30}")
    print(f"  {'─' * 52}")
    for margin_pct in [30, 35, 40]:
        sell_per_bottle = landed_per_bottle / (1 - margin_pct / 100)
        sell_per_case = sell_per_bottle * 12
        print(f"  {f'Wholesale @ {margin_pct}% margin':<30} ${sell_per_case:>11,.2f} ${sell_per_bottle:>9,.2f}")
    
    # Flag exchange rate staleness
    rate_date = data["metadata"].get("exchange_rate_date", "unknown")
    print(f"\n  ⚠️  Exchange rate from: {rate_date}")
    print(f"  ⚠️  FL JDBW distributor license: PENDING — direct distribution not yet authorized")
    
    return {
        "total_landed": total_landed,
        "per_case": landed_per_case,
        "per_bottle": landed_per_bottle,
        "cases": cases,
        "method": shipping_method
    }


def cost_breakdown(args):
    """Show cost breakdown for a specific SKU."""
    data = ensure_data()
    catalog = {item["sku"]: item for item in data["catalog"]}
    
    if args.sku not in catalog:
        print(f"❌ SKU {args.sku} not found. Available: {', '.join(catalog.keys())}")
        return
    
    wine = catalog[args.sku]
    exchange_rate = args.exchange_rate or data["metadata"]["exchange_rate"]
    cases = args.cases or 50
    
    fob_usd_per_case = wine["fob_thb"] / exchange_rate
    fob_usd_per_bottle = fob_usd_per_case / 12
    
    print(f"\n🍷 Cost Breakdown: {wine['name']} ({args.sku})")
    print(f"{'=' * 50}")
    print(f"  Vintage: {wine['vintage']}")
    print(f"  ABV: {wine['abv']}%")
    print(f"  FOB: ฿{wine['fob_thb']:,} / case")
    print(f"  FOB: ${fob_usd_per_case:.2f} / case (${fob_usd_per_bottle:.2f} / bottle)")
    print(f"  Exchange rate: ฿{exchange_rate}")
    print(f"  Quantity: {cases} cases")
    
    # Simulate a cost calculation for this specific SKU
    # Re-use the calculate logic
    class FakeArgs:
        pass
    fake = FakeArgs()
    fake.cases = cases
    fake.exchange_rate = exchange_rate
    fake.shipping_method = "LCL" if cases < 200 else "FCL"
    fake.sku = args.sku
    
    cost_calculate(fake)


# ── Quote Generation ─────────────────────────────────────────────────────────

def quote_generate(args):
    """Generate a wholesale price quote for a restaurant."""
    data = ensure_data()
    catalog = {item["sku"]: item for item in data["catalog"]}
    
    # Parse SKUs and cases
    skus = args.skus.split(",")
    case_counts = [int(c) for c in args.cases.split(",")]
    margin_pct = args.margin or 35
    exchange_rate = data["metadata"]["exchange_rate"]
    
    if len(skus) != len(case_counts):
        print("❌ Number of SKUs must match number of case quantities")
        return
    
    # Validate SKUs
    for sku in skus:
        if sku not in catalog:
            print(f"❌ SKU {sku} not found. Available: {', '.join(catalog.keys())}")
            return
    
    # Generate quote ID
    existing_ids = [int(q["id"][1:]) for q in data["quotes"] if q["id"].startswith("Q")]
    next_id = max(existing_ids, default=0) + 1
    qid = f"Q{next_id:03d}"
    
    # Calculate line items
    items = []
    subtotal = 0
    
    for sku, cases in zip(skus, case_counts):
        wine = catalog[sku]
        fob_per_case = wine["fob_thb"] / exchange_rate
        
        # Rough landed cost estimate (FOB + ~40% for all import costs)
        landed_per_case = fob_per_case * 1.40
        landed_per_bottle = landed_per_case / 12
        
        # Apply margin
        wholesale_per_bottle = landed_per_bottle / (1 - margin_pct / 100)
        wholesale_per_case = wholesale_per_bottle * 12
        line_total = wholesale_per_case * cases
        
        items.append({
            "sku": sku,
            "name": wine["name"],
            "varietal": wine["varietal"],
            "vintage": wine["vintage"],
            "cases": cases,
            "bottles": cases * 12,
            "price_per_bottle": round(wholesale_per_bottle, 2),
            "price_per_case": round(wholesale_per_case, 2),
            "line_total": round(line_total, 2),
            "suggested_retail_low": round(wholesale_per_bottle * 2.5, 2),
            "suggested_retail_high": round(wholesale_per_bottle * 3.5, 2)
        })
        subtotal += line_total
    
    quote = {
        "id": qid,
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "restaurant_id": None,
        "restaurant_name": args.restaurant,
        "valid_until": (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d"),
        "items": items,
        "subtotal": round(subtotal, 2),
        "payment_terms": "NET30",
        "notes": args.notes or "",
        "status": "draft",
        "margin_pct": margin_pct
    }
    
    # Link to prospect if exists
    prospect = next((p for p in data["prospects"] if p["name"].lower() == args.restaurant.lower()), None)
    if prospect:
        quote["restaurant_id"] = prospect["id"]
        prospect["quoted"] = True
        prospect["quote_id"] = qid
        if prospect["status"] in ("lead", "contacted"):
            prospect["status"] = "quoted"
    
    data["quotes"].append(quote)
    save_data(data)
    
    # Print quote
    print(f"\n{'=' * 65}")
    print(f"  WHOLESALE PRICE QUOTE — {qid}")
    print(f"  GranMonte Thai Wine — Florida Distribution")
    print(f"{'=' * 65}")
    print(f"  To:         {args.restaurant}")
    print(f"  Date:       {quote['date']}")
    print(f"  Valid until: {quote['valid_until']}")
    print(f"  Terms:      {quote['payment_terms']}")
    print(f"{'─' * 65}")
    
    print(f"\n  {'Wine':<24} {'Cs':>4} {'Btl':>5} {'$/Btl':>8} {'$/Case':>9} {'Total':>10}")
    print(f"  {'─' * 62}")
    
    for item in items:
        print(f"  {item['name'][:22]:<24} {item['cases']:>4} {item['bottles']:>5} "
              f"${item['price_per_bottle']:>6,.2f} ${item['price_per_case']:>8,.2f} ${item['line_total']:>9,.2f}")
    
    print(f"  {'─' * 62}")
    print(f"  {'SUBTOTAL':<24} {'':>4} {'':>5} {'':>8} {'':>9} ${subtotal:>9,.2f}")
    
    print(f"\n  Suggested Retail Range (per bottle):")
    for item in items:
        print(f"    {item['name']}: ${item['suggested_retail_low']:.2f} – ${item['suggested_retail_high']:.2f}")
    
    print(f"\n  ⚠️  DRAFT — Review before sending to customer")
    print(f"  ⚠️  Margin: {margin_pct}% over estimated landed cost")
    print(f"  ⚠️  Prices subject to exchange rate fluctuation (current: ฿{exchange_rate}/$1)")
    if not any(c["status"] == "approved" for c in data.get("cola_status", [])):
        print(f"  ⚠️  COLA approval pending — cannot ship until labels approved by TTB")


def quote_list(args):
    """List all quotes."""
    data = ensure_data()
    quotes = data.get("quotes", [])
    
    if not quotes:
        print("📋 No quotes yet.")
        return
    
    print(f"\n{'ID':<6} {'Restaurant':<28} {'Date':<12} {'Total':>10} {'Status':<10} {'Margin':>6}")
    print("─" * 75)
    
    for q in quotes:
        print(f"{q['id']:<6} {q['restaurant_name'][:26]:<28} {q['date']:<12} "
              f"${q['subtotal']:>9,.2f} {q['status']:<10} {q['margin_pct']:>5}%")


# ── Inventory Management ────────────────────────────────────────────────────

def inventory_status(args):
    """Show current inventory status."""
    data = ensure_data()
    catalog = {item["sku"]: item for item in data["catalog"]}
    
    print(f"\n🍷 GranMonte Wine Inventory")
    print(f"{'=' * 75}")
    print(f"  {'SKU':<10} {'Wine':<24} {'On Hand':>8} {'Committed':>10} {'Available':>10} {'Last Move':<12}")
    print(f"  {'─' * 73}")
    
    total_on_hand = 0
    total_committed = 0
    total_available = 0
    
    for inv in data["inventory"]:
        wine_name = catalog.get(inv["sku"], {}).get("name", inv["sku"])
        last_move = inv.get("last_received_date") or inv.get("last_sold_date") or "—"
        
        print(f"  {inv['sku']:<10} {wine_name[:22]:<24} {inv['cases_on_hand']:>8} "
              f"{inv['cases_committed']:>10} {inv['cases_available']:>10} {str(last_move):<12}")
        
        total_on_hand += inv["cases_on_hand"]
        total_committed += inv["cases_committed"]
        total_available += inv["cases_available"]
    
    print(f"  {'─' * 73}")
    print(f"  {'TOTAL':<10} {'':<24} {total_on_hand:>8} {total_committed:>10} {total_available:>10}")
    print(f"\n  Total bottles in stock: {total_on_hand * 12}")
    
    # COLA status
    print(f"\n  COLA Status:")
    for cola in data.get("cola_status", []):
        emoji = "✅" if cola["status"] == "approved" else "⏳" if cola["status"] in ("submitted", "under_review") else "❌"
        print(f"    {emoji} {cola['wine_name']}: {cola['status']}")


def inventory_receive(args):
    """Record receiving inventory."""
    data = ensure_data()
    
    inv = next((i for i in data["inventory"] if i["sku"] == args.sku), None)
    if not inv:
        print(f"❌ SKU {args.sku} not found")
        return
    
    date = args.date or datetime.utcnow().strftime("%Y-%m-%d")
    
    inv["cases_on_hand"] += args.cases
    inv["cases_available"] += args.cases
    inv["last_received_date"] = date
    inv["movements"].append({
        "date": date,
        "type": "receive",
        "cases": args.cases,
        "reference": args.reference or f"Received {args.cases} cases"
    })
    
    save_data(data)
    catalog = {item["sku"]: item for item in data["catalog"]}
    wine_name = catalog.get(args.sku, {}).get("name", args.sku)
    
    print(f"✅ Received {args.cases} cases of {wine_name} ({args.sku})")
    print(f"   Date: {date}")
    print(f"   On hand: {inv['cases_on_hand']} cases")
    print(f"   Available: {inv['cases_available']} cases")


def inventory_sell(args):
    """Record a sale (decrease inventory)."""
    data = ensure_data()
    
    inv = next((i for i in data["inventory"] if i["sku"] == args.sku), None)
    if not inv:
        print(f"❌ SKU {args.sku} not found")
        return
    
    if inv["cases_available"] < args.cases:
        print(f"❌ Insufficient inventory. Available: {inv['cases_available']} cases, Requested: {args.cases}")
        return
    
    date = args.date or datetime.utcnow().strftime("%Y-%m-%d")
    restaurant = args.restaurant or "Walk-in"
    
    inv["cases_on_hand"] -= args.cases
    inv["cases_available"] -= args.cases
    inv["last_sold_date"] = date
    inv["movements"].append({
        "date": date,
        "type": "sell",
        "cases": -args.cases,
        "reference": f"Sold to {restaurant}"
    })
    
    # Record sale
    existing_sale_ids = [int(s["id"][1:]) for s in data["sales"] if s["id"].startswith("S")]
    next_id = max(existing_sale_ids, default=0) + 1
    sid = f"S{next_id:03d}"
    
    catalog = {item["sku"]: item for item in data["catalog"]}
    wine = catalog.get(args.sku, {})
    
    # Default price if not specified
    price_per_case = args.price or 120.00
    
    sale = {
        "id": sid,
        "date": date,
        "restaurant_id": None,
        "restaurant_name": restaurant,
        "items": [{
            "sku": args.sku,
            "name": wine.get("name", args.sku),
            "cases": args.cases,
            "price_per_case": price_per_case,
            "total": price_per_case * args.cases
        }],
        "subtotal": price_per_case * args.cases,
        "tax": 0,
        "total": price_per_case * args.cases,
        "payment_terms": "NET30",
        "payment_status": "pending",
        "invoice_number": f"INV-{datetime.utcnow().strftime('%Y')}-{next_id:03d}"
    }
    
    # Link to prospect
    prospect = next((p for p in data["prospects"] if p["name"].lower() == restaurant.lower()), None)
    if prospect:
        sale["restaurant_id"] = prospect["id"]
        if prospect["status"] != "active":
            prospect["status"] = "active"
    
    data["sales"].append(sale)
    save_data(data)
    
    wine_name = wine.get("name", args.sku)
    print(f"✅ Sale recorded: {sid}")
    print(f"   {args.cases} cases of {wine_name} → {restaurant}")
    print(f"   Revenue: ${sale['total']:,.2f}")
    print(f"   Invoice: {sale['invoice_number']}")
    print(f"   Remaining inventory: {inv['cases_on_hand']} cases")


# ── Sales Reports ────────────────────────────────────────────────────────────

def report_monthly(args):
    """Generate monthly sales report."""
    data = ensure_data()
    
    month = args.month  # format: YYYY-MM
    sales = [s for s in data["sales"] if s["date"].startswith(month)]
    
    print(f"\n📊 GranMonte Thai Wine — Monthly Sales Report")
    print(f"{'=' * 60}")
    print(f"  Period: {month}")
    print(f"  Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    
    if not sales:
        print(f"\n  No sales recorded for {month}")
        return
    
    # Summary
    total_revenue = sum(s["total"] for s in sales)
    total_cases = sum(item["cases"] for s in sales for item in s["items"])
    total_bottles = total_cases * 12
    num_transactions = len(sales)
    unique_restaurants = len(set(s["restaurant_name"] for s in sales))
    
    print(f"\n  Summary")
    print(f"  {'─' * 40}")
    print(f"  Transactions:     {num_transactions}")
    print(f"  Unique customers: {unique_restaurants}")
    print(f"  Cases sold:       {total_cases}")
    print(f"  Bottles sold:     {total_bottles}")
    print(f"  Total revenue:    ${total_revenue:,.2f}")
    print(f"  Avg per transaction: ${total_revenue/num_transactions:,.2f}")
    
    # By SKU
    sku_totals = {}
    for s in sales:
        for item in s["items"]:
            sku = item["sku"]
            if sku not in sku_totals:
                sku_totals[sku] = {"name": item.get("name", sku), "cases": 0, "revenue": 0}
            sku_totals[sku]["cases"] += item["cases"]
            sku_totals[sku]["revenue"] += item["total"]
    
    print(f"\n  By SKU")
    print(f"  {'SKU':<10} {'Wine':<24} {'Cases':>6} {'Revenue':>10} {'%Rev':>6}")
    print(f"  {'─' * 58}")
    for sku, totals in sorted(sku_totals.items(), key=lambda x: x[1]["revenue"], reverse=True):
        pct = (totals["revenue"] / total_revenue * 100) if total_revenue > 0 else 0
        print(f"  {sku:<10} {totals['name'][:22]:<24} {totals['cases']:>6} ${totals['revenue']:>9,.2f} {pct:>5.1f}%")
    
    # By restaurant
    rest_totals = {}
    for s in sales:
        name = s["restaurant_name"]
        if name not in rest_totals:
            rest_totals[name] = {"cases": 0, "revenue": 0}
        for item in s["items"]:
            rest_totals[name]["cases"] += item["cases"]
            rest_totals[name]["revenue"] += item["total"]
    
    print(f"\n  By Restaurant")
    print(f"  {'Restaurant':<28} {'Cases':>6} {'Revenue':>10} {'%Rev':>6}")
    print(f"  {'─' * 52}")
    for name, totals in sorted(rest_totals.items(), key=lambda x: x[1]["revenue"], reverse=True):
        pct = (totals["revenue"] / total_revenue * 100) if total_revenue > 0 else 0
        print(f"  {name[:26]:<28} {totals['cases']:>6} ${totals['revenue']:>9,.2f} {pct:>5.1f}%")
    
    # Payment status
    pending = sum(s["total"] for s in sales if s["payment_status"] == "pending")
    paid = sum(s["total"] for s in sales if s["payment_status"] == "paid")
    print(f"\n  Payment Status")
    print(f"  {'─' * 40}")
    print(f"  Paid:    ${paid:,.2f}")
    print(f"  Pending: ${pending:,.2f}")


def report_summary(args):
    """Generate summary report for a date range."""
    data = ensure_data()
    
    start = args.start
    end = args.end
    sales = [s for s in data["sales"] if start <= s["date"] <= end]
    
    print(f"\n📊 GranMonte Thai Wine — Sales Summary")
    print(f"{'=' * 60}")
    print(f"  Period: {start} to {end}")
    
    if not sales:
        print(f"\n  No sales in this period.")
        return
    
    total_revenue = sum(s["total"] for s in sales)
    total_cases = sum(item["cases"] for s in sales for item in s["items"])
    
    print(f"\n  Total revenue:  ${total_revenue:,.2f}")
    print(f"  Total cases:    {total_cases}")
    print(f"  Total bottles:  {total_cases * 12}")
    print(f"  Transactions:   {len(sales)}")
    print(f"  Avg case price: ${total_revenue/total_cases:,.2f}" if total_cases > 0 else "")
    
    # Monthly trend
    monthly = {}
    for s in sales:
        m = s["date"][:7]
        if m not in monthly:
            monthly[m] = {"revenue": 0, "cases": 0}
        monthly[m]["revenue"] += s["total"]
        for item in s["items"]:
            monthly[m]["cases"] += item["cases"]
    
    print(f"\n  Monthly Trend")
    print(f"  {'Month':<10} {'Revenue':>10} {'Cases':>6}")
    print(f"  {'─' * 28}")
    for m in sorted(monthly.keys()):
        print(f"  {m:<10} ${monthly[m]['revenue']:>9,.2f} {monthly[m]['cases']:>6}")


def report_top_restaurants(args):
    """Show top restaurants by revenue."""
    data = ensure_data()
    limit = args.limit or 10
    
    rest_totals = {}
    for s in data["sales"]:
        name = s["restaurant_name"]
        if name not in rest_totals:
            rest_totals[name] = {"cases": 0, "revenue": 0, "transactions": 0, "first_order": s["date"], "last_order": s["date"]}
        rest_totals[name]["transactions"] += 1
        rest_totals[name]["revenue"] += s["total"]
        if s["date"] < rest_totals[name]["first_order"]:
            rest_totals[name]["first_order"] = s["date"]
        if s["date"] > rest_totals[name]["last_order"]:
            rest_totals[name]["last_order"] = s["date"]
        for item in s["items"]:
            rest_totals[name]["cases"] += item["cases"]
    
    if not rest_totals:
        print("📋 No sales data yet.")
        return
    
    print(f"\n🏆 Top {limit} Restaurants by Revenue")
    print(f"{'=' * 80}")
    print(f"  {'#':<4} {'Restaurant':<28} {'Revenue':>10} {'Cases':>6} {'Orders':>7} {'Last Order':<12}")
    print(f"  {'─' * 76}")
    
    sorted_rests = sorted(rest_totals.items(), key=lambda x: x[1]["revenue"], reverse=True)[:limit]
    for i, (name, t) in enumerate(sorted_rests, 1):
        print(f"  {i:<4} {name[:26]:<28} ${t['revenue']:>9,.2f} {t['cases']:>6} {t['transactions']:>7} {t['last_order']:<12}")


# ── CLI Parser ───────────────────────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        description="GranMonte Thai Wine Import Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command")
    
    # Init
    subparsers.add_parser("init", help="Initialize fresh data store")
    
    # Prospect
    prospect_parser = subparsers.add_parser("prospect", help="Manage restaurant prospects")
    prospect_sub = prospect_parser.add_subparsers(dest="subcommand")
    
    p_add = prospect_sub.add_parser("add", help="Add a prospect")
    p_add.add_argument("--name", required=True)
    p_add.add_argument("--city", default="")
    p_add.add_argument("--metro", default="")
    p_add.add_argument("--address", default="")
    p_add.add_argument("--contact", default="")
    p_add.add_argument("--phone", default="")
    p_add.add_argument("--email", default="")
    p_add.add_argument("--commitment", type=int, default=0, help="Cases per month")
    p_add.add_argument("--notes", default="")
    
    prospect_sub.add_parser("list", help="List all prospects")
    
    p_update = prospect_sub.add_parser("update", help="Update a prospect")
    p_update.add_argument("--id", required=True)
    p_update.add_argument("--status", default=None)
    p_update.add_argument("--commitment", type=int, default=None)
    p_update.add_argument("--notes", default=None)
    p_update.add_argument("--contact", default=None)
    p_update.add_argument("--phone", default=None)
    p_update.add_argument("--email", default=None)
    
    prospect_sub.add_parser("pipeline", help="Pipeline summary")
    
    # Cost
    cost_parser = subparsers.add_parser("cost", help="Calculate import costs")
    cost_sub = cost_parser.add_subparsers(dest="subcommand")
    
    c_calc = cost_sub.add_parser("calculate", help="Calculate landed cost")
    c_calc.add_argument("--cases", type=int, required=True)
    c_calc.add_argument("--shipping-method", default="LCL", choices=["LCL", "FCL", "lcl", "fcl"])
    c_calc.add_argument("--exchange-rate", type=float, default=None)
    c_calc.add_argument("--sku", default=None)
    
    c_break = cost_sub.add_parser("breakdown", help="SKU cost breakdown")
    c_break.add_argument("--sku", required=True)
    c_break.add_argument("--cases", type=int, default=50)
    c_break.add_argument("--exchange-rate", type=float, default=None)
    
    # Quote
    quote_parser = subparsers.add_parser("quote", help="Generate price quotes")
    quote_sub = quote_parser.add_subparsers(dest="subcommand")
    
    q_gen = quote_sub.add_parser("generate", help="Generate a quote")
    q_gen.add_argument("--restaurant", required=True)
    q_gen.add_argument("--skus", required=True, help="Comma-separated SKU codes")
    q_gen.add_argument("--cases", required=True, help="Comma-separated case counts")
    q_gen.add_argument("--margin", type=int, default=35, help="Margin percentage")
    q_gen.add_argument("--notes", default="")
    
    quote_sub.add_parser("list", help="List all quotes")
    
    # Inventory
    inv_parser = subparsers.add_parser("inventory", help="Manage inventory")
    inv_sub = inv_parser.add_subparsers(dest="subcommand")
    
    inv_sub.add_parser("status", help="Show inventory status")
    
    i_recv = inv_sub.add_parser("receive", help="Receive inventory")
    i_recv.add_argument("--sku", required=True)
    i_recv.add_argument("--cases", type=int, required=True)
    i_recv.add_argument("--date", default=None)
    i_recv.add_argument("--reference", default=None)
    
    i_sell = inv_sub.add_parser("sell", help="Record a sale")
    i_sell.add_argument("--sku", required=True)
    i_sell.add_argument("--cases", type=int, required=True)
    i_sell.add_argument("--restaurant", default=None)
    i_sell.add_argument("--price", type=float, default=None, help="Price per case")
    i_sell.add_argument("--date", default=None)
    
    # Report
    report_parser = subparsers.add_parser("report", help="Generate reports")
    report_sub = report_parser.add_subparsers(dest="subcommand")
    
    r_month = report_sub.add_parser("monthly", help="Monthly report")
    r_month.add_argument("--month", required=True, help="YYYY-MM format")
    
    r_summary = report_sub.add_parser("summary", help="Period summary")
    r_summary.add_argument("--start", required=True, help="YYYY-MM-DD")
    r_summary.add_argument("--end", required=True, help="YYYY-MM-DD")
    
    r_top = report_sub.add_parser("top-restaurants", help="Top restaurants")
    r_top.add_argument("--limit", type=int, default=10)
    
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "init":
        data = init_data()
        print(f"✅ Fresh data store initialized at {DATA_FILE}")
        print(f"   {len(data['catalog'])} SKUs loaded: {', '.join(s['sku'] for s in data['catalog'])}")
        return
    
    # Route commands
    commands = {
        "prospect": {
            "add": prospect_add,
            "list": prospect_list,
            "update": prospect_update,
            "pipeline": prospect_pipeline
        },
        "cost": {
            "calculate": cost_calculate,
            "breakdown": cost_breakdown
        },
        "quote": {
            "generate": quote_generate,
            "list": quote_list
        },
        "inventory": {
            "status": inventory_status,
            "receive": inventory_receive,
            "sell": inventory_sell
        },
        "report": {
            "monthly": report_monthly,
            "summary": report_summary,
            "top-restaurants": report_top_restaurants
        }
    }
    
    if args.command in commands:
        sub = getattr(args, "subcommand", None)
        if sub and sub in commands[args.command]:
            commands[args.command][sub](args)
        else:
            print(f"❌ Unknown subcommand. Available: {', '.join(commands[args.command].keys())}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
