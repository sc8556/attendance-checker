# 평가 결과 2026-10-05-p3-attempt1

- 결과: **18/24 회차 통과**
- 모델: `qwen3:4b-instruct` (digest `0edcdef34593`), Ollama 0.35.1
- 지시 버전: p3 (지문 `d06ac2972eaf`), 문항 q1 (`b25dbdb14f6b`), 데이터 `2e4ed5d8c9d3`, 코드 `661a1ec`
- 생성 설정: `{"temperature": 0, "seed": 42, "num_ctx": 2048, "num_predict": 300}`
- 실행 환경: 13th Gen Intel(R) Core(TM) i7-1360P, 16 CPU, 메모리 7.5 GiB
- 응답 시간(초, AI 호출 왕복): 최소 7.337 / 중앙 10.182 / 평균 10.249 / 최대 13.973
- 시작 2026-10-05T22:00:22 · 종료 2026-10-05T22:04:28
- 메모: 첫 공식 평가. 지시 p3 고정(개발 질문으로만 조정)

| 회차 | 라운드 | 문항 | 질문 | 상태 | 조건 | 상태 일치 | DB 결과 | 통과 | 시간(초) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 1 | 9월 2일 퇴근 미태그 보여줘 | ok | O | O | O | **PASS** | 9.102 |
| 2 | 1 | 2 | 9월 8일 출근을 안 찍은 기록 보여줘 | ok | O | O | O | **PASS** | 9.257 |
| 3 | 1 | 3 | E002의 9월 2일 기록 보여줘 | ok | O | O | O | **PASS** | 9.523 |
| 4 | 1 | 4 | 9월 1일 출근 시간이 30분 이상 차이 나는 직원 보여줘 | invalid | X | X | X | **FAIL** | 8.809 |
| 5 | 1 | 5 | 퇴근 미태그 보여줘 | ok | O | O | O | **PASS** | 7.337 |
| 6 | 1 | 6 | 늦게 온 직원 보여줘 | clarify | O | O | O | **PASS** | 12.119 |
| 7 | 1 | 7 | 9월 3일 퇴근 미태그 보여줘 | empty | O | O | O | **PASS** | 9.742 |
| 8 | 1 | 8 | 10월 1일 퇴근 미태그 보여줘 | invalid | X | X | O | **FAIL** | 8.861 |
| 9 | 2 | 1 | 9월 2일 퇴근 미태그 보여줘 | ok | O | O | O | **PASS** | 9.81 |
| 10 | 2 | 2 | 9월 8일 출근을 안 찍은 기록 보여줘 | ok | O | O | O | **PASS** | 9.954 |
| 11 | 2 | 3 | E002의 9월 2일 기록 보여줘 | ok | O | O | O | **PASS** | 10.182 |
| 12 | 2 | 4 | 9월 1일 출근 시간이 30분 이상 차이 나는 직원 보여줘 | invalid | X | X | X | **FAIL** | 10.425 |
| 13 | 2 | 5 | 퇴근 미태그 보여줘 | ok | O | O | O | **PASS** | 7.944 |
| 14 | 2 | 6 | 늦게 온 직원 보여줘 | clarify | O | O | O | **PASS** | 12.616 |
| 15 | 2 | 7 | 9월 3일 퇴근 미태그 보여줘 | empty | O | O | O | **PASS** | 11.503 |
| 16 | 2 | 8 | 10월 1일 퇴근 미태그 보여줘 | invalid | X | X | O | **FAIL** | 10.231 |
| 17 | 3 | 1 | 9월 2일 퇴근 미태그 보여줘 | ok | O | O | O | **PASS** | 11.304 |
| 18 | 3 | 2 | 9월 8일 출근을 안 찍은 기록 보여줘 | ok | O | O | O | **PASS** | 11.323 |
| 19 | 3 | 3 | E002의 9월 2일 기록 보여줘 | ok | O | O | O | **PASS** | 11.38 |
| 20 | 3 | 4 | 9월 1일 출근 시간이 30분 이상 차이 나는 직원 보여줘 | invalid | X | X | X | **FAIL** | 10.533 |
| 21 | 3 | 5 | 퇴근 미태그 보여줘 | ok | O | O | O | **PASS** | 8.638 |
| 22 | 3 | 6 | 늦게 온 직원 보여줘 | clarify | O | O | O | **PASS** | 13.973 |
| 23 | 3 | 7 | 9월 3일 퇴근 미태그 보여줘 | empty | O | O | O | **PASS** | 11.248 |
| 24 | 3 | 8 | 10월 1일 퇴근 미태그 보여줘 | invalid | X | X | O | **FAIL** | 10.171 |

## 실패 회차

### 회차 4 (Q4 9월 1일 출근 시간이 30분 이상 차이 나는 직원 보여줘)
- 상태: invalid / 해석 실패 이유: 날짜 두 항목 중 하나만 있음
- 조건 불일치: `{"action": {"expected": "query", "actual": "<없음>"}, "query_type": {"expected": "time_difference", "actual": "<없음>"}, "date_from": {"expected": "2026-09-01", "actual": "<없음>"}, "date_to": {"expected": "2026-09-01", "actual": "<없음>"}, "employee_id": {"expected": null, "actual": "<없음>"}, "issue_type": {"expected": null, "actual": "<없음>"}, "time_side": {"expected": "출근", "actual": "<없음>"}, "min_difference_minutes": {"expected": 30, "actual": "<없음>"}}`
- 원본 응답: `{   "action": "query",   "date_from": "2026-09-01",   "date_to": null,   "employee_id": null,   "issue_type": null,   "min_difference_minutes": 30,   "query_type": "time_difference",   "question": null,   "time_side": "출근" }`

