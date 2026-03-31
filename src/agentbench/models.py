"""Core data models for agentbench."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class TaskStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class EvalResult:
    """Result from a single evaluator criterion."""

    passed: bool
    score: float = 0.0  # 0.0 - 1.0 normalized
    message: str = ""
    evaluator_type: str = ""
    raw_value: Any = None


@dataclass
class TaskResult:
    """Result from running a single task."""

    task_id: str
    status: TaskStatus
    output: str = ""
    eval_results: list[EvalResult] = field(default_factory=list)

    # Metrics
    input_tokens: int = 0
    output_tokens: int = 0
    latency_seconds: float = 0.0
    cost_usd: float = 0.0
    iterations: int = 0

    # Error info
    error: Optional[str] = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def all_criteria_passed(self) -> bool:
        return all(er.passed for er in self.eval_results)

    @property
    def avg_score(self) -> float:
        scores = [er.score for er in self.eval_results if er.score > 0]
        return sum(scores) / len(scores) if scores else 0.0


@dataclass
class ScenarioResult:
    """Aggregate result from running all tasks in a scenario."""

    scenario_name: str
    scenario_description: str = ""
    task_results: list[TaskResult] = field(default_factory=list)
    agent_name: str = ""

    @property
    def total_tasks(self) -> int:
        return len(self.task_results)

    @property
    def passed_tasks(self) -> int:
        return sum(1 for tr in self.task_results if tr.status == TaskStatus.PASS)

    @property
    def pass_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.passed_tasks / self.total_tasks

    @property
    def total_tokens(self) -> int:
        return sum(tr.total_tokens for tr in self.task_results)

    @property
    def total_latency(self) -> float:
        return sum(tr.latency_seconds for tr in self.task_results)

    @property
    def total_cost(self) -> float:
        return sum(tr.cost_usd for tr in self.task_results)

    @property
    def avg_tokens(self) -> int:
        if self.total_tasks == 0:
            return 0
        return self.total_tokens // self.total_tasks

    @property
    def avg_latency(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.total_latency / self.total_tasks

    @property
    def avg_cost(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.total_cost / self.total_tasks

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dictionary."""
        return {
            "scenario": self.scenario_name,
            "description": self.scenario_description,
            "agent": self.agent_name,
            "summary": {
                "total_tasks": self.total_tasks,
                "passed": self.passed_tasks,
                "pass_rate": round(self.pass_rate, 3),
                "total_tokens": self.total_tokens,
                "avg_latency_seconds": round(self.avg_latency, 2),
                "total_cost_usd": round(self.total_cost, 4),
            },
            "tasks": [
                {
                    "id": tr.task_id,
                    "status": tr.status.value,
                    "tokens": tr.total_tokens,
                    "latency_seconds": round(tr.latency_seconds, 2),
                    "cost_usd": round(tr.cost_usd, 4),
                    "criteria": [
                        {
                            "type": er.evaluator_type,
                            "passed": er.passed,
                            "score": round(er.score, 3),
                            "message": er.message,
                        }
                        for er in tr.eval_results
                    ],
                    "error": tr.error,
                }
                for tr in self.task_results
            ],
        }
