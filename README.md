# AI Reality Check: Decide, Defend, Deliver
### AI Masterclass - Data Professionals | September 30, 2026 | SimCorp Copenhagen

This repository contains all materials for the workshop session **Act 3 - Deliver: AI Development Pipeline**.

---

## What this is

A real AI development pipeline built in 2026 - not a textbook example.

The scenario: an e-commerce team said "go" on an AI-powered insights feature. This repo shows what disciplined delivery looks like from that moment forward - how the feature gets built, reviewed, and shipped, and how it runs in production every day.

---

## Repository structure

```
ai-masterclass-workshop/
|-- data/
|   |-- ecommerce_dataset.csv       (92 days of e-commerce metrics, Oct-Dec 2025)
|   └-- business_context.csv        (holidays, campaigns, release dates)
|-- pipeline/
|   |-- agents/                     (4 agent definitions)
|   |-- skills/                     (4 reusable skills)
|   |-- spec/                      (architecture specification)
|   |-- src/                       (anomaly detection engine)
|   |-- tests/                     (unit tests - Gate 2)
|   |-- scripts/                   (DeepSeek test generator)
|   └-- review/                    (Gate 3 review logic)
|-- vibe_coding/
|   └-- app.py                     (demo: Prompt 1 — no business context, Black Friday flagged as CRITICAL)
|-- vibe_coding_with_context/
|   └-- app.py                     (demo: Prompt 2 — business context added, Black Friday Expected)
|-- docs/
|   └-- act3_deliver.md             (full session notes)
|-- requirements.txt
└-- README.md
```

---

## The pipeline

### Level 1 - Development Pipeline
How the feature gets built:

```
Claude Opus (Architect agent) -> spec -> Gate 1 (human review)
-> Claude Code (Implementer agent) -> code
-> DeepSeek (Test Engineer agent) via skill -> tests -> Gate 2 (automated)
-> Claude Sonnet (Reviewer agent) via skill -> Gate 3 (methodology review)
-> Human sign-off -> deploy
```

### Level 2 - Runtime Pipeline
How the feature runs every day:

```
Scheduled job -> Python script -> Anomaly Detection Engine -> dashboard / alerts
```

---

## The datasets

### ecommerce_dataset.csv
92 days of e-commerce metrics (Oct 1 - Dec 31, 2025).

| Column | Description |
|---|---|
| date | Date (YYYY-MM-DD) |
| revenue_usd | Daily revenue in USD |
| orders_count | Number of orders |
| avg_order_value_usd | Average order value |
| customer_churn_rate | Daily churn rate |
| support_tickets | Number of support tickets |
| ai_feature_usage_rate | AI feature usage rate |

Contains 4 hidden anomalies. Can you find them all?

### business_context.csv
Calendar context for the same period.

| Column | Description |
|---|---|
| date | Date (YYYY-MM-DD) |
| is_holiday | 1 if holiday, 0 otherwise |
| holiday_name | Name of the holiday |
| is_release_day | 1 if product release, 0 otherwise |
| marketing_campaign | Active campaign name if any |
| expected_revenue_multiplier | Expected revenue multiplier vs baseline |

---

## Live Demo

- `vibe_coding/app.py` — one prompt, no context, Black Friday flagged as CRITICAL
- `vibe_coding_with_context/app.py` — second prompt, context added, Black Friday Expected
- `pipeline/` — disciplined version with agents, skills and Gates

## Key concepts from the session

**The Gates Principle** - not everything in an AI pipeline should move at AI speed. The key design decision is not which model to use - it is where to put the human checkpoint.

**Agents vs Skills** - agents are reusable roles, while skills encode the domain knowledge and procedural rules those roles operate with.

**Vibe Coding vs Vibe Engineering** - same tools, same speed, different discipline. Vibe coding is fast and improvisational; vibe engineering adds structure, validation, and human review.

**Silent Failure** - an AI feature that passes all tests, deploys cleanly, and produces wrong outputs with no errors in the logs. The most dangerous class of bug in AI products.

**methodology_critical** - files tagged this way never pass through automated review alone. The anomaly detection logic and threshold calibration in this repo carry this flag.

---

## Getting started

```bash
git clone https://github.com/galinazirneeva/ai-masterclass-workshop
cd ai-masterclass-workshop
pip install -r requirements.txt
python pipeline/src/anomaly_detection.py
```

---

## Requirements

See requirements.txt for full list. Main dependencies:
- Python 3.10+
- pandas
- numpy

---

## GitHub repository secrets

This project uses GitHub Actions for the automated Gate 2 and Gate 3 checks. Before the workflow can run successfully, add the following repository secrets in GitHub:

1. Open your repository on GitHub.
2. Go to Settings -> Secrets and variables -> Actions.
3. Click New repository secret.
4. Add:
   - `ANTHROPIC_API_KEY` — your Anthropic API key for Claude Sonnet Gate 3 reviews
   - `DEEPSEEK_API_KEY` — your DeepSeek API key used for model-history checks and validation

After adding them, push or open a pull request and GitHub Actions will run the test suite and the Gate 3 review automatically.

---

## Workshop

**AI Reality Check: Decide, Defend, Deliver**
September 30, 2026 | SimCorp Copenhagen | 5:00 - 8:00pm

Organized by TechWomen Copenhagen x Women in Data & Analytics

Presenters: Galina Zirneeva, Monique Marins, Sara Mehrabi
# AI Reality Check Workshop
