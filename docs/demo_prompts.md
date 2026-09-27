# Act 3 — Demo prompts: correlated outage feature

## Step 1 — Spec (Claude Code, model: Opus) → Gate 1
You are the Architect agent defined in pipeline/agents/architect.md. Follow pipeline/skills/architecture_spec.md.

Feature request: detect a correlated outage. When on the same day revenue falls below 40% of its expected value AND support tickets exceed 3x their expected value, the alert must be classified as anomaly_type "outage", severity "critical", is_expected false — regardless of holiday, campaign or release context.

Add ONE new section to pipeline/spec/architecture_spec.md describing this rule. Include:
- the rule and why it overrides business context
- where it is implemented: pipeline/src/alert_ranking.py (methodology_critical)
- acceptance criteria: when running the pipeline on data/, the only change in the alert list is 2025-11-05 becoming "outage"; every other alert stays exactly the same; all existing tests pass
- what tests cannot verify (what needs human judgment)

Do not write code. Do not change any other section. Show me the diff.

## Step 2 — Code (Claude Code, model: Sonnet)
You are the Implementer agent defined in pipeline/agents/implementer.md. Follow pipeline/skills/implementation.md.

Implement section 10 "Correlated Outage Override" of pipeline/spec/architecture_spec.md exactly as specified, in pipeline/src/alert_ranking.py only.

Rules:
- Do not modify the spec. Do not modify any other file.
- Do not write or edit tests — that is the Test Engineer agent.
- Keep the "# methodology_critical: true" header.

When done, run `python -m pytest pipeline/tests -q --ignore=pipeline/tests/exploratory_deepseek.py` and show me the result and the diff.

## Step 3 — Tests (DeepSeek, terminal)
DEEPSEEK_TESTS_OUT=pipeline/tests/test_feature_correlated_outage.py \
DEEPSEEK_FOCUS="Write 4-6 tests ONLY for the correlated outage override (spec section 10). Test against the real dataset, not synthetic rows: ROOT = Path(__file__).resolve().parents[2]; add ROOT/'pipeline'/'src' to sys.path; from anomaly_detection import run_pipeline; alerts = run_pipeline(ROOT/'data'). Each alert is a dict with keys date ('YYYY-MM-DD'), anomaly_type, severity, is_expected. Assert: 2025-11-05 has anomaly_type 'outage', severity 'critical', is_expected False; 2025-11-05 is the only alert with anomaly_type 'outage'; 2025-11-28 is not 'outage', has is_expected True and severity 'medium'; there are exactly 15 alerts. Do not build DataFrames by hand. Each test has a docstring with the business scenario." \
python pipeline/scripts/generate_tests_deepseek.py

## Check the output (before / after)
python3 -c "
import sys; sys.path.insert(0,'pipeline/src')
from anomaly_detection import run_pipeline
for a in sorted(run_pipeline('data'), key=lambda x: x['date']):
    print(a['date'][:10], a['severity'].ljust(8), a['anomaly_type'].ljust(20), 'expected' if a['is_expected'] else '')
"
