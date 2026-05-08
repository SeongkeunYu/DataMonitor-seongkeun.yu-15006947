"""
Phase 6: textual PoC
- DataTable + Input 위젯으로 JSON 실시간 필터링
- watchdog으로 파일 변경 감지 → 자동 리로드
- deepdiff로 변경 행 하이라이트
- run_headless(): 자동화 검증용 (bash 실행)
- DataMonitorApp: 실제 TUI (터미널에서 직접 실행)
"""

import asyncio
import copy
import io
import json
import sys
import threading
import time
from pathlib import Path

from deepdiff import DeepDiff
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, Input, Static
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "sample.json"

_utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
console = Console(file=_utf8_stdout, force_terminal=True)


# ── JSON 평탄화 ───────────────────────────────────────────────────────────────

def flatten_json(data, prefix: str = "root") -> list[tuple[str, str, str]]:
    """중첩 JSON을 (path, value, type) 튜플 리스트로 변환."""
    rows: list[tuple[str, str, str]] = []
    if isinstance(data, dict):
        for k, v in data.items():
            key = f"{prefix}.{k}"
            if isinstance(v, (dict, list)):
                rows.extend(flatten_json(v, key))
            else:
                rows.append((key, str(v), type(v).__name__))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            key = f"{prefix}[{i}]"
            if isinstance(item, (dict, list)):
                rows.extend(flatten_json(item, key))
            else:
                rows.append((key, str(item), type(item).__name__))
    return rows


def changed_paths_from_diff(diff: DeepDiff) -> set[str]:
    paths: set[str] = set()
    for change_type in ("values_changed", "dictionary_item_added",
                        "dictionary_item_removed", "iterable_item_added",
                        "iterable_item_removed"):
        for p in diff.get(change_type, {}):
            paths.add(str(p))
    return paths


# ── watchdog 핸들러 ───────────────────────────────────────────────────────────

class _FileHandler(FileSystemEventHandler):
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
        if now - self._cooldown < 0.15:
            return
        self._cooldown = now
        self._callback()


# ── Textual 앱 ────────────────────────────────────────────────────────────────

