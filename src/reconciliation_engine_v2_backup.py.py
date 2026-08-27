import pandas as pd
from pathlib import Path


# =========================================================
# 1. FILE LOCATIONS
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"


# =========================================================
# 2. LOAD DATA
# =========================================================

def load_data():

    payments = pd.read_csv(
        DATA_DIR / "payments.csv"
    )

    settlements = pd.read_csv(
        DATA_DIR / "settlements.csv"
    )

    bank = pd.read_csv(
        DATA_DIR / "bank_transactions.csv"
    )

    return payments, settlements, bank


# =========================================================
# 3. NORMALIZATION
# =========================================================

def normalize_data(
    payments,
    settlements,
    bank
):

    # -----------------------------------------------------
    # Dates
    # -----------------------------------------------------

    payments["payment_date"] = pd.to_datetime(
        payments["payment_date"],
        errors="coerce"
    )

    settlements["settlement_date"] = pd.to_datetime(
        settlements["settlement_date"],
        errors="coerce"
    )

    bank["bank_date"] = pd.to_datetime(
        bank["bank_date"],
        errors="coerce"
    )

    # -----------------------------------------------------
    # IDs / references
    # -----------------------------------------------------

    column_groups = [

        (
            payments,
            [
                "payment_id",
                "merchant_id",
                "customer_id",
                "reference_id"
            ]
        ),

        (
            settlements,
            [
                "settlement_id",
                "payment_id",
                "merchant_id",
                "reference_id"
            ]
        ),

        (
            bank,
            [
                "bank_transaction_id",
                "settlement_id",
                "bank_reference"
            ]
        )
    ]

    for df, columns in column_groups:

        for column in columns:

            if column in df.columns:

                df[column] = (
                    df[column]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .str.upper()
                )

    # -----------------------------------------------------
    # Numeric fields
    # -----------------------------------------------------

    payments["amount"] = pd.to_numeric(
        payments["amount"],
        errors="coerce"
    )

    for column in [
        "gross_amount",
        "processing_fee",
        "tax",
        "adjustment",
        "net_amount"
    ]:

        settlements[column] = pd.to_numeric(
            settlements[column],
            errors="coerce"
        )

    bank["credit_amount"] = pd.to_numeric(
        bank["credit_amount"],
        errors="coerce"
    )

    return (
        payments,
        settlements,
        bank
    )


# =========================================================
# 4. DUPLICATE DETECTION
# =========================================================

def find_duplicates(payments):

    duplicate_ids = set()

    duplicate_groups = payments.groupby(
        [
            "merchant_id",
            "customer_id",
            "amount",
            "reference_id"
        ],
        dropna=False
    )

    for _, group in duplicate_groups:

        if len(group) > 1:

            # Keep the first occurrence as legitimate.
            # Flag only subsequent identical records.

            group = group.sort_values(
                "payment_id"
            )

            duplicate_rows = group.iloc[1:]

            for payment_id in duplicate_rows[
                "payment_id"
            ]:

                duplicate_ids.add(
                    payment_id
                )

    return duplicate_ids


# =========================================================
# 5. RECONCILE ONE PAYMENT
# =========================================================

