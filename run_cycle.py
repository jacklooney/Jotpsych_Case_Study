#!/usr/bin/env python3
import argparse

from dotenv import load_dotenv

load_dotenv()

from machine.engine import run_cycle  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="Run one cycle of the JotPsych re-engagement machine."
    )
    parser.add_argument(
        "csv_path", nargs="?", default="data/sample_clinicians.csv",
        help="Path to a name,email,mobile CSV. Swap this to rerun on different data.",
    )
    parser.add_argument("--state", default="state.json")
    parser.add_argument("--dry-run", action="store_true",
                         help="Skip the real SMTP send, simulate only.")
    args = parser.parse_args()

    report, _ = run_cycle(args.csv_path, state_path=args.state, live=not args.dry_run)

    print(f"\n=== Cycle {report['cycle']} on {args.csv_path} ===")
    print(f"Sent:      {len(report['sent'])}")
    print(f"Rejected:  {len(report['rejected'])}")
    print(f"Skipped:   {len(report['skipped'])}")
    print(f"Invalid:   {len(report['invalid'])}")

    if report["rejected"]:
        print("\n--- Rejected drafts (quality gate caught these before send) ---")
        for r in report["rejected"]:
            print(f"  {r['record'].get('name')}: {r['reasons']}")

    if report["invalid"]:
        print("\n--- Invalid rows (never reached content generation) ---")
        for r in report["invalid"]:
            print(f"  {r['record']}: {r['reasons']}")

    print(f"\nFull state written to {args.state}")


if __name__ == "__main__":
    main()
