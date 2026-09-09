"""Replay saved spots and report ranking changes without claiming unlabeled accuracy."""

import argparse
import json
from pathlib import Path

from tft_spot.engine.simulator import SimulationRequest, generate_run, load_run


def compare(previous, current):
    def top(case):
        return [r["sourceId"] for r in case["rankings"] if r["eligible"]][:3]

    changes = []
    for before, after in zip(previous["cases"], current["cases"], strict=True):
        if before["spot"] != after["spot"]:
            raise ValueError("Replay changed input spot")
        if top(before) != top(after):
            changes.append(
                {"caseId": before["id"], "before": top(before), "after": top(after)}
            )
    return {
        "previousRunId": previous["id"],
        "runId": current["id"],
        "cases": len(current["cases"]),
        "changedTop3": len(changes),
        "changes": changes,
        "benchmark": current["benchmark"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument(
        "--run",
        action="append",
        default=[],
        help="Existing run UUID; repeat for multiple runs",
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Also generate 50 stress cases across compositions",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if not args.run and not args.coverage:
        parser.error("Provide --run or --coverage")
    report = {
        "replays": [],
        "accuracyNote": "Only player-labeled cases contribute to top3HitRate. Changes are not evidence of improvement.",
    }
    for run_id in args.run:
        previous = load_run(args.root, run_id)
        current = generate_run(
            args.root,
            SimulationRequest(
                setNumber=previous["setNumber"],
                seed=previous["seed"],
                count=previous["count"],
            ),
            previous,
        )
        report["replays"].append(compare(previous, current))
    if args.coverage:
        current = generate_run(
            args.root, SimulationRequest(mode="coverage", seed=args.seed)
        )
        report["coverage"] = {"runId": current["id"], "benchmark": current["benchmark"]}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
