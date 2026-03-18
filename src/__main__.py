"""CLI for vidya."""
import sys, json, argparse
from .core import Vidya

def main():
    parser = argparse.ArgumentParser(description="Vidya — AI Adaptive Tutor. Personalized learning with knowledge gap detection and spaced repetition.")
    parser.add_argument("command", nargs="?", default="status", choices=["status", "run", "info"])
    parser.add_argument("--input", "-i", default="")
    args = parser.parse_args()
    instance = Vidya()
    if args.command == "status":
        print(json.dumps(instance.get_stats(), indent=2))
    elif args.command == "run":
        print(json.dumps(instance.detect(input=args.input or "test"), indent=2, default=str))
    elif args.command == "info":
        print(f"vidya v0.1.0 — Vidya — AI Adaptive Tutor. Personalized learning with knowledge gap detection and spaced repetition.")

if __name__ == "__main__":
    main()
