Perfect. I’ll convert the **advisor thinking** into **exact, machine-executable inference rules** you can directly implement.

I’ll structure this like a **rules engine spec** (deterministic + extensible for ML later).

---

# 🔍 Expense Tracker – Inference Rules Specification

> Input: Normalized bank transactions
> Output: Financial insights, behavior flags, advisor recommendations

---

## 0️⃣ Prerequisite: Normalized Transaction Schema

Every transaction **must** be normalized first:

```json
{
  "txn_id": "string",
  "date": "YYYY-MM-DD",
  "amount": 1250.00,
  "type": "CREDIT | DEBIT",
  "description": "UPI-ZOMATO",
  "counterparty": "ZOMATO",
  "channel": "UPI | IMPS | NEFT | CARD | CASH",
  "account_id": "string"
}
```

---

## 1️⃣ Income Backbone Rules

### Rule 1.1 — Salary Detection

```text
IF
  CREDIT appears ≥ 2 times
  AND amount variance ≤ 10%
  AND date difference ≈ 30 ± 5 days
THEN
  classify as SALARY
```

**Output**

```json
{
  "income_type": "salary",
  "stability": "high"
}
```

---

### Rule 1.2 — Stable vs Volatile Income

```text
IF CREDIT frequency ≥ monthly AND variance ≤ 20%
→ STABLE_INCOME

ELSE
→ VOLATILE_INCOME
```

---

## 2️⃣ Fixed Obligation Rules

### Rule 2.1 — Fixed Expense Identification

```text
IF
  DEBIT repeats monthly
  AND same counterparty
  AND variance ≤ 15%
THEN
  classify as FIXED_EXPENSE
```

Examples:

* Rent
* EMI
* Insurance
* Subscriptions

---

### Rule 2.2 — Survival Cost Calculation

```text
SURVIVAL_COST =
  SUM(FIXED_EXPENSES)
```

Flag:

```text
IF SURVIVAL_COST > 50% of STABLE_INCOME
→ HIGH_FIXED_BURDEN
```

---

## 3️⃣ Discretionary & Impulse Spending Rules

### Rule 3.1 — Small Frequent Debit Detection

```text
IF
  DEBIT amount ≤ 150
  AND frequency ≥ 10 per month
THEN
  classify as MICRO_LEAK
```

---

### Rule 3.2 — Food / Convenience Overuse

```text
IF
  merchant IN [ZOMATO, SWIGGY, UBER EATS]
  AND monthly total > 8% of income
THEN
  FOOD_OVERSPEND
```

---

### Rule 3.3 — Weekend Emotional Spending

```text
IF
  DEBIT occurs on Sat/Sun
  AND discretionary category
  AND > 60% of weekly discretionary spend
THEN
  WEEKEND_SPENDER
```

---

## 4️⃣ Investment Discipline Rules

### Rule 4.1 — Automated Investment Detection

```text
IF
  DEBIT repeats monthly
  AND merchant IN [GROWW, COIN, ZERODHA]
THEN
  AUTOMATED_INVESTMENT
```

---

### Rule 4.2 — Discipline Score

```text
DISCIPLINE_SCORE =
  (# automated investment months) / (total months)
```

Flag:

```text
IF DISCIPLINE_SCORE < 0.6
→ WEAK_DISCIPLINE
```

---

## 5️⃣ Transfers to People (Emotional Load)

### Rule 5.1 — Family Support Detection

```text
IF
  counterparty repeats
  AND description contains [MOM, DAD, FAMILY]
THEN
  FAMILY_TRANSFER
```

---

### Rule 5.2 — Obligation Creep

```text
IF
  FAMILY_TRANSFER amount increases ≥ 20% over 3 months
THEN
  EMOTIONAL_BURDEN_INCREASING
```

---

## 6️⃣ Cash Flow Timing & Stress

### Rule 6.1 — Salary Day Spend Spike

```text
IF
  discretionary spend in 5 days post salary
  > 40% of monthly discretionary spend
THEN
  SALARY_DAY_SPENDER
```

---

### Rule 6.2 — End-Month Balance Stress

```text
IF
  average balance (last 5 days) < 15% of income
THEN
  CASH_FLOW_STRESS
```

---

## 7️⃣ Personality Inference Engine

### Rule 7.1 — Impulsive Profile

```text
IF
  MICRO_LEAK present
  AND WEEKEND_SPENDER
  AND SALARY_DAY_SPENDER
THEN
  PERSONALITY = IMPULSIVE
```

---

### Rule 7.2 — Anxious Saver

```text
IF
  high savings transfers
  AND low discretionary spend
  AND irregular investments
THEN
  PERSONALITY = ANXIOUS
```

---

### Rule 7.3 — Generous Over-Committer

```text
IF
  FAMILY_TRANSFER > 25% of income
THEN
  PERSONALITY = OVER_COMMITTED
```

---

## 8️⃣ Advisor Recommendation Rules (Actionable Output)

### Rule 8.1 — One Rule Recommendation

```text
IF CASH_FLOW_STRESS
→ Recommend: "Weekly discretionary cap"
```

```json
{
  "advisor_rule": "Cap discretionary spending weekly, not monthly"
}
```

---

### Rule 8.2 — Auto-Correction Suggestions

```text
IF FOOD_OVERSPEND
→ Suggest prepaid food wallet
```

---

## 9️⃣ Final Advisor Output Schema

```json
{
  "income_health": "stable | volatile",
  "fixed_burden": "low | medium | high",
  "leak_sources": ["food", "micro_spends"],
  "investment_discipline": "strong | weak",
  "financial_personality": "impulsive",
  "stress_level": "high",
  "one_change_that_matters": "Weekly discretionary cap"
}
```

---

## 🔑 Why this is powerful

* Deterministic (explainable)
* No ML needed initially
* Works from **raw bank statements**
* Can later be enhanced with ML / LLM reasoning

---

