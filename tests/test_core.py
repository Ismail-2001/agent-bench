"""Tests for agentbench core functionality."""

import json
import os
import tempfile

import pytest
import yaml

from agentbench import AgentAdapter, Runner, TaskStatus
from agentbench.evaluators.core import evaluate_criterion
from agentbench.models import AuditReport, EvalResult, ScenarioResult, TaskResult
from agentbench.scenario import load_scenario, load_scenarios


# ---------------------------------------------------------------------------
# Test adapter
# ---------------------------------------------------------------------------


class EchoAgent(AgentAdapter):
    """Simple test agent that echoes the input with a prefix."""

    async def run(self, task_input: str) -> str:
        return f"Response about: {task_input}. LangGraph is a graph-based framework. CrewAI uses role-based agents."


class FailingAgent(AgentAdapter):
    """Agent that always raises an error."""

    async def run(self, task_input: str) -> str:
        raise RuntimeError("Agent crashed!")


# ---------------------------------------------------------------------------
# Evaluator tests
# ---------------------------------------------------------------------------


class TestEvaluators:
    def test_contains_all_pass(self):
        result = evaluate_criterion(
            {"type": "contains_all", "values": ["hello", "world"]},
            "hello world",
            {},
        )
        assert result.passed is True

    def test_contains_all_fail(self):
        result = evaluate_criterion(
            {"type": "contains_all", "values": ["hello", "missing"]},
            "hello world",
            {},
        )
        assert result.passed is False
        assert "missing" in result.message.lower()

    def test_contains_any_pass(self):
        result = evaluate_criterion(
            {"type": "contains_any", "values": ["hello", "missing"]},
            "hello world",
            {},
        )
        assert result.passed is True

    def test_contains_any_fail(self):
        result = evaluate_criterion(
            {"type": "contains_any", "values": ["missing", "absent"]},
            "hello world",
            {},
        )
        assert result.passed is False

    def test_not_contains_pass(self):
        result = evaluate_criterion(
            {"type": "not_contains", "values": ["error", "sorry"]},
            "Everything is fine",
            {},
        )
        assert result.passed is True

    def test_not_contains_fail(self):
        result = evaluate_criterion(
            {"type": "not_contains", "values": ["error"]},
            "There was an error",
            {},
        )
        assert result.passed is False

    def test_min_length_pass(self):
        result = evaluate_criterion(
            {"type": "min_length", "value": 5},
            "Hello world",
            {},
        )
        assert result.passed is True

    def test_min_length_fail(self):
        result = evaluate_criterion(
            {"type": "min_length", "value": 100},
            "Short",
            {},
        )
        assert result.passed is False

    def test_max_length_pass(self):
        result = evaluate_criterion(
            {"type": "max_length", "value": 100},
            "Short text",
            {},
        )
        assert result.passed is True

    def test_regex_pass(self):
        result = evaluate_criterion(
            {"type": "regex", "pattern": r"\$\d+\.\d{2}"},
            "The price is $29.99",
            {},
        )
        assert result.passed is True

    def test_regex_fail(self):
        result = evaluate_criterion(
            {"type": "regex", "pattern": r"\$\d+\.\d{2}"},
            "No price here",
            {},
        )
        assert result.passed is False

    def test_json_valid_pass(self):
        result = evaluate_criterion(
            {"type": "json_valid"},
            '{"name": "test", "value": 42}',
            {},
        )
        assert result.passed is True

    def test_json_valid_fail(self):
        result = evaluate_criterion(
            {"type": "json_valid"},
            "not valid json",
            {},
        )
        assert result.passed is False

    def test_json_schema_pass(self):
        result = evaluate_criterion(
            {"type": "json_schema", "schema": {"required": ["name", "price"]}},
            '{"name": "Widget", "price": 9.99}',
            {},
        )
        assert result.passed is True

    def test_json_schema_fail(self):
        result = evaluate_criterion(
            {"type": "json_schema", "schema": {"required": ["name", "price"]}},
            '{"name": "Widget"}',
            {},
        )
        assert result.passed is False

    def test_exact_match_pass(self):
        result = evaluate_criterion(
            {"type": "exact_match"},
            "exact output",
            {"expected": "exact output"},
        )
        assert result.passed is True

    def test_unknown_evaluator(self):
        result = evaluate_criterion({"type": "nonexistent"}, "output", {})
        assert result.passed is False
        assert "unknown" in result.message.lower()


# ---------------------------------------------------------------------------
# Scenario loader tests
# ---------------------------------------------------------------------------


