import copy
import io
import json
import random
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from deepdiff import DeepDiff
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "sample.json"

_utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
console = Console(file=_utf8_stdout, force_terminal=True)


# ── JSON 로드 ─────────────────────────────────────────────────────────────────

def load_json() -> dict:
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


# ── DeepDiff 결과 파싱 ────────────────────────────────────────────────────────

def parse_diff(before: dict, after: dict) -> list[dict]:
    """DeepDiff 결과를 변경 유형별로 정리한 레코드 리스트로 반환."""
    diff = DeepDiff(before, after, ignore_order=True, verbose_level=2)
    records = []

    for path, change in diff.get("values_changed", {}).items():
        records.append({
            "type": "changed",
            "path": path,
            "old": str(change["old_value"]),
            "new": str(change["new_value"]),
        })

    for path in diff.get("dictionary_item_added", set()):
        records.append({
            "type": "added",
            "path": str(path),
            "old": "",
            "new": str(_get_nested(after, path)),
        })

    for path in diff.get("dictionary_item_removed", set()):
        records.append({
            "type": "removed",
            "path": str(path),
            "old": str(_get_nested(before, path)),
            "new": "",
        })

    for path, change in diff.get("iterable_item_added", {}).items():
        records.append({
            "type": "added",
            "path": path,
            "old": "",
            "new": str(change),
        })

    for path, change in diff.get("iterable_item_removed", {}).items():
        records.append({
            "type": "removed",
            "path": path,
            "old": str(change),
            "new": "",
        })

    return records


def _get_nested(data: dict, deepdiff_path: str):
    """root['key1']['key2'] 형식의 DeepDiff 경로로 값을 추출."""
    import re
    keys = re.findall(r"\['(.*?)'\]|\[(\d+)\]", deepdiff_path)
    node = data
    try:
        for str_key, int_key in keys:
            node = node[str_key if str_key else int(int_key)]
    except (KeyError, IndexError, TypeError):
        return "?"
    return node


# ── 화면 렌더링 ───────────────────────────────────────────────────────────────

_TYPE_STYLE = {
    "changed": ("yellow", "~"),
    "added":   ("green",  "+"),
    "removed": ("red",    "-"),
}


def build_diff_table(records: list[dict]) -> Table:
    table = Table(title="Diff Result", box=box.ROUNDED, show_lines=True)
    table.add_column("Type",  width=8)
    table.add_column("Path",  style="dim", overflow="fold")
    table.add_column("Before", overflow="fold")
    table.add_column("After",  overflow="fold")

    for r in records:
        color, symbol = _TYPE_STYLE.get(r["type"], ("white", "?"))
        table.add_row(
            f"[{color}]{symbol} {r['type']}[/]",
            r["path"],
            f"[red]{r['old']}[/]" if r["old"] else "",
            f"[green]{r['new']}[/]" if r["new"] else "",
        )
    return table


def build_history_table(history: list[dict]) -> Table:
    table = Table(title="Diff History", box=box.SIMPLE)
    table.add_column("Time", style="dim", width=10)
    table.add_column("Changed", justify="right", style="yellow")
    table.add_column("Added",   justify="right", style="green")
    table.add_column("Removed", justify="right", style="red")
    table.add_column("Total",   justify="right")

    for h in history[-6:]:
        table.add_row(
            h["time"],
            str(h["changed"]),
            str(h["added"]),
            str(h["removed"]),
            str(h["total"]),
        )
    return table


def build_summary(records: list[dict]) -> Text:
    counts = {"changed": 0, "added": 0, "removed": 0}
    for r in records:
        counts[r["type"]] = counts.get(r["type"], 0) + 1
    t = Text()
    t.append(f"  ~ changed: {counts['changed']}  ", style="yellow")
    t.append(f"+ added: {counts['added']}  ", style="green")
    t.append(f"- removed: {counts['removed']}", style="red")
    return t


