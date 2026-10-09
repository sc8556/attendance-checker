"""정답 12건 검증: 누락 0 · 오탐 0 · 결과 중복 0. 건수만으로 통과시키지 않는다."""

from collections import Counter

import pytest

import checks
from answers import ANSWERS, ISSUE_TYPES


def test_row_counts(conn):
    count = lambda sql: conn.execute(sql).fetchone()[0]
    # 10명(정답 12건 포함) + 정상 기록만 있는 E011(홀수, 하루 4번)·E012(짝수, 하루 6번)
    assert count("SELECT COUNT(*) FROM employees") == 12
    assert count("SELECT COUNT(*) FROM manual_sheet") == 120
    assert count("SELECT COUNT(*) FROM terminal_logs") == 585
    assert count("SELECT COUNT(*) FROM terminal_logs WHERE direction = 'IN'") == 293
    assert count("SELECT COUNT(*) FROM terminal_logs WHERE direction = 'OUT'") == 292


def test_time_format_is_two_digit(conn):
    bad = conn.execute(
        "SELECT COUNT(*) FROM terminal_logs WHERE log_time NOT GLOB '[0-2][0-9]:[0-5][0-9]'"
    ).fetchone()[0]
    assert bad == 0


def keys(results):
    return [(r["issue_type"], r["emp_id"], r["work_date"]) for r in results]


def test_find_all_matches_answers_exactly(conn):
    found = keys(checks.find_all(conn))
    expected = [(t, e, d) for t, e, d, _ in ANSWERS]
    assert [k for k, n in Counter(found).items() if n > 1] == [], "결과 중복"
    assert sorted(set(expected) - set(found)) == [], "누락"
    assert sorted(set(found) - set(expected)) == [], "오탐"


@pytest.mark.parametrize("issue_type", ISSUE_TYPES)
def test_each_rule_matches_answers(conn, issue_type):
    found = sorted(keys(checks.RULES[issue_type](conn)))
    expected = sorted((t, e, d) for t, e, d, _ in ANSWERS if t == issue_type)
    assert found == expected


def test_filters_by_date_and_employee(conn):
    rows = checks.find_all(conn, date_from="2026-09-02", date_to="2026-09-02")
    assert keys(rows) == [("퇴근 미태그", "E002", "2026-09-02")]
    rows = checks.find_all(conn, emp_id="E008")
    assert sorted(keys(rows)) == [("기록 없음", "E008", "2026-09-09"), ("출근 미태그", "E008", "2026-09-11")]


def test_details_use_real_times(conn):
    by_key = {(r["issue_type"], r["emp_id"], r["work_date"]): r for r in checks.find_all(conn)}
    assert by_key[("시각 어긋남(출근)", "E001", "2026-09-01")]["detail"] == "단말 08:40 / 수기 08:00 (40분)"
    assert by_key[("시각 어긋남(퇴근)", "E006", "2026-09-08")]["detail"] == "단말 16:15 / 수기 17:00 (45분)"
    assert by_key[("기록 없음", "E004", "2026-09-04")]["detail"] == "수기 08:00~17:00, 단말 기록 0건"


def test_seeded_e002_0902_logs(conn):
    """평가 문항 ③의 기대값. jitter 공식으로 손으로 계산한 값과 seed 결과를 대조한다."""
    rows = conn.execute(
        "SELECT log_time, direction FROM terminal_logs WHERE emp_id='E002' AND work_date='2026-09-02' ORDER BY log_time"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        ("08:02", "IN"), ("11:58", "OUT"), ("13:01", "IN"), ("15:00", "OUT"), ("15:13", "IN"),
    ]


def test_seed_is_deterministic():
    import sqlite3
    import seed

    dumps = []
    for _ in range(2):
        c = sqlite3.connect(":memory:")
        seed.build(c)
        dumps.append(list(c.iterdump()))
        c.close()
    assert dumps[0] == dumps[1]
