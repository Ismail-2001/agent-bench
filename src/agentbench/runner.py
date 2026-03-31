"""Runner — executes scenarios against agent adapters and collects results."""

from __future__ import annotations

import asyncio
import time
from typing import Optional

from .adapter import AgentAdapter
from .evaluators.core import evaluate_criterion
from .models import EvalResult, ScenarioResult, TaskResult, TaskStatus
from .scenario import load_scenarios


class Runner:
    """Execute scenarios against an agent adapter."""

    def __init__(self, adapter: AgentAdapter, token_counter=None):
        self.adapter = adapter
        self.agent_name = adapter.__class__.__name__
        self._token_counter = token_counter

    def _count_tokens(self, text: str) -> int:
        if self._token_counter:
            return self._token_counter.count(text)
        # Rough fallback: 1 token ≈ 4 chars
        return max(1, len(text) // 4)

    async def run_task(self, task: dict) -> TaskResult:
        """Run a single task and evaluate the output."""
        task_id = task["id"]
        task_input = task.get("input", "")
        conversation = task.get("conversation")
        limits = task.get("limits", {})
        criteria = task.get("criteria", [])

        # Execute the agent
        start_time = time.monotonic()
        try:
            if conversation:
                output = await self.adapter.run_conversation(conversation)
            else:
                output = await self.adapter.run(task_input)
            latency = time.monotonic() - start_time
        except Exception as e:
            latency = time.monotonic() - start_time
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.ERROR,
                latency_seconds=latency,
                error=str(e),
            )

        # Token counting
        input_tokens = self._count_tokens(task_input)
        output_tokens = self._count_tokens(output)

        # Check resource limits
        max_latency = limits.get("max_latency_seconds", float("inf"))
        max_tokens = limits.get("max_tokens", float("inf"))
        total_tokens = input_tokens + output_tokens

        limit_violations = []
        if latency > max_latency:
            limit_violations.append(f"Latency {latency:.1f}s > {max_latency}s")
        if total_tokens > max_tokens:
            limit_violations.append(f"Tokens {total_tokens:,} > {max_tokens:,}")

        # Run evaluators
        eval_results: list[EvalResult] = []
        for criterion in criteria:
            result = evaluate_criterion(criterion, output, task)
            eval_results.append(result)

        # Add limit violation as a failing criterion
        if limit_violations:
            eval_results.append(
                EvalResult(
                    passed=False,
                    score=0.0,
                    message=f"Limit exceeded: {'; '.join(limit_violations)}",
                    evaluator_type="limits",
                )
            )

        # Determine overall status
        all_passed = all(er.passed for er in eval_results)
        status = TaskStatus.PASS if (all_passed and eval_results) else TaskStatus.FAIL
        if not criteria and not limit_violations:
            # No criteria defined — mark as pass if agent returned output
            status = TaskStatus.PASS if output.strip() else TaskStatus.FAIL

        return TaskResult(
            task_id=task_id,
            status=status,
            output=output,
            eval_results=eval_results,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_seconds=latency,
        )

    async def run_scenario(self, scenario: dict, concurrency: int = 5) -> ScenarioResult:
        """Run all tasks in a scenario, potentially in parallel."""
        result = ScenarioResult(
            scenario_name=scenario.get("name", "unnamed"),
            scenario_description=scenario.get("description", ""),
            agent_name=self.agent_name,
        )

        semaphore = asyncio.Semaphore(concurrency)

        async def _run_with_semaphore(task: dict):
            async with semaphore:
                runs = task.get("runs", 1)
                pass_threshold = task.get("pass_threshold", 1.0)

                if runs == 1:
                    task_result = await self.run_task(task)
                    return task_result
                else:
                    # Multiple runs — check pass rate
                    run_results = []
                    for _ in range(runs):
                        tr = await self.run_task(task)
                        run_results.append(tr)

                    passes = sum(1 for r in run_results if r.status == TaskStatus.PASS)
                    actual_rate = passes / runs

                    # Use the last run as the representative result
                    representative = run_results[-1]
                    if actual_rate >= pass_threshold:
                        representative.status = TaskStatus.PASS
                    else:
                        representative.status = TaskStatus.FAIL

                    # Add consistency note
                    representative.eval_results.append(
                        EvalResult(
                            passed=actual_rate >= pass_threshold,
                            score=actual_rate,
                            message=f"Consistency: {passes}/{runs} passed ({actual_rate:.0%})",
                            evaluator_type="consistency",
                        )
                    )
                    return representative

        # Execute tasks in parallel
        tasks_to_run = scenario.get("tasks", [])
        coros = [_run_with_semaphore(t) for t in tasks_to_run]
        task_results = await asyncio.gather(*coros)
        
        result.task_results.extend(task_results)
        return result

    async def run_all(self, scenario_path: str) -> list[ScenarioResult]:
        """Load and run all scenarios from a path."""
        scenarios = load_scenarios(scenario_path)
        results = []

        self.adapter.setup()
        try:
            for scenario in scenarios:
                sr = await self.run_scenario(scenario)
                results.append(sr)
        finally:
            self.adapter.teardown()

        return results
