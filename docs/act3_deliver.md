# Act 3 — Deliver: AI Development Pipeline

## The scenario

This scenario centers on an e-commerce anomaly detection feature that monitors revenue, churn, support demand, and AI feature usage across a 92-day period. The team has a business requirement: identify real operational issues quickly, while ignoring expected seasonal or campaign-driven spikes.

The challenge is not simply to build an alerting model. It is to build a system that makes the right distinction between:

- real anomalies that require action
- expected business events such as Black Friday promotions or holiday traffic
- silent failure modes where the model appears confident but is wrong in a dangerous way

The repository demonstrates how a lightweight but disciplined AI development pipeline can help teams move from a rough prototype to a production-ready workflow with review gates and explicit human checkpoints.

---

## Live Demo Flow

### Step 1 — Vibe Coding: no business context

Open `vibe_coding/app.py`.

This version uses a very direct prompt and no business context. As a result, the model treats Black Friday as an obvious incident and flags it as CRITICAL.

This is a classic example of Vibe Coding: fast, persuasive, and wrong for business reasons.

### Step 2 — Add context: business-aware interpretation

Open `vibe_coding_with_context/app.py`.

This version adds business context from `business_context.csv` and correctly recognizes Black Friday as an expected promotional period, not an operational anomaly.

The result: Black Friday is marked as `Expected` rather than `Critical`.

This highlights the real lesson: model output is only useful when it is grounded in the correct business context.

### Step 3 — The pipeline: repo structure and discipline

The disciplined version lives under `pipeline/` and shows how the team moves from a quick prototype to a structured engineering workflow.

Repository structure:

- `pipeline/agents/` — four agent definitions
- `pipeline/skills/` — reusable domain knowledge and process guidance
- `pipeline/spec/` — architecture specification and design contract
- `pipeline/src/` — anomaly detection logic
- `pipeline/tests/` — Gate 2 validation tests
- `pipeline/scripts/` — DeepSeek-based test generation helper
- `pipeline/review/` — Gate 3 methodology review logic

This is where the difference between "vibe coding" and "vibe engineering" becomes visible.

### Step 4 — New feature: PR workflow with Gates

The real phase is not just writing code. It is shipping it through a controlled workflow:

1. Architect agent defines the specification
2. Human reviews Gate 1
3. Implementer agent writes the code
4. Test Engineer agent generates validation tests
5. Automated Gate 2 runs the test suite
6. Reviewer agent performs methodology review in Gate 3
7. Human sign-off allows deployment

This creates a delivery model where speed is not the goal alone. The goal is correct, reviewable, defendable engineering decisions.

---

## The Gates Principle

The core idea is simple: not every step in an AI pipeline should move at AI speed.

### Gate 1 — Human review of the specification

This gate ensures the feature contract is clear before implementation starts.

Questions it catches:

- Are we solving the right business problem?
- Did the team agree on the expected behavior?
- Are edge cases and business rules clearly defined?

### Gate 2 — Automated validation

This gate checks whether the implementation matches the expected behavior through automated tests.

It catches:

- regressions
- logic errors
- missed anomaly conditions
- context-aware versus no-context behavior mismatches

### Gate 3 — Methodology review

This gate focuses on the quality of the engineering judgment behind the model and alert logic.

It reviews:

- silent failure risk
- business context dependence
- threshold ownership
- methodology-critical logic
- whether the model is being used in a disciplined and explainable way

The overall principle: use AI as a force multiplier, but keep the safety checkpoints in the right places.

---

## Agents and Skills

The repo uses a role-based workflow with a clear distinction between agents and skills.

### Agents

Agents are reusable roles that own part of the delivery lifecycle.

- Architect agent — defines the design and writes the specification
- Implementer agent — writes production code
- Test Engineer agent — designs and validates tests
- Reviewer agent — performs methodology review before merge

### Skills

Skills are reusable pieces of domain knowledge and operational guidance that the agents use.

Examples:

- architecture skill for the spec and design contract
- implementation skill for engineering rules and delivery workflow
- test engineering skill for behavioral testing and validation
- methodology review skill for rubric-based review decisions

In other words:

- agents are roles
- skills are the playbook for those roles

---

## Hands-on #5

This is the methodology review prompt participants use in Claude.ai.

The review prompt evaluates whether the implementation is truly business-safe and whether the team has introduced hidden risks.

The reviewer checks:

- whether the logic is overly dependent on one noisy signal
- whether context is being ignored when it should be used
- whether thresholds are calibrated honestly
- whether silent failure is possible
- whether the alerting logic is explainable and reviewable

The important point is that this review is not a generic code review. It is a methodology review of the operational decisions behind the alerting system itself.

---

## Key concepts

### Vibe Coding vs Vibe Engineering

**Vibe Coding**

- fast iteration
- persuasive outputs
- minimal process
- high risk of wrong-but-confident behavior

**Vibe Engineering**

- same AI tools
- same speed advantages
- but with structure, validation, context, and review
- designed to reduce silent failure and improve trust

### Silent Failure

An AI system can appear healthy while producing materially wrong results with no obvious errors.

This is especially dangerous in operational analytics, because the model may produce plausible explanations and confident outputs while missing the actual business story.

### methodology_critical

Some files carry business-critical impact because they define thresholds, detection logic, or alert interpretation. These files are tagged as `methodology_critical` and require explicit human review before merge.

This is not a stylistic tag. It is a guardrail against unsafe automation.

---

## Closing note

The key lesson of Act 3 is that AI does not replace engineering judgment. It amplifies it.

The difference between a quick prototype and a reliable operational system is not whether the model can generate a result. It is whether the team can defend that result under business pressure, with the right context, right tests, and right review gates.
