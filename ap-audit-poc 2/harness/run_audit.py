"""
run_audit.py
Replays the labeled dataset through match_engine, compares predictions to
ground truth, and emits the empirical metrics the impact/risk scoring needs:
per-category recall (did we catch this exception type?) and the residual
miss rate that drives the risk score for the payment-release step.

This is the offline-eval stage of the de-risking pipeline. Shadow / canary /
rollout stages would point the same engine at live systems with actions
disabled, then enabled on a small slice.
"""
import csv, os, json
from collections import defaultdict
from match_engine import run_engine

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

CATEGORIES = ["clean", "price_mismatch", "qty_mismatch", "duplicate",
              "missing_po", "tax_error", "fraud"]


def main():
    truth = {r["invoice_id"]: r["disposition"]
             for r in csv.DictReader(open(os.path.join(DATA, "ground_truth.csv")))}
    preds = {p["invoice_id"]: p["predicted"] for p in run_engine()}

    # Confusion: per true category, counts of predicted
    conf = defaultdict(lambda: defaultdict(int))
    support = defaultdict(int)
    correct = 0
    for inv_id, t in truth.items():
        p = preds[inv_id]
        conf[t][p] += 1
        support[t] += 1
        if p == t:
            correct += 1

    per_cat = {}
    for c in CATEGORIES:
        tp = conf[c][c]
        sup = support[c]
        # precision: of all predicted c, how many were truly c
        pred_c = sum(conf[t][c] for t in CATEGORIES)
        recall = tp / sup if sup else None
        precision = tp / pred_c if pred_c else None
        per_cat[c] = {"support": sup, "recall": recall, "precision": precision}

    # The number that matters most: fraud caught vs missed (would-be paid)
    fraud_missed = support["fraud"] - conf["fraud"]["fraud"]
    dup_missed = support["duplicate"] - conf["duplicate"]["duplicate"]

    results = {
        "total_invoices": len(truth),
        "overall_accuracy": round(correct / len(truth), 4),
        "per_category": per_cat,
        "fraud_support": support["fraud"],
        "fraud_missed": fraud_missed,
        "duplicate_support": support["duplicate"],
        "duplicate_missed": dup_missed,
        "clean_share": round(support["clean"] / len(truth), 4),
        "exception_share": round(1 - support["clean"] / len(truth), 4),
    }

    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(results, f, indent=2)

    print(f"Overall accuracy: {results['overall_accuracy']:.1%}")
    print(f"Clean (auto-payable) share: {results['clean_share']:.1%}")
    print(f"Exception (needs handling) share: {results['exception_share']:.1%}")
    print("\nPer-category recall:")
    for c in CATEGORIES:
        r = per_cat[c]["recall"]
        print(f"  {c:14s} support={per_cat[c]['support']:4d}  recall={r:.0%}" if r is not None else f"  {c}: n/a")
    print(f"\nFraud: {fraud_missed} of {support['fraud']} would have been PAID if fully automated.")
    print(f"Duplicates: {dup_missed} of {support['duplicate']} missed.")


if __name__ == "__main__":
    main()
