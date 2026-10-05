"""이상 기록을 찾는 SQL 규칙. 모든 함수는 DB 연결을 받아서 쓰고, 값은 매개변수로만 넣는다.

출근 = 그날 첫 기록, 퇴근 = 그날 마지막 기록 (IN이든 OUT이든).
시각 어긋남은 같은 쪽 미태그인 날을 제외해 같은 문제를 두 번 세지 않는다.
"""

import sqlite3

from answers import DIFF_IN, DIFF_OUT, DUPLICATE, ISSUE_TYPES, MISSING_IN, MISSING_OUT, NO_RECORD
from seed import DEMO_END, DEMO_START

TIME_DIFF_MINUTES = 10

FILTER = "work_date BETWEEN :date_from AND :date_to AND (:emp_id IS NULL OR emp_id = :emp_id)"


def minutes(col):
    return f"(CAST(substr({col}, 1, 2) AS INTEGER) * 60 + CAST(substr({col}, 4, 2) AS INTEGER))"


# 직원·날짜별 첫/마지막 기록과 그 방향, 수기 시각
DAY_CTE = f"""
WITH bounds AS (
    SELECT emp_id, work_date, MIN(log_time) AS first_time, MAX(log_time) AS last_time
    FROM terminal_logs
    WHERE {FILTER}
    GROUP BY emp_id, work_date
), day AS (
    SELECT b.emp_id, b.work_date, b.first_time, b.last_time,
           (SELECT t.direction FROM terminal_logs t
             WHERE t.emp_id = b.emp_id AND t.work_date = b.work_date AND t.log_time = b.first_time
             ORDER BY t.id LIMIT 1) AS first_dir,
           (SELECT t.direction FROM terminal_logs t
             WHERE t.emp_id = b.emp_id AND t.work_date = b.work_date AND t.log_time = b.last_time
             ORDER BY t.id DESC LIMIT 1) AS last_dir,
           m.check_in, m.check_out
    FROM bounds b
    LEFT JOIN manual_sheet m ON m.emp_id = b.emp_id AND m.work_date = b.work_date
)
"""

SQL_DUPLICATE = f"""
SELECT emp_id, work_date, log_time, direction, COUNT(*) AS cnt
FROM terminal_logs
WHERE {FILTER}
GROUP BY emp_id, work_date, log_time, direction
HAVING COUNT(*) >= 2
ORDER BY work_date, emp_id
"""

SQL_NO_RECORD = f"""
SELECT m.emp_id, m.work_date, m.check_in, m.check_out
FROM manual_sheet m
WHERE m.work_date BETWEEN :date_from AND :date_to AND (:emp_id IS NULL OR m.emp_id = :emp_id)
  AND NOT EXISTS (SELECT 1 FROM terminal_logs t WHERE t.emp_id = m.emp_id AND t.work_date = m.work_date)
ORDER BY m.work_date, m.emp_id
"""

SQL_MISSING_IN = DAY_CTE + """
SELECT emp_id, work_date, first_time, check_in FROM day WHERE first_dir = 'OUT' ORDER BY work_date, emp_id
"""

SQL_MISSING_OUT = DAY_CTE + """
SELECT emp_id, work_date, last_time, check_out FROM day WHERE last_dir = 'IN' ORDER BY work_date, emp_id
"""

# 시간 차이: 같은 쪽 미태그인 날 제외. queries.py의 시간 차이 조회도 이 SQL을 쓴다.
SQL_DIFF_IN = DAY_CTE + f"""
SELECT emp_id, work_date, first_time AS terminal_time, check_in AS manual_time,
       ABS({minutes('first_time')} - {minutes('check_in')}) AS diff
FROM day
WHERE first_dir = 'IN' AND check_in IS NOT NULL
  AND ABS({minutes('first_time')} - {minutes('check_in')}) >= :min_diff
ORDER BY work_date, emp_id
"""

