# PLAN: DataMonitor PoC 실행 계획

## 1. 개요

PRD에 정의된 5개 라이브러리(`rich`, `textual`, `watchdog`, `deepdiff`, `pydantic`)를 단계별로 PoC하여 최종 기술 스택을 선정한다.

---

## 2. 환경 구성

### 2.1 디렉토리 구조

```
DataMonitor/
├── CLAUDE.md
├── PRD.md
├── PLAN.md
├── requirements.txt
├── data/
│   └── sample.json          # 테스트용 샘플 JSON 데이터
└── poc/
    ├── 01_rich/
    │   └── main.py
    ├── 02_textual/
    │   └── main.py
    ├── 03_watchdog/
    │   └── main.py
    ├── 04_deepdiff/
    │   └── main.py
    └── 05_pydantic/
        └── main.py
```

### 2.2 공통 환경 설정

- Python 3.11+
- 가상환경: `venv`
- 패키지 관리: `requirements.txt`

```
rich
textual
watchdog
deepdiff
pydantic
```

---

## 3. 단계별 실행 계획

### Phase 1 — 샘플 데이터 준비

**목표**: 모든 PoC에서 공통으로 사용할 JSON 데이터 구성

- 중첩 depth 3 이상의 JSON 구조 설계
- 리스트·딕셔너리 혼합 구조 포함
- 변경 감지 테스트를 위한 초기값 설정

---

### Phase 2 — `rich` PoC (콘솔 UI 렌더링)

**목표**: JSON 데이터를 구조화된 형태로 콘솔에 출력

| 항목 | 내용 |
|------|------|
| 검증 기능 | 테이블 렌더링, 트리 구조 출력, 색상 강조 |
| 시나리오 | 시나리오 1 (기본 출력) |
| 성공 기준 | 중첩 JSON을 트리/테이블로 명확히 출력 |

**구현 항목**
- `Table`으로 flat JSON 출력
- `Tree`로 중첩 JSON 계층 출력
- `Console`의 `Live` 컴포넌트로 주기적 화면 갱신 테스트

---

### Phase 3 — `watchdog` PoC (파일 변경 감지)

**목표**: JSON 파일 수정 시 이벤트를 수신하여 화면 갱신 트리거

| 항목 | 내용 |
|------|------|
| 검증 기능 | 파일 시스템 이벤트 감지, 콜백 실행 |
| 시나리오 | 시나리오 2 (실시간 갱신) |
| 성공 기준 | 파일 저장 후 1초 이내 갱신 이벤트 수신 |

**구현 항목**
- `Observer` + `FileSystemEventHandler` 설정
- `on_modified` 이벤트에서 JSON 리로드 및 출력 갱신
- `rich`와 연동하여 화면 자동 갱신

---

### Phase 4 — `deepdiff` PoC (변경 감지 및 하이라이트)

**목표**: JSON 이전/이후 상태를 비교하여 변경 필드를 식별

| 항목 | 내용 |
|------|------|
| 검증 기능 | 딕셔너리 diff, 추가/삭제/수정 분류 |
| 시나리오 | 시나리오 3 (변경 감지) |
| 성공 기준 | 변경된 키/값을 색상 또는 기호로 명확히 구분 출력 |

**구현 항목**
- `DeepDiff`로 before/after JSON 비교
- 변경 유형별(`added`, `removed`, `changed`) 분류
- `rich`와 연동하여 변경 항목 컬러 하이라이트 출력

---

### Phase 5 — `pydantic` PoC (스키마 검증)

**목표**: JSON 데이터의 구조와 타입을 스키마 기반으로 검증

| 항목 | 내용 |
|------|------|
| 검증 기능 | 타입 검증, 필수 필드 확인, 오류 메시지 출력 |
| 시나리오 | 시나리오 4 (스키마 검증) |
| 성공 기준 | 잘못된 JSON 입력 시 명확한 오류 메시지 출력 |

**구현 항목**
- `BaseModel`로 JSON 스키마 정의
- 정상/비정상 JSON 데이터 각각 검증
- `ValidationError` 메시지를 `rich`로 포맷해 출력

---

### Phase 6 — `textual` PoC (TUI 프레임워크)

**목표**: 위젯 기반 대화형 TUI로 필터/검색 기능 구현

| 항목 | 내용 |
|------|------|
| 검증 기능 | 위젯 레이아웃, 키 입력 처리, 동적 필터링 |
| 시나리오 | 시나리오 5 (필터링) |
| 성공 기준 | 키워드 입력 시 JSON 항목이 실시간 필터링 |

**구현 항목**
- `Input` 위젯으로 검색어 입력
- `DataTable` 위젯으로 필터링된 결과 출력
- `watchdog` + `deepdiff`와 연동하여 통합 시나리오 검증

---

### Phase 7 — 통합 평가 및 기술 스택 선정

**목표**: 각 라이브러리의 결과를 종합해 최종 기술 스택 결정

**평가 항목**

| 라이브러리 | 렌더링 품질 | 성능 | 학습 비용 | 유지보수성 | 종합 |
|------------|------------|------|-----------|------------|------|
| `rich` | | | | | |
| `textual` | | | | | |
| `watchdog` | | | | | |
| `deepdiff` | | | | | |
| `pydantic` | | | | | |

**산출물**
- 라이브러리별 샘플 코드
- 평가표 작성
- 최종 기술 스택 선정 결과 문서화

---

## 4. 일정

| Phase | 내용 | 비고 |
|-------|------|------|
| Phase 1 | 환경 구성 + 샘플 데이터 준비 | |
| Phase 2 | `rich` PoC | |
| Phase 3 | `watchdog` PoC | |
| Phase 4 | `deepdiff` PoC | |
| Phase 5 | `pydantic` PoC | |
| Phase 6 | `textual` PoC | |
| Phase 7 | 통합 평가 및 기술 스택 선정 | |

---

## 5. 참고 문서

- [CLAUDE.md](CLAUDE.md)
- [PRD.md](PRD.md)
