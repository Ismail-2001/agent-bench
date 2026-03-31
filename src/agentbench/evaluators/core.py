"""Evaluators for agentbench — deterministic and LLM-based."""

from __future__ import annotations

import json
import re
from typing import Any

from ..models import EvalResult


def evaluate_criterion(criterion: dict, output: str, task: dict) -> EvalResult:
    """Route a criterion to the appropriate evaluator function."""
    eval_type = criterion.get("type", "")
    evaluators = {
        "contains_all": _eval_contains_all,
        "contains_any": _eval_contains_any,
        "not_contains": _eval_not_contains,
        "min_length": _eval_min_length,
        "max_length": _eval_max_length,
        "regex": _eval_regex,
        "json_valid": _eval_json_valid,
        "json_schema": _eval_json_schema,
        "exact_match": _eval_exact_match,
        "llm_judge": _eval_llm_judge,
        "similarity": _eval_similarity,
        "custom": _eval_custom,
    }

    evaluator_fn = evaluators.get(eval_type)
    if evaluator_fn is None:
        return EvalResult(
            passed=False,
            message=f"Unknown evaluator type: {eval_type}",
            evaluator_type=eval_type,
        )

    result = evaluator_fn(criterion, output, task)
    result.evaluator_type = eval_type
    return result


# ---------------------------------------------------------------------------
# Deterministic evaluators
# ---------------------------------------------------------------------------


def _eval_contains_all(criterion: dict, output: str, task: dict) -> EvalResult:
    values = criterion.get("values", [])
    output_lower = output.lower()
    missing = [v for v in values if v.lower() not in output_lower]
    passed = len(missing) == 0
    return EvalResult(
        passed=passed,
        score=1.0 if passed else (len(values) - len(missing)) / max(len(values), 1),
        message=f"Missing: {missing}" if missing else "All values found",
    )


def _eval_contains_any(criterion: dict, output: str, task: dict) -> EvalResult:
    values = criterion.get("values", [])
    output_lower = output.lower()
    found = [v for v in values if v.lower() in output_lower]
    passed = len(found) > 0
    return EvalResult(
        passed=passed,
        score=len(found) / max(len(values), 1),
        message=f"Found: {found}" if found else "None of the values found",
    )


def _eval_not_contains(criterion: dict, output: str, task: dict) -> EvalResult:
    values = criterion.get("values", [])
    output_lower = output.lower()
    found = [v for v in values if v.lower() in output_lower]
    passed = len(found) == 0
    return EvalResult(
        passed=passed,
        score=1.0 if passed else 0.0,
        message=f"Unwanted values found: {found}" if found else "Clean",
    )


def _eval_min_length(criterion: dict, output: str, task: dict) -> EvalResult:
    min_len = criterion.get("value", 0)
    actual = len(output)
    passed = actual >= min_len
    return EvalResult(
        passed=passed,
        score=min(actual / max(min_len, 1), 1.0),
        message=f"Length: {actual} (min: {min_len})",
        raw_value=actual,
    )


def _eval_max_length(criterion: dict, output: str, task: dict) -> EvalResult:
    max_len = criterion.get("value", 10000)
    actual = len(output)
    passed = actual <= max_len
    return EvalResult(
        passed=passed,
        score=1.0 if passed else max_len / max(actual, 1),
        message=f"Length: {actual} (max: {max_len})",
        raw_value=actual,
    )


def _eval_regex(criterion: dict, output: str, task: dict) -> EvalResult:
    pattern = criterion.get("pattern", "")
    try:
        match = re.search(pattern, output)
        passed = match is not None
        return EvalResult(
            passed=passed,
            score=1.0 if passed else 0.0,
            message=f"Pattern {'matched' if passed else 'not found'}: {pattern}",
        )
    except re.error as e:
        return EvalResult(passed=False, score=0.0, message=f"Invalid regex: {e}")


def _eval_json_valid(criterion: dict, output: str, task: dict) -> EvalResult:
    try:
        json.loads(output.strip())
        return EvalResult(passed=True, score=1.0, message="Valid JSON")
    except (json.JSONDecodeError, ValueError) as e:
        return EvalResult(passed=False, score=0.0, message=f"Invalid JSON: {e}")


def _eval_json_schema(criterion: dict, output: str, task: dict) -> EvalResult:
    schema = criterion.get("schema", {})
    try:
        data = json.loads(output.strip())
        required = schema.get("required", [])
        missing = [k for k in required if k not in data]
        passed = len(missing) == 0
        return EvalResult(
            passed=passed,
            score=1.0 if passed else (len(required) - len(missing)) / max(len(required), 1),
            message=f"Missing keys: {missing}" if missing else "Schema valid",
        )
    except (json.JSONDecodeError, ValueError) as e:
        return EvalResult(passed=False, score=0.0, message=f"Invalid JSON: {e}")


def _eval_exact_match(criterion: dict, output: str, task: dict) -> EvalResult:
    expected = task.get("expected", criterion.get("value", ""))
    passed = output.strip() == expected.strip()
    return EvalResult(
        passed=passed,
        score=1.0 if passed else 0.0,
        message="Exact match" if passed else "Mismatch",
    )


# ---------------------------------------------------------------------------
# LLM-based evaluators
# ---------------------------------------------------------------------------


def _eval_llm_judge(criterion: dict, output: str, task: dict) -> EvalResult:
    """Use an LLM to judge output quality. Requires OPENAI_API_KEY."""
    prompt = criterion.get("prompt", "Rate this response 0-10 for quality.")
    threshold = criterion.get("threshold", 7)
    model = criterion.get("model", "gpt-4o-mini")

    try:
        import openai

        client = openai.OpenAI()
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an evaluator. Score the following agent output. "
                        "Respond with ONLY a JSON object: "
                        '{"score": <number 0-10>, "reasoning": "<brief explanation>"}'
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Task input: {task.get('input', '')}\n\n"
                        f"Agent output:\n{output}\n\n"
                        f"Evaluation criteria: {prompt}\n\n"
                        f"Score (0-10):"
                    ),
                },
            ],
        )

        raw = response.choices[0].message.content or ""
        # Parse score from response
        try:
            parsed = json.loads(raw)
            score = float(parsed.get("score", 0))
            reasoning = parsed.get("reasoning", "")
        except (json.JSONDecodeError, ValueError):
            # Fallback: extract first number
            numbers = re.findall(r"\b(\d+(?:\.\d+)?)\b", raw)
            score = float(numbers[0]) if numbers else 0
            reasoning = raw

        passed = score >= threshold
        return EvalResult(
            passed=passed,
            score=score / 10.0,
            message=f"Score: {score}/10 (threshold: {threshold}) — {reasoning}",
            raw_value=score,
        )

    except ImportError:
        return EvalResult(
            passed=False,
            score=0.0,
            message="openai package not installed. Run: pip install openai",
        )
    except Exception as e:
        return EvalResult(passed=False, score=0.0, message=f"LLM judge error: {e}")


def _eval_similarity(criterion: dict, output: str, task: dict) -> EvalResult:
    """Semantic similarity between output and expected answer."""
    expected = task.get("expected", "")
    threshold = criterion.get("threshold", 0.85)

    if not expected:
        return EvalResult(
            passed=False,
            score=0.0,
            message="No 'expected' field in task for similarity comparison",
        )

    # Simple word overlap as fallback (production: use embeddings)
    output_words = set(output.lower().split())
    expected_words = set(expected.lower().split())
    if not expected_words:
        return EvalResult(passed=False, score=0.0, message="Empty expected")

    overlap = len(output_words & expected_words) / len(expected_words)
    passed = overlap >= threshold

    return EvalResult(
        passed=passed,
        score=overlap,
        message=f"Word overlap: {overlap:.2f} (threshold: {threshold})",
    )


# ---------------------------------------------------------------------------
# Custom evaluators
# ---------------------------------------------------------------------------


def _eval_custom(criterion: dict, output: str, task: dict) -> EvalResult:
    """Load and run a custom evaluator function."""
    function_path = criterion.get("function", "")
    if ":" not in function_path:
        return EvalResult(
            passed=False,
            message=f"Invalid function path: {function_path}. Use 'module:function'",
        )

    module_path, func_name = function_path.rsplit(":", 1)
    try:
        import importlib
        module = importlib.import_module(module_path)
        func = getattr(module, func_name)
        return func(output, task)
    except Exception as e:
        return EvalResult(passed=False, score=0.0, message=f"Custom eval error: {e}")
