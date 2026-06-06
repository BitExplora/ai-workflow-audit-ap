# AI Workflow Audit — Accounts Payable (Three-Way Match)

A reproducible proof-of-concept for **auditing an AI automation opportunity before
building it**: decompose a workflow, score each step on impact × risk, measure the
risky steps in a sandbox, and quantify the dollar value of the right operating
model (usually hybrid, not full automation).

POC #1 of a three-part series: manufacturing AP → finance/banking fraud → healthcare (HIPAA).

## Why this exists

Most enterprise AI pilots fail on integration and risk, not model quality. The fix
is a diagnostic *before* the build: which steps to automate, which to run hybrid
(AI proposes, human approves), and which to leave manual — scored on business
impact and the cost of an AI error.

## Headline result

On a synthetic three-way-match dataset, the automation matches invoices at
**99.4% accuracy** but catches only **50% of fraud**. Because a paid fraudulent
invoice is irreversible, the value model shows **naive full automation nets
~$0.10M/yr while a hybrid model with a human payment gate nets ~$3.28M/yr**
(illustrative inputs). Finding that gap before the client builds is the product.

## Files

| File | What it is |
|---|---|
| `audit_report.md` | The consulting deliverable: scoring, matrix, recommendations, value math |
| `value_model.xlsx` | Impact×risk scoring + value equation (formula-driven, swap in client numbers) |
| `generate_data.py` | Reproducible synthetic dataset generator (seed = 42) |
| `match_engine.py` | The automation under test (rules now; an LLM via MCP in production) |
| `run_audit.py` | Offline-eval: scores the engine vs ground truth, writes `results.json` |
| `vendors.csv`, `purchase_orders.csv`, `goods_receipts.csv`, `invoices.csv` | Inputs |
| `ground_truth.csv` | Labeled correct disposition per invoice (the edge-case tail) |
| `results.json` | Metrics emitted by the harness (feeds the value model) |
| `build_value_model.py` | Builds `value_model.xlsx` from `results.json` |

## How to run

All files live in one folder, so just run them in order:

```bash
pip install pandas openpyxl
python generate_data.py      # writes the CSVs
python run_audit.py          # prints metrics, writes results.json
python build_value_model.py  # writes value_model.xlsx
```

## The edge-case tail (what makes this a real audit)

The dataset deliberately includes the exceptions that break naive automation:
price mismatch, quantity mismatch, duplicate invoice, missing PO, tax error, and
**fraud (vendor bank-detail change / payment redirect)**. The harness reports
per-category recall so the risk score is measured, not guessed.

## Production note (MCP)

The audit itself is tool-agnostic. The *implementation* would give the agent
permissioned access to ERP, vendor master, and banking systems through MCP tools.
Every write-capable tool (`release_payment`, `update_vendor_bank`) is both an
attack surface and the high-risk cell of the matrix — so the MCP tool scope is
audited alongside the workflow.

## License / use

Portfolio demonstration. Synthetic data only; no real client information.
