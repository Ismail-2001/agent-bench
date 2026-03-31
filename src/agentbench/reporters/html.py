"""HTML Reporter — generates a stunning, premium HTML report for agentbench results."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models import ScenarioResult, TaskStatus


class HTMLReporter:
    """Generates a premium, interactive HTML report."""

    def __init__(self, results: list[ScenarioResult], output_path: str | Path):
        self.results = results
        self.output_path = Path(output_path)
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _get_summary_stats(self) -> dict[str, Any]:
        total_tasks = 0
        passed_tasks = 0
        total_tokens = 0
        total_latency = 0.0
        
        for sr in self.results:
            for tr in sr.task_results:
                total_tasks += 1
                if tr.status == TaskStatus.PASS:
                    passed_tasks += 1
                total_tokens += (tr.input_tokens + tr.output_tokens)
                total_latency += tr.latency_seconds
                
        pass_rate = (passed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        avg_latency = (total_latency / total_tasks) if total_tasks > 0 else 0
        
        return {
            "total_tasks": total_tasks,
            "passed_tasks": passed_tasks,
            "failed_tasks": total_tasks - passed_tasks,
            "pass_rate": f"{pass_rate:.1f}%",
            "total_tokens": f"{total_tokens:,}",
            "avg_latency": f"{avg_latency:.2f}s",
            "total_latency": f"{total_latency:.1f}s",
        }

    def render(self) -> str:
        """Render results to HTML file."""
        stats = self._get_summary_stats()
        
        # Prepare JSON data for charts
        chart_data = {
            "labels": [sr.scenario_name for sr in self.results],
            "pass_rates": [
                (sum(1 for tr in sr.task_results if tr.status == TaskStatus.PASS) / len(sr.task_results) * 100)
                if sr.task_results else 0
                for sr in self.results
            ],
            "latency": [
                (sum(tr.latency_seconds for tr in sr.task_results) / len(sr.task_results))
                if sr.task_results else 0
                for sr in self.results
            ]
        }

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>agentbench | Performance Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
        
        :root {{
            --bg-dark: #0f172a;
            --glass: rgba(30, 41, 59, 0.7);
            --border: rgba(255, 255, 255, 0.1);
            --primary: #6366f1;
            --secondary: #a855f7;
            --success: #22c55e;
            --error: #ef4444;
        }}

        body {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-dark);
            color: #f8fafc;
            background-image: 
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(168, 85, 247, 0.15) 0px, transparent 50%);
            min-height: 100vh;
        }}

        .glass {{
            background: var(--glass);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 1.5rem;
        }}

        .status-pass {{ color: var(--success); }}
        .status-fail {{ color: var(--error); }}
        
        .badge-pass {{ 
            background: rgba(34, 197, 94, 0.1);
            color: var(--success);
            border: 1px solid rgba(34, 197, 94, 0.2);
        }}
        
        .badge-fail {{ 
            background: rgba(239, 68, 68, 0.1);
            color: var(--error);
            border: 1px solid rgba(239, 68, 68, 0.2);
        }}

        .task-card:hover {{
            border-color: var(--primary);
            transform: translateY(-2px);
            transition: all 0.2s ease;
        }}

        ::-webkit-scrollbar {{
            width: 8px;
        }}
        ::-webkit-scrollbar-track {{
            background: #0f172a;
        }}
        ::-webkit-scrollbar-thumb {{
            background: #334155;
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: #475569;
        }}
    </style>
</head>
<body class="p-4 md:p-8">
    <div class="max-w-7xl mx-auto">
        <!-- Header -->
        <header class="flex flex-col md:flex-row justify-between items-start md:items-center mb-12 gap-6">
            <div>
                <h1 class="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400 mb-2">
                    agentbench <span class="text-lg font-normal text-slate-500">v0.1.0</span>
                </h1>
                <p class="text-slate-400 flex items-center gap-2">
                    <i data-lucide="calendar" class="w-4 h-4"></i>
                    Report generated on {self.timestamp}
                </p>
            </div>
            <div class="flex gap-4">
                <div class="glass px-6 py-3 flex flex-col items-center">
                    <span class="text-xs text-slate-500 uppercase tracking-wider font-semibold">Pass Rate</span>
                    <span class="text-2xl font-bold { 'status-pass' if stats['passed_tasks'] == stats['total_tasks'] else 'text-indigo-400' }">{stats['pass_rate']}</span>
                </div>
                <div class="glass px-6 py-3 flex flex-col items-center">
                    <span class="text-xs text-slate-500 uppercase tracking-wider font-semibold">Latency (Avg)</span>
                    <span class="text-2xl font-bold text-slate-200">{stats['avg_latency']}</span>
                </div>
            </div>
        </header>

        <!-- Stats Overview -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">
            <div class="glass p-6">
                <div class="flex justify-between items-center mb-4">
                    <span class="text-slate-400 font-medium">Total Tasks</span>
                    <div class="bg-indigo-500/20 p-2 rounded-lg text-indigo-400"><i data-lucide="layers" class="w-5 h-5"></i></div>
                </div>
                <div class="text-3xl font-bold">{stats['total_tasks']}</div>
            </div>
            <div class="glass p-6">
                <div class="flex justify-between items-center mb-4">
                    <span class="text-slate-400 font-medium">Passed</span>
                    <div class="bg-emerald-500/20 p-2 rounded-lg text-emerald-400"><i data-lucide="check-circle" class="w-5 h-5"></i></div>
                </div>
                <div class="text-3xl font-bold text-emerald-400">{stats['passed_tasks']}</div>
            </div>
            <div class="glass p-6">
                <div class="flex justify-between items-center mb-4">
                    <span class="text-slate-400 font-medium">Failed</span>
                    <div class="bg-rose-500/20 p-2 rounded-lg text-rose-400"><i data-lucide="alert-circle" class="w-5 h-5"></i></div>
                </div>
                <div class="text-3xl font-bold text-rose-400">{stats['failed_tasks']}</div>
            </div>
            <div class="glass p-6">
                <div class="flex justify-between items-center mb-4">
                    <span class="text-slate-400 font-medium">Total Tokens</span>
                    <div class="bg-amber-500/20 p-2 rounded-lg text-amber-400"><i data-lucide="coins" class="w-5 h-5"></i></div>
                </div>
                <div class="text-3xl font-bold text-slate-200">{stats['total_tokens']}</div>
            </div>
        </div>

        <!-- Charts Row -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
            <div class="glass p-8">
                <h3 class="text-xl font-semibold mb-6 flex items-center gap-2">
                    <i data-lucide="bar-chart-2" class="w-5 h-5 text-indigo-400"></i>
                    Scenario Pass Rates
                </h3>
                <div class="h-64">
                    <canvas id="passRateChart"></canvas>
                </div>
            </div>
            <div class="glass p-8">
                <h3 class="text-xl font-semibold mb-6 flex items-center gap-2">
                    <i data-lucide="zap" class="w-5 h-5 text-purple-400"></i>
                    Average Latency (s)
                </h3>
                <div class="h-64">
                    <canvas id="latencyChart"></canvas>
                </div>
            </div>
        </div>

        <!-- Scenarios & Tasks Breakdown -->
        <div class="space-y-12">
            <h2 class="text-3xl font-bold mb-8 flex items-center gap-3">
                <span class="w-1.5 h-8 bg-indigo-500 rounded-full"></span>
                Scenario Breakdown
            </h2>
            
            {self._render_scenarios()}
        </div>

        <footer class="mt-24 pt-8 border-t border-slate-800 text-center text-slate-500 pb-12">
            <p>agentbench © 2026 — Testing excellence for AI agents.</p>
        </footer>
    </div>

    <script>
        // Initialize Lucide icons
        lucide.createIcons();

        // Pass Rate Chart
        const passRateCtx = document.getElementById('passRateChart').getContext('2d');
        new Chart(passRateCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(chart_data['labels'])},
                datasets: [{{
                    label: 'Pass Rate %',
                    data: {json.dumps(chart_data['pass_rates'])},
                    backgroundColor: 'rgba(99, 102, 241, 0.6)',
                    borderColor: 'rgba(99, 102, 241, 1)',
                    borderWidth: 2,
                    borderRadius: 8
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    y: {{ beginAtZero: true, max: 100, grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}, ticks: {{ color: '#94a3b8' }} }},
                    x: {{ grid: {{ display: false }}, ticks: {{ color: '#94a3b8' }} }}
                }}
            }}
        }});

        // Latency Chart
        const latencyCtx = document.getElementById('latencyChart').getContext('2d');
        new Chart(latencyCtx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(chart_data['labels'])},
                datasets: [{{
                    label: 'Latency (s)',
                    data: {json.dumps(chart_data['latency'])},
                    borderColor: '#a855f7',
                    backgroundColor: 'rgba(168, 85, 247, 0.1)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 3,
                    pointBackgroundColor: '#a855f7'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    y: {{ beginAtZero: true, grid: {{ color: 'rgba(255, 255, 255, 0.05)' }}, ticks: {{ color: '#94a3b8' }} }},
                    x: {{ grid: {{ display: false }}, ticks: {{ color: '#94a3b8' }} }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
        
        self.output_path.write_text(html, encoding="utf-8")
        return str(self.output_path)

    def _render_scenarios(self) -> str:
        html = []
        for sr in self.results:
            passed = sum(1 for tr in sr.task_results if tr.status == TaskStatus.PASS)
            total = len(sr.task_results)
            
            html.append(f"""
            <div class="glass overflow-hidden">
                <div class="p-8 border-b border-slate-800 bg-slate-900/50">
                    <div class="flex justify-between items-start mb-4">
                        <div>
                            <span class="text-xs font-bold text-indigo-400 uppercase tracking-widest mb-2 block">Scenario</span>
                            <h3 class="text-2xl font-bold mb-1">{sr.scenario_name}</h3>
                            <p class="text-slate-400">{sr.scenario_description}</p>
                        </div>
                        <div class="flex flex-col items-end">
                            <span class="text-sm text-slate-500 mb-1">Success Rate</span>
                            <span class="text-2xl font-bold { 'status-pass' if passed == total else 'text-white' }">
                                {passed}/{total} <span class="text-lg text-slate-500 font-normal">({(passed/total*100) if total > 0 else 0:.0f}%)</span>
                            </span>
                        </div>
                    </div>
                    <div class="flex gap-4">
                        <span class="text-xs bg-slate-800 px-2 py-1 rounded text-slate-400 flex items-center gap-1">
                            <i data-lucide="cpu" class="w-3 h-3"></i> Agent: {sr.agent_name}
                        </span>
                    </div>
                </div>
                <div class="p-6 overflow-x-auto">
                    <table class="w-full text-left">
                        <thead>
                            <tr class="text-slate-500 text-sm uppercase tracking-wider">
                                <th class="pb-4 pl-4 font-semibold">Task ID</th>
                                <th class="pb-4 font-semibold">Status</th>
                                <th class="pb-4 font-semibold text-center">Latency</th>
                                <th class="pb-4 font-semibold text-center">Tokens</th>
                                <th class="pb-4 pr-4 font-semibold text-right">Details</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800">
                            {self._render_tasks(sr)}
                        </tbody>
                    </table>
                </div>
            </div>
            """)
        return "\n".join(html)

    def _render_tasks(self, sr: ScenarioResult) -> str:
        rows = []
        for tr in sr.task_results:
            status_class = "badge-pass" if tr.status == TaskStatus.PASS else "badge-fail"
            status_icon = "check" if tr.status == TaskStatus.PASS else "x"
            
            rows.append(f"""
            <tr class="group hover:bg-slate-800/30 transition-colors">
                <td class="py-5 pl-4 font-medium text-slate-200">{tr.task_id}</td>
                <td class="py-5">
                    <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold {status_class}">
                        <i data-lucide="{status_icon}" class="w-4 h-4"></i>
                        {tr.status.name}
                    </span>
                </td>
                <td class="py-5 text-center text-slate-400">{tr.latency_seconds:.2f}s</td>
                <td class="py-5 text-center">
                    <div class="text-slate-200">{tr.input_tokens + tr.output_tokens:,}</div>
                    <div class="text-[10px] text-slate-500 uppercase tracking-tighter">I: {{tr.input_tokens}} / O: {{tr.output_tokens}}</div>
                </td>
                <td class="py-5 pr-4 text-right">
                    <button class="text-indigo-400 hover:text-indigo-300 text-sm font-medium transition-colors flex items-center gap-1 justify-end w-full">
                        View Analysis <i data-lucide="chevron-right" class="w-4 h-4"></i>
                    </button>
                    <!-- Expandable criteria content could go here in a production version -->
                </td>
            </tr>
            """)
        return "\n".join(rows)
