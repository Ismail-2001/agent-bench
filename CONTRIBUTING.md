# Contributing to agentbench

## Setup
```bash
git clone https://github.com/daniellopez882/agentbench.git
cd agentbench
pip install -e ".[dev,llm]"
pytest tests/ -v
```

## High-Impact Contributions
- **Built-in scenario packs** — Add YAML scenarios for common agent types
- **New evaluators** — trajectory efficiency, plan quality, tool accuracy
- **Framework adapters** — pre-built adapters for LangGraph, CrewAI, AutoGen
- **HTML report generator** — standalone report with charts
- **Trace capture** — record tool calls and intermediate reasoning steps

## Code Style
- Python 3.10+ with type hints
- Lint with `ruff check`
- Tests required for new features
- Every evaluator needs at least pass + fail test cases
