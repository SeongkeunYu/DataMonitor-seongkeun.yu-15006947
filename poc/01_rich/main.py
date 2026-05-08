import io
import json
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.columns import Columns
from rich import box

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "sample.json"

# Windows cp949 터미널에서 UTF-8 강제 적용
_utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
console = Console(file=_utf8_stdout, force_terminal=True, highlight=True)


def load_json() -> dict:
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_tree(label: str, data, tree: Tree | None = None) -> Tree:
    node = tree.add(f"[bold cyan]{label}[/]") if tree else Tree(f"[bold cyan]{label}[/]")
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                build_tree(k, v, node)
            else:
                status_color = _value_color(k, v)
                node.add(f"[dim]{k}[/]: [{status_color}]{v}[/]")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            build_tree(f"[{i}]", item, node)
    else:
        node.add(str(data))
    return node


def _value_color(key: str, value) -> str:
    if key == "status":
        return {"running": "green", "connected": "green", "active": "green",
                "paused": "yellow", "error": "red"}.get(str(value), "white")
    if key == "level":
        return {"info": "blue", "warning": "yellow", "error": "red"}.get(str(value), "white")
    if isinstance(value, float):
        return "magenta"
    if isinstance(value, int):
        return "cyan"
    return "white"


def build_queues_table(queues: list) -> Table:
    table = Table(title="Queues", box=box.ROUNDED, highlight=True)
    table.add_column("Name", style="bold")
    table.add_column("Status")
    table.add_column("Pending", justify="right")
    table.add_column("Processed Today", justify="right")
    table.add_column("Workers (run/idle)", justify="center")

    for q in queues:
        status = q["status"]
        color = {"active": "green", "paused": "yellow"}.get(status, "white")
        workers = q.get("workers", {})
        table.add_row(
            q["name"],
            f"[{color}]{status}[/]",
            str(q["pending"]),
            str(q["processed_today"]),
            f"{workers.get('running', 0)} / {workers.get('idle', 0)}",
        )
    return table


def build_alerts_table(alerts: list) -> Table:
    table = Table(title="Alerts", box=box.ROUNDED, highlight=True)
    table.add_column("ID", style="dim")
    table.add_column("Level")
    table.add_column("Message")
    table.add_column("Triggered At", style="dim")

    for a in alerts:
        level = a["level"]
        color = {"info": "blue", "warning": "yellow", "error": "red"}.get(level, "white")
        table.add_row(
            a["id"],
            f"[{color}]{level}[/]",
            a["message"],
            a["triggered_at"],
        )
    return table


def build_layout(data: dict) -> list:
    tree = build_tree("system", data["system"])
    db_tree = build_tree("database", data["database"])
    cache_tree = build_tree("cache", data["cache"])

    queues_table = build_queues_table(data["queues"])
    alerts_table = build_alerts_table(data["alerts"])

    return [
        Panel(Columns([tree, db_tree, cache_tree], equal=True, expand=True), title="[bold]Infrastructure State[/]"),
        queues_table,
        alerts_table,
    ]


def demo_static():
    console.rule("[bold green]Scenario 1 -- Static JSON Output (Table + Tree)[/]")
    data = load_json()
    for widget in build_layout(data):
        console.print(widget)


def demo_live(refresh_seconds: int = 2, cycles: int = 5):
    console.rule("[bold green]Live Refresh Demo (2s interval, 5 cycles)[/]")
    with Live(console=console, refresh_per_second=4, screen=False) as live:
        for i in range(cycles):
            data = load_json()
            from rich.console import Group
            group = Group(*build_layout(data))
            live.update(Panel(group, title=f"[bold]DataMonitor — refresh #{i + 1}[/]", border_style="blue"))
            time.sleep(refresh_seconds)


if __name__ == "__main__":
    demo_static()
    console.print()
    demo_live()