SQL_DIFF_OUT = DAY_CTE + f"""
SELECT emp_id, work_date, last_time AS terminal_time, check_out AS manual_time,
       ABS({minutes('last_time')} - {minutes('check_out')}) AS diff
FROM day
WHERE last_dir = 'OUT' AND check_out IS NOT NULL
  AND ABS({minutes('last_time')} - {minutes('check_out')}) >= :min_diff
ORDER BY work_date, emp_id
"""


def query(conn, sql, values):
    cur = conn.cursor()
    cur.row_factory = sqlite3.Row
    return cur.execute(sql, values).fetchall()


def params(date_from, date_to, emp_id, **extra):
    return {"date_from": date_from or DEMO_START, "date_to": date_to or DEMO_END, "emp_id": emp_id, **extra}


def hm(total):
    h, m = divmod(abs(total), 60)
    return f"{h}시간 {m}분" if h else f"{m}분"


def to_min(hhmm):
    h, m = map(int, hhmm.split(":"))
    return h * 60 + m


def issue(issue_type, row, detail):
    return {"issue_type": issue_type, "emp_id": row["emp_id"], "work_date": row["work_date"], "detail": detail}


def find_duplicates(conn, date_from=None, date_to=None, emp_id=None):
    rows = query(conn, SQL_DUPLICATE, params(date_from, date_to, emp_id))
    return [issue(DUPLICATE, r, f"{r['direction']} {r['log_time']} 이 {r['cnt']}번") for r in rows]


def find_no_records(conn, date_from=None, date_to=None, emp_id=None):
    rows = query(conn, SQL_NO_RECORD, params(date_from, date_to, emp_id))
    return [issue(NO_RECORD, r, f"수기 {r['check_in']}~{r['check_out']}, 단말 기록 0건") for r in rows]


def find_missing_in(conn, date_from=None, date_to=None, emp_id=None):
    rows = query(conn, SQL_MISSING_IN, params(date_from, date_to, emp_id))
    return [
        issue(MISSING_IN, r, f"출근 등록 {r['first_time']}(첫 기록) / 수기 {r['check_in']} → "
                             f"{hm(to_min(r['first_time']) - to_min(r['check_in']))} 늦게 잡힘")
        for r in rows
    ]


def find_missing_out(conn, date_from=None, date_to=None, emp_id=None):
    rows = query(conn, SQL_MISSING_OUT, params(date_from, date_to, emp_id))
    return [
        issue(MISSING_OUT, r, f"퇴근 등록 {r['last_time']}(마지막 기록) / 수기 {r['check_out']} → "
                              f"{hm(to_min(r['check_out']) - to_min(r['last_time']))} 짧게 잡힘")
        for r in rows
    ]


def time_diff_rows(conn, side, min_diff, date_from=None, date_to=None, emp_id=None):
    sql = SQL_DIFF_IN if side == "출근" else SQL_DIFF_OUT
    return query(conn, sql, params(date_from, date_to, emp_id, min_diff=min_diff))


def diff_detail(r):
    return f"단말 {r['terminal_time']} / 수기 {r['manual_time']} ({r['diff']}분)"


def find_diff_in(conn, date_from=None, date_to=None, emp_id=None):
    rows = time_diff_rows(conn, "출근", TIME_DIFF_MINUTES, date_from, date_to, emp_id)
    return [issue(DIFF_IN, r, diff_detail(r)) for r in rows]


def find_diff_out(conn, date_from=None, date_to=None, emp_id=None):
    rows = time_diff_rows(conn, "퇴근", TIME_DIFF_MINUTES, date_from, date_to, emp_id)
    return [issue(DIFF_OUT, r, diff_detail(r)) for r in rows]


RULES = {
    DUPLICATE: find_duplicates,
    NO_RECORD: find_no_records,
    MISSING_IN: find_missing_in,
    MISSING_OUT: find_missing_out,
    DIFF_IN: find_diff_in,
    DIFF_OUT: find_diff_out,
}
assert list(RULES) == ISSUE_TYPES


def find_all(conn, date_from=None, date_to=None, emp_id=None, issue_type=None):
    types = [issue_type] if issue_type else ISSUE_TYPES
    results = []
    for t in types:
        results.extend(RULES[t](conn, date_from, date_to, emp_id))
    return results
