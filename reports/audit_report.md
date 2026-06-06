# AP Three-Way Match — AI Workflow Audit

**Client profile:** mid-market manufacturing / distribution company
**Workflow audited:** accounts-payable invoice processing (purchase-order three-way match)
**Engagement type:** pre-build diagnostic (impact × risk scoring → automate / hybrid / manual)
**Status:** proof-of-concept on synthetic data

> This is a portfolio proof-of-concept. The dataset is synthetic and the dollar
> figures run on illustrative inputs. In a live engagement the rates and costs in
> `value_model.xlsx` are replaced with the client's own numbers, supplied by their
> FP&A and risk teams. The methodology, harness, and conclusions are the product.

---

## 1. Executive summary

The objective was not to ask "should we use AI in AP." It was to score each step of
the AP workflow on business impact and on the cost of an AI error, then decide —
per step — whether to automate, run hybrid (AI proposes, human approves), or leave
manual.

The headline finding mirrors the well-documented industry pattern that most AI
pilots fail on integration and risk, not model quality: **full automation of this
workflow is the wrong answer, and it is wrong by millions.** The replay sandbox
matched invoices at 99.4% overall accuracy, but caught only **50% of fraud
(6 of 12 fraudulent invoices would have been paid)**. Because a paid fraudulent
invoice is irreversible cash out the door, automating the payment-release step
destroys value even though the classifier looks excellent on average.

On illustrative inputs, the value model returns:

| Operating model | Net annual value |
|---|---|
| Recommended (hybrid gates on fraud & payment release) | ~$3.28M |
| Naive full automation | ~$0.10M |

The ~$3.19M gap is the value of *not* over-automating. That is the engagement's
single most important number.

## 2. Method

1. **Decompose** the single "process an invoice" workflow into eight atomic
   sub-steps that score differently on risk.
2. **Score** each on impact (1–5) and risk (1–5); the impact × risk position
   dictates the decision via a fixed matrix rule.
3. **Quantify** with a value equation: labor saved + losses prevented + discount
   capture − run cost − error cost.
4. **Measure risk empirically** by replaying a labeled dataset (including an
   over-sampled edge-case tail) through the candidate automation and recording
   where it fails — especially on the expensive, irreversible steps.

## 3. Sub-workflow scoring

| Sub-workflow | Impact | Risk | Decision | Rationale |
|---|:---:|:---:|---|---|
| Invoice data capture (OCR/extract) | 4 | 2 | Automate | Deterministic; reversible before posting |
| Three-way match (clean invoices) | 5 | 2 | Automate | ~81% of volume; high sandbox accuracy |
| Duplicate detection / auto-hold | 4 | 2 | Automate | 100% recall; catches dupes humans miss |
| Price / quantity mismatch resolution | 4 | 3 | Automate* | Automatable with tolerance rules; sample-audit |
| Missing-PO / non-PO routing | 3 | 3 | Hybrid | Policy-dependent; route to an owner |
| Tax / GL coding | 3 | 3 | Hybrid | Automate with periodic sampling |
| Fraud / bank-change screening | 5 | 5 | **Hybrid** | Sandbox missed 50% of fraud; irreversible |
| Payment approval & release | 5 | 5 | **Hybrid** | Binding cash out; gate above a threshold |

\*Price/quantity resolution can begin hybrid and graduate to automate once the
sandbox shows stable accuracy in shadow mode.

The two cells that carry the risk — fraud screening and payment release — are
exactly the ones the matrix pulls into hybrid. AI drafts and flags; a human
approves anything binding or irreversible.

## 4. Sandbox findings (empirical)

Replaying 1,000 labeled invoices (`harness/run_audit.py`):

- **Overall accuracy:** 99.4%
- **Auto-payable (clean) share:** 81.1% of volume
- **Deterministic checks** (price, quantity, duplicate, missing-PO, tax): 100% recall
- **Fraud recall:** 50% — the residual miss is the entire argument for the
  human gate on payment release

The lesson is not "the model is bad." It is "the step where errors are most
expensive is also the step where the automation is least reliable, and the error
is irreversible." High average accuracy hides catastrophic tail risk.

## 5. Value model

See `value_model.xlsx` (three sheets: Assumptions, Workflow Audit, Value Model).
All figures are formula-driven and recalculate when the client's real inputs are
entered. On the illustrative inputs:

- Labor saved (hybrid): ~$549K
- Duplicate losses prevented: ~$940K
- Early-pay discount capture gain: ~$1.94M
- Fraud losses incurred: $0 (hybrid) vs ~$3.24M (full automation)
- Cost to run: ~$150K
- **Net annual value: ~$3.28M (hybrid) vs ~$0.10M (full automation)**

## 6. Recommendations

- Automate capture, clean matching, and duplicate auto-hold immediately.
- Keep fraud/bank-change screening and payment release **hybrid** with a hard
  human approval gate above a client-set dollar threshold (set by FP&A, not us).
- Start price/quantity and tax coding in hybrid; graduate to automate when shadow
  mode demonstrates stable accuracy.
- Instrument every step so the risk score is continuously re-measured, not
  assumed once.

## 7. De-risking rollout

Offline eval (this report) → shadow mode (engine runs on live traffic, actions
disabled) → canary (acts on a small low-risk slice, human-reviewed) → full
rollout with the hybrid gates above. Each gate has a numeric pass bar, e.g.
"≥99% match accuracy and zero unreviewed payments above threshold."

## 8. Assumptions & limitations

- Synthetic data with an **elevated fraud rate (1.2%)** for demonstration; real AP
  fraud rates are far lower, but the conclusion holds because the case for the
  human gate rests on irreversibility and tail risk, not on expected value alone.
- Discount-capture and duplicate-prevention inputs are illustrative.
- The production automation would reach AP systems (ERP, vendor master, banking)
  through controlled, permissioned **MCP tools**. Every write-capable tool —
  "release payment," "update vendor bank detail" — is a risk surface and maps
  directly to the high-risk cells above; scoping those tool permissions is part
  of the audit, not an afterthought.

## 9. Roadmap

This is POC #1 of three, in ascending order of risk and governance:

1. **Manufacturing AP** (this) — clean hard-ROI baseline; establishes the harness.
2. **Finance / banking** — payments fraud and account takeover under AML/KYC.
3. **Healthcare (HIPAA)** — the same framework under strict PHI governance.
