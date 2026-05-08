"""
Phase 7: 통합 평가 및 기술 스택 선정
Phase 2~6 PoC 결과를 종합해 라이브러리 평가표와 최종 권장 스택을 출력한다.
"""

import io
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.rule import Rule
from rich import box
from rich.console import Group

_utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
console = Console(file=_utf8_stdout, force_terminal=True, width=110)


# ── PoC 결과 데이터 ───────────────────────────────────────────────────────────

RESULTS = [
    {
        "lib":      "rich",
        "role":     "콘솔 UI 렌더링",
        "phase":    "Phase 2",
        "scenario": "기본 출력 (Table + Tree + Live)",
        "score": {"렌더링 품질": 5, "성능": 5, "학습 비용": 5, "유지보수성": 5},
        "evidence": [
            "Tree / Table / Panel / Columns 모두 정상 렌더링",
            "Live 컴포넌트 4fps 갱신 확인",
            "depth 3 이상 중첩 JSON 계층 구조 보존 출력",
        ],
        "issues": ["Windows cp949 터미널: io.TextIOWrapper UTF-8 래핑으로 해결"],
        "verdict": "채택",
    },
    {
        "lib":      "watchdog",
        "role":     "파일 변경 감지",
        "phase":    "Phase 3",
        "scenario": "실시간 갱신 (JSON 파일 수정 → 자동 리로드)",
        "score": {"렌더링 품질": 0, "성능": 5, "학습 비용": 5, "유지보수성": 5},
        "evidence": [
            "파일 저장 후 평균 0.0 ms 이내 이벤트 수신 (6회)",
            "Observer + FileSystemEventHandler 패턴 간결",
            "rich Live와 연동하여 화면 자동 갱신 확인",
        ],
        "issues": ["중복 이벤트 100 ms 디바운싱 필요 (직접 구현)"],
        "verdict": "채택",
    },
    {
        "lib":      "deepdiff",
        "role":     "JSON diff 비교",
        "phase":    "Phase 4",
        "scenario": "변경 감지 하이라이트 (before/after 비교)",
        "score": {"렌더링 품질": 0, "성능": 4, "학습 비용": 4, "유지보수성": 4},
        "evidence": [
            "5회 diff 이벤트, 총 48개 필드 변경 정확 감지",
            "values_changed / added / removed 유형별 분류",
            "rich와 연동해 Before/After 컬러 하이라이트 출력",
        ],
        "issues": [
            "DeepDiff 경로(root['key']) → 내부 경로 변환 로직 직접 구현 필요",
            "대형 JSON에서 성능 검토 필요",
        ],
        "verdict": "채택",
    },
    {
        "lib":      "pydantic",
        "role":     "JSON 스키마 검증",
        "phase":    "Phase 5",
        "scenario": "스키마 검증 (8개 케이스 정상/비정상)",
        "score": {"렌더링 품질": 0, "성능": 5, "학습 비용": 4, "유지보수성": 5},
        "evidence": [
            "Case 1 (정상) PASS, Cases 2~8 (비정상) 모두 FAIL 정확 감지",
            "에러 위치·유형·입력값을 명확한 메시지로 출력",
            "field_validator로 커스텀 ISO 8601 검증 정상 동작",
        ],
        "issues": ["BaseModel + Field 개념 학습 필요 (1~2시간 수준)"],
        "verdict": "채택",
    },
    {
        "lib":      "textual",
        "role":     "TUI 프레임워크",
        "phase":    "Phase 6",
        "scenario": "필터링 + watchdog + deepdiff 통합",
        "score": {"렌더링 품질": 5, "성능": 4, "학습 비용": 3, "유지보수성": 3},
        "evidence": [
            "Input 위젯 → DataTable 실시간 필터링 (48→12→18→4→48 rows)",
            "watchdog call_from_thread 연동 정상",
            "deepdiff 변경 경로 DataTable Status 컬럼 표시 확인",
        ],
        "issues": [
            "pilot.type() v8에서 제거 — API 변경 잦음 (유지보수 리스크)",
            "async 이벤트 루프 + watchdog 스레드 연동 복잡도 존재",
            "CSS + 위젯 + async 학습 비용 높음",
        ],
        "verdict": "조건부 채택",
    },
]

STAR = {"5": "★★★★★", "4": "★★★★☆", "3": "★★★☆☆", "2": "★★☆☆☆", "1": "★☆☆☆☆", "0": "N/A"}

VERDICT_STYLE = {
    "채택":      "bold green",
    "조건부 채택": "bold yellow",
    "미채택":    "bold red",
}


# ── 렌더 함수 ─────────────────────────────────────────────────────────────────

def star(n: int) -> str:
    return STAR.get(str(n), "N/A")


