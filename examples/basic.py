"""Basic usage example for vidya."""
from src.core import Vidya

def main():
    instance = Vidya(config={"verbose": True})

    print("=== vidya Example ===\n")

    # Run primary operation
    result = instance.detect(input="example data", mode="demo")
    print(f"Result: {result}")

    # Run multiple operations
    ops = ["detect", "scan", "monitor]
    for op in ops:
        r = getattr(instance, op)(source="example")
        print(f"  {op}: {"✓" if r.get("ok") else "✗"}")

    # Check stats
    print(f"\nStats: {instance.get_stats()}")

if __name__ == "__main__":
    main()
