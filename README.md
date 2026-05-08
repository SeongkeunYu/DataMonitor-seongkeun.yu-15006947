# DataMonitor

> JSON 데이터 상태를 콘솔에서 실시간 조회할 수 있는 관리자 도구 개발을 위한 파이썬 라이브러리 PoC

## 개요

운영 중인 시스템의 JSON 데이터를 별도 GUI 없이 터미널에서 빠르게 파악할 수 있는 관리자 도구 개발에 앞서, 핵심 라이브러리들의 적합성을 검증한다.

## 디렉토리 구조

```
DataMonitor/
├── data/
│   └── sample.json          # 공통 테스트 데이터 (depth 3+ 중첩 JSON)
├── poc/
│   ├── 01_rich/             # Phase 2: 콘솔 UI 렌더링
│   ├── 02_textual/          # Phase 6: TUI 프레임워크
│   ├── 03_watchdog/         # Phase 3: 파일 변경 감지
│   ├── 04_deepdiff/         # Phase 4: JSON diff 비교
│   ├── 05_pydantic/         # Phase 5: 스키마 검증
│   └── 07_evaluation/       # Phase 7: 통합 평가 리포트
├── CLAUDE.md
├── PRD.md
├── PLAN.md
├── EVALUATION.md
└── requirements.txt
```

## 환경 설정

Python 3.11 이상 필요

```bash
python -m venv .venv
.venv/Scripts/activate      # Windows
# source .venv/bin/activate  # macOS / Linux

pip install -r requirements.txt
```

## PoC 실행

각 Phase를 독립적으로 실행할 수 있다.

```bash
# Phase 2: rich — 콘솔 UI 렌더링 (Tree / Table / Live)
python poc/01_rich/main.py

# Phase 3: watchdog — 파일 변경 실시간 감지 (20초 자동 데모)
python poc/03_watchdog/main.py

# Phase 4: deepdiff — JSON diff 비교 및 변경 하이라이트 (20초 자동 데모)
python poc/04_deepdiff/main.py

# Phase 5: pydantic — 스키마 검증 (8개 케이스)
python poc/05_pydantic/main.py

# Phase 6: textual — TUI 필터링 (헤드리스 검증)
python poc/02_textual/main.py
# 인터랙티브 TUI 실행
python poc/02_textual/main.py --interactive

# Phase 7: 통합 평가 리포트
python poc/07_evaluation/report.py
```

## 검증 결과 요약

| Phase | 라이브러리 | 성공 기준 | 결과 |
|-------|------------|-----------|------|
| Phase 2 | `rich` | 중첩 JSON Tree/Table 명확 출력 | PASS |
| Phase 3 | `watchdog` | 파일 저장 후 1초 이내 이벤트 수신 | PASS |
| Phase 4 | `deepdiff` | 변경 필드 색상/기호로 명확히 구분 | PASS |
| Phase 5 | `pydantic` | 잘못된 JSON 입력 시 명확한 오류 출력 | PASS |
| Phase 6 | `textual` | 키워드 입력 시 JSON 실시간 필터링 | PASS |

## 최종 기술 스택 선정

| 구분 | 라이브러리 | 역할 | 판정 |
|------|------------|------|------|
| Core | `rich` | 콘솔 UI 렌더링 (Tree / Table / Live) | 채택 |
| Core | `watchdog` | 파일 변경 실시간 감지 | 채택 |
| Core | `deepdiff` | JSON 필드 단위 diff 비교 | 채택 |
| Core | `pydantic` | JSON 스키마 검증 및 타입 안전성 | 채택 |
| Optional | `textual` | 대화형 TUI (필터링 / 검색 UI) | 조건부 채택 |

**개발 로드맵**
- **MVP**: `rich` + `watchdog` + `deepdiff` + `pydantic` 로 CLI 관리자 도구 구축
- **v2.0**: `textual` 도입으로 대화형 UI 추가 (버전 고정 운용 권장)

## 참고 문서

| 문서 | 설명 |
|------|------|
| [PRD.md](PRD.md) | 요구사항 정의 |
| [PLAN.md](PLAN.md) | PoC 실행 계획 |
| [EVALUATION.md](EVALUATION.md) | 라이브러리 평가 결과 및 기술 스택 선정 |
