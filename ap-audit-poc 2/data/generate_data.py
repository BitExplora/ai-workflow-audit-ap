"""
Generate a synthetic Accounts Payable three-way-match dataset for a
mid-market manufacturing / distribution company.

Outputs four CSVs plus a ground-truth label file:
  purchase_orders.csv  - what we agreed to buy
  goods_receipts.csv   - what the warehouse actually received
  invoices.csv         - what the vendor billed us
  vendors.csv          - master vendor list (incl. bank details)
  ground_truth.csv     - the CORRECT disposition of each invoice

The "disposition" is the labeled tail used to score the automation harness:
  clean          - PO, receipt and invoice agree within tolerance -> pay
  price_mismatch - invoice unit price exceeds PO beyond tolerance
  qty_mismatch   - invoice qty exceeds received qty beyond tolerance
  duplicate      - same vendor/PO/amount already invoiced
  missing_po     - invoice references a PO that does not exist
  tax_error      - tax amount inconsistent with taxable base
  fraud          - vendor bank detail changed OR unknown payee (payment risk)

Deterministic via SEED so the repo reproduces identical numbers.
"""
import csv, random, os
from datetime import date, timedelta

SEED = 42
N_INVOICES = 1000
random.seed(SEED)

HERE = os.path.dirname(os.path.abspath(__file__))

# Target mix of the edge-case tail (the rest are clean)
TAIL_MIX = {
    "price_mismatch": 0.060,
    "qty_mismatch":   0.050,
    "duplicate":      0.030,
    "missing_po":     0.030,
    "tax_error":      0.020,
    "fraud":          0.010,
}
TAX_RATE = 0.08
PRICE_TOL = 0.02   # 2% price tolerance
QTY_TOL = 0          # qty must not exceed received

ITEMS = [
    ("STEEL-COIL", 1250.00), ("BEARING-SET", 42.50), ("HYDRAULIC-PUMP", 880.00),
    ("CONVEYOR-BELT", 310.00), ("CONTROL-PANEL", 1520.00), ("PALLET-WRAP", 18.75),
    ("MOTOR-3PH", 640.00), ("SENSOR-PROX", 95.00), ("GEARBOX", 2100.00),
    ("LUBRICANT-DRUM", 220.00),
]

def make_vendors(n=60):
    vendors = []
    for i in range(1, n + 1):
        vendors.append({
            "vendor_id": f"V{i:04d}",
            "name": f"Supplier {i:02d} Inc",
            "bank_account": f"ACCT{random.randint(10_000_000, 99_999_999)}",
            "approved": "Y",
        })
    return vendors

def daterange_start():
    return date(2025, 1, 1) + timedelta(days=random.randint(0, 120))

def build():
    vendors = make_vendors()
    vendor_ids = [v["vendor_id"] for v in vendors]
    vendor_bank = {v["vendor_id"]: v["bank_account"] for v in vendors}

    # Decide disposition for each invoice up front
    dispositions = []
    for _ in range(N_INVOICES):
        r = random.random()
        cum = 0.0
        chosen = "clean"
        for label, p in TAIL_MIX.items():
            cum += p
            if r < cum:
                chosen = label
                break
        dispositions.append(chosen)

    pos, receipts, invoices, truth = [], [], [], []
    prior_clean = []  # pool to clone for duplicates

    for idx in range(N_INVOICES):
        disp = dispositions[idx]
        po_id = f"PO{idx + 100000}"
        inv_id = f"INV{idx + 500000}"
        vendor = random.choice(vendor_ids)
        item, unit_price = random.choice(ITEMS)
        qty = random.randint(1, 40)
        d0 = daterange_start()

        # --- Duplicate: clone a prior clean invoice, new invoice id ---
        if disp == "duplicate" and prior_clean:
            src = random.choice(prior_clean)
            invoices.append({
                "invoice_id": inv_id, "po_id": src["po_id"], "vendor_id": src["vendor_id"],
                "item": src["item"], "qty": src["qty"], "unit_price": src["unit_price"],
                "subtotal": src["subtotal"], "tax": src["tax"], "total": src["total"],
                "invoice_date": str(d0), "remit_bank": vendor_bank[src["vendor_id"]],
            })
            truth.append({"invoice_id": inv_id, "disposition": "duplicate"})
            continue

        po_qty = qty
        recv_qty = qty
        inv_qty = qty
        po_price = unit_price
        inv_price = unit_price
        remit_bank = vendor_bank[vendor]
        po_exists = True

        if disp == "price_mismatch":
            inv_price = round(unit_price * (1 + random.uniform(0.05, 0.25)), 2)
        elif disp == "qty_mismatch":
            inv_qty = recv_qty + random.randint(1, 5)  # billed more than received
        elif disp == "missing_po":
            po_exists = False
        elif disp == "fraud":
            # vendor bank detail changed vs master (payment-redirect risk)
            remit_bank = f"ACCT{random.randint(10_000_000, 99_999_999)}"

        subtotal = round(inv_qty * inv_price, 2)
        if disp == "tax_error":
            tax = round(subtotal * (TAX_RATE + random.uniform(0.03, 0.07)), 2)
        else:
            tax = round(subtotal * TAX_RATE, 2)
        total = round(subtotal + tax, 2)

        if po_exists:
            pos.append({"po_id": po_id, "vendor_id": vendor, "item": item,
                        "qty": po_qty, "unit_price": po_price, "po_date": str(d0)})
            receipts.append({"po_id": po_id, "vendor_id": vendor, "item": item,
                             "recv_qty": recv_qty, "recv_date": str(d0 + timedelta(days=3))})

        inv_row = {
            "invoice_id": inv_id, "po_id": po_id if po_exists else f"PO{random.randint(900000, 999999)}",
            "vendor_id": vendor, "item": item, "qty": inv_qty, "unit_price": inv_price,
            "subtotal": subtotal, "tax": tax, "total": total,
            "invoice_date": str(d0), "remit_bank": remit_bank,
        }
        invoices.append(inv_row)
        truth.append({"invoice_id": inv_id, "disposition": disp})
        if disp == "clean":
            prior_clean.append(inv_row)

    _write("vendors.csv", vendors, ["vendor_id", "name", "bank_account", "approved"])
    _write("purchase_orders.csv", pos, ["po_id", "vendor_id", "item", "qty", "unit_price", "po_date"])
    _write("goods_receipts.csv", receipts, ["po_id", "vendor_id", "item", "recv_qty", "recv_date"])
    _write("invoices.csv", invoices, ["invoice_id", "po_id", "vendor_id", "item", "qty",
                                      "unit_price", "subtotal", "tax", "total", "invoice_date", "remit_bank"])
    _write("ground_truth.csv", truth, ["invoice_id", "disposition"])

    counts = {}
    for t in truth:
        counts[t["disposition"]] = counts.get(t["disposition"], 0) + 1
    print("Generated", len(invoices), "invoices:", counts)

def _write(name, rows, cols):
    with open(os.path.join(HERE, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

if __name__ == "__main__":
    build()
