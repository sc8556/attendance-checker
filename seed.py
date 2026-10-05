"""가짜 근태 데이터 생성. 실행할 때마다 DB를 지우고 새로 만든다.

정상 데이터는 규칙적으로 만들고(흔들림 ±3분, 매번 같은 결과), answers.py의 정답 12건을 심는다.
실제 회사 데이터는 쓰지 않는다.
"""

import os
import sqlite3

from answers import PLANTED_TIMES

DB_PATH = os.environ.get("ATTENDANCE_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "attendance.db"))

DEMO_START = "2026-09-01"
DEMO_END = "2026-09-14"
WORK_DATES = [
    "2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-07",
    "2026-09-08", "2026-09-09", "2026-09-10", "2026-09-11", "2026-09-14",
]
EMPLOYEES = [(f"E{n:03d}", f"직원{n:02d}") for n in range(1, 11)]

MANUAL_IN = "08:00"
MANUAL_OUT = "17:00"

# (슬롯 번호, 기준 시각, 방향). 슬롯 4·5는 짝수 직원만(흡연·화장실)
BASE_SLOTS = [(0, "08:00", "IN"), (1, "12:00", "OUT"), (2, "13:00", "IN"), (3, "17:00", "OUT")]
EVEN_SLOTS = [(4, "15:00", "OUT"), (5, "15:10", "IN")]
CHECK_IN_SLOT = 0
CHECK_OUT_SLOT = 3

SCHEMA = """
CREATE TABLE employees (
    emp_id TEXT PRIMARY KEY,
    name   TEXT NOT NULL
);
CREATE TABLE terminal_logs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_id    TEXT NOT NULL REFERENCES employees(emp_id),
    work_date TEXT NOT NULL,
    log_time  TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('IN', 'OUT'))
);
CREATE TABLE manual_sheet (
    emp_id    TEXT NOT NULL REFERENCES employees(emp_id),
    work_date TEXT NOT NULL,
    check_in  TEXT NOT NULL,
    check_out TEXT NOT NULL,
    PRIMARY KEY (emp_id, work_date)
);
CREATE INDEX idx_logs_emp_date ON terminal_logs(emp_id, work_date);
"""


def jitter(emp_no, day_idx, slot):
    """-3~+3분. 같은 입력이면 항상 같은 값."""
    return (emp_no * 7 + day_idx * 5 + slot * 3) % 7 - 3


def shift(hhmm, minutes):
    h, m = map(int, hhmm.split(":"))
    total = h * 60 + m + minutes
    return f"{total // 60:02d}:{total % 60:02d}"


def normal_logs(emp_no, day_idx):
    slots = BASE_SLOTS + (EVEN_SLOTS if emp_no % 2 == 0 else [])
    return [(slot, shift(base, jitter(emp_no, day_idx, slot)), direction) for slot, base, direction in slots]


def build(conn):
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO employees VALUES (?, ?)", EMPLOYEES)

    rows = []
    for day_idx, work_date in enumerate(WORK_DATES):
        for emp_no in range(1, 11):
            emp_id = f"E{emp_no:03d}"
            conn.execute("INSERT INTO manual_sheet VALUES (?, ?, ?, ?)", (emp_id, work_date, MANUAL_IN, MANUAL_OUT))
            for slot, log_time, direction in normal_logs(emp_no, day_idx):
                rows.append([emp_id, work_date, log_time, direction, slot])

    def find(emp_id, work_date, slot):
        return next(r for r in rows if r[0] == emp_id and r[1] == work_date and r[4] == slot)

    # 시각 어긋남: 정확한 시각으로 바꿈
    for (emp_id, work_date, direction), planted in PLANTED_TIMES.items():
        slot = CHECK_IN_SLOT if direction == "IN" else CHECK_OUT_SLOT
        find(emp_id, work_date, slot)[2] = planted

    # 기록 없음: 그날 단말 기록 전부 뺌
    for emp_id, work_date in [("E004", "2026-09-04"), ("E008", "2026-09-09")]:
        rows = [r for r in rows if not (r[0] == emp_id and r[1] == work_date)]

    # 출근 미태그 / 퇴근 미태그: 해당 기록 하나만 뺌
    removals = [("E003", "2026-09-08", CHECK_IN_SLOT), ("E008", "2026-09-11", CHECK_IN_SLOT),
                ("E002", "2026-09-02", CHECK_OUT_SLOT), ("E005", "2026-09-07", CHECK_OUT_SLOT),
                ("E009", "2026-09-11", CHECK_OUT_SLOT)]
    for emp_id, work_date, slot in removals:
        rows.remove(find(emp_id, work_date, slot))

    # 중복 기록: 같은 기록을 한 번 더 넣음
    for emp_id, work_date, slot in [("E003", "2026-09-03", CHECK_IN_SLOT), ("E007", "2026-09-10", CHECK_OUT_SLOT)]:
        rows.append(list(find(emp_id, work_date, slot)))

    rows.sort(key=lambda r: (r[1], r[0], r[2]))
    conn.executemany(
        "INSERT INTO terminal_logs (emp_id, work_date, log_time, direction) VALUES (?, ?, ?, ?)",
        [r[:4] for r in rows],
    )
    conn.commit()


def main(db_path=None):
    db_path = db_path or DB_PATH
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    try:
        build(conn)
        for table in ("employees", "manual_sheet", "terminal_logs"):
            print(table, conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    finally:
        conn.close()


if __name__ == "__main__":
    main()
