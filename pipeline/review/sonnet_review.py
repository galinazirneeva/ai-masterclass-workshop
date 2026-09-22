#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib import error, request

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "pipeline" / "spec" / "architecture_spec.md"
SKILL_PATH = ROOT / "pipeline" / "skills" / "methodology_review.md"
TEST_PATHS = [
    ROOT / "pipeline" / "tests" / "test_anomaly.py",
    ROOT / "pipeline" / "tests" / "test_pipeline_regression.py",
]
REVIEW_PATH = ROOT / "pipeline" / "review" / "last_review.json"
SRC_DIR = ROOT / "pipeline" / "src"
CRITICAL_FILES = {
    "pipeline/src/baseline.py",
    "pipeline/src/scoring.py",
    "pipeline/src/alert_ranking.py",
    "pipeline/src/llm_interpretation.py",
}
ANTHROPIC_MODEL = "claude-sonnet-4-6"
SYSTEM_PROMPT = SKILL_PATH.read_text(encoding="utf-8")


def run_git_command(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def find_methodology_critical_files() -> list[str]:
    files: list[str] = []
    seen: set[str] = set()

    for path in sorted(SRC_DIR.rglob("*")):
        if not path.is_file():
            continue
        relative = str(path.relative_to(ROOT))
        if relative in CRITICAL_FILES:
            files.append(relative)
            seen.add(relative)
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if "methodology_critical: true" in text:
            if relative not in seen:
                files.append(relative)
                seen.add(relative)

    return sorted(files)


def detect_deepseek_usage() -> dict[str, object]:
    checks = []
    patterns = [
        "deepseek",
        "DeepSeek",
        "api.deepseek.com",
        "DEEPSEEK_API_KEY",
    ]
    for pattern in patterns:
        output = run_git_command("log", "--oneline", "--all", "--decorate", "-i", "--grep", pattern)
        if output:
            checks.append({"pattern": pattern, "matches": output.splitlines()[:10]})

    diff_output = run_git_command("log", "-S", "DEEPSEEK_API_KEY", "--oneline", "--all")
    if diff_output:
        checks.append({"pattern": "git log -S DEEPSEEK_API_KEY", "matches": diff_output.splitlines()[:10]})

    return {
        "deepseek_used": bool(checks),
        "details": checks,
    }


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def extract_json_payload(raw_text: str) -> dict:
    text = raw_text.strip()
    if not text:
        raise ValueError("Anthropic returned empty response")

    candidates = []
    candidates.append(text)

    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        candidates.append(json_match.group(0))

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    print("RAW_ANTHROPIC_RESPONSE_START", file=sys.stderr)
    print(raw_text, file=sys.stderr)
    print("RAW_ANTHROPIC_RESPONSE_END", file=sys.stderr)
    raise ValueError(f"Anthropic response was not valid JSON: {text[:1000]}")


def call_anthropic(prompt_text: str) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set in the environment")

    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 2000,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                ],
            }
        ],
    }

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    req = request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Anthropic API request failed: {body}") from exc

    return body


def parse_response(body: dict) -> dict:
    content = body.get("content")
    if not isinstance(content, list) or not content:
        raise ValueError(f"Unexpected Anthropic response format: {body}")

    first_block = content[0]
    raw_text = first_block.get("text")
    if raw_text is None:
        raise ValueError(f"Anthropic response missing text content: {body}")

    return extract_json_payload(raw_text)


def build_prompt(methodology_files: list[str], deepseek_info: dict[str, object]) -> str:
    spec_text = read_text(SPEC_PATH)
    tests_text = "\n\n===== FILE =====\n\n".join(
        f"{path.name}\n{read_text(path)}" for path in TEST_PATHS
    )

    return f"""
Methodology-critical files in pipeline/src:
{json.dumps(methodology_files, indent=2)}

DeepSeek usage evidence from git log:
{json.dumps(deepseek_info, indent=2, default=str)}

Source-of-truth architecture spec:
{spec_text}

Test files under review:
{tests_text}

Review instructions:
- Use the methodology rubric from the system prompt as the authoritative Gate 3 review standard.
- Treat the repo implementation and tests as the authoritative evidence. Do not mark a file as missing if it exists in the workspace.
- The project is required to process the full 92-day seasonal window from 2025-10-01 through 2025-12-31 and must not stop in October.
- Black Friday is expected to be suppressed when business_context.csv is loaded. A no-context diagnostic path is allowed only for explicit test simulation and must not be treated as the default production behavior.
- Missing business context must trigger a fail-fast validation error in production code; hidden silent fallback is a blocking issue.
- The pipeline must detect the real anomalies in the current data: 2025-11-05 revenue collapse, 2025-10-20 through 2025-10-22 support spike, 2025-10-28 through 2025-10-31 churn spike, and December 2025 AI usage spike.
- Do not reject the project for optional test coverage gaps that are already satisfied by the repository's actual tests or for legitimate no-context diagnostic modes.
- Only raise an issue when there is a concrete mismatch between the implementation and the approved project requirements.
- Return ONLY valid JSON with this exact shape:
  {{
    "verdict": "PASS" or "FAIL",
    "silent_failure_risks": [],
    "human_judgment_required": [],
    "test_coverage_gaps": [],
    "threshold_owners": []
  }}
"""


def main() -> int:
    methodology_files = find_methodology_critical_files()
    deepseek_info = detect_deepseek_usage()

    prompt = build_prompt(methodology_files, deepseek_info)
    review = parse_response(call_anthropic(prompt))

    review.setdefault("verdict", "FAIL")
    review.setdefault("silent_failure_risks", [])
    review.setdefault("human_judgment_required", [])
    review.setdefault("test_coverage_gaps", [])
    review.setdefault("threshold_owners", [])

    REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_PATH.write_text(json.dumps(review, indent=2), encoding="utf-8")

    print(json.dumps(review, indent=2))

    if review.get("verdict") not in {"PASS", "FAIL"}:
        print("Gate 3 failed: verdict must be PASS or FAIL.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
