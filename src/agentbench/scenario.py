"""Load and validate scenario YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_scenario(path: str | Path) -> dict:
    """Load a scenario from a YAML file and apply defaults."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Scenario file not found: {path}")

    with open(path) as f:
        scenario = yaml.safe_load(f)

    if not isinstance(scenario, dict):
        raise ValueError(f"Invalid scenario format in {path}")

    # Validate required fields
    if "tasks" not in scenario:
        raise ValueError(f"Scenario {path} must contain 'tasks'")

    # Apply defaults to tasks
    defaults = scenario.get("defaults", {})
    default_limits = defaults.get("limits", {})

    for task in scenario["tasks"]:
        if "id" not in task:
            raise ValueError(f"Every task must have an 'id' field in {path}")

        # Merge default limits with task-specific limits
        task_limits = {**default_limits, **task.get("limits", {})}
        task["limits"] = task_limits

        # Ensure criteria is a list
        if "criteria" not in task:
            task["criteria"] = []

    scenario.setdefault("name", path.stem)
    scenario.setdefault("description", "")
    scenario.setdefault("tags", [])

    return scenario


def load_scenarios(path: str | Path) -> list[dict]:
    """Load all scenarios from a file, directory, or 'builtin:<name>'."""
    if str(path).startswith("builtin:"):
        scenario_name = str(path).split(":", 1)[1]
        # Locate the scenarios directory inside the package
        package_dir = Path(__file__).parent.parent.parent / "scenarios"
        builtin_path = package_dir / f"{scenario_name}.yaml"
        if not builtin_path.exists():
            builtin_path = package_dir / f"{scenario_name}.yml"
        
        if not builtin_path.exists():
            raise FileNotFoundError(f"Builtin scenario not found: {scenario_name}")
        return [load_scenario(builtin_path)]

    path = Path(path)

    if path.is_file():
        return [load_scenario(path)]

    if path.is_dir():
        scenarios = []
        for yaml_file in sorted(path.glob("*.yaml")):
            scenarios.append(load_scenario(yaml_file))
        for yml_file in sorted(path.glob("*.yml")):
            scenarios.append(load_scenario(yml_file))
        return scenarios

    raise FileNotFoundError(f"Path not found: {path}")
