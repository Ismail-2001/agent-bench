<div align="center">

# agentbench

**Pytest for AI agents.**

Define test scenarios in YAML. Run any agent — LangGraph, CrewAI, AutoGen, or custom.
Get a report with pass/fail, tokens, latency, cost, and failure analysis.

[![PyPI](https://img.shields.io/badge/pypi-v0.1.0-blue?style=flat-square)](https://pypi.org/project/agentbench/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg?style=flat-square)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](CONTRIBUTING.md)

[Quick Start](#-quick-start) · [Scenarios](#-scenarios) · [Adapters](#-adapters) · [Evaluators](#-evaluators) · [Reports](#-reports) · [CI/CD](#-cicd-integration)

</div>

---

## 🔥 The Problem

> *"52% of organizations don't run evaluations on their agents."*
> — LangChain State of Agent Engineering, 2026

Agent evaluation is broken. The existing options are:

- **LangSmith / Braintrust / Maxim**: Paid platforms, locked to ecosystems, overkill for most teams
- **GAIA / AgentBench (THUDM)**: Academic benchmarks for foundation models, not your custom agents
- **DeepEval**: Great for LLM unit tests, but not designed for multi-step agent workflows
- **Ad-hoc pytest**: What most teams actually do — brittle, non-reproducible, no standard metrics

**agentbench** fills the gap: a free, open-source CLI tool that lets you define test scenarios in YAML and run them against any agent framework. Think of it as `pytest` meets `k6` for AI agents.

---

## ⚡ Quick Start

### Install

```bash
pip install agentbench
```

### 1. Define a scenario

```yaml
# scenarios/research.yaml
name: "basic-research"
description: "Agent should research a topic and produce a summary"

tasks:
  - id: "research-ai-frameworks"
    input: "Compare LangGraph and CrewAI for production multi-agent systems"
    
    criteria:
      - type: contains_all
        values: ["LangGraph", "CrewAI"]
      - type: min_length
        value: 200
      - type: llm_judge
        prompt: "Does this response provide a balanced comparison with specific technical details? Score 0-10."
        threshold: 7
    
    limits:
      max_tokens: 50000
      max_latency_seconds: 60
      max_cost_usd: 0.50
```

### 2. Write a thin adapter for your agent

```python
# my_agent_adapter.py
from agentbench import AgentAdapter

class MyResearchAgent(AgentAdapter):
    """Wrap your existing agent for benchmarking."""
    
    def setup(self):
        # Initialize your agent (runs once before all tasks)
        from my_app import create_research_agent
        self.agent = create_research_agent()
    
    async def run(self, task_input: str) -> str:
        # Run your agent and return the output as a string
        result = await self.agent.ainvoke({"query": task_input})
        return result["output"]
    
    def teardown(self):
        # Cleanup (runs once after all tasks)
        pass
```

### 3. Run the benchmark

```bash
agentbench run --scenario scenarios/research.yaml --agent my_agent_adapter:MyResearchAgent

# ┌────────────────────────────────────────────────────────────────┐
# │                    agentbench results                         │
# ├────────────────────────┬──────────┬────────┬────────┬────────┤
# │ Task                   │  Result  │ Tokens │ Latency│  Cost  │
# ├────────────────────────┼──────────┼────────┼────────┼────────┤
# │ research-ai-frameworks │ ✅ PASS  │ 12,847 │  8.3s  │ $0.04  │
# │  ├ contains_all        │ ✅       │        │        │        │
# │  ├ min_length           │ ✅ (847) │        │        │        │
# │  └ llm_judge (8/10)    │ ✅       │        │        │        │
# ├────────────────────────┼──────────┼────────┼────────┼────────┤
# │ SUMMARY                │ 1/1 pass │ 12,847 │  8.3s  │ $0.04  │
# └────────────────────────┴──────────┴────────┴────────┴────────┘
```

---

## 📋 Scenarios

Scenarios are YAML files that define what to test. Each scenario contains one or more tasks, and each task has input, evaluation criteria, and optional resource limits.

### Scenario Structure

```yaml
name: "scenario-name"          # Unique identifier
description: "What this tests"  # Human-readable description
tags: ["research", "multi-step"] # For filtering

# Global defaults (can be overridden per task)
defaults:
  limits:
    max_tokens: 100000
    max_latency_seconds: 120
    max_cost_usd: 1.00
  evaluator:
    model: "gpt-4o-mini"        # Model for LLM-judge evaluations

tasks:
  - id: "task-identifier"
    input: "The prompt sent to your agent"
    
    # Multi-turn conversations
    conversation:               # Alternative to single 'input'
      - role: user
        content: "Book a flight to Tokyo"
      - role: user
        content: "Actually, make it Osaka instead"
    
    # Expected output (for exact match or reference)
    expected: "Optional reference answer"
    
    # Evaluation criteria (ALL must pass for task to pass)
    criteria:
      - type: contains_all          # Output contains all these strings
        values: ["Tokyo", "flight"]
      - type: contains_any          # Output contains at least one
        values: ["confirmed", "booked"]
      - type: not_contains          # Output must NOT contain these
        values: ["error", "sorry, I can't"]
      - type: min_length            # Minimum character count
        value: 100
      - type: max_length            # Maximum character count
        value: 5000
      - type: regex                 # Matches a regex pattern
        pattern: "\\$\\d+\\.\\d{2}" # Contains a price like $29.99
      - type: json_valid            # Output is valid JSON
      - type: json_schema           # Output matches a JSON schema
        schema: { "type": "object", "required": ["name", "price"] }
      - type: similarity            # Semantic similarity to expected
        threshold: 0.85
      - type: llm_judge             # LLM evaluates quality
        prompt: "Rate this response for accuracy (0-10)"
        threshold: 7
      - type: custom                # Your own Python function
        function: "my_evals:check_citations"
    
    # Resource limits (fail if exceeded)
    limits:
      max_tokens: 50000
      max_latency_seconds: 60
      max_cost_usd: 0.50
      max_iterations: 20           # For agents with loops
    
    # How many times to run this task (for consistency measurement)
    runs: 3                        # Default: 1
    pass_threshold: 0.67           # 2/3 runs must pass
```

### Built-in Scenario Packs

```bash
# List available built-in scenarios
agentbench scenarios list

# Run a built-in scenario pack
agentbench run --scenario builtin:research-basic --agent my_agent:MyAgent
agentbench run --scenario builtin:tool-use --agent my_agent:MyAgent
agentbench run --scenario builtin:error-recovery --agent my_agent:MyAgent
agentbench run --scenario builtin:multi-turn --agent my_agent:MyAgent
```

| Pack | Tasks | What It Tests |
|------|:-----:|---------------|
| `research-basic` | 5 | Single-query research with fact-checking |
| `tool-use` | 8 | Tool selection accuracy, parameter correctness |
| `error-recovery` | 5 | Graceful handling of tool failures and ambiguous inputs |
| `multi-turn` | 5 | Context retention across multi-turn conversations |
| `hallucination` | 10 | Factual accuracy, admitting uncertainty |
| `adversarial` | 5 | Prompt injection, off-topic redirection, jailbreak attempts |

---

## 🔌 Adapters

Adapters connect agentbench to your agent framework. Write a class that inherits from `AgentAdapter` — that's it.

### Base Interface

```python
from agentbench import AgentAdapter

class AgentAdapter:
    """Override these methods to connect your agent."""
    
    def setup(self) -> None:
        """Initialize agent. Called once before all tasks."""
        pass
    
    async def run(self, task_input: str) -> str:
        """Run agent on input, return output as string."""
        raise NotImplementedError
    
    async def run_conversation(self, messages: list[dict]) -> str:
        """Run agent on multi-turn conversation. Override for multi-turn support."""
        # Default: send last message only
        return await self.run(messages[-1]["content"])
    
    def teardown(self) -> None:
        """Cleanup. Called once after all tasks."""
        pass
```

### LangGraph Adapter Example

```python
from agentbench import AgentAdapter

class LangGraphResearchAgent(AgentAdapter):
    def setup(self):
        from langchain_openai import ChatOpenAI
        from langgraph.prebuilt import create_react_agent
        
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.agent = create_react_agent(llm, tools=[...])
    
    async def run(self, task_input: str) -> str:
        result = await self.agent.ainvoke(
            {"messages": [{"role": "user", "content": task_input}]}
        )
        return result["messages"][-1].content
```

### CrewAI Adapter Example

```python
from agentbench import AgentAdapter

class CrewAIResearchTeam(AgentAdapter):
    def setup(self):
        from crewai import Agent, Task, Crew, Process
        
        self.researcher = Agent(role="Researcher", ...)
        self.writer = Agent(role="Writer", ...)
    
    async def run(self, task_input: str) -> str:
        task = Task(description=task_input, agent=self.researcher)
        crew = Crew(agents=[self.researcher, self.writer], tasks=[task])
        result = crew.kickoff()
        return str(result)
```

### OpenAI Agents SDK Adapter

```python
from agentbench import AgentAdapter

class OpenAISDKAgent(AgentAdapter):
    def setup(self):
        from agents import Agent, Runner
        self.agent = Agent(name="researcher", instructions="...", model="gpt-4o")
    
    async def run(self, task_input: str) -> str:
        from agents import Runner
        result = await Runner.run(self.agent, task_input)
        return result.final_output
```

---

## 📊 Evaluators

Every criterion in a scenario maps to an evaluator. Mix and match them freely.

### Deterministic Evaluators (Fast, Free)

| Evaluator | What It Checks |
|-----------|---------------|
| `contains_all` | Output contains all specified strings |
| `contains_any` | Output contains at least one string |
| `not_contains` | Output does NOT contain specified strings |
| `min_length` / `max_length` | Character count bounds |
| `regex` | Matches a regex pattern |
| `json_valid` | Output is parseable JSON |
| `json_schema` | Output matches a JSON schema |
| `exact_match` | Exact string equality |
| `tool_called` | Specific tool was invoked (requires trace) |
| `tool_not_called` | Specific tool was NOT invoked |

### LLM-Based Evaluators (Powerful, Costs Tokens)

| Evaluator | What It Checks |
|-----------|---------------|
| `llm_judge` | Custom prompt scored 0-10 against threshold |
| `similarity` | Semantic similarity to reference answer |
| `factual_accuracy` | Claims checked against provided facts |
| `faithfulness` | Output doesn't contradict provided context |
| `plan_quality` | Agent's plan is logical and complete |
| `trajectory_efficiency` | Agent took reasonable path (not excessive tool calls) |

### Custom Evaluators

```python
# my_evals.py
from agentbench import EvalResult

def check_citations(output: str, task: dict) -> EvalResult:
    """Custom evaluator — check that output contains citations."""
    import re
    citations = re.findall(r'\[(\d+)\]', output)
    passed = len(citations) >= 2
    return EvalResult(
        passed=passed,
        score=len(citations) / 5,  # Normalize to 0-1
        message=f"Found {len(citations)} citations (need >= 2)",
    )
```

```yaml
# In your scenario YAML
criteria:
  - type: custom
    function: "my_evals:check_citations"
```

---

## 📈 Reports

### CLI Output (Default)

```bash
agentbench run --scenario scenarios/ --agent my_agent:MyAgent
```

Produces a Rich terminal table with pass/fail, tokens, latency, and cost per task.

### JSON Export

```bash
agentbench run --scenario scenarios/ --agent my_agent:MyAgent --format json > results.json
```

### HTML Report

```bash
agentbench run --scenario scenarios/ --agent my_agent:MyAgent --format html -o report.html
```

Generates a standalone HTML file with charts, per-task breakdowns, and failure analysis.

### Compare Two Agents

```bash
agentbench compare \
  --scenario scenarios/research.yaml \
  --agent-a my_agent:LangGraphAgent \
  --agent-b my_agent:CrewAIAgent

# ┌────────────────────────┬──────────────┬──────────────┐
# │ Metric                 │ LangGraph    │ CrewAI       │
# ├────────────────────────┼──────────────┼──────────────┤
# │ Pass rate              │ 4/5 (80%)    │ 3/5 (60%)    │
# │ Avg tokens             │ 12,340       │ 28,910       │
# │ Avg latency            │ 6.2s         │ 14.8s        │
# │ Avg cost               │ $0.037       │ $0.087       │
# │ Avg LLM judge score    │ 8.2/10       │ 7.1/10       │
# └────────────────────────┴──────────────┴──────────────┘
# Winner: LangGraphAgent (higher pass rate, 57% fewer tokens, 58% lower cost)
```

---

## 🔁 CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/agent-eval.yml
name: Agent Evaluation
on: [push, pull_request]

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install agentbench
      - run: pip install -e .  # Install your agent
      
      - name: Run agent benchmarks
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          agentbench run \
            --scenario scenarios/ \
            --agent my_agent:ProductionAgent \
            --min-pass-rate 0.8 \
            --max-avg-cost 0.10 \
            --exit-code
        # Fails CI if pass rate < 80% or avg cost > $0.10
      
      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: agent-eval-results
          path: agentbench-results.json
```

### CLI Flags for CI

```bash
# Fail if pass rate drops below threshold
agentbench run --scenario scenarios/ --agent my_agent:MyAgent \
  --min-pass-rate 0.8 \
  --exit-code

# Fail if any task exceeds cost limit
agentbench run --scenario scenarios/ --agent my_agent:MyAgent \
  --max-avg-cost 0.10 \
  --exit-code

# Run with retries for flaky tasks
agentbench run --scenario scenarios/ --agent my_agent:MyAgent \
  --retries 2
```

---

## 📐 Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         agentbench                           │
│                                                              │
│  ┌───────────┐   ┌────────────┐   ┌────────────────────┐    │
│  │  Scenario  │   │  Adapter   │   │    Evaluators      │    │
│  │  Loader    │   │  Registry  │   │  ┌──────────────┐  │    │
│  │  (YAML)    │   │            │   │  │ Deterministic│  │    │
│  └─────┬─────┘   └─────┬──────┘   │  │ (contains,   │  │    │
│        │               │          │  │  regex, json) │  │    │
│        ▼               ▼          │  ├──────────────┤  │    │
│  ┌─────────────────────────────┐  │  │  LLM Judge   │  │    │
│  │        Runner               │  │  │ (quality,    │  │    │
│  │  • Loads scenario           │  │  │  accuracy)   │  │    │
│  │  • Instantiates adapter     │  │  ├──────────────┤  │    │
│  │  • Executes tasks           │──│  │   Custom     │  │    │
│  │  • Measures tokens/latency  │  │  │  (Python fn) │  │    │
│  │  • Applies evaluators       │  │  └──────────────┘  │    │
│  │  • Enforces limits          │  └────────────────────┘    │
│  └─────────────┬───────────────┘                            │
│                │                                            │
│  ┌─────────────▼──────────────────────────────────────┐     │
│  │              Reporters                              │     │
│  │  • CLI table (Rich)                                 │     │
│  │  • JSON export                                      │     │
│  │  • HTML report                                      │     │
│  │  • Compare mode (A vs B)                            │     │
│  └────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
          │                     │                     │
     ┌────▼────┐         ┌────▼────┐          ┌────▼────┐
     │LangGraph│         │ CrewAI  │          │ Custom  │
     │ Agent   │         │  Agent  │          │  Agent  │
     └─────────┘         └─────────┘          └─────────┘
```

---

## 🧪 Core Metrics

Every task run captures:

| Metric | How It's Measured |
|--------|------------------|
| **Pass/Fail** | All criteria must pass |
| **Tokens (input)** | Counted via tiktoken |
| **Tokens (output)** | Counted via tiktoken |
| **Latency** | Wall-clock time from `run()` call to return |
| **Cost** | Estimated from token counts × model pricing |
| **Iterations** | Tool calls / LLM invocations (if adapter reports them) |
| **Criteria scores** | Individual score per evaluator |
| **Consistency** | Pass rate across multiple runs of same task |
| **LLM Judge score** | 0-10 quality score from evaluator model |

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

**High-impact contributions:**
- **New evaluators** — trajectory efficiency, plan quality, tool accuracy
- **Built-in scenarios** — expand the scenario packs
- **Framework adapters** — pre-built adapters for popular frameworks
- **Reporters** — Markdown, PDF, Grafana dashboard export
- **Trace integration** — capture full agent traces (tool calls, intermediate steps)

---

## 📚 Prior Art & Differentiation

| Tool | What It Does | How agentbench Differs |
|------|-------------|----------------------|
| [THUDM/AgentBench](https://github.com/THUDM/AgentBench) | Benchmarks foundation models on 8 environments | We benchmark YOUR custom agents, not models |
| [LangSmith](https://langchain.com/langsmith) | Paid platform with eval + observability | We're free, open-source, CLI-first |
| [DeepEval](https://github.com/confident-ai/deepeval) | LLM unit testing with 50+ metrics | We focus on multi-step agent workflows, not single LLM calls |
| [AstaBench](https://allenai.org/blog/astabench) | Scientific agent benchmark | Domain-specific; we're domain-agnostic |
| [Inspect AI](https://inspect.ai-safety-institute.org.uk/) | UK AISI's eval framework | Great foundation; we add YAML scenarios + agent adapters |
| [GAIA](https://huggingface.co/gaia-benchmark) | General AI assistant benchmark | Fixed tasks; we let you define your own |

**agentbench is not a platform.** It's a tool. No accounts, no dashboards, no vendor lock-in. Define scenarios in YAML, run from CLI, get results. That's it.

---

## 🗺️ Roadmap

- [x] YAML scenario loading
- [x] Agent adapter interface
- [x] Deterministic evaluators (contains, regex, json, length)
- [x] LLM-judge evaluator
- [x] CLI with Rich output
- [x] JSON export
- [x] Compare mode (A vs B)
- [x] CI/CD integration (exit codes, thresholds)
- [ ] HTML report generation
- [ ] Built-in scenario packs (6 packs, 38 tasks)
- [ ] Trace capture (tool calls, intermediate reasoning)
- [ ] Parallel task execution
- [ ] Retry with exponential backoff
- [ ] Cost tracking with model-specific pricing
- [ ] Snapshot testing (detect output regressions)
- [ ] Community scenario registry

---

## License

[MIT](LICENSE) — Test everything. Trust nothing.

---

<div align="center">

**[agentbench](https://github.com/daniellopez882/agentbench)** by [Daniel López Orta](https://github.com/daniellopez882)

*You wouldn't deploy code without tests. Don't deploy agents without benchmarks.*

</div>
