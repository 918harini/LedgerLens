# LedgerLens — AI Finance Controller

**Track 04: AI Finance Controller — Razorpay Buildathon**

LedgerLens is a rule-based financial reconciliation and exception detection system designed to compare payment, settlement, and bank transaction records, identify reconciliation exceptions, classify their causes, and route ambiguous transactions for human review.

---

## 1. Problem Statement

Financial transactions often pass through multiple systems before they are completely settled.

A single payment may appear in:

- Payment records
- Settlement records
- Bank transaction records

Differences between these sources can occur because of:

- Missing settlements
- Missing bank credits
- Amount mismatches
- Fee and tax differences
- Partial settlements
- Settlement delays
- Duplicate transactions
- Reference-format differences
- Ambiguous settlement candidates

Manually identifying these issues can be time-consuming and error-prone.

LedgerLens automates this reconciliation process using deterministic rules while maintaining a human-in-the-loop mechanism for cases that cannot be uniquely resolved.

---

## 2. Objective

The main objective of LedgerLens is to:

1. Match payment records with settlement records.
2. Validate settlement amounts.
3. Verify corresponding bank credits.
4. Detect duplicate transactions.
5. Identify reconciliation exceptions.
6. Classify the reason for each exception.
7. Detect ambiguous cases that require human intervention.
8. Evaluate reconciliation performance against known ground truth.

---

## 3. Key Features

### Multi-source Reconciliation

LedgerLens compares information across:

- Payment records
- Settlement records
- Bank transactions

### Reference Normalization

Transaction references can be normalized before matching, allowing records with formatting differences to be reconciled.

Example:

```text
ORD-123456
```
