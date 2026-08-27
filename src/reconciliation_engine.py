from pathlib import Path
import pandas as pd


# ============================================================
# LEDGERLENS V2
# Deterministic Financial Reconciliation Engine
# ============================================================


# ============================================================
# 1. CONSTANTS
# ============================================================

MATCHED = "MATCHED"
EXCEPTION = "EXCEPTION"
UNRESOLVED = "UNRESOLVED"

HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"

SETTLEMENT_WINDOW_DAYS = 3
AMOUNT_TOLERANCE = 0.01


# ============================================================
# 2. FILE LOCATIONS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

PAYMENTS_FILE = DATA_DIR / "payments.csv"
SETTLEMENTS_FILE = DATA_DIR / "settlements.csv"
BANK_FILE = DATA_DIR / "bank_transactions.csv"

OUTPUT_FILE = DATA_DIR / "reconciliation_results.csv"


# ============================================================
# 3. UTILITY FUNCTIONS
# ============================================================

def normalize_reference(value):

    if pd.isna(value):
        return ""

    value = str(value).strip().upper()

    return (
        value
        .replace("-", "")
        .replace("_", "")
        .replace(" ", "")
    )


def safe_float(value):

    try:
        return float(value)

    except (TypeError, ValueError):
        return 0.0


def parse_date(value):

    try:
        return pd.to_datetime(value)

    except Exception:
        return pd.NaT


def amount_matches(expected, actual):

    return abs(
        safe_float(expected)
        - safe_float(actual)
    ) <= AMOUNT_TOLERANCE


# ============================================================
# 4. STATE MACHINE
# ============================================================

class ReconciliationStateMachine:

    LOAD = "LOAD"
    DUPLICATE_CHECK = "DUPLICATE_CHECK"
    MATCH_EVIDENCE = "MATCH_EVIDENCE"
    VALIDATION = "VALIDATION"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    FINAL = "FINAL"

    def __init__(self):

        self.state = self.LOAD

    def transition(self, new_state):

        self.state = new_state


# ============================================================
# 5. DATA LOADING
# ============================================================

def load_data():

    payments = pd.read_csv(
        PAYMENTS_FILE
    )

    settlements = pd.read_csv(
        SETTLEMENTS_FILE
    )

    bank = pd.read_csv(
        BANK_FILE
    )

    return payments, settlements, bank


# ============================================================
# 6. DUPLICATE DETECTION
# ============================================================

def detect_duplicate_payments(payments):

    duplicate_columns = [

        "merchant_id",
        "customer_id",
        "payment_date",
        "payment_time",
        "amount",
        "payment_method",
        "reference_id"
    ]

    duplicate_mask = payments.duplicated(
        subset=duplicate_columns,
        keep=False
    )

    duplicate_ids = set(
        payments.loc[
            duplicate_mask,
            "payment_id"
        ].astype(str)
    )

    return duplicate_ids


# ============================================================
# 7. BUILD LOOKUP TABLES
# ============================================================

def build_settlement_indexes(settlements):

    by_payment_id = {}
    by_reference = {}

    for _, row in settlements.iterrows():

        payment_id = str(
            row.get(
                "payment_id",
                ""
            )
        )

        reference = normalize_reference(
            row.get(
                "reference_id",
                ""
            )
        )

        by_payment_id.setdefault(
            payment_id,
            []
        ).append(row)

        if reference:

            by_reference.setdefault(
                reference,
                []
            ).append(row)

    return (
        by_payment_id,
        by_reference
    )


def build_bank_indexes(bank):

    by_settlement_id = {}

    for _, row in bank.iterrows():

        settlement_id = str(
            row.get(
                "settlement_id",
                ""
            )
        )

        by_settlement_id.setdefault(
            settlement_id,
            []
        ).append(row)

    return by_settlement_id


# ============================================================
# 8. CANDIDATE SETTLEMENT SEARCH
# ============================================================

def find_settlement_candidates(
    payment,
    settlements_by_payment,
    settlements_by_reference
):

    payment_id = str(
        payment["payment_id"]
    )

    reference = normalize_reference(
        payment["reference_id"]
    )

    candidates = []


    # --------------------------------------------------------
    # First preference: exact payment ID
    # --------------------------------------------------------

    if payment_id in settlements_by_payment:

        candidates.extend(
            settlements_by_payment[payment_id]
        )


    # --------------------------------------------------------
    # Second preference: normalized reference
    # --------------------------------------------------------

    if not candidates and reference:

        candidates.extend(
            settlements_by_reference.get(
                reference,
                []
            )
        )


    # --------------------------------------------------------
    # Remove duplicate candidate rows
    # --------------------------------------------------------

    unique = {}

    for row in candidates:

        settlement_id = str(
            row.get(
                "settlement_id",
                ""
            )
        )

        unique[settlement_id] = row

    return list(
        unique.values()
    )


# ============================================================
# 9. EXPECTED NET CALCULATION
# ============================================================

def calculate_expected_net(
    payment,
    settlement
):

    gross_amount = safe_float(
        payment["amount"]
    )

    method = str(
        payment["payment_method"]
    ).upper()


    # Synthetic policy used by generator.
    fee_rate = (
        0.015
        if method == "CARD"
        else 0.01
    )

    processing_fee = round(
        gross_amount * fee_rate,
        2
    )

    tax = round(
        processing_fee * 0.18,
        2
    )

    adjustment = safe_float(
        settlement.get(
            "adjustment",
            0
        )
    )

    expected_net = round(
        gross_amount
        - processing_fee
        - tax
        + adjustment,
        2
    )

    return expected_net


# ============================================================
# 10. CONFIDENCE CALCULATION
# ============================================================

def calculate_confidence(
    reference_match,
    payment_id_match,
    amount_match,
    bank_match,
    duplicate=False,
    delayed=False,
    ambiguous=False
):

    score = 0.50

    if reference_match:
        score += 0.15

    if payment_id_match:
        score += 0.15

    if amount_match:
        score += 0.15

    if bank_match:
        score += 0.10

    if duplicate:
        score += 0.03

    if delayed:
        score -= 0.08

    if ambiguous:
        score -= 0.25

    score = max(
        0.0,
        min(0.99, score)
    )

    return round(
        score,
        2
    )


# ============================================================
# 11. RECONCILE ONE PAYMENT
# ============================================================

def reconcile_payment(
    payment,
    settlements_by_payment,
    settlements_by_reference,
    bank_by_settlement,
    duplicate_ids
):

    machine = ReconciliationStateMachine()

    machine.transition(
        ReconciliationStateMachine.DUPLICATE_CHECK
    )

    payment_id = str(
        payment["payment_id"]
    )

    payment_reference = normalize_reference(
        payment["reference_id"]
    )

    payment_date = parse_date(
        payment["payment_date"]
    )


    result = {

        "payment_id":
            payment_id,

        "status":
            EXCEPTION,

        "reason":
            "",

        "confidence":
            0.0,

        "state":
            machine.state,

        "payment_evidence":
            "AVAILABLE",

        "settlement_evidence":
            "UNKNOWN",

        "bank_evidence":
            "UNKNOWN",

        "match_method":
            "NONE",

        "settlement_id":
            "",

        "bank_transaction_id":
            "",

        "expected_net_amount":
            None,

        "recorded_settlement_amount":
            None,

        "bank_credit_amount":
            None,

        "human_review_required":
            False,

        "human_review_reason":
            ""
    }


    # ========================================================
    # DUPLICATE CHECK
    # ========================================================

    if payment_id in duplicate_ids:

        result["status"] = EXCEPTION

        result["reason"] = (
            "Duplicate payment record detected."
        )

        result["confidence"] = 0.99

        result["match_method"] = (
            "DUPLICATE_DETECTION"
        )

        result["state"] = (
            ReconciliationStateMachine.FINAL
        )

        return result


    # ========================================================
    # MATCH EVIDENCE
    # ========================================================

    machine.transition(
        ReconciliationStateMachine.MATCH_EVIDENCE
    )

    candidates = find_settlement_candidates(
        payment,
        settlements_by_payment,
        settlements_by_reference
    )


    # ========================================================
    # NO SETTLEMENT
    # ========================================================

    if len(candidates) == 0:

        result["settlement_evidence"] = (
            "NOT_FOUND"
        )

        result["status"] = EXCEPTION

        result["reason"] = (
            "No corresponding settlement "
            "record was found for the payment."
        )

        result["confidence"] = 0.98

        result["match_method"] = (
            "NO_SETTLEMENT"
        )

        result["state"] = (
            ReconciliationStateMachine.FINAL
        )

        return result


    # ========================================================
    # MULTIPLE SETTLEMENTS
    # ========================================================

    if len(candidates) > 1:

        result["settlement_evidence"] = (
            "MULTIPLE_CANDIDATES"
        )

        result["status"] = UNRESOLVED

        result["reason"] = (
            "Multiple settlement candidates found. "
            "Unique reconciliation cannot be established."
        )

        result["confidence"] = 0.60

        result["human_review_required"] = True

        result["human_review_reason"] = (
            "Multiple possible settlement records "
            "require manual verification."
        )

        result["state"] = (
            ReconciliationStateMachine.HUMAN_REVIEW
        )

        return result


    # ========================================================
    # UNIQUE SETTLEMENT
    # ========================================================

    settlement = candidates[0]

    settlement_id = str(
        settlement["settlement_id"]
    )

    result["settlement_id"] = (
        settlement_id
    )

    result["settlement_evidence"] = (
        "FOUND"
    )


    # ========================================================
    # MATCH METHOD
    # ========================================================

    settlement_payment_id = str(
        settlement.get(
            "payment_id",
            ""
        )
    )

    settlement_reference = normalize_reference(
        settlement.get(
            "reference_id",
            ""
        )
    )

    payment_id_match = (
        settlement_payment_id
        == payment_id
    )

    reference_match = (
        bool(payment_reference)
        and
        payment_reference
        == settlement_reference
    )


    if payment_id_match:

        result["match_method"] = (
            "PAYMENT_ID"
        )

    elif reference_match:

        result["match_method"] = (
            "NORMALIZED_REFERENCE"
        )

    else:

        result["match_method"] = (
            "WEAK_MATCH"
        )


    # ========================================================
    # EXPECTED SETTLEMENT AMOUNT
    # ========================================================

    expected_net = calculate_expected_net(
        payment,
        settlement
    )

    recorded_net = safe_float(
        settlement["net_amount"]
    )

    result["expected_net_amount"] = (
        round(
            expected_net,
            2
        )
    )

    result["recorded_settlement_amount"] = (
        round(
            recorded_net,
            2
        )
    )

    amount_match = amount_matches(
        expected_net,
        recorded_net
    )


    # ========================================================
    # BANK VALIDATION
    # ========================================================

    bank_records = bank_by_settlement.get(
        settlement_id,
        []
    )


    # --------------------------------------------------------
    # Missing bank credit
    # --------------------------------------------------------

    if len(bank_records) == 0:

        result["bank_evidence"] = (
            "NOT_FOUND"
        )

        result["status"] = EXCEPTION

        result["reason"] = (
            "Settlement exists but bank credit "
            "was not found."
        )

        result["confidence"] = calculate_confidence(
            reference_match,
            payment_id_match,
            amount_match,
            False
        )

        result["state"] = (
            ReconciliationStateMachine.FINAL
        )

        return result


    # --------------------------------------------------------
    # Multiple bank credits
    # --------------------------------------------------------

    if len(bank_records) > 1:

        result["bank_evidence"] = (
            "MULTIPLE_CREDITS"
        )

        result["status"] = UNRESOLVED

        result["reason"] = (
            "Multiple bank credits were found "
            "for the settlement."
        )

        result["confidence"] = 0.60

        result["human_review_required"] = True

        result["human_review_reason"] = (
            "Multiple bank transactions require "
            "manual verification."
        )

        result["state"] = (
            ReconciliationStateMachine.HUMAN_REVIEW
        )

        return result


    bank_record = bank_records[0]

    result["bank_evidence"] = (
        "FOUND"
    )

    result["bank_transaction_id"] = str(
        bank_record["bank_transaction_id"]
    )

    bank_amount = safe_float(
        bank_record["credit_amount"]
    )

    result["bank_credit_amount"] = (
        round(
            bank_amount,
            2
        )
    )

    bank_match = amount_matches(
        recorded_net,
        bank_amount
    )


    # ========================================================
    # SETTLEMENT DELAY
    # ========================================================

    settlement_date = parse_date(
        settlement["settlement_date"]
    )

    delayed = False

    if (
        not pd.isna(payment_date)
        and
        not pd.isna(settlement_date)
    ):

        delay_days = (
            settlement_date
            - payment_date
        ).days

        if delay_days > SETTLEMENT_WINDOW_DAYS:

            delayed = True


    # ========================================================
    # VALIDATION STATE
    # ========================================================

    machine.transition(
        ReconciliationStateMachine.VALIDATION
    )


    # ========================================================
    # BANK AMOUNT MISMATCH
    # ========================================================

    if not bank_match:

        result["status"] = EXCEPTION

        result["reason"] = (
            "Bank credit mismatch. "
            f"Expected ₹{recorded_net:.2f}, "
            f"received ₹{bank_amount:.2f}."
        )

        result["confidence"] = max(
            calculate_confidence(
                reference_match,
                payment_id_match,
                amount_match,
                False
            ),
            0.97
        )

        result["state"] = (
            ReconciliationStateMachine.FINAL
        )

        return result


    # ========================================================
    # SETTLEMENT DELAY
    # ========================================================

    if delayed:

        result["status"] = EXCEPTION

        result["reason"] = (
            "Settlement occurred outside "
            "the configured settlement window."
        )

        result["confidence"] = calculate_confidence(
            reference_match,
            payment_id_match,
            amount_match,
            bank_match,
            delayed=True
        )

        result["state"] = (
            ReconciliationStateMachine.FINAL
        )

        return result


    # ========================================================
    # SETTLEMENT AMOUNT MISMATCH
    # ========================================================

    if not amount_match:

        difference = round(
            expected_net
            - recorded_net,
            2
        )


        # ----------------------------------------------------
        # IMPORTANT:
        # Partial settlement is identified by a materially
        # smaller settlement amount.
        #
        # This threshold is intentionally strict so that
        # normal fee/tax differences are not misdiagnosed
        # as partial settlements.
        # ----------------------------------------------------

        if (
            expected_net > 0
            and
            recorded_net
            <= expected_net * 0.60
        ):

            result["status"] = EXCEPTION

            result["reason"] = (
                "Partial settlement detected. "
                f"Expected ₹{expected_net:.2f}, "
                f"received ₹{recorded_net:.2f}."
            )

            result["confidence"] = 0.98

            result["state"] = (
                ReconciliationStateMachine.FINAL
            )

            return result


        # ----------------------------------------------------
        # Normal amount mismatch
        # ----------------------------------------------------

        result["status"] = EXCEPTION

        result["reason"] = (
            "Settlement amount mismatch. "
            f"Expected ₹{expected_net:.2f}, "
            f"recorded ₹{recorded_net:.2f}."
        )

        result["confidence"] = calculate_confidence(
            reference_match,
            payment_id_match,
            False,
            bank_match
        )

        result["state"] = (
            ReconciliationStateMachine.FINAL
        )

        return result


    # ========================================================
    # ALL CHECKS PASSED
    # ========================================================

    result["status"] = MATCHED

    result["reason"] = (
        "Payment, settlement, and bank records "
        "reconcile within configured rules."
    )

    result["confidence"] = calculate_confidence(
        reference_match,
        payment_id_match,
        amount_match,
        bank_match
    )

    result["state"] = (
        ReconciliationStateMachine.FINAL
    )

    return result


# ============================================================
# 12. MAIN RECONCILIATION PIPELINE
# ============================================================

def run_reconciliation():

    print(
        "\n=========================================="
    )

    print(
        "       LEDGERLENS RECONCILIATION V2"
    )

    print(
        "==========================================\n"
    )


    # ========================================================
    # LOAD DATA
    # ========================================================

    payments, settlements, bank = load_data()

    print(
        f"Payments loaded:     {len(payments)}"
    )

    print(
        f"Settlements loaded:  {len(settlements)}"
    )

    print(
        f"Bank records loaded: {len(bank)}"
    )


    # ========================================================
    # DUPLICATES
    # ========================================================

    duplicate_ids = detect_duplicate_payments(
        payments
    )

    print(
        f"Duplicate payment records detected: "
        f"{len(duplicate_ids)}"
    )


    # ========================================================
    # INDEXES
    # ========================================================

    (
        settlements_by_payment,
        settlements_by_reference
    ) = build_settlement_indexes(
        settlements
    )

    bank_by_settlement = (
        build_bank_indexes(
            bank
        )
    )


    # ========================================================
    # RECONCILIATION
    # ========================================================

    results = []

    for _, payment in payments.iterrows():

        result = reconcile_payment(

            payment,

            settlements_by_payment,

            settlements_by_reference,

            bank_by_settlement,

            duplicate_ids
        )

        results.append(result)


    results_df = pd.DataFrame(
        results
    )


    # ========================================================
    # SUMMARY
    # ========================================================

    matched = int(
        (
            results_df["status"]
            == MATCHED
        ).sum()
    )

    exceptions = int(
        (
            results_df["status"]
            == EXCEPTION
        ).sum()
    )

    unresolved = int(
        (
            results_df["status"]
            == UNRESOLVED
        ).sum()
    )

    human_review = int(
        results_df[
            "human_review_required"
        ].sum()
    )

    total = len(
        results_df
    )

    match_rate = (
        matched
        / total
        * 100
        if total > 0
        else 0
    )


    # ========================================================
    # PRINT RESULTS
    # ========================================================

    print(
        "\n=========================================="
    )

    print(
        "                 RESULTS"
    )

    print(
        "=========================================="
    )

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
        f"Unresolved:        {unresolved}"
    )

    print(
        f"Human review:      {human_review}"
    )

    print(
        f"Match rate:        {match_rate:.2f}%"
    )


    # ========================================================
    # STATUS DISTRIBUTION
    # ========================================================

    print(
        "\n------------------------------------------"
    )

    print(
        "STATUS DISTRIBUTION"
    )

    print(
        "------------------------------------------"
    )

    print(
        results_df[
            "status"
        ]
        .value_counts()
        .to_string()
    )


    # ========================================================
    # HUMAN REVIEW QUEUE
    # ========================================================

    review_df = results_df[
        results_df[
            "human_review_required"
        ]
        == True
    ]

    print(
        "\n------------------------------------------"
    )

    print(
        "HUMAN REVIEW QUEUE"
    )

    print(
        "------------------------------------------"
    )


    if len(review_df) == 0:

        print(
            "No records require human review."
        )

    else:

        print(
            review_df[
                [
                    "payment_id",
                    "status",
                    "reason",
                    "confidence",
                    "human_review_reason"
                ]
            ]
            .to_string(
                index=False
            )
        )


    # ========================================================
    # SAVE RESULTS
    # ========================================================

    results_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        "\n------------------------------------------"
    )

    print(
        "Results saved to:"
    )

    print(
        OUTPUT_FILE
    )

    print(
        "\n==========================================\n"
    )


# ============================================================
# 13. RUN
# ============================================================

if __name__ == "__main__":

    run_reconciliation()