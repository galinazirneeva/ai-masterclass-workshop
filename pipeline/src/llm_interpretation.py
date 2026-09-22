# methodology_critical: true
from __future__ import annotations

import json
import os
from typing import Any, Dict
from urllib import request


def build_llm_payload(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Convert structured alert data into a prompt-friendly payload."""
    return {
        "date": alert["date"],
        "anomaly_type": alert["anomaly_type"],
        "severity": alert["severity"],
        "confidence": alert["confidence"],
        "context": alert["context"],
        "metrics": {
            "expected_value": alert["expected_value"],
            "actual_value": alert["actual_value"],
            "delta": alert["delta"],
            "related_metrics": alert["related_metrics"],
        },
    }


def generate_llm_summary(alert: Dict[str, Any]) -> str:
    """Generate a short summary via the Anthropic API when configured."""
    fallback = (
        f"On {alert['date']}, the anomaly for {', '.join(alert['related_metrics'])} is "
        f"{alert['anomaly_type']} with {alert['severity']} severity and {alert['confidence']:.2f} confidence."
    )
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return fallback

    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 300,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Explain this anomaly succinctly in business language. "
                            f"Date: {alert['date']}. Type: {alert['anomaly_type']}. "
                            f"Severity: {alert['severity']}. Confidence: {alert['confidence']}. "
                            f"Expected: {alert['expected_value']}. Actual: {alert['actual_value']}. "
                            f"Delta: {alert['delta']}. Context: {alert['context']}. "
                            f"Related metrics: {', '.join(alert['related_metrics'])}."
                        ),
                    }
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
        with request.urlopen(req, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except Exception:
        return fallback

    content = body.get("content", [])
    if not content or not isinstance(content, list):
        return fallback

    text = content[0].get("text")
    if not isinstance(text, str) or not text.strip():
        return fallback

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and "summary" in parsed:
            return str(parsed["summary"]) if parsed["summary"] is not None else fallback
    except (TypeError, ValueError):
        pass

    return text.strip()


_HYPOTHESIS_CACHE: Dict[str, list[str]] = {}


def _type_specific_fallback_hypotheses(alert: Dict[str, Any]) -> list[str]:
    """Return concrete, type-specific fallback hypotheses when the Anthropic call fails."""
    anomaly_type = alert.get("anomaly_type", "")
    if anomaly_type.startswith("revenue_shortfall"):
        return [
            "Possible payment gateway outage prevented successful checkout conversions.",
            "Inventory stock-out or fulfillment delay reduced available products and suppressed revenue.",
            "A major third-party integration or pricing bug disrupted sales on this date.",
        ]
    if anomaly_type.startswith("support_spike"):
        return [
            "Checkout or payment failures drove a surge in support tickets from affected customers.",
            "Shipping delays or fulfillment errors created a backlog of refund and tracking requests.",
            "A product bug or outage triggered a spike in customer service volume.",
        ]
    if anomaly_type.startswith("orders_collapse"):
        return [
            "Checkout or payment provider failure blocked order completion for a large share of customers.",
            "Inventory stock-outs prevented customers from placing valid orders for key products.",
            "A conversion bug or frontend issue prevented carts from being completed successfully.",
        ]
    if anomaly_type.startswith("churn_deterioration"):
        return [
            "Billing or subscription friction caused customers to cancel after failed renewals.",
            "Service quality or delivery issues eroded customer trust and drove cancellations.",
            "A product or UX regression caused higher churn in the affected customer cohort.",
        ]
    if anomaly_type.startswith("ai_usage_spike"):
        return [
            "A new AI feature rollout or campaign drove unexpectedly high adoption and traffic.",
            "A UI or integration bug caused repeated AI requests and inflated usage metrics.",
            "A marketing push or onboarding flow increased AI engagement beyond the normal baseline.",
        ]
    if anomaly_type.startswith("aov_decline"):
        return [
            "Discounting or mixed basket behavior reduced average order value on this date.",
            "A product mix shift favored lower-value purchases and depressed AOV.",
            "A checkout or recommendation failure pushed customers toward cheaper items.",
        ]
    return [
        "An operational issue in a critical transaction or fulfillment path disrupted the normal baseline.",
        "A business or platform event outside the usual pattern created abnormal operating conditions.",
        "An upstream system or data quality issue skewed the observed metrics relative to the baseline.",
    ]


def _call_sonnet_for_hypotheses(alert: Dict[str, Any]) -> list[str]:
    """Ask Anthropic Sonnet for 3 specific, actionable hypotheses for the anomaly."""
    context = alert.get("context", {}) or {}
    cache_key = json.dumps({
        "date": alert.get("date"),
        "anomaly_type": alert.get("anomaly_type"),
        "actual_value": alert.get("actual_value"),
        "expected_value": alert.get("expected_value"),
        "delta": alert.get("delta"),
        "holiday_name": context.get("holiday_name"),
        "marketing_campaign": context.get("marketing_campaign"),
        "is_release_day": context.get("is_release_day"),
        "related_metrics": alert.get("related_metrics", []),
    }, sort_keys=True)
    if cache_key in _HYPOTHESIS_CACHE:
        return _HYPOTHESIS_CACHE[cache_key]

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        hypotheses = _type_specific_fallback_hypotheses(alert)
        _HYPOTHESIS_CACHE[cache_key] = hypotheses
        return hypotheses

    prompt = (
        "You are an e-commerce operations analyst. Based on this anomaly data, provide exactly 3 specific, actionable hypotheses about what caused this anomaly. Be concrete - name specific systems, processes, or business events that could explain this pattern.\n\n"
        f"Anomaly: {alert.get('anomaly_type', '')}\n"
        f"Date: {alert.get('date', '')}\n"
        f"Actual value: {alert.get('actual_value', '')}\n"
        f"Expected value: {alert.get('expected_value', '')}\n"
        f"Delta: {alert.get('delta', '')}\n"
        f"Business context: holiday={context.get('holiday_name') or 'none'}, campaign={context.get('marketing_campaign') or 'none'}, release_day={bool(context.get('is_release_day'))}\n"
        f"Related metrics: {', '.join(alert.get('related_metrics', []))}\n\n"
        "Return only a JSON array of 3 strings. No other text."
    )

    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 300,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
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
        with request.urlopen(req, timeout=10) as response:
            body = json.loads(response.read().decode("utf-8"))
    except Exception:
        hypotheses = _type_specific_fallback_hypotheses(alert)
        _HYPOTHESIS_CACHE[cache_key] = hypotheses
        return hypotheses

    content = body.get("content", [])
    if not isinstance(content, list) or not content:
        hypotheses = _type_specific_fallback_hypotheses(alert)
        _HYPOTHESIS_CACHE[cache_key] = hypotheses
        return hypotheses

    text = content[0].get("text")
    if not isinstance(text, str) or not text.strip():
        hypotheses = _type_specific_fallback_hypotheses(alert)
        _HYPOTHESIS_CACHE[cache_key] = hypotheses
        return hypotheses

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
            hypotheses = [str(item) for item in parsed[:3]]
            _HYPOTHESIS_CACHE[cache_key] = hypotheses
            return hypotheses
    except (TypeError, ValueError):
        pass

    hypotheses = _type_specific_fallback_hypotheses(alert)
    _HYPOTHESIS_CACHE[cache_key] = hypotheses
    return hypotheses


def build_llm_response(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Return schema-compatible interpretation output for downstream review."""
    summary = generate_llm_summary(alert)
    hypotheses = _call_sonnet_for_hypotheses(alert)
    likely_cause = hypotheses[0] if hypotheses else "Operational issue detected in the affected business flow."

    return {
        "summary": summary,
        "likely_cause": likely_cause,
        "confidence": alert["confidence"],
        "recommended_actions": hypotheses,
        "alert_type": "mixed" if len(alert["related_metrics"]) > 1 else "ops",
        "evidence_summary": [
            f"Expected value: {alert['expected_value']}",
            f"Actual value: {alert['actual_value']}",
            f"Delta: {alert['delta']}",
            f"Context: {alert['context']}",
        ],
    }


__all__ = ["build_llm_payload", "generate_llm_summary", "build_llm_response"]