class DataMonitorApp(App):
    TITLE = "DataMonitor -- textual PoC"
    CSS = """
    Screen { background: $surface; }
    #filter { dock: top; margin: 1 2; height: 3; }
    #status  { dock: bottom; height: 1; background: $panel; padding: 0 2; color: $text-muted; }
    DataTable { height: 1fr; margin: 0 1; }
    """
    BINDINGS = [
        Binding("q",      "quit",         "Quit"),
        Binding("f5",     "reload",       "Reload"),
        Binding("escape", "clear_filter", "Clear Filter"),
    ]

    def __init__(self, watch: bool = True):
        super().__init__()
        self._watch = watch
        self._data: dict = {}
        self._prev: dict = {}
        self._changed: set[str] = set()
        self._rows: list[tuple[str, str, str]] = []
        self._observer: Observer | None = None

    # ── 위젯 구성 ─────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(id="filter", placeholder="Filter by path or value...  (ESC=clear  Q=quit)")
        yield DataTable(id="table")
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        t = self.query_one(DataTable)
        t.add_column("Path",    key="path",    width=46)
        t.add_column("Value",   key="value",   width=22)
        t.add_column("Type",    key="type",    width=8)
        t.add_column("Status",  key="status",  width=10)
        t.cursor_type = "row"
        self._reload()
        if self._watch:
            self._start_watcher()

    # ── 데이터 로드 / diff ────────────────────────────────────────────────────

    def _reload(self) -> None:
        try:
            with open(DATA_PATH, encoding="utf-8") as f:
                new_data = json.load(f)
        except Exception as e:
            self._set_status(f"Load error: {e}")
            return

        if self._data:
            diff = DeepDiff(self._data, new_data, ignore_order=True)
            self._changed = changed_paths_from_diff(diff)
        else:
            self._changed = set()

        self._prev = copy.deepcopy(self._data)
        self._data = new_data
        self._rows = flatten_json(new_data)
        self._apply_filter(self.query_one(Input).value)
        self._set_status(
            f"{len(self._rows)} fields  |  {DATA_PATH.name}  |  changed: {len(self._changed)}"
        )

    def _apply_filter(self, keyword: str) -> None:
        kw = keyword.lower()
        t = self.query_one(DataTable)
        t.clear()
        for path, value, typ in self._rows:
            if kw and kw not in path.lower() and kw not in value.lower():
                continue
            is_changed = bool(self._changed) and any(cp in path for cp in self._changed)
            status = "~ changed" if is_changed else ""
            t.add_row(path, value, typ, status)

    # ── 이벤트 핸들러 ─────────────────────────────────────────────────────────

    def on_input_changed(self, event: Input.Changed) -> None:
        self._apply_filter(event.value)

    def action_reload(self) -> None:
        self._reload()

    def action_clear_filter(self) -> None:
        self.query_one(Input).value = ""

    # ── watchdog 연동 ─────────────────────────────────────────────────────────

    def _start_watcher(self) -> None:
        handler = _FileHandler(DATA_PATH, lambda: self.call_from_thread(self._reload))
        self._observer = Observer()
        self._observer.schedule(handler, str(DATA_PATH.parent), recursive=False)
        self._observer.start()

    def on_unmount(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer.join()

    def _set_status(self, msg: str) -> None:
        try:
            self.query_one("#status", Static).update(msg)
        except Exception:
            pass


# ── 헤드리스 자동 검증 ────────────────────────────────────────────────────────

async def run_headless() -> None:
    """bash 실행용 헤드리스 검증: pilot으로 상호작용 후 결과를 rich로 출력."""
    console.rule("[bold green]Phase 6 -- textual PoC (Headless Verification)[/]")

    results: list[tuple[str, str, bool]] = []

    app = DataMonitorApp(watch=False)
    async with app.run_test(headless=True, size=(120, 40)) as pilot:
        await pilot.pause(0.3)

        table = app.query_one(DataTable)
        inp   = app.query_one(Input)

        # [1] 초기 전체 로드
        total = table.row_count
        results.append(("Initial load", f"{total} rows", total > 0))

        # [2] 'database' 필터
        inp.value = "database"
        await pilot.pause(0.2)
        db_rows = table.row_count
        results.append(("Filter 'database'", f"{db_rows} rows", 0 < db_rows < total))

        # [3] 'queue' 필터
        inp.value = "queue"
        await pilot.pause(0.2)
        q_rows = table.row_count
        results.append(("Filter 'queue'", f"{q_rows} rows", 0 < q_rows < total))

        # [4] 'active' 필터
        inp.value = "active"
        await pilot.pause(0.2)
        a_rows = table.row_count
        results.append(("Filter 'active'", f"{a_rows} rows", 0 < a_rows < total))

        # [5] ESC로 필터 초기화
        await pilot.press("escape")
        await pilot.pause(0.2)
        reset_rows = table.row_count
        results.append(("ESC clear filter", f"{reset_rows} rows", reset_rows == total))

        # [6] watchdog 연동 검증 (파일 수정 후 리로드)
        orig = copy.deepcopy(app._data)
        mutated = copy.deepcopy(orig)
        mutated["cache"]["redis"]["stats"]["hit_rate"] = 0.42
        mutated["database"]["primary"]["connections"]["active"] = 99
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(mutated, f, indent=2, ensure_ascii=False)
        app._reload()                      # 헤드리스에선 직접 호출
        await pilot.pause(0.2)
        changed_count = len(app._changed)
        results.append(("watchdog+deepdiff reload", f"{changed_count} changed paths", changed_count > 0))

        # 원본 복원
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(orig, f, indent=2, ensure_ascii=False)

        await pilot.press("q")

    # ── rich로 결과 출력 ──────────────────────────────────────────────────────
    summary = Table(title="Textual PoC -- Headless Verification Results", box=box.ROUNDED)
    summary.add_column("#",       width=3)
    summary.add_column("Scenario")
    summary.add_column("Result",  justify="center")
    summary.add_column("Pass",    justify="center", width=6)

    for i, (scenario, result, ok) in enumerate(results, 1):
        summary.add_row(
            str(i),
            scenario,
            result,
            "[green]YES[/]" if ok else "[red]NO[/]",
        )
    console.print(summary)

    passed = sum(1 for _, _, ok in results if ok)
    console.print(f"\nTotal: {len(results)}  |  [green]PASS: {passed}[/]  |  [red]FAIL: {len(results)-passed}[/]")
    all_ok = all(ok for _, _, ok in results)
    console.print(f"Success criterion: {'[green]MET[/]' if all_ok else '[red]NOT MET[/]'}")
    console.print("\n[dim]Interactive mode:[/] python main.py --interactive")


# ── 진입점 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--interactive" in sys.argv:
        DataMonitorApp(watch=True).run()
    else:
        asyncio.run(run_headless())
