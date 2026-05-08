# EVALUATION: DataMonitor PoC 평가 결과

## 1. PoC 전체 결과 요약

| Phase   | 라이브러리 | 성공 기준                         | 결과 |
|---------|------------|-----------------------------------|------|
| Phase 2 | `rich`     | 중첩 JSON Tree/Table 명확 출력    | PASS |
| Phase 3 | `watchdog` | 파일 저장 후 1초 이내 이벤트 수신 | PASS |
| Phase 4 | `deepdiff` | 변경 필드 색상/기호로 명확히 구분  | PASS |
| Phase 5 | `pydantic` | 잘못된 JSON 입력 시 명확한 오류 출력 | PASS |
| Phase 6 | `textual`  | 키워드 입력 시 JSON 실시간 필터링 | PASS |

---

## 2. 라이브러리 평가표

| 라이브러리 | 역할           | 렌더링 품질 | 성능    | 학습 비용 | 유지보수성 | 평균 | 판정        |
|------------|----------------|------------|---------|-----------|------------|------|-------------|
| `rich`     | 콘솔 UI 렌더링 | ★★★★★      | ★★★★★  | ★★★★★    | ★★★★★     | 5.0  | **채택**    |
| `watchdog` | 파일 변경 감지 | N/A        | ★★★★★  | ★★★★★    | ★★★★★     | 5.0  | **채택**    |
| `pydantic` | 스키마 검증    | N/A        | ★★★★★  | ★★★★☆    | ★★★★★     | 4.7  | **채택**    |
| `deepdiff` | JSON diff 비교 | N/A        | ★★★★☆  | ★★★★☆    | ★★★★☆     | 4.0  | **채택**    |
| `textual`  | TUI 프레임워크 | ★★★★★      | ★★★★☆  | ★★★☆☆    | ★★★☆☆     | 3.8  | **조건부 채택** |

---

## 3. 라이브러리별 상세 평가

### `rich` — 채택

- **검증 결과**
  - Tree / Table / Panel / Columns 모두 정상 렌더링
  - Live 컴포넌트 4fps 갱신 확인
  - depth 3 이상 중첩 JSON 계층 구조 보존 출력
- **이슈**
  - Windows cp949 터미널: `io.TextIOWrapper` UTF-8 래핑으로 해결

---

### `watchdog` — 채택

- **검증 결과**
  - 파일 저장 후 평균 0.0 ms 이내 이벤트 수신 (6회 측정)
  - Observer + FileSystemEventHandler 패턴 간결
  - rich Live와 연동하여 화면 자동 갱신 확인
- **이슈**
  - 중복 이벤트 100 ms 디바운싱 필요 (직접 구현)

---

### `deepdiff` — 채택

- **검증 결과**
  - 5회 diff 이벤트, 총 48개 필드 변경 정확 감지
  - `values_changed` / `added` / `removed` 유형별 분류
  - rich와 연동해 Before/After 컬러 하이라이트 출력
- **이슈**
  - DeepDiff 경로(`root['key']`) → 내부 경로 변환 로직 직접 구현 필요
  - 대형 JSON에서 성능 검토 필요

---

### `pydantic` — 채택

- **검증 결과**
  - Case 1(정상) PASS, Cases 2~8(비정상) 모두 FAIL 정확 감지
  - 에러 위치·유형·입력값을 명확한 메시지로 출력
  - `field_validator`로 커스텀 ISO 8601 검증 정상 동작
- **이슈**
  - BaseModel + Field 개념 학습 필요 (1~2시간 수준)

---

### `textual` — 조건부 채택

- **검증 결과**
  - Input 위젯 → DataTable 실시간 필터링 (48→12→18→4→48 rows)
  - watchdog `call_from_thread` 연동 정상
  - deepdiff 변경 경로 DataTable Status 컬럼 표시 확인
- **이슈**
  - `pilot.type()` v8에서 제거 — API 변경 잦음 (유지보수 리스크)
  - async 이벤트 루프 + watchdog 스레드 연동 복잡도 존재
  - CSS + 위젯 + async 학습 비용 높음

---

## 4. 최종 기술 스택 선정

### Core Stack (필수)

```
rich       — 콘솔 UI 렌더링 (Tree / Table / Live)
watchdog   — 파일 변경 실시간 감지
deepdiff   — JSON 필드 단위 diff 비교
pydantic   — JSON 스키마 검증 및 타입 안전성
```

### Optional Stack (2단계 도입 검토)

```
textual    — 대화형 TUI 필요 시 도입
             단, API 변경 잦으므로 버전 고정 운용 권장
```

### 개발 로드맵

| 단계 | 구성 | 목표 |
|------|------|------|
| MVP  | `rich` + `watchdog` + `deepdiff` + `pydantic` | 콘솔 기반 CLI 관리자 도구 |
| v2.0 | + `textual` | 대화형 필터링 / 검색 UI 추가 |

---

## 5. 참고 문서

- [CLAUDE.md](CLAUDE.md)
- [PRD.md](PRD.md)
- [PLAN.md](PLAN.md)
- [poc/07_evaluation/report.py](poc/07_evaluation/report.py)
