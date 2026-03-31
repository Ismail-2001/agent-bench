"""CLI interface for agentbench."""

from __future__ import annotations

import asyncio
import importlib
import json
import sys

import click

from .models import ScenarioResult, TaskStatus
from .runner import Runner


def _load_adapter(adapter_path: str):
    """Load an AgentAdapter class from a 'module:ClassName' string."""
    if ":" not in adapter_path:
        click.echo(f"Error: Adapter must be 'module:ClassName', got '{adapter_path}'")
        sys.exit(1)

    module_path, class_name = adapter_path.rsplit(":", 1)
    try:
        module = importlib.import_module(module_path)
        adapter_cls = getattr(module, class_name)
        return adapter_cls()
    except (ModuleNotFoundError, AttributeError) as e:
        click.echo(f"Error loading adapter '{adapter_path}': {e}")
        sys.exit(1)


def _print_results(results: list[ScenarioResult]) -> None:
    """Print results as a Rich terminal table."""
    try:
        from rich.console import Console
        from rich.table import Table
        from rich import box
    except ImportError:
        _print_results_plain(results)
        return

    console = Console()

    for sr in results:
        console.print()
        table = Table(
            title=f"agentbench — {sr.scenario_name}",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Task", style="bold")
        table.add_column("Result", justify="center", width=8)
        table.add_column("Tokens", justify="right")
        table.add_column("Latency", justify="right")
        table.add_column("Cost", justify="right")

        for tr in sr.task_results:
            status_str = (
                "[green]✅ PASS[/]" if tr.status == TaskStatus.PASS
                else "[red]❌ FAIL[/]" if tr.status == TaskStatus.FAIL
                else "[yellow]⚠ ERROR[/]"
            )
            table.add_row(
                tr.task_id,
                status_str,
                f"{tr.total_tokens:,}",
                f"{tr.latency_seconds:.1f}s",
                f"${tr.cost_usd:.3f}",
            )

            # Show individual criteria
            for er in tr.eval_results:
                crit_status = "[green]✅[/]" if er.passed else "[red]❌[/]"
                table.add_row(
                    f"  └ {er.evaluator_type}",
                    crit_status,
                    "",
                    "",
                    er.message[:40] if er.message else "",
                )

        # Summary row
        table.add_section()
        rate = sr.pass_rate
        rate_style = "green bold" if rate >= 0.8 else "yellow" if rate >= 0.5 else "red bold"
        table.add_row(
            "[bold]SUMMARY[/]",
            f"[{rate_style}]{sr.passed_tasks}/{sr.total_tasks}[/{rate_style}]",
            f"[bold]{sr.total_tokens:,}[/bold]",
            f"[bold]{sr.total_latency:.1f}s[/bold]",
            f"[bold]${sr.total_cost:.3f}[/bold]",
        )

        console.print(table)
    console.print()


def _print_results_plain(results: list[ScenarioResult]) -> None:
    """Fallback plain text output."""
    for sr in results:
        print(f"\n  agentbench — {sr.scenario_name}")
        print(f"  {'='*50}")
        for tr in sr.task_results:
            status = "PASS" if tr.status == TaskStatus.PASS else "FAIL"
            print(f"  {tr.task_id}: {status} | {tr.total_tokens:,} tokens | {tr.latency_seconds:.1f}s")
        print(f"  {'='*50}")
        print(f"  Summary: {sr.passed_tasks}/{sr.total_tasks} passed | {sr.total_tokens:,} tokens")


@click.group()
@click.version_option(version="0.1.0", prog_name="agentbench")
def cli():
    """Pytest for AI agents. Define scenarios in YAML, run any agent, get results."""


@cli.command()
@click.option("--scenario", required=True, help="Path to scenario YAML file or directory")
@click.option("--agent", required=True, help="Agent adapter as 'module:ClassName'")
@click.option("--format", "output_format", type=click.Choice(["table", "json", "html"]), default="table")
@click.option("--min-pass-rate", type=float, help="Minimum pass rate (0-1)")
@click.option("--max-avg-cost", type=float, help="Maximum average cost per task")
@click.option("--exit-code", is_flag=True, help="Non-zero exit code on failure")
@click.option("-o", "--output", type=click.Path(), help="Save results to file")
def run(scenario, agent, output_format, min_pass_rate, max_avg_cost, exit_code, output):
    """Run scenarios against an agent."""
    adapter = _load_adapter(agent)
    runner = Runner(adapter)

    results = asyncio.run(runner.run_all(scenario))

    if output_format == "json":
        data = [sr.to_dict() for sr in results]
        json_str = json.dumps(data, indent=2)
        if output:
            with open(output, "w") as f:
                f.write(json_str)
            click.echo(f"Results saved to {output}")
        else:
            click.echo(json_str)
    elif output_format == "html":
        from .reporters.html import HTMLReporter
        
        output_path = output or "agentbench-report.html"
        reporter = HTMLReporter(results, output_path)
        path = reporter.render()
        click.echo(f"✨ Stunning HTML report generated at {path}")
    else:
        _print_results(results)

    # Save JSON alongside table output
    if output and output_format == "table":
        data = [sr.to_dict() for sr in results]
        with open(output, "w") as f:
            json.dump(data, f, indent=2)

    # CI checks
    failed = False
    for sr in results:
        if min_pass_rate is not None and sr.pass_rate < min_pass_rate:
            click.echo(
                f"⚠ Pass rate {sr.pass_rate:.0%} < minimum {min_pass_rate:.0%} "
                f"for {sr.scenario_name}"
            )
            failed = True
        if max_avg_cost is not None and sr.avg_cost > max_avg_cost:
            click.echo(
                f"⚠ Avg cost ${sr.avg_cost:.3f} > maximum ${max_avg_cost:.3f} "
                f"for {sr.scenario_name}"
            )
            failed = True

    if exit_code and failed:
        sys.exit(1)


@cli.command()
@click.option("--scenario", required=True)
@click.option("--agent-a", required=True, help="First agent as 'module:Class'")
@click.option("--agent-b", required=True, help="Second agent as 'module:Class'")
def compare(scenario, agent_a, agent_b):
    """Compare two agents on the same scenario."""
    adapter_a = _load_adapter(agent_a)
    adapter_b = _load_adapter(agent_b)

    async def _run_both():
        runner_a = Runner(adapter_a)
        runner_b = Runner(adapter_b)
        results_a = await runner_a.run_all(scenario)
        results_b = await runner_b.run_all(scenario)
        return results_a, results_b

    results_a, results_b = asyncio.run(_run_both())

    try:
        from rich.console import Console
        from rich.table import Table
        from rich import box

        console = Console()

        for sa, sb in zip(results_a, results_b):
            table = Table(
                title=f"Comparison — {sa.scenario_name}",
                box=box.ROUNDED,
                header_style="bold cyan",
            )
            table.add_column("Metric")
            table.add_column(sa.agent_name, justify="right")
            table.add_column(sb.agent_name, justify="right")

            # Pass rate
            ra, rb = sa.pass_rate, sb.pass_rate
            table.add_row(
                "Pass rate",
                f"{'[green]' if ra >= rb else ''}{sa.passed_tasks}/{sa.total_tasks} ({ra:.0%}){'[/]' if ra >= rb else ''}",
                f"{'[green]' if rb >= ra else ''}{sb.passed_tasks}/{sb.total_tasks} ({rb:.0%}){'[/]' if rb >= ra else ''}",
            )
            table.add_row("Avg tokens", f"{sa.avg_tokens:,}", f"{sb.avg_tokens:,}")
            table.add_row("Avg latency", f"{sa.avg_latency:.1f}s", f"{sb.avg_latency:.1f}s")
            table.add_row("Avg cost", f"${sa.avg_cost:.3f}", f"${sb.avg_cost:.3f}")

            console.print()
            console.print(table)
            console.print()
    except ImportError:
        for sa, sb in zip(results_a, results_b):
            print(f"\nComparison — {sa.scenario_name}")
            print(f"  {sa.agent_name}: {sa.passed_tasks}/{sa.total_tasks} | {sa.avg_tokens:,} tokens")
            print(f"  {sb.agent_name}: {sb.passed_tasks}/{sb.total_tasks} | {sb.avg_tokens:,} tokens")


def main():
    cli()


if __name__ == "__main__":
    main()
