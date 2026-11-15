"""
Core routing logic for TierGate.

TierGate models an 8-task intake pipeline (think: any multi-step case-processing
system -- claims, applications, support tickets) where each task is tagged with
a complexity tier and a recommended model size, and the three highest-stakes
tasks get confidence-gated routing by *causal level* rather than a single raw
confidence score. One task -- fraud referral -- is a permanent, unconditional
human-review gate that no confidence score can ever bypass.
"""
from dataclasses import dataclass, field
from enum import Enum


class TaskComplexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ModelSize(str, Enum):
    SMALL = "small"
    SMALL_MEDIUM = "small-medium"
    MEDIUM = "medium"
    LARGE_GATED = "large-confidence-gated"


@dataclass(frozen=True)
class Task:
    index: int
    name: str
    complexity: TaskComplexity
    model_size: ModelSize
    rationale: str


TASKS = [
    Task(1, "Receive and register submission", TaskComplexity.LOW, ModelSize.SMALL,
         "Pure intake/logging -- no judgment involved."),
    Task(2, "Identify, classify, group materials", TaskComplexity.MEDIUM, ModelSize.SMALL_MEDIUM,
         "Document-type classification and dedup; low stakes if occasionally wrong."),
    Task(3, "Extract and standardize information", TaskComplexity.MEDIUM, ModelSize.MEDIUM,
         "Structured extraction from messy, varied formats needs more robustness."),
    Task(4, "Verify identity and fraud indicators", TaskComplexity.HIGH, ModelSize.LARGE_GATED,
         "Real consequences either way; only correlation-level signals should be model-driven."),
    Task(5, "Check completeness and consistency", TaskComplexity.MEDIUM, ModelSize.SMALL_MEDIUM,
         "Largely rule-checking; reliable at smaller model sizes."),
    Task(6, "Enrich case with context", TaskComplexity.LOW, ModelSize.SMALL,
         "Mostly retrieval, not reasoning."),
    Task(7, "Evaluate risk, eligibility, exceptions", TaskComplexity.HIGH, ModelSize.LARGE_GATED,
         "Combines interpretation, severity estimation, and weighted judgment."),
    Task(8, "Decide disposition (incl. routing/SLA)", TaskComplexity.HIGH, ModelSize.LARGE_GATED,
         "Final call on case outcome; same reliability profile as task 7."),
]

HIGH_COMPLEXITY_TASK_NAMES = {t.name for t in TASKS if t.complexity == TaskComplexity.HIGH}

_INTERVENTION_MARKERS = ("if we", "would increase", "would decrease", "would the", "if the process")
_COUNTERFACTUAL_MARKERS = ("had this", "had the", "instead of", "would this have", "would have been")


def classify_causal_level(question: str) -> str:
    """Keyword-heuristic causal-level classifier: correlation / intervention / counterfactual.

    Checked most-specific-first: a counterfactual phrasing ("had X, would Y have...")
    is checked before the broader intervention markers, since counterfactuals often
    also contain words like "would".
    """
    q = question.lower()
    if any(m in q for m in _COUNTERFACTUAL_MARKERS):
        return "counterfactual"
    if any(m in q for m in _INTERVENTION_MARKERS):
        return "intervention"
    return "correlation"


@dataclass(frozen=True)
class RoutingDecision:
    task_name: str
    causal_level: str
    auto_actioned: bool
    reason: str


def route_task(task_name: str, question: str) -> RoutingDecision:
    """Route a High-complexity task's model output by causal level.

    Only correlation-level output is ever auto-actioned. Intervention- and
    counterfactual-level output is surfaced as input to a human, never as an
    automated decision -- regardless of how confident the model is.
    """
    if task_name not in HIGH_COMPLEXITY_TASK_NAMES:
        return RoutingDecision(task_name, "n/a", True, "not a High-complexity task; normal auto-routing applies")
    level = classify_causal_level(question)
    if level == "correlation":
        return RoutingDecision(task_name, level, True, "correlation-level pattern match; safe to auto-action")
    return RoutingDecision(task_name, level, False,
                            f"{level}-level reasoning required; routed to human with model output as a starting point")


@dataclass(frozen=True)
class FraudGateResult:
    requires_human: bool
    reason: str


def evaluate_fraud_referral(confidence: float, suspected_fraud: bool) -> FraudGateResult:
    """The always-human-review gate for Task 4's fraud referrals.

    This gate is unconditional: no confidence score, however high, ever
    bypasses it. A fraud determination carries legal/regulatory consequences
    in both directions, so it is a permanent design decision, not a
    compensating measure for a weak model.
    """
    if not suspected_fraud:
        return FraudGateResult(False, "no fraud suspected; normal routing applies")
    # Note: `confidence` is accepted and reported for audit purposes, but it
    # NEVER changes the outcome below -- that is the entire point of the gate.
    return FraudGateResult(
        True,
        f"fraud suspected (model confidence={confidence:.2f}) -- routed to human SIU "
        "reviewer regardless of confidence; this gate cannot be bypassed by score",
    )
