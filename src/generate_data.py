"""
LedgerLens synthetic dataset generator.

This starter version creates the same four CSV files used for development.
Run:
    python src/generate_data.py
"""

from pathlib import Path
import random
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

def main():
    print("Dataset generation logic will be expanded here as the reconciliation engine evolves.")
    print(f"Data directory: {DATA_DIR}")

if __name__ == "__main__":
    main()
