"""심어 둔 정답 12건. 판정 규칙(checks.py)과 독립적으로 사람이 손으로 적은 목록이다.

seed.py는 이 목록대로 이상 기록을 심고, tests/test_checks.py는 checks.py의 결과가
이 목록과 (종류, 직원, 날짜) 기준으로 정확히 같은지 비교한다.
"""

DUPLICATE = "중복 기록"
NO_RECORD = "기록 없음"
MISSING_IN = "출근 미태그"
MISSING_OUT = "퇴근 미태그"
DIFF_IN = "시각 어긋남(출근)"
DIFF_OUT = "시각 어긋남(퇴근)"

ISSUE_TYPES = [DUPLICATE, NO_RECORD, MISSING_IN, MISSING_OUT, DIFF_IN, DIFF_OUT]

# (종류, 직원, 날짜, 심는 방법)
ANSWERS = [
    (DUPLICATE, "E003", "2026-09-03", "출근 IN 기록을 한 번 더 넣음"),
    (DUPLICATE, "E007", "2026-09-10", "퇴근 OUT 기록을 한 번 더 넣음"),
    (NO_RECORD, "E004", "2026-09-04", "그날 단말 기록 전부 뺌"),
    (NO_RECORD, "E008", "2026-09-09", "그날 단말 기록 전부 뺌"),
    (MISSING_IN, "E003", "2026-09-08", "08:00 출근 IN만 뺌"),
    (MISSING_IN, "E008", "2026-09-11", "08:00 출근 IN만 뺌"),
    (MISSING_OUT, "E002", "2026-09-02", "17:00 퇴근 OUT만 뺌"),
    (MISSING_OUT, "E005", "2026-09-07", "17:00 퇴근 OUT만 뺌"),
    (MISSING_OUT, "E009", "2026-09-11", "17:00 퇴근 OUT만 뺌"),
    (DIFF_IN, "E001", "2026-09-01", "출근 IN을 08:40으로"),
    (DIFF_IN, "E010", "2026-09-14", "출근 IN을 07:20으로"),
    (DIFF_OUT, "E006", "2026-09-08", "퇴근 OUT을 16:15로"),
]

# 시각을 바꿔 심는 경우의 정확한 값
PLANTED_TIMES = {
    ("E001", "2026-09-01", "IN"): "08:40",
    ("E010", "2026-09-14", "IN"): "07:20",
    ("E006", "2026-09-08", "OUT"): "16:15",
}