def build_renderable(records: list[dict], history: list[dict], status: str) -> Panel:
    from rich.console import Group
    ts = datetime.now().strftime("%H:%M:%S")
    body = Group(
        Text(f"  Status: {status}  |  {ts}", style="dim"),
        build_summary(records),
        build_diff_table(records) if records else Text("  [No changes yet]", style="dim"),
        build_history_table(history),
    )
    return Panel(body, title="[bold]DataMonitor -- deepdiff PoC[/]", border_style="blue")


# ── watchdog 핸들러 ───────────────────────────────────────────────────────────

class DiffHandler(FileSystemEventHandler):
    def __init__(self, target: Path, callback):
        self._target = str(target.resolve())
        self._callback = callback
        self._cooldown = 0.0

    def on_modified(self, event):
        if event.is_directory:
            return
        if str(Path(event.src_path).resolve()) != self._target:
            return
        now = time.monotonic()
        if now - self._cooldown < 0.1:
            return
        self._cooldown = now
        self._callback()


# ── 데이터 자동 변경 (시뮬레이터) ────────────────────────────────────────────

def _mutate(data: dict) -> dict:
    d = copy.deepcopy(data)
    for role in d["database"].values():
        role["connections"]["active"] = random.randint(1, 30)
        role["connections"]["idle"]   = random.randint(0, 10)
    for q in d["queues"]:
        if q["status"] == "active":
            q["pending"] = random.randint(0, 100)
            q["processed_today"] += random.randint(1, 20)
    d["cache"]["redis"]["stats"]["hit_rate"]   = round(random.uniform(0.70, 0.99), 2)
    d["cache"]["redis"]["stats"]["total_keys"] = random.randint(10000, 20000)
    return d


def file_mutator(stop_event: threading.Event, interval: float = 3.5):
    while not stop_event.is_set():
        stop_event.wait(interval)
        if stop_event.is_set():
            break
        try:
            data = load_json()
            with open(DATA_PATH, "w", encoding="utf-8") as f:
                json.dump(_mutate(data), f, indent=2, ensure_ascii=False)
        except Exception:
            pass


# ── 메인 실행 ─────────────────────────────────────────────────────────────────

def run(duration: int = 20, mutate_interval: float = 3.5):
    current_data = load_json()
    current_records: list[dict] = []
    history: list[dict] = []
    status = "Watching..."

    def on_changed():
        nonlocal current_data, current_records, status
        time.sleep(0.05)          # 파일 쓰기 완료 대기
        try:
            new_data = load_json()
        except Exception:
            return
        records = parse_diff(current_data, new_data)
        if records:
            history.append({
                "time":    datetime.now().strftime("%H:%M:%S"),
                "changed": sum(1 for r in records if r["type"] == "changed"),
                "added":   sum(1 for r in records if r["type"] == "added"),
                "removed": sum(1 for r in records if r["type"] == "removed"),
                "total":   len(records),
            })
        current_data    = new_data
        current_records = records
        status = f"Last diff at {datetime.now().strftime('%H:%M:%S')} -- {len(records)} change(s)"

    handler = DiffHandler(DATA_PATH, on_changed)
    observer = Observer()
    observer.schedule(handler, str(DATA_PATH.parent), recursive=False)
    observer.start()

    stop_event = threading.Event()
    mutator = threading.Thread(target=file_mutator,
                               args=(stop_event, mutate_interval), daemon=True)
    mutator.start()

    console.print(f"[dim]Watching:[/] {DATA_PATH}")
    console.print(f"[dim]Auto-mutating every {mutate_interval}s for {duration}s.[/]\n")

    try:
        with Live(console=console, refresh_per_second=4, screen=False) as live:
            end = time.monotonic() + duration
            while time.monotonic() < end:
                live.update(build_renderable(current_records, history, status))
                time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        observer.stop()
        observer.join()

    # ── 최종 요약 ──
    console.rule("[bold green]PoC Complete[/]")
    console.print(f"Total diff events: [bold]{len(history)}[/]")
    if history:
        total_changes = sum(h["total"] for h in history)
        console.print(f"Total field changes detected: [cyan]{total_changes}[/]")
        console.print("\n[bold]Final diff table:[/]")
        console.print(build_diff_table(current_records))


if __name__ == "__main__":
    run(duration=20, mutate_interval=3.5)
