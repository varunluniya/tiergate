import pytest
from tiergate.core import (
    TASKS, TaskComplexity, ModelSize, classify_causal_level, route_task,
    evaluate_fraud_referral, HIGH_COMPLEXITY_TASK_NAMES,
)


def test_task_map_has_eight_tasks():
    assert len(TASKS) == 8


def test_three_tasks_are_high_complexity():
    high = [t for t in TASKS if t.complexity == TaskComplexity.HIGH]
    assert len(high) == 3
    assert {t.name for t in high} == HIGH_COMPLEXITY_TASK_NAMES


def test_high_complexity_tasks_use_large_gated_model():
    for t in TASKS:
        if t.complexity == TaskComplexity.HIGH:
            assert t.model_size == ModelSize.LARGE_GATED


def test_low_complexity_tasks_use_small_model():
    low = [t for t in TASKS if t.complexity == TaskComplexity.LOW]
    assert len(low) == 2
    for t in low:
        assert t.model_size == ModelSize.SMALL


@pytest.mark.parametrize("question,expected", [
    ("This claimant's phone number appears on 3 other claims. Is this likely fraudulent?", "correlation"),
    ("If we added mandatory video-KYC for all claims above $5,000, would the fraud detection rate increase?", "intervention"),
    ("Had this claimant filed from their registered email, would this claim have been auto-approved?", "counterfactual"),
    ("This is a water-damage claim in a flood-zone postcode. What's the likely severity?", "correlation"),
])
def test_classify_causal_level(question, expected):
    assert classify_causal_level(question) == expected


def test_route_task_correlation_is_auto_actioned():
    d = route_task("Verify identity and fraud indicators",
                    "This matches 200 prior claims we've seen resolve the same way.")
    assert d.auto_actioned is True
    assert d.causal_level == "correlation"


def test_route_task_intervention_is_not_auto_actioned():
    d = route_task("Evaluate risk, eligibility, exceptions",
                    "If we raised the auto-settlement threshold, would more claims bypass review?")
    assert d.auto_actioned is False
    assert d.causal_level == "intervention"


def test_route_task_counterfactual_is_not_auto_actioned():
    d = route_task("Decide disposition (incl. routing/SLA)",
                    "Had the adjuster not flagged the estimate, would this have been auto-settled?")
    assert d.auto_actioned is False
    assert d.causal_level == "counterfactual"


def test_route_task_non_high_task_always_auto_actioned():
    d = route_task("Receive and register submission", "Had this been filed differently, would it matter?")
    assert d.auto_actioned is True
    assert d.causal_level == "n/a"


def test_fraud_gate_requires_human_even_at_high_confidence():
    g = evaluate_fraud_referral(confidence=0.99, suspected_fraud=True)
    assert g.requires_human is True


def test_fraud_gate_requires_human_even_at_low_confidence():
    g = evaluate_fraud_referral(confidence=0.10, suspected_fraud=True)
    assert g.requires_human is True


def test_fraud_gate_no_referral_when_not_suspected():
    g = evaluate_fraud_referral(confidence=0.99, suspected_fraud=False)
    assert g.requires_human is False


def test_fraud_gate_cannot_be_bypassed_by_confidence_sweep():
    # Sweep confidence from 0.0 to 1.0 -- the outcome must never change when
    # fraud is suspected. This is the "confidence-sweep test" the gate design
    # is explicitly meant to pass.
    results = {evaluate_fraud_referral(c / 10, True).requires_human for c in range(11)}
    assert results == {True}