def build_score_table() -> Table:
    t = Table(title="라이브러리 평가표", box=box.ROUNDED, show_lines=True)
    t.add_column("라이브러리",   style="bold", width=12)
    t.add_column("역할",        width=16)
    t.add_column("렌더링 품질", justify="center", width=12)
    t.add_column("성능",       justify="center", width=12)
    t.add_column("학습 비용",  justify="center", width=12)
    t.add_column("유지보수성", justify="center", width=12)
    t.add_column("평균",       justify="center", width=8)
    t.add_column("판정",       justify="center", width=12)

    for r in RESULTS:
        s = r["score"]
        non_zero = [v for v in s.values() if v > 0]
        avg = f"{sum(non_zero)/len(non_zero):.1f}" if non_zero else "-"
        verdict = r["verdict"]
        t.add_row(
            f"[cyan]{r['lib']}[/]",
            r["role"],
            star(s["렌더링 품질"]),
            star(s["성능"]),
            star(s["학습 비용"]),
            star(s["유지보수성"]),
            avg,
            f"[{VERDICT_STYLE[verdict]}]{verdict}[/]",
        )
    return t


def build_detail_panel(r: dict) -> Panel:
    ev_text = "\n".join(f"  [green]✓[/] {e}" for e in r["evidence"])
    is_text = "\n".join(f"  [yellow]![/] {i}" for i in r["issues"])
    body = Text.assemble(
        (f"{r['phase']}  |  시나리오: {r['scenario']}\n\n", "dim"),
        ("검증 결과\n", "bold"),
        (ev_text + "\n\n"),
        ("이슈\n", "bold"),
        (is_text + "\n"),
    )
    verdict = r["verdict"]
    return Panel(
        body,
        title=f"[bold cyan]{r['lib']}[/]  [{VERDICT_STYLE[verdict]}]{verdict}[/]",
        border_style="cyan",
    )


def build_stack_recommendation() -> Panel:
    body = Group(
        Text("최종 권장 기술 스택\n", style="bold"),
        Text(),
        Text("  Core Stack (필수)", style="bold green"),
        Text("  ├── rich       — 콘솔 UI 렌더링 (Tree / Table / Live)", style="green"),
        Text("  ├── watchdog   — 파일 변경 실시간 감지", style="green"),
        Text("  ├── deepdiff   — JSON 필드 단위 diff 비교", style="green"),
        Text("  └── pydantic   — JSON 스키마 검증 및 타입 안전성", style="green"),
        Text(),
        Text("  Optional Stack (2단계 도입 검토)", style="bold yellow"),
        Text("  └── textual    — 대화형 TUI 필요 시 도입", style="yellow"),
        Text("                   단, API 변경 잦으므로 버전 고정 운용 권장", style="dim"),
        Text(),
        Text("  개발 로드맵", style="bold"),
        Text("  MVP  : rich + watchdog + deepdiff + pydantic 로 CLI 도구 구축"),
        Text("  v2.0 : textual 도입으로 대화형 필터링 / 검색 UI 추가"),
    )
    return Panel(body, title="[bold]Phase 7 -- 기술 스택 선정[/]", border_style="blue", padding=(1, 2))


def build_poc_summary() -> Table:
    t = Table(title="PoC 전체 결과 요약", box=box.SIMPLE_HEAVY)
    t.add_column("Phase", width=9)
    t.add_column("라이브러리", width=12)
    t.add_column("성공 기준", width=35)
    t.add_column("결과", justify="center", width=8)

    rows = [
        ("Phase 2", "rich",     "중첩 JSON Tree/Table 명확 출력",       "PASS"),
        ("Phase 3", "watchdog", "파일 저장 후 1초 이내 이벤트 수신",    "PASS"),
        ("Phase 4", "deepdiff", "변경 필드 색상/기호로 명확히 구분",     "PASS"),
        ("Phase 5", "pydantic", "잘못된 JSON 입력 시 명확한 오류 출력",  "PASS"),
        ("Phase 6", "textual",  "키워드 입력 시 JSON 실시간 필터링",     "PASS"),
    ]
    for phase, lib, criterion, result in rows:
        color = "green" if result == "PASS" else "red"
        t.add_row(phase, f"[cyan]{lib}[/]", criterion, f"[{color}]{result}[/]")
    return t


# ── 메인 실행 ─────────────────────────────────────────────────────────────────

def run():
    console.print(Rule("[bold]Phase 7 -- 통합 평가 및 기술 스택 선정[/]"))
    console.print()

    # 1. 전체 PoC 요약
    console.print(build_poc_summary())
    console.print()

    # 2. 라이브러리 평가표
    console.print(build_score_table())
    console.print()

    # 3. 라이브러리별 상세 패널 (2열 배치)
    console.print(Rule("[bold]라이브러리별 상세 평가[/]"))
    left  = [build_detail_panel(r) for r in RESULTS[:3]]
    right = [build_detail_panel(r) for r in RESULTS[3:]]
    for l, r in zip(left, right):
        console.print(Columns([l, r], equal=True, expand=True))
    if len(left) > len(right):
        console.print(left[-1])
    console.print()

    # 4. 최종 기술 스택 선정
    console.print(build_stack_recommendation())


if __name__ == "__main__":
    run()
