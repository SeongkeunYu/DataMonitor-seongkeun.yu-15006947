import io
import json
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "sample.json"

_utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
console = Console(file=_utf8_stdout, force_terminal=True)


# ── Pydantic 스키마 정의 ──────────────────────────────────────────────────────

class Connections(BaseModel):
    active: int = Field(ge=0)
    idle:   int = Field(ge=0)
    max:    int = Field(gt=0)

class DbInstance(BaseModel):
    host:        str
    port:        int = Field(gt=0, lt=65536)
    status:      Literal["connected", "disconnected", "error"]
    connections: Connections

class Database(BaseModel):
    primary: DbInstance
    replica: DbInstance

class RedisStats(BaseModel):
    hit_rate:       float = Field(ge=0.0, le=1.0)
    used_memory_mb: int   = Field(ge=0)
    total_keys:     int   = Field(ge=0)

class Redis(BaseModel):
    host:   str
    port:   int = Field(gt=0, lt=65536)
    status: Literal["connected", "disconnected", "error"]
    stats:  RedisStats

class Cache(BaseModel):
    redis: Redis

class Workers(BaseModel):
    running: int = Field(ge=0)
    idle:    int = Field(ge=0)

class Queue(BaseModel):
    name:            str
    status:          Literal["active", "paused", "stopped"]
    pending:         int = Field(ge=0)
    processed_today: int = Field(ge=0)
    workers:         Workers

class Alert(BaseModel):
    id:           str
    level:        Literal["info", "warning", "error"]
    message:      str
    triggered_at: str

    @field_validator("triggered_at")
    @classmethod
    def must_be_iso8601(cls, v: str) -> str:
        from datetime import datetime
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"triggered_at must be ISO 8601 format, got: {v!r}")
        return v

class System(BaseModel):
    name:           str
    version:        str
    status:         Literal["running", "stopped", "error"]
    uptime_seconds: int = Field(ge=0)

class DataMonitorSchema(BaseModel):
    system:   System
    database: Database
    cache:    Cache
    queues:   list[Queue]
    alerts:   list[Alert]


# ── 검증 결과 렌더링 ──────────────────────────────────────────────────────────

def render_success(label: str, data: DataMonitorSchema) -> Panel:
    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("Field", style="dim")
    table.add_column("Value")
    table.add_row("system.name",    data.system.name)
    table.add_row("system.status",  f"[green]{data.system.status}[/]")
    table.add_row("db.primary",     f"[green]{data.database.primary.status}[/]  active={data.database.primary.connections.active}")
    table.add_row("db.replica",     f"[green]{data.database.replica.status}[/]  active={data.database.replica.connections.active}")
    table.add_row("cache.hit_rate", f"[magenta]{data.cache.redis.stats.hit_rate:.0%}[/]")
    table.add_row("queues",         f"{len(data.queues)} queue(s)")
    table.add_row("alerts",         f"{len(data.alerts)} alert(s)")

    body = Text()
    body.append("  VALID  ", style="bold green on dark_green")
    body.append(f"  {label}\n\n")
    from rich.console import Group
    return Panel(Group(body, table), title="[bold green]Validation PASS[/]", border_style="green")


def render_failure(label: str, exc: ValidationError) -> Panel:
    table = Table(box=box.ROUNDED, show_lines=True)
    table.add_column("#",      width=3,  style="dim")
    table.add_column("Field",  overflow="fold")
    table.add_column("Error",  overflow="fold", style="red")
    table.add_column("Input",  overflow="fold", style="yellow")

    for i, err in enumerate(exc.errors(), start=1):
        loc   = " > ".join(str(p) for p in err["loc"])
        msg   = err["msg"]
        inp   = str(err.get("input", ""))[:60]
        table.add_row(str(i), loc, msg, inp)

    body = Text()
    body.append("  INVALID  ", style="bold white on red")
    body.append(f"  {label}\n\n")
    from rich.console import Group
    return Panel(Group(body, table),
                 title=f"[bold red]Validation FAIL  ({exc.error_count()} error(s))[/]",
                 border_style="red")


def validate(label: str, data: dict) -> bool:
    console.print(f"\n[dim]Case:[/] [bold]{label}[/]")
    try:
        model = DataMonitorSchema.model_validate(data)
        console.print(render_success(label, model))
        return True
    except ValidationError as exc:
        console.print(render_failure(label, exc))
        return False


# ── 테스트 케이스 ─────────────────────────────────────────────────────────────

def load_json() -> dict:
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def run():
    console.rule("[bold green]Phase 5 -- pydantic PoC (Schema Validation)[/]")

    base = load_json()
    import copy

    cases: list[tuple[str, dict]] = []

    # 1. 정상 데이터
    cases.append(("Case 1: Valid data (sample.json)", copy.deepcopy(base)))

    # 2. 필수 필드 누락
    c2 = copy.deepcopy(base)
    del c2["database"]["primary"]["host"]
    cases.append(("Case 2: Missing required field (database.primary.host)", c2))

    # 3. 타입 오류 — active에 문자열 전달
    c3 = copy.deepcopy(base)
    c3["database"]["primary"]["connections"]["active"] = "많음"
    cases.append(("Case 3: Wrong type (connections.active = string)", c3))

    # 4. 범위 초과 — hit_rate > 1.0
    c4 = copy.deepcopy(base)
    c4["cache"]["redis"]["stats"]["hit_rate"] = 1.5
    cases.append(("Case 4: Out of range (hit_rate = 1.5, max 1.0)", c4))

    # 5. 허용되지 않는 Literal — status 값
    c5 = copy.deepcopy(base)
    c5["system"]["status"] = "unknown"
    cases.append(("Case 5: Invalid literal (system.status = 'unknown')", c5))

    # 6. 음수 값 — pending < 0
    c6 = copy.deepcopy(base)
    c6["queues"][0]["pending"] = -10
    cases.append(("Case 6: Negative value (queues[0].pending = -10)", c6))

    # 7. 잘못된 날짜 형식
    c7 = copy.deepcopy(base)
    c7["alerts"][0]["triggered_at"] = "2026/05/08 09:15:00"
    cases.append(("Case 7: Invalid datetime format (triggered_at)", c7))

    # 8. 복합 오류 — 여러 필드 동시 오류
    c8 = copy.deepcopy(base)
    c8["system"]["status"] = "broken"
    c8["cache"]["redis"]["stats"]["hit_rate"] = -0.1
    c8["queues"][1]["status"] = "pending"
    cases.append(("Case 8: Multiple errors (status + hit_rate + queue status)", c8))

    results = []
    for label, data in cases:
        ok = validate(label, data)
        results.append((label, ok))

    # ── 최종 요약 ──
    console.rule("[bold]Summary[/]")
    summary = Table(box=box.ROUNDED)
    summary.add_column("Case")
    summary.add_column("Result", justify="center")

    for label, ok in results:
        result_text = "[green]PASS[/]" if ok else "[red]FAIL[/]"
        summary.add_row(label, result_text)

    console.print(summary)
    passed = sum(1 for _, ok in results if ok)
    console.print(f"\nTotal: {len(results)} cases  |  "
                  f"[green]PASS: {passed}[/]  |  [red]FAIL: {len(results) - passed}[/]")
    console.print("\n[dim]Success criterion: Case 1 PASS, Cases 2~8 all FAIL (errors clearly reported)[/]")
    criterion_ok = results[0][1] and all(not ok for _, ok in results[1:])
    console.print(f"Criterion: {'[green]MET[/]' if criterion_ok else '[red]NOT MET[/]'}")


if __name__ == "__main__":
    run()
