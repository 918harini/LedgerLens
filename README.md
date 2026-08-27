# LedgerLens — AI Finance Controller

Track 04: AI Finance Controller — Razorpay Buildathon

## Current stage
Phase 1: synthetic finance data and ground truth.

## Data files
- `data/payments.csv` — successful payment records
- `data/settlements.csv` — settlement records
- `data/bank_transactions.csv` — bank credit records
- `data/ground_truth.csv` — hidden evaluation labels used during development

## Scenarios represented
Perfect matches, fee/tax differences, missing settlements, missing bank credits,
duplicates, partial settlements, settlement delays, amount mismatches,
noisy references, and ambiguous/unresolved cases.

## Important
`ground_truth.csv` is for development/evaluation. It should not be exposed to the
reconciliation agent during inference.

## Planned architecture
1. Data normalization
2. Reconciliation engine
3. Exception classification
4. Evidence-backed AI investigation
5. Finance control tower
6. Evaluation and throughput reporting