def reconcile_payment(
    payment,
    settlement,
    bank_record,
    duplicate_ids
):

    payment_id = payment["payment_id"]

    result = {

        "payment_id":
            payment_id,

        "payment_amount":
            payment["amount"],

        "settlement_id":
            "",

        "settlement_amount":
            None,

        "bank_transaction_id":
            "",

        "bank_amount":
            None,

        "status":
            "",

        "reason":
            "",

        "confidence":
            0.0
    }


    # =====================================================
    # DUPLICATE
    # =====================================================

    if payment_id in duplicate_ids:

        result["status"] = "EXCEPTION"

        result["reason"] = (
            "Duplicate payment detected using "
            "merchant, customer, amount and reference."
        )

        result["confidence"] = 0.99

        return result


    # =====================================================
    # MISSING SETTLEMENT
    # =====================================================

    if settlement is None:

        result["status"] = "EXCEPTION"

        result["reason"] = (
            "No corresponding settlement found."
        )

        result["confidence"] = 0.99

        return result


    result["settlement_id"] = (
        settlement["settlement_id"]
    )

    result["settlement_amount"] = (
        settlement["net_amount"]
    )


    # =====================================================
    # SETTLEMENT CALCULATION
    # =====================================================

    gross = settlement["gross_amount"]

    fee = settlement["processing_fee"]

    tax = settlement["tax"]

    adjustment = settlement["adjustment"]

    expected_net = round(
        gross
        - fee
        - tax
        - adjustment,
        2
    )

    actual_net = round(
        settlement["net_amount"],
        2
    )

    difference = round(
        expected_net
        - actual_net,
        2
    )


    # =====================================================
    # PARTIAL SETTLEMENT
    # =====================================================
    #
    # The synthetic generator creates partial settlements
    # at approximately 35%, 50% or 60% of expected amount.
    #
    # Therefore we use 65% as the upper boundary.
    #
    # This prevents normal AMOUNT_MISMATCH records such as
    # 78%, 80%, etc. from being incorrectly classified as
    # PARTIAL_SETTLEMENT.
    #
    # =====================================================

    settlement_ratio = (
        actual_net / expected_net
        if expected_net != 0
        else 0
    )

    if (
        0 < settlement_ratio <= 0.65
        and difference > 0.01
    ):

        result["status"] = "EXCEPTION"

        result["reason"] = (
            f"Partial settlement detected. "
            f"Expected ₹{expected_net:.2f}, "
            f"received ₹{actual_net:.2f}."
        )

        result["confidence"] = 0.98

        return result


    # =====================================================
    # OTHER AMOUNT MISMATCH
    # =====================================================

    if abs(difference) > 0.01:

        result["status"] = "EXCEPTION"

        result["reason"] = (
            f"Settlement amount mismatch. "
            f"Expected ₹{expected_net:.2f}, "
            f"recorded ₹{actual_net:.2f}."
        )

        result["confidence"] = 0.96

        return result


    # =====================================================
    # SETTLEMENT DELAY
    # =====================================================

    payment_date = payment["payment_date"]

    settlement_date = settlement[
        "settlement_date"
    ]

    if (
        pd.notna(payment_date)
        and pd.notna(settlement_date)
    ):

        settlement_days = (
            settlement_date
            - payment_date
        ).days

        # Two days is the expected settlement window.

        if settlement_days > 2:

            result["status"] = "EXCEPTION"

            result["reason"] = (
                f"Settlement delay detected. "
                f"Settlement occurred "
                f"{settlement_days} days after payment."
            )

            result["confidence"] = 0.98

            return result


    # =====================================================
    # MISSING BANK CREDIT
    # =====================================================

    if bank_record is None:

        result["status"] = "EXCEPTION"

        result["reason"] = (
            "Settlement exists but corresponding "
            "bank credit was not found."
        )

        result["confidence"] = 0.99

        return result


    result["bank_transaction_id"] = (
        bank_record["bank_transaction_id"]
    )

    result["bank_amount"] = (
        bank_record["credit_amount"]
    )


    # =====================================================
    # BANK AMOUNT CHECK
    # =====================================================

    bank_difference = round(
        settlement["net_amount"]
        - bank_record["credit_amount"],
        2
    )

    if abs(bank_difference) > 0.01:

        result["status"] = "EXCEPTION"

        result["reason"] = (
            f"Bank credit mismatch. "
            f"Expected ₹"
            f"{settlement['net_amount']:.2f}, "
            f"received ₹"
            f"{bank_record['credit_amount']:.2f}."
        )

        result["confidence"] = 0.97

        return result


    # =====================================================
    # SUCCESS
    # =====================================================

    result["status"] = "MATCHED"

    result["reason"] = (
        "Payment, settlement and bank credit "
        "reconcile successfully."
    )

    result["confidence"] = 0.99

    return result


# =========================================================
# 6. MAIN RECONCILIATION ENGINE
# =========================================================

def run_reconciliation():

    print("\n======================================")
    print("     LEDGERLENS RECONCILIATION V2")
    print("======================================\n")


    # -----------------------------------------------------
    # Load
    # -----------------------------------------------------

    payments, settlements, bank = (
        load_data()
    )

    print(
        f"Payments loaded:     {len(payments)}"
    )

    print(
        f"Settlements loaded:  {len(settlements)}"
    )

    print(
        f"Bank records loaded: {len(bank)}"
    )


    # -----------------------------------------------------
    # Normalize
    # -----------------------------------------------------

    payments, settlements, bank = (
        normalize_data(
            payments,
            settlements,
            bank
        )
    )


    # -----------------------------------------------------
    # Detect duplicates
    # -----------------------------------------------------

    duplicate_ids = find_duplicates(
        payments
    )

    print(
        f"Duplicate payment records detected: "
        f"{len(duplicate_ids)}"
    )


    # -----------------------------------------------------
    # Lookup tables
    # -----------------------------------------------------

    settlement_lookup = {

        row["payment_id"]:
            row

        for _, row
        in settlements.iterrows()
    }


    bank_lookup = {

        row["settlement_id"]:
            row

        for _, row
        in bank.iterrows()

        if row["settlement_id"] != ""
    }


    # -----------------------------------------------------
    # Process payments
    # -----------------------------------------------------

    results = []

    for _, payment in (
        payments.iterrows()
    ):

        payment_id = (
            payment["payment_id"]
        )

        settlement = (
            settlement_lookup.get(
                payment_id
            )
        )

        bank_record = None

        if settlement is not None:

            bank_record = (
                bank_lookup.get(
                    settlement[
                        "settlement_id"
                    ]
                )
            )

        result = reconcile_payment(
            payment,
            settlement,
            bank_record,
            duplicate_ids
        )

        results.append(result)


    results_df = pd.DataFrame(
        results
    )


    # -----------------------------------------------------
    # Save results
    # -----------------------------------------------------

    output_path = (
        DATA_DIR
        / "reconciliation_results.csv"
    )

    results_df.to_csv(
        output_path,
        index=False
    )


    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    total = len(results_df)

    matched = len(
        results_df[
            results_df["status"]
            == "MATCHED"
        ]
    )

    exceptions = (
        total
        - matched
    )

    match_rate = (

        matched
        / total
        * 100

        if total > 0

        else 0
    )


    print("\n======================================")
    print("               RESULTS")
    print("======================================")

    print(
        f"Records processed: {total}"
    )

    print(
        f"Matched:           {matched}"
    )

    print(
        f"Exceptions:        {exceptions}"
    )

    print(
        f"Match rate:        "
        f"{match_rate:.2f}%"
    )

    print("\nResults saved to:")

    print(output_path)

    print(
        "\n======================================\n"
    )


# =========================================================
# 7. RUN
# =========================================================

if __name__ == "__main__":

    run_reconciliation()