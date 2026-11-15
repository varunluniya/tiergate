# TierGate

A small, tested Python library for complexity-tiered task routing in multi-step
decision pipelines (claims processing, support triage, loan underwriting — any
system where some steps are mechanical and a few are genuinely high-stakes).

TierGate answers three questions for a pipeline of tasks:

1. **Which tasks need a big, expensive model, and which are fine on something small?**
   An 8-task map tags each task with a complexity tier (Low / Medium / High) and
   a recommended model size.
2. **For the highest-stakes tasks, when is model output safe to auto-action?**
   A causal-level classifier (correlation / intervention / counterfactual) decides
   this per question, not per task — only correlation-level pattern matches are
   auto-actioned; intervention- and counterfactual-level reasoning always routes
   to a human, with the model's output attached as a starting point, not a verdict.
3. **Is there a decision that should NEVER be automated, no matter how confident
   the model is?** The fraud-referral gate is unconditional: it ignores the
   confidence score entirely once fraud is suspected, by design — a confidence
   sweep from 0.0 to 1.0 proves it.

## Install

```bash
pip install -e .
```

## Usage

```bash
python -m tiergate.cli map    # print the 8-task complexity/model-size map
python -m tiergate.cli demo   # run the causal-level routing + fraud-gate demo
```

```python
from tiergate import route_task, evaluate_fraud_referral

decision = route_task(
    "Evaluate risk, eligibility, exceptions",
    "If we tightened underwriting for flood-zone properties, would severity decrease?",
)
# decision.causal_level == "intervention", decision.auto_actioned == False

gate = evaluate_fraud_referral(confidence=0.97, suspected_fraud=True)
# gate.requires_human is True regardless of how high confidence is
```

## Design notes

- The causal-level classifier is a lightweight keyword heuristic, not a model
  call — it is intentionally simple and disclosed as such. It exists to decide
  *routing*, not to replace the model doing the actual reasoning.
- The fraud gate is a permanent design decision, not a stand-in for a weak
  model. See `tests/test_tiergate.py::test_fraud_gate_cannot_be_bypassed_by_confidence_sweep`.

## Tests

```bash
pytest -v
```

16/16 passing.

## License

MIT
