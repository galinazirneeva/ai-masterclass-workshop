# Prompt 2 — Adding Business Context

The anomaly detection script is flagging Black Friday
as a critical incident. This is wrong.

Add business context from business_context.csv:
- Load the file and join it with ecommerce_dataset.csv on date
- Use expected_revenue_multiplier to adjust the baseline
- Mark anomalies as is_expected: true when holiday
  or campaign explains them
- Show is_expected status in the dashboard

Rule: if revenue drops below 20% of baseline OR
support tickets exceed 5x baseline, always mark
is_expected: false regardless of any campaign or holiday.
