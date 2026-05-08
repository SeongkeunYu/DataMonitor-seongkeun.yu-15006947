import io
import json
import random
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.tree import Tree
from rich import box
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "sample.json"

_utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
console = Console(file=_utf8_stdout, force_terminal=True)

# 이벤트 감지 시각 측정용
_last_modified_at: float | None = None
_last_detected_at: float | None = None


def load_json() -> dict:
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


# ── 화면 렌더링 ──────────────────────────────────────────────────────────────

def _status_color(value: str) -> str:
    return {"running": "green", "connected": "green", "active": "green",
            "paused": "yellow", "error": "red"}.get(str(value), "white")


def build_db_table(data: dict) -> Table:
    table = Table(title="Database", box=box.ROUNDED)
    table.add_column("Role")
    table.add_column("Host")
    table.add_column("Status")
    table.add_column("Active", justify="right")
    table.add_column("Idle", justify="right")

    for role, info in data["database"].items():
        conn = info["connections"]
        color = _status_color(info["status"])
        table.add_row(role, info["host"], f"[{color}]{info['status']}[/]",
                      str(conn["active"]), str(conn["idle"]))
    return table


def build_queues_table(data: dict) -> Table:
    table = Table(title="Queues", box=box.ROUNDED)
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Pending", justify="right")
    table.add_column("Processed", justify="right")

    for q in data["queues"]:
        color = _status_color(q["status"])
        table.add_row(q["name"], f"[{color}]{q['status']}[/]",
                      str(q["pending"]), str(q["processed_today"]))
    return table


def build_event_log(events: list[dict]) -> Table:
    table = Table(title="Change Event Log", box=box.SIMPLE, show_header=True)
    table.add_column("Time", style="dim", width=12)
    table.add_column("Event")
    table.add_column("Latency", justify="right")

    for e in events[-8:]:          # 최근 8건만 표시
        latency = f"[green]{e['latency_ms']:.1f} ms[/]" if e["latency_ms"] < 1000 else f"[yellow]{e['latency_ms']:.1f} ms[/]"
        table.add_row(e["time"], e["message"], latency)
    return table


def build_renderable(data: dict, events: list[dict]) -> Panel:
    db_tbl = build_db_table(data)
    q_tbl = build_queues_table(data)
    cache = data["cache"]["redis"]
    cache_text = Text()
    cache_text.append(f"Redis  {cache['host']}:{cache['port']}  ", style="dim")
    cache_text.append(f"hit_rate={cache['stats']['hit_rate']:.0%}  ", style="magenta")
    cache_text.append(f"keys={cache['stats']['total_keys']:,}  ", style="cyan")
    cache_text.append(f"mem={cache['stats']['used_memory_mb']} MB", style="cyan")

    event_tbl = build_event_log(events)

    from rich.console import Group
    body = Group(
        cache_text,
        Columns([db_tbl, q_tbl], expand=True),
        event_tbl,
    )
    ts = datetime.now().strftime("%H:%M:%S")
    return Panel(body, title=f"[bold]DataMonitor -- watchdog PoC[/]  [dim]{ts}[/]", border_style="blue")


# ── watchdog 핸들러 ──────────────────────────────────────────────────────────

class JsonFileHandler(FileSystemEventHandler):
    def __init__(self, target: Path, callback):
        self._target = str(target.resolve())
        self._callback = callback
        self._last_event_time = 0.0

    def on_modified(self, event):
        if event.is_directory:
            return
        if str(Path(event.src_path).resolve()) != self._target:
            return
        # 중복 이벤트 억제 (100 ms 이내 재발화 무시)
        now = time.monotonic()
        if now - self._last_event_time < 0.1:
            return
        self._last_event_time = now
        self._callback(now)


# ── 데이터 자동 변경 (시뮬레이터) ────────────────────────────────────────────

def _mutate(data: dict) -> dict:
    import copy
    d = copy.deepcopy(data)
    for role in d["database"].values():
        role["connections"]["active"] = random.randint(1, 30)
        role["connections"]["idle"] = random.randint(0, 10)
    for q in d["queues"]:
        if q["status"] == "active":
            q["pending"] = random.randint(0, 100)
            q["processed_today"] += random.randint(1, 20)
    d["cache"]["redis"]["stats"]["hit_rate"] = round(random.uniform(0.70, 0.99), 2)
    d["cache"]["redis"]["stats"]["total_keys"] = random.randint(10000, 20000)
    return d


def file_mutator(stop_event: threading.Event, interval: float = 3.0):
    """interval초마다 sample.json을 랜덤 변경하여 watchdog 이벤트를 발생시킨다."""
    while not stop_event.is_set():
        stop_event.wait(interval)
        if stop_event.is_set():
            break
        try:
            data = load_json()
            mutated = _mutate(data)
            with open(DATA_PATH, "w", encoding="utf-8") as f:
                json.dump(mutated, f, indent=2, ensure_ascii=False)
        except Exception:
            pass


# ── 메인 실행 ────────────────────────────────────────────────────────────────

def run(duration: int = 20, mutate_interval: float = 3.0):
    events: list[dict] = []
    data = load_json()

    def on_file_changed(detected_at: float):
        nonlocal data
        write_at = _file_mtime()
        latency_ms = (detected_at - write_at) * 1000
        try:
            data = load_json()
        except Exception:
            return
        events.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": "sample.json modified -- reloaded",
            "latency_ms": max(latency_ms, 0.0),
        })

    def _file_mtime() -> float:
        return DATA_PATH.stat().st_mtime

    handler = JsonFileHandler(DATA_PATH, on_file_changed)
    observer = Observer()
    observer.schedule(handler, str(DATA_PATH.parent), recursive=False)
    observer.start()

    stop_event = threading.Event()
    mutator_thread = threading.Thread(target=file_mutator,
                                      args=(stop_event, mutate_interval), daemon=True)
    mutator_thread.start()

    console.print(f"[dim]Watching:[/] {DATA_PATH}")
    console.print(f"[dim]Auto-mutating every {mutate_interval}s for {duration}s. Press Ctrl+C to stop.[/]\n")

    try:
        with Live(console=console, refresh_per_second=4, screen=False) as live:
            end = time.monotonic() + duration
            while time.monotonic() < end:
                live.update(build_renderable(data, events))
                time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        observer.stop()
        observer.join()

    console.rule("[bold green]PoC Complete[/]")
    console.print(f"Total change events detected: [bold]{len(events)}[/]")
    if events:
        avg_ms = sum(e["latency_ms"] for e in events) / len(events)
        max_ms = max(e["latency_ms"] for e in events)
        console.print(f"Avg latency: [cyan]{avg_ms:.1f} ms[/]   Max latency: [yellow]{max_ms:.1f} ms[/]")
        success = all(e["latency_ms"] < 1000 for e in events)
        label = "[green]PASS[/]" if success else "[red]FAIL[/]"
        console.print(f"Success criterion (<1s): {label}")


if __name__ == "__main__":
    run(duration=20, mutate_interval=3.0)
