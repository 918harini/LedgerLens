from pathlib import Path
from datetime import datetime, timedelta
import random
import pandas as pd


# ============================================================
# LEDGERLENS V2
# Synthetic Dataset Generator
# ============================================================

random.seed(42)

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"


# ============================================================
# SCENARIOS
# ============================================================

SCENARIOS = (
    ["PERFECT_MATCH"] * 300
    + ["FEE_TAX_DIFFERENCE"] * 45
    + ["MISSING_SETTLEMENT"] * 35
    + ["MISSING_BANK_CREDIT"] * 30
    + ["DUPLICATE"] * 25
    + ["PARTIAL_SETTLEMENT"] * 20
    + ["SETTLEMENT_DELAY"] * 20
    + ["AMOUNT_MISMATCH"] * 15
    + ["NOISY_REFERENCE"] * 5
    + ["AMBIGUOUS_UNRESOLVED"] * 5
)


# ============================================================
# GENERATE DATA
# ============================================================

def generate():

    scenarios = SCENARIOS.copy()
    random.shuffle(scenarios)

    start_date = datetime(2026, 8, 1)

    payments = []
    settlements = []
    bank = []
    truth = []

    for i, scenario in enumerate(scenarios, start=1):

        payment_id = f"PAY{100000 + i}"

        merchant_id = (
            f"MER{random.randint(1, 20):03d}"
        )

        customer_id = (
            f"CUST{random.randint(1000, 9999)}"
        )

        payment_date = (
            start_date
            + timedelta(days=random.randint(0, 20))
        )

        payment_dt = datetime(
            payment_date.year,
            payment_date.month,
            payment_date.day,
            random.randint(8, 21),
            random.randint(0, 59),
            random.randint(0, 59)
        )

        amount = random.choice([
            500,
            750,
            1200,
            2500,
            5000,
            8500,
            12000,
            25000,
            50000,
            75000,
            100000
        ])

        method = random.choice([
            "UPI",
            "CARD",
            "NETBANKING"
        ])

        reference_id = (
            f"ORD-{random.randint(100000, 999999)}"
        )

        # --------------------------------------------------------
        # Synthetic fee/tax policy
        # --------------------------------------------------------

        fee_rate = (
            0.015
            if method == "CARD"
            else 0.01
        )

        processing_fee = round(
            amount * fee_rate,
            2
        )

        tax = round(
            processing_fee * 0.18,
            2
        )

        expected_net = round(
            amount
            - processing_fee
            - tax,
            2
        )

        settlement_id = (
            f"SET{500000 + i}"
        )

        settlement_date = (
            payment_date
            + timedelta(days=2)
        )

        actual_net = expected_net
        adjustment = 0.0

        settlement_exists = True
        bank_exists = True

        bank_date = settlement_date


        # ========================================================
        # SCENARIO MODIFICATIONS
        # ========================================================

        if scenario == "FEE_TAX_DIFFERENCE":

            actual_net = round(
                expected_net
                - random.choice([
                    50,
                    100,
                    150,
                    250
                ]),
                2
            )


        elif scenario == "MISSING_SETTLEMENT":

            settlement_exists = False
            settlement_id = ""


        elif scenario == "MISSING_BANK_CREDIT":

            bank_exists = False


        elif scenario == "DUPLICATE":

            pass


        elif scenario == "PARTIAL_SETTLEMENT":

            actual_net = round(
                expected_net
                * random.choice([
                    0.35,
                    0.50,
                    0.60
                ]),
                2
            )


        elif scenario == "SETTLEMENT_DELAY":

            settlement_date = (
                payment_date
                + timedelta(
                    days=random.randint(5, 8)
                )
            )

            bank_date = settlement_date


        elif scenario == "AMOUNT_MISMATCH":

            actual_net = round(
                expected_net
                - random.choice([
                    250,
                    500,
                    1000,
                    1500,
                    2500
                ]),
                2
            )


        elif scenario == "NOISY_REFERENCE":

            reference_id = (
                reference_id.replace("-", "")
            )


        elif scenario == "AMBIGUOUS_UNRESOLVED":

            actual_net = round(
                expected_net
                - random.choice([
                    100,
                    150,
                    200
                ]),
                2
            )


        # ========================================================
        # PAYMENT RECORD
        # ========================================================

        payments.append({

            "payment_id":
                payment_id,

            "merchant_id":
                merchant_id,

            "customer_id":
                customer_id,

            "payment_date":
                payment_date.strftime(
                    "%Y-%m-%d"
                ),

            "payment_time":
                payment_dt.strftime(
                    "%H:%M:%S"
                ),

            "amount":
                amount,

            "currency":
                "INR",

            "payment_method":
                method,

            "status":
                "SUCCESS",

            "reference_id":
                reference_id
        })


        # ========================================================
        # SETTLEMENT RECORD
        # ========================================================

        if settlement_exists:

            settlements.append({

                "settlement_id":
                    settlement_id,

                "payment_id":
                    payment_id,

                "merchant_id":
                    merchant_id,

                "settlement_date":
                    settlement_date.strftime(
                        "%Y-%m-%d"
                    ),

                "gross_amount":
                    amount,

                "processing_fee":
                    processing_fee,

                "tax":
                    tax,

                "adjustment":
                    adjustment,

                "net_amount":
                    actual_net,

                "settlement_status":
                    "SETTLED",

                "reference_id":
                    reference_id
            })


        # ========================================================
        # BANK RECORD
        # ========================================================

        if bank_exists:

            bank.append({

                "bank_transaction_id":
                    f"BANK{900000 + i}",

                "settlement_id":
                    settlement_id,

                "bank_date":
                    bank_date.strftime(
                        "%Y-%m-%d"
                    ),

                "credit_amount":
                    actual_net,

                "bank_reference":
                    f"NEFT-{random.randint(10000000, 99999999)}",

                "bank_status":
                    "CREDITED"
            })


        # ========================================================
        # AMBIGUOUS SETTLEMENT CANDIDATE
        # ========================================================

        if (
            scenario == "AMBIGUOUS_UNRESOLVED"
            and settlement_exists
        ):

            ambiguous_settlement_id = (
                f"SET{800000 + i}"
            )

            ambiguous_net = round(
                expected_net
                + random.choice([
                    25,
                    50,
                    75
                ]),
                2
            )

            settlements.append({

                "settlement_id":
                    ambiguous_settlement_id,

                "payment_id":
                    payment_id,

                "merchant_id":
                    merchant_id,

                "settlement_date":
                    settlement_date.strftime(
                        "%Y-%m-%d"
                    ),

                "gross_amount":
                    amount,

                "processing_fee":
                    processing_fee,

                "tax":
                    tax,

                "adjustment":
                    0.0,

                "net_amount":
                    ambiguous_net,

                "settlement_status":
                    "SETTLED",

                "reference_id":
                    reference_id
            })


        # ========================================================
        # GROUND TRUTH
        # ========================================================

        if scenario in [
            "PERFECT_MATCH",
            "NOISY_REFERENCE"
        ]:

            expected_status = "MATCH"

        elif scenario == "AMBIGUOUS_UNRESOLVED":

            expected_status = "UNRESOLVED"

        else:

            expected_status = "EXCEPTION"


        reasons = {

            "PERFECT_MATCH":
                "All sources reconcile within configured rules.",

            "FEE_TAX_DIFFERENCE":
                "Settlement is lower than expected net after configured fee and tax.",

            "MISSING_SETTLEMENT":
                "No settlement record exists for successful payment.",

            "MISSING_BANK_CREDIT":
                "Settlement exists but no bank credit exists.",

            "DUPLICATE":
                "Duplicate payment record.",

            "PARTIAL_SETTLEMENT":
                "Settlement amount is materially lower than expected net amount.",

            "SETTLEMENT_DELAY":
                "Settlement occurred outside the configured settlement window.",

            "AMOUNT_MISMATCH":
                "Settlement amount differs from expected net without a valid adjustment.",

            "NOISY_REFERENCE":
                "Reference formatting differs but records should match after normalization.",

            "AMBIGUOUS_UNRESOLVED":
                "Insufficient evidence to uniquely resolve the transaction."
        }


        truth.append({

            "payment_id":
                payment_id,

            "scenario":
                scenario,

            "expected_status":
                expected_status,

            "expected_reason":
                reasons[scenario]
        })


        # ========================================================
        # DUPLICATE PAYMENT
        # ========================================================

        if scenario == "DUPLICATE":

            payments.append({

                "payment_id":
                    f"PAY{200000 + i}",

                "merchant_id":
                    merchant_id,

                "customer_id":
                    customer_id,

                "payment_date":
                    payment_date.strftime(
                        "%Y-%m-%d"
                    ),

                "payment_time":
                    payment_dt.strftime(
                        "%H:%M:%S"
                    ),

                "amount":
                    amount,

                "currency":
                    "INR",

                "payment_method":
                    method,

                "status":
                    "SUCCESS",

                "reference_id":
                    reference_id
            })


    # ============================================================
    # WRITE FILES
    # ============================================================

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    pd.DataFrame(payments).to_csv(
        DATA_DIR / "payments.csv",
        index=False
    )

    pd.DataFrame(settlements).to_csv(
        DATA_DIR / "settlements.csv",
        index=False
    )

    pd.DataFrame(bank).to_csv(
        DATA_DIR / "bank_transactions.csv",
        index=False
    )

    pd.DataFrame(truth).to_csv(
        DATA_DIR / "ground_truth.csv",
        index=False
    )


    # ============================================================
    # SUMMARY
    # ============================================================

    print()
    print("==============================================")
    print("       LEDGERLENS V2 DATA GENERATOR")
    print("==============================================")
    print()

    print("LedgerLens V2 dataset generated.")
    print(f"Payments: {len(payments)}")
    print(f"Settlements: {len(settlements)}")
    print(f"Bank records: {len(bank)}")
    print(f"Ground truth: {len(truth)}")

    print()
    print("Scenario counts:")
    print(
        pd.Series(scenarios)
        .value_counts()
        .to_string()
    )

    print()
    print("FILES GENERATED")
    print("----------------------------------------------")
    print("data/payments.csv")
    print("data/settlements.csv")
    print("data/bank_transactions.csv")
    print("data/ground_truth.csv")
    print()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    generate()