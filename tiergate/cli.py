"""Command-line demo for TierGate."""
import argparse
from .core import TASKS, route_task, evaluate_fraud_referral, HIGH_COMPLEXITY_TASK_NAMES


def print_task_map():
    print(f"{'#':<3}{'Task':<42}{'Complexity':<10}{'Model size':<24}")
    print("-" * 80)
    for t in TASKS:
        print(f"{t.index:<3}{t.name:<42}{t.complexity.value:<10}{t.model_size.value:<24}")


def demo_routing():
    print("\n--- Confidence-gated routing on High-complexity tasks ---")
    examples = [
        ("Verify identity and fraud indicators",
         "This claimant's phone number appears on 3 other claims filed in the past 30 days. "
         "Is this claim likely fraudulent?"),
        ("Evaluate risk, eligibility, exceptions",
         "If we tightened the underwriting appetite for flood-zone properties, would claim "
         "frequency or severity decrease?"),
        ("Decide disposition (incl. routing/SLA)",
         "Had the adjuster not flagged the repair estimate as inconsistent with the submitted "
         "photos, would this claim have been auto-settled instead of escalated?"),
    ]
    for task_name, question in examples:
        d = route_task(task_name, question)
        print(f"\nTask: {d.task_name}\nQuestion: {question}\n-> level={d.causal_level} "
              f"auto_actioned={d.auto_actioned}\n-> {d.reason}")

    print("\n--- The always-human fraud gate ---")
    for confidence, suspected in [(0.98, True), (0.55, True), (0.80, False)]:
        g = evaluate_fraud_referral(confidence, suspected)
        print(f"confidence={confidence} suspected_fraud={suspected} -> "
              f"requires_human={g.requires_human} ({g.reason})")


def main():
    parser = argparse.ArgumentParser(prog="tiergate")
    parser.add_argument("command", choices=["map", "demo"], help="map: print the task map; demo: run the routing demo")
    args = parser.parse_args()
    if args.command == "map":
        print_task_map()
    else:
        demo_routing()


if __name__ == "__main__":
    main()
