"""자연어 조회용 고정 SQL. 값은 모두 매개변수로 넣는다. AI가 만든 문자열을 SQL로 실행하지 않는다."""

import checks

SQL_EMPLOYEE_EXISTS = "SELECT 1 FROM employees WHERE emp_id = ?"

SQL_LOGS = """
SELECT log_time, direction FROM terminal_logs
WHERE emp_id = ? AND work_date = ?
ORDER BY log_time, id
"""

SQL_MANUAL_IN_RANGE = """
SELECT work_date, check_in, check_out FROM manual_sheet
WHERE emp_id = ? AND work_date BETWEEN ? AND ?
ORDER BY work_date
"""

SQL_LOG_DATES_IN_RANGE = """
SELECT DISTINCT work_date FROM terminal_logs
WHERE emp_id = ? AND work_date BETWEEN ? AND ?
"""


def employee_exists(conn, emp_id):
    return conn.execute(SQL_EMPLOYEE_EXISTS, (emp_id,)).fetchone() is not None


def logs_for(conn, emp_id, work_date):
    return [{"time": t, "direction": d} for t, d in conn.execute(SQL_LOGS, (emp_id, work_date)).fetchall()]


def issues(conn, date_from, date_to, emp_id=None, issue_type=None):
    rows = checks.find_all(conn, date_from, date_to, emp_id, issue_type)
    for row in rows:
        row["logs"] = logs_for(conn, row["emp_id"], row["work_date"])
    return rows


def employee_records(conn, emp_id, date_from, date_to):
    manual = {d: (i, o) for d, i, o in conn.execute(SQL_MANUAL_IN_RANGE, (emp_id, date_from, date_to)).fetchall()}
    dates = set(manual) | {d for (d,) in conn.execute(SQL_LOG_DATES_IN_RANGE, (emp_id, date_from, date_to)).fetchall()}
    rows = []
    for work_date in sorted(dates):
        check_in, check_out = manual.get(work_date, (None, None))
        rows.append({
            "emp_id": emp_id,
            "work_date": work_date,
            "manual_in": check_in,
            "manual_out": check_out,
            "logs": logs_for(conn, emp_id, work_date),
        })
    return rows


def time_difference(conn, side, min_diff, date_from, date_to, emp_id=None):
    """수기와 단말(출근=첫 기록, 퇴근=마지막 기록)의 차이가 min_diff분 이상. 같은 쪽 미태그인 날은 제외."""
    rows = checks.time_diff_rows(conn, side, min_diff, date_from, date_to, emp_id)
    return [{
        "emp_id": r["emp_id"],
        "work_date": r["work_date"],
        "side": side,
        "terminal_time": r["terminal_time"],
        "manual_time": r["manual_time"],
        "diff_minutes": r["diff"],
        "logs": logs_for(conn, r["emp_id"], r["work_date"]),
    } for r in rows]