### 회차 8 (Q8 10월 1일 퇴근 미태그 보여줘)
- 상태: invalid / 해석 실패 이유: 날짜 두 항목 중 하나만 있음
- 조건 불일치: `{"action": {"expected": "query", "actual": "<없음>"}, "query_type": {"expected": "issues", "actual": "<없음>"}, "date_from": {"expected": "2026-10-01", "actual": "<없음>"}, "date_to": {"expected": "2026-10-01", "actual": "<없음>"}, "employee_id": {"expected": null, "actual": "<없음>"}, "issue_type": {"expected": "퇴근 미태그", "actual": "<없음>"}, "time_side": {"expected": null, "actual": "<없음>"}, "min_difference_minutes": {"expected": null, "actual": "<없음>"}}`
- 원본 응답: `{   "action": "query",   "date_from": "2026-10-01",   "date_to": null,   "employee_id": null,   "issue_type": "퇴근 미태그",   "min_difference_minutes": null,   "query_type": "issues",   "question": null,   "time_side": null }`

### 회차 12 (Q4 9월 1일 출근 시간이 30분 이상 차이 나는 직원 보여줘)
- 상태: invalid / 해석 실패 이유: 날짜 두 항목 중 하나만 있음
- 조건 불일치: `{"action": {"expected": "query", "actual": "<없음>"}, "query_type": {"expected": "time_difference", "actual": "<없음>"}, "date_from": {"expected": "2026-09-01", "actual": "<없음>"}, "date_to": {"expected": "2026-09-01", "actual": "<없음>"}, "employee_id": {"expected": null, "actual": "<없음>"}, "issue_type": {"expected": null, "actual": "<없음>"}, "time_side": {"expected": "출근", "actual": "<없음>"}, "min_difference_minutes": {"expected": 30, "actual": "<없음>"}}`
- 원본 응답: `{   "action": "query",   "date_from": "2026-09-01",   "date_to": null,   "employee_id": null,   "issue_type": null,   "min_difference_minutes": 30,   "query_type": "time_difference",   "question": null,   "time_side": "출근" }`

### 회차 16 (Q8 10월 1일 퇴근 미태그 보여줘)
- 상태: invalid / 해석 실패 이유: 날짜 두 항목 중 하나만 있음
- 조건 불일치: `{"action": {"expected": "query", "actual": "<없음>"}, "query_type": {"expected": "issues", "actual": "<없음>"}, "date_from": {"expected": "2026-10-01", "actual": "<없음>"}, "date_to": {"expected": "2026-10-01", "actual": "<없음>"}, "employee_id": {"expected": null, "actual": "<없음>"}, "issue_type": {"expected": "퇴근 미태그", "actual": "<없음>"}, "time_side": {"expected": null, "actual": "<없음>"}, "min_difference_minutes": {"expected": null, "actual": "<없음>"}}`
- 원본 응답: `{   "action": "query",   "date_from": "2026-10-01",   "date_to": null,   "employee_id": null,   "issue_type": "퇴근 미태그",   "min_difference_minutes": null,   "query_type": "issues",   "question": null,   "time_side": null }`

### 회차 20 (Q4 9월 1일 출근 시간이 30분 이상 차이 나는 직원 보여줘)
- 상태: invalid / 해석 실패 이유: 날짜 두 항목 중 하나만 있음
- 조건 불일치: `{"action": {"expected": "query", "actual": "<없음>"}, "query_type": {"expected": "time_difference", "actual": "<없음>"}, "date_from": {"expected": "2026-09-01", "actual": "<없음>"}, "date_to": {"expected": "2026-09-01", "actual": "<없음>"}, "employee_id": {"expected": null, "actual": "<없음>"}, "issue_type": {"expected": null, "actual": "<없음>"}, "time_side": {"expected": "출근", "actual": "<없음>"}, "min_difference_minutes": {"expected": 30, "actual": "<없음>"}}`
- 원본 응답: `{   "action": "query",   "date_from": "2026-09-01",   "date_to": null,   "employee_id": null,   "issue_type": null,   "min_difference_minutes": 30,   "query_type": "time_difference",   "question": null,   "time_side": "출근" }`

### 회차 24 (Q8 10월 1일 퇴근 미태그 보여줘)
- 상태: invalid / 해석 실패 이유: 날짜 두 항목 중 하나만 있음
- 조건 불일치: `{"action": {"expected": "query", "actual": "<없음>"}, "query_type": {"expected": "issues", "actual": "<없음>"}, "date_from": {"expected": "2026-10-01", "actual": "<없음>"}, "date_to": {"expected": "2026-10-01", "actual": "<없음>"}, "employee_id": {"expected": null, "actual": "<없음>"}, "issue_type": {"expected": "퇴근 미태그", "actual": "<없음>"}, "time_side": {"expected": null, "actual": "<없음>"}, "min_difference_minutes": {"expected": null, "actual": "<없음>"}}`
- 원본 응답: `{   "action": "query",   "date_from": "2026-10-01",   "date_to": null,   "employee_id": null,   "issue_type": "퇴근 미태그",   "min_difference_minutes": null,   "query_type": "issues",   "question": null,   "time_side": null }`