class TestScenarioLoader:
    def test_load_valid_scenario(self, tmp_path):
        scenario_data = {
            "name": "test-scenario",
            "description": "A test",
            "tasks": [
                {
                    "id": "task-1",
                    "input": "Hello",
                    "criteria": [{"type": "min_length", "value": 1}],
                }
            ],
        }
        path = tmp_path / "test.yaml"
        path.write_text(yaml.dump(scenario_data))

        scenario = load_scenario(path)
        assert scenario["name"] == "test-scenario"
        assert len(scenario["tasks"]) == 1
        assert scenario["tasks"][0]["id"] == "task-1"

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_scenario("/nonexistent/path.yaml")

    def test_load_missing_tasks(self, tmp_path):
        path = tmp_path / "bad.yaml"
        path.write_text(yaml.dump({"name": "no-tasks"}))
        with pytest.raises(ValueError, match="tasks"):
            load_scenario(path)

    def test_load_directory(self, tmp_path):
        for i in range(3):
            data = {"name": f"scenario-{i}", "tasks": [{"id": f"t{i}", "input": "x"}]}
            (tmp_path / f"s{i}.yaml").write_text(yaml.dump(data))

        scenarios = load_scenarios(tmp_path)
        assert len(scenarios) == 3

    def test_defaults_applied(self, tmp_path):
        data = {
            "name": "with-defaults",
            "defaults": {"limits": {"max_tokens": 5000}},
            "tasks": [{"id": "t1", "input": "hello"}],
        }
        path = tmp_path / "defaults.yaml"
        path.write_text(yaml.dump(data))

        scenario = load_scenario(path)
        assert scenario["tasks"][0]["limits"]["max_tokens"] == 5000


# ---------------------------------------------------------------------------
# Runner tests
# ---------------------------------------------------------------------------


class TestRunner:
    @pytest.mark.asyncio
    async def test_run_task_pass(self):
        adapter = EchoAgent()
        runner = Runner(adapter)

        task = {
            "id": "test-task",
            "input": "Compare LangGraph and CrewAI",
            "criteria": [
                {"type": "contains_all", "values": ["LangGraph", "CrewAI"]},
                {"type": "min_length", "value": 10},
            ],
        }

        result = await runner.run_task(task)
        assert result.status == TaskStatus.PASS
        assert result.latency_seconds > 0
        assert len(result.eval_results) == 2
        assert all(er.passed for er in result.eval_results)

    @pytest.mark.asyncio
    async def test_run_task_fail(self):
        adapter = EchoAgent()
        runner = Runner(adapter)

        task = {
            "id": "failing-task",
            "input": "Hello",
            "criteria": [
                {"type": "contains_all", "values": ["nonexistent_word_xyz"]},
            ],
        }

        result = await runner.run_task(task)
        assert result.status == TaskStatus.FAIL

    @pytest.mark.asyncio
    async def test_run_task_error(self):
        adapter = FailingAgent()
        runner = Runner(adapter)

        task = {"id": "error-task", "input": "Hello", "criteria": []}
        result = await runner.run_task(task)
        assert result.status == TaskStatus.ERROR
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_run_scenario(self):
        adapter = EchoAgent()
        runner = Runner(adapter)

        scenario = {
            "name": "test",
            "tasks": [
                {
                    "id": "t1",
                    "input": "LangGraph and CrewAI comparison",
                    "criteria": [{"type": "contains_all", "values": ["LangGraph"]}],
                },
                {
                    "id": "t2",
                    "input": "Simple test",
                    "criteria": [{"type": "min_length", "value": 5}],
                },
            ],
        }

        result = await runner.run_scenario(scenario)
        assert result.total_tasks == 2
        assert result.passed_tasks == 2
        assert result.pass_rate == 1.0
        assert result.total_tokens > 0
        assert result.total_latency > 0


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestModels:
    def test_scenario_result_to_dict(self):
        sr = ScenarioResult(
            scenario_name="test",
            task_results=[
                TaskResult(
                    task_id="t1",
                    status=TaskStatus.PASS,
                    input_tokens=100,
                    output_tokens=200,
                    latency_seconds=1.5,
                )
            ],
        )
        d = sr.to_dict()
        assert d["summary"]["total_tasks"] == 1
        assert d["summary"]["passed"] == 1
        assert d["summary"]["pass_rate"] == 1.0

    def test_scenario_result_to_dict_json(self):
        sr = ScenarioResult(
            scenario_name="test",
            task_results=[
                TaskResult(task_id="t1", status=TaskStatus.PASS)
            ],
        )
        # Should not raise
        json.dumps(sr.to_dict())

    def test_task_result_metrics(self):
        tr = TaskResult(
            task_id="t1",
            status=TaskStatus.PASS,
            input_tokens=100,
            output_tokens=200,
            eval_results=[
                EvalResult(passed=True, score=0.8),
                EvalResult(passed=True, score=0.9),
            ],
        )
        assert tr.total_tokens == 300
        assert tr.all_criteria_passed is True
        assert tr.avg_score == pytest.approx(0.85, rel=0.01)
