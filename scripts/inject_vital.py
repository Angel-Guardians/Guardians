"""Debug: inject a synthetic vital sample.

Useful for testing the anomaly path on Day 3 without waiting for a
real HR excursion from the Polar H10.

  $ python scripts/inject_vital.py --kind hr --value 138
"""
from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", default="hr")
    parser.add_argument("--value", type=float, required=True)
    parser.add_argument("--device", default="manual_inject")
    args = parser.parse_args()
    # TODO: POST to a debug endpoint that publishes a VitalSampleEvent
    print(f"injecting {args.kind}={args.value} from {args.device}")
    raise NotImplementedError


if __name__ == "__main__":
    main()
