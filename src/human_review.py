from pathlib import Path
import pandas as pd


# ============================================================
# LEDGERLENS - HUMAN REVIEW MODULE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

RESULTS_FILE = DATA_DIR / "reconciliation_results.csv"
REVIEW_FILE = DATA_DIR / "human_review_results.csv"


def load_results():
    """Load reconciliation results."""
    if not RESULTS_FILE.exists():
        print()
        print("ERROR: reconciliation_results.csv not found.")
        print("Run reconciliation_engine.py first.")
        return None

    try:
        return pd.read_csv(RESULTS_FILE)
    except Exception as e:
        print(f"ERROR: Could not read results file: {e}")
        return None


def find_review_records(df):
    """Find records that require human review."""

    if "status" not in df.columns:
        print("ERROR: 'status' column not found.")
        return pd.DataFrame()

    review_statuses = {
        "UNRESOLVED",
        "HUMAN_REVIEW",
        "REVIEW_REQUIRED"
    }

    return df[
        df["status"]
        .astype(str)
        .str.upper()
        .isin(review_statuses)
    ].copy()


def display_record(record, number, total):
    """Display one record requiring review."""

    print()
    print("=" * 70)
    print(f"HUMAN REVIEW RECORD {number} OF {total}")
    print("=" * 70)

    for column, value in record.items():
        print(f"{column}: {value}")

    print("=" * 70)


def review_records(review_df):
    """Interactively review unresolved records."""

    if review_df.empty:
        print()
        print("=" * 70)
        print("HUMAN REVIEW QUEUE")
        print("=" * 70)
        print("No records require human review.")
        return review_df

    print()
    print("=" * 70)
    print("HUMAN REVIEW QUEUE")
    print("=" * 70)
    print(f"Records requiring review: {len(review_df)}")

    reviewed_records = []

    for index, (_, row) in enumerate(review_df.iterrows(), start=1):

        display_record(
            row,
            index,
            len(review_df)
        )

        while True:
            decision = input(
                "Decision [A=Approve / R=Reject / S=Skip / Q=Quit]: "
            ).strip().upper()

            if decision in {"A", "R", "S", "Q"}:
                break

            print("Please enter A, R, S, or Q.")

        record = row.to_dict()

        if decision == "A":
            record["human_review_decision"] = "APPROVED"
            record["human_review_status"] = "REVIEWED"

        elif decision == "R":
            record["human_review_decision"] = "REJECTED"
            record["human_review_status"] = "REVIEWED"

        elif decision == "S":
            record["human_review_decision"] = "SKIPPED"
            record["human_review_status"] = "PENDING"

        elif decision == "Q":
            record["human_review_decision"] = "NOT_REVIEWED"
            record["human_review_status"] = "PENDING"

            reviewed_records.append(record)
            break

        reviewed_records.append(record)

        if decision == "Q":
            break

    return pd.DataFrame(reviewed_records)


def save_review_results(reviewed_df):
    """Save human review decisions."""

    if reviewed_df.empty:
        print()
        print("No review decisions to save.")
        return

    try:
        reviewed_df.to_csv(
            REVIEW_FILE,
            index=False
        )

        print()
        print("=" * 70)
        print("HUMAN REVIEW RESULTS SAVED")
        print("=" * 70)
        print(REVIEW_FILE)
        print("=" * 70)

    except Exception as e:
        print(f"ERROR: Could not save review results: {e}")


def show_summary(reviewed_df):
    """Display review summary."""

    if reviewed_df.empty:
        return

    print()
    print("=" * 70)
    print("REVIEW SUMMARY")
    print("=" * 70)

    if "human_review_decision" in reviewed_df.columns:
        counts = (
            reviewed_df["human_review_decision"]
            .value_counts()
        )

        for decision, count in counts.items():
            print(f"{decision}: {count}")

    print("=" * 70)


def main():
    """Main Human Review workflow."""

    print()
    print("=" * 70)
    print("LEDGERLENS - HUMAN REVIEW")
    print("=" * 70)

    results = load_results()

    if results is None:
        return

    review_queue = find_review_records(results)

    print()
    print(f"Total reconciliation records: {len(results)}")
    print(f"Records requiring review: {len(review_queue)}")

    if review_queue.empty:
        print()
        print("No records require human review.")
        return

    reviewed_results = review_records(review_queue)

    save_review_results(reviewed_results)

    show_summary(reviewed_results)

    print()
    print("Human review process completed.")
    print()


if __name__ == "__main__":
    main()