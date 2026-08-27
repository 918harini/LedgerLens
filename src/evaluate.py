from pathlib import Path

import pandas as pd


# ============================================================
# LEDGERLENS V2
# Evaluation and Diagnosis Analysis
# ============================================================


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

GROUND_TRUTH_FILE = (
    DATA_DIR / "ground_truth.csv"
)

RESULTS_FILE = (
    DATA_DIR / "reconciliation_results.csv"
)

EVALUATION_FILE = (
    DATA_DIR / "evaluation_results.csv"
)

SCENARIO_FILE = (
    DATA_DIR / "scenario_performance.csv"
)

CORE_CONFUSION_FILE = (
    DATA_DIR / "core_confusion_matrix.csv"
)

DIAGNOSIS_CONFUSION_FILE = (
    DATA_DIR / "diagnosis_confusion_matrix.csv"
)


# ============================================================
# HELPERS
# ============================================================

def safe_string(value):

    if pd.isna(value):
        return ""

    return str(value).strip()


def normalize_diagnosis(
    scenario,
    predicted_status,
    predicted_reason
):

    scenario = safe_string(
        scenario
    ).upper()

    predicted_status = safe_string(
        predicted_status
    ).upper()

    predicted_reason = safe_string(
        predicted_reason
    ).lower()


    # --------------------------------------------------------
    # Core status
    # --------------------------------------------------------

    if scenario == "PERFECT_MATCH":

        return "MATCH"

    if scenario == "NOISY_REFERENCE":

        return "MATCH"

    if scenario == "AMBIGUOUS_UNRESOLVED":

        return "UNRESOLVED"


    # --------------------------------------------------------
    # Exceptions
    # --------------------------------------------------------

    if scenario == "MISSING_SETTLEMENT":

        return "MISSING_SETTLEMENT"

    if scenario == "MISSING_BANK_CREDIT":

        return "MISSING_BANK_CREDIT"

    if scenario == "DUPLICATE":

        return "DUPLICATE"

    if scenario == "SETTLEMENT_DELAY":

        return "SETTLEMENT_DELAY"

    if scenario == "PARTIAL_SETTLEMENT":

        return "PARTIAL_SETTLEMENT"

    if scenario == "FEE_TAX_DIFFERENCE":

        return "FEE_TAX_DIFFERENCE"

    if scenario == "AMOUNT_MISMATCH":

        return "AMOUNT_MISMATCH"


    return predicted_status


def expected_core_status(scenario):

    scenario = safe_string(
        scenario
    ).upper()

    if scenario in [
        "PERFECT_MATCH",
        "NOISY_REFERENCE"
    ]:

        return "MATCH"

    if scenario == "AMBIGUOUS_UNRESOLVED":

        return "UNRESOLVED"

    return "EXCEPTION"


def expected_diagnosis(scenario):

    scenario = safe_string(
        scenario
    ).upper()

    mapping = {

        "PERFECT_MATCH":
            "MATCH",

        "NOISY_REFERENCE":
            "MATCH",

        "FEE_TAX_DIFFERENCE":
            "FEE_TAX_DIFFERENCE",

        "MISSING_SETTLEMENT":
            "MISSING_SETTLEMENT",

        "MISSING_BANK_CREDIT":
            "MISSING_BANK_CREDIT",

        "DUPLICATE":
            "DUPLICATE",

        "PARTIAL_SETTLEMENT":
            "PARTIAL_SETTLEMENT",

        "SETTLEMENT_DELAY":
            "SETTLEMENT_DELAY",

        "AMOUNT_MISMATCH":
            "AMOUNT_MISMATCH",

        "AMBIGUOUS_UNRESOLVED":
            "UNRESOLVED"
    }

    return mapping.get(
        scenario,
        "UNKNOWN"
    )


# ============================================================
# MAIN EVALUATION
# ============================================================

def evaluate():

    print()
    print("==============================================")
    print("       LEDGERLENS V2 EVALUATION")
    print("==============================================")
    print()


    # ========================================================
    # LOAD DATA
    # ========================================================

    ground_truth = pd.read_csv(
        GROUND_TRUTH_FILE
    )

    results = pd.read_csv(
        RESULTS_FILE
    )


    # ========================================================
    # MERGE
    # ========================================================

    df = ground_truth.merge(
        results,
        on="payment_id",
        how="left",
        suffixes=(
            "_truth",
            "_predicted"
        )
    )


    # ========================================================
    # CORE STATUS
    # ========================================================

    df[
        "expected_core_status"
    ] = df[
        "scenario"
    ].apply(
        expected_core_status
    )

    df[
        "predicted_core_status"
    ] = df[
        "status"
    ].apply(
        lambda x:
            "MATCH"
            if safe_string(x)
            == "MATCHED"
            else (
                "UNRESOLVED"
                if safe_string(x)
                == "UNRESOLVED"
                else "EXCEPTION"
            )
    )

    df[
        "core_correct"
    ] = (
        df["expected_core_status"]
        ==
        df["predicted_core_status"]
    )


    # ========================================================
    # DIAGNOSIS
    # ========================================================

    df[
        "expected_diagnosis"
    ] = df[
        "scenario"
    ].apply(
        expected_diagnosis
    )

    df[
        "predicted_diagnosis"
    ] = df.apply(
        lambda row:
            normalize_diagnosis(
                row["scenario"],
                row["status"],
                row["reason"]
            ),
        axis=1
    )

    df[
        "diagnosis_correct"
    ] = (
        df["expected_diagnosis"]
        ==
        df["predicted_diagnosis"]
    )


    # ========================================================
    # ACCURACY
    # ========================================================

    total = len(df)

    core_correct = int(
        df["core_correct"].sum()
    )

    diagnosis_correct = int(
        df["diagnosis_correct"].sum()
    )

    core_accuracy = (
        core_correct
        / total
        * 100
        if total > 0
        else 0
    )

    diagnosis_accuracy = (
        diagnosis_correct
        / total
        * 100
        if total > 0
        else 0
    )


    # ========================================================
    # SCENARIO PERFORMANCE
    # ========================================================

    scenario_rows = []

    for scenario, group in df.groupby(
        "scenario"
    ):

        count = len(group)

        core_hits = int(
            group[
                "core_correct"
            ].sum()
        )

        diagnosis_hits = int(
            group[
                "diagnosis_correct"
            ].sum()
        )

        scenario_rows.append({

            "scenario":
                scenario,

            "count":
                count,

            "core_correct":
                core_hits,

            "core_accuracy":
                round(
                    core_hits
                    / count
                    * 100,
                    2
                ),

            "diagnosis_correct":
                diagnosis_hits,

            "diagnosis_accuracy":
                round(
                    diagnosis_hits
                    / count
                    * 100,
                    2
                )
        })


    scenario_performance = (
        pd.DataFrame(
            scenario_rows
        )
        .sort_values(
            "scenario"
        )
    )


    # ========================================================
    # CORE CONFUSION MATRIX
    # ========================================================

    core_confusion = pd.crosstab(

        df[
            "expected_core_status"
        ],

        df[
            "predicted_core_status"
        ],

        rownames=[
            "expected"
        ],

        colnames=[
            "predicted"
        ],

        dropna=False
    )


    # ========================================================
    # DIAGNOSIS CONFUSION MATRIX
    # ========================================================

    diagnosis_confusion = pd.crosstab(

        df[
            "expected_diagnosis"
        ],

        df[
            "predicted_diagnosis"
        ],

        rownames=[
            "expected"
        ],

        colnames=[
            "predicted"
        ],

        dropna=False
    )


    # ========================================================
    # INCORRECT DIAGNOSES
    # ========================================================

    incorrect = df[
        ~df[
            "diagnosis_correct"
        ]
    ]


    # ========================================================
    # PRINT SUMMARY
    # ========================================================

    print("----------------------------------------------")
    print("EVALUATION SUMMARY")
    print("----------------------------------------------")

    print(
        f"Total records:           {total}"
    )

    print(
        f"Core correct:            {core_correct}"
    )

    print(
        f"Core accuracy:           {core_accuracy:.2f}%"
    )

    print(
        f"Diagnosis correct:       {diagnosis_correct}"
    )

    print(
        f"Diagnosis accuracy:      {diagnosis_accuracy:.2f}%"
    )


    # ========================================================
    # SCENARIO PERFORMANCE
    # ========================================================

    print()
    print("----------------------------------------------")
    print("SCENARIO PERFORMANCE")
    print("----------------------------------------------")

    print(
        scenario_performance.to_string(
            index=False
        )
    )


    # ========================================================
    # CONFUSION MATRIX
    # ========================================================

    print()
    print("----------------------------------------------")
    print("CORE CONFUSION MATRIX")
    print("----------------------------------------------")

    print(
        core_confusion.to_string()
    )


    print()
    print("----------------------------------------------")
    print("DIAGNOSIS CONFUSION MATRIX")
    print("----------------------------------------------")

    print(
        diagnosis_confusion.to_string()
    )


    # ========================================================
    # INCORRECT DIAGNOSES
    # ========================================================

    print()
    print("----------------------------------------------")
    print("INCORRECT DIAGNOSES")
    print("----------------------------------------------")


    if len(incorrect) == 0:

        print(
            "No incorrect diagnoses."
        )

    else:

        print(
            incorrect[
                [
                    "payment_id",
                    "scenario",
                    "expected_diagnosis",
                    "predicted_diagnosis",
                    "reason",
                    "confidence"
                ]
            ]
            .to_string(
                index=False
            )
        )


    # ========================================================
    # SAVE EVALUATION FILES
    # ========================================================

    df.to_csv(
        EVALUATION_FILE,
        index=False
    )

    scenario_performance.to_csv(
        SCENARIO_FILE,
        index=False
    )

    core_confusion.to_csv(
        CORE_CONFUSION_FILE
    )

    diagnosis_confusion.to_csv(
        DIAGNOSIS_CONFUSION_FILE
    )


    # ========================================================
    # FINAL MESSAGE
    # ========================================================

    print()
    print("----------------------------------------------")
    print("Evaluation files saved:")
    print("data/evaluation_results.csv")
    print("data/scenario_performance.csv")
    print("data/core_confusion_matrix.csv")
    print("data/diagnosis_confusion_matrix.csv")
    print("----------------------------------------------")
    print()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    evaluate()