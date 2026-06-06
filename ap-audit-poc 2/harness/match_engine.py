"""
match_engine.py
The "automation under test": a rules-based three-way-match engine that proposes
a disposition for each invoice. In production this component would be an LLM /
agent reaching the same systems through MCP tools; here it is a deterministic
stand-in so the sandbox runs offline and reproducibly.

Design note: the engine is intentionally strong on deterministic checks
(price, quantity, missing PO, tax, exact duplicate) and intentionally imperfect
on fraud (FRAUD_DETECTION_GAP) to reflect a real limitation -- fraud rarely
trips a single clean rule. That residual miss rate is the empirical input the
audit uses to argue the payment-release step must stay HYBRID.
"""
import csv, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

PRICE_TOL = 0.02       # accept invoice price within 2% of PO price
FRAUD_DETECTION_GAP = 0.25  # fraction of true fraud the rule fails to catch
random.seed(7)


def _load(name, key=None):
    rows = list(csv.DictReader(open(os.path.join(DATA, name))))
    if key:
        return {r[key]: r for r in rows}, rows
    return rows


def run_engine():
    pos, _ = _load("purchase_orders.csv", key="po_id")
    receipts_rows = _load("goods_receipts.csv")
    receipts = {r["po_id"]: r for r in receipts_rows}
    vendors, _ = _load("vendors.csv", key="vendor_id")
    invoices = _load("invoices.csv")

    seen = set()              # (vendor, po, total) for duplicate detection
    predictions = []

    for inv in invoices:
        vid, po, total = inv["vendor_id"], inv["po_id"], inv["total"]
        pred = "clean"

        # 1. Missing PO
        if po not in pos:
            pred = "missing_po"

        # 2. Exact duplicate (same vendor, PO, amount already invoiced)
        elif (vid, po, total) in seen:
            pred = "duplicate"

        else:
            po_row = pos[po]
            rec = receipts.get(po)
            inv_qty = float(inv["qty"])
            inv_price = float(inv["unit_price"])
            po_price = float(po_row["unit_price"])
            recv_qty = float(rec["recv_qty"]) if rec else 0.0
            subtotal = float(inv["subtotal"])
            tax = float(inv["tax"])

            # 3. Fraud: remit bank differs from vendor master (with detection gap)
            if inv["remit_bank"] != vendors[vid]["bank_account"]:
                if random.random() > FRAUD_DETECTION_GAP:
                    pred = "fraud"
                else:
                    pred = "clean"   # missed -> would be paid
            # 4. Quantity billed exceeds quantity received
            elif inv_qty > recv_qty:
                pred = "qty_mismatch"
            # 5. Price exceeds PO beyond tolerance
            elif inv_price > po_price * (1 + PRICE_TOL):
                pred = "price_mismatch"
            # 6. Tax inconsistent with taxable base (expect ~8%)
            elif abs(tax - subtotal * 0.08) > 0.01 * subtotal + 0.01:
                pred = "tax_error"

        seen.add((vid, po, total))
        predictions.append({"invoice_id": inv["invoice_id"], "predicted": pred})

    return predictions


if __name__ == "__main__":
    preds = run_engine()
    print(f"Scored {len(preds)} invoices")
