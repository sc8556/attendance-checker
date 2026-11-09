"""MCP 도구를 전송 계층 없이 직접 불러 정답 12건과 비교한다. 조건 검사 실패도 0건이 아닌 상태로 돌아와야 한다."""

import asyncio
import json
import sqlite3
from collections import Counter

import pytest

import mcp_server
import seed
from answers import ANSWERS, ISSUE_TYPES


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    """테스트마다 새 파일 DB. 도구가 connect()로 직접 만들고 읽기 전용으로 연다."""
    monkeypatch.setattr(seed, "DB_PATH", str(tmp_path / "test.db"))


def keys(rows):
    return [(r["issue_type"], r["emp_id"], r["work_date"]) for r in rows]


def test_tools_are_read_only_and_few():
    tools = asyncio.run(mcp_server.server.list_tools())
    assert sorted(t.name for t in tools) == ["data_range", "employee_records", "find_issues", "time_difference"]
    assert all(t.annotations.read_only_hint for t in tools)
    assert all(t.description and "YYYY-MM-DD" in t.description for t in tools)


def test_db_opens_read_only_and_seed_output_stays_off_stdout(capfd):
    conn = mcp_server.connect()  # DB가 없으니 여기서 만든다
    try:
        assert conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 12
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("DELETE FROM terminal_logs")
    finally:
        conn.close()
    assert capfd.readouterr().out == ""  # stdout은 MCP 통신용이라 seed 출력이 섞이면 안 된다


def test_data_range():
    r = mcp_server.data_range()
    assert (r["date_from"], r["date_to"]) == ("2026-09-01", "2026-09-14")
    assert [e["emp_id"] for e in r["employees"]] == [e for e, _ in seed.EMPLOYEES]
    assert r["issue_types"] == ISSUE_TYPES and r["time_sides"] == ["출근", "퇴근"]
    json.dumps(r, ensure_ascii=False)


def test_find_issues_matches_answers_exactly():
    r = mcp_server.find_issues()
    assert r["status"] == "ok" and r["total"] == 12
    found = keys(r["rows"])
    expected = [(t, e, d) for t, e, d, _ in ANSWERS]
    assert [k for k, n in Counter(found).items() if n > 1] == [], "결과 중복"
    assert sorted(set(expected) - set(found)) == [], "누락"
    assert sorted(set(found) - set(expected)) == [], "오탐"
    json.dumps(r, ensure_ascii=False)


@pytest.mark.parametrize("issue_type", ISSUE_TYPES)
def test_each_issue_type_matches_answers(issue_type):
    r = mcp_server.find_issues(issue_type=issue_type)
    expected = sorted((t, e, d) for t, e, d, _ in ANSWERS if t == issue_type)
    assert sorted(keys(r["rows"])) == expected


def test_find_issues_one_day():
    """시연 질문 '9월 2일 퇴근 미태그 보여줘'에 해당하는 호출."""
    r = mcp_server.find_issues("2026-09-02", "2026-09-02", issue_type="퇴근 미태그")
    assert r["status"] == "ok"
    assert keys(r["rows"]) == [("퇴근 미태그", "E002", "2026-09-02")]
    assert [l["time"] for l in r["rows"][0]["logs"]] == ["08:02", "11:58", "13:01", "15:00", "15:13"]


def test_find_issues_by_employee():
    r = mcp_server.find_issues(emp_id="E008")
    assert sorted(keys(r["rows"])) == [("기록 없음", "E008", "2026-09-09"), ("출근 미태그", "E008", "2026-09-11")]


def test_empty_is_not_error():
    r = mcp_server.find_issues("2026-09-03", "2026-09-03", issue_type="퇴근 미태그")
    assert r["status"] == "empty" and r["rows"] == [] and r["invalid_reason"] is None


def test_employee_records():
    r = mcp_server.employee_records("E002", "2026-09-02", "2026-09-02")
    assert r["status"] == "ok" and r["total"] == 1
    row = r["rows"][0]
    assert (row["manual_in"], row["manual_out"]) == ("08:00", "17:00")
    assert [(l["time"], l["direction"]) for l in row["logs"]] == [
        ("08:02", "IN"), ("11:58", "OUT"), ("13:01", "IN"), ("15:00", "OUT"), ("15:13", "IN")]
    # 날짜를 생략하면 근무일 10일 전부
    assert mcp_server.employee_records("E002")["total"] == 10


def test_time_difference():
    r = mcp_server.time_difference("출근", 30, "2026-09-01", "2026-09-01")
    assert r["status"] == "ok"
    assert [(x["emp_id"], x["terminal_time"], x["manual_time"], x["diff_minutes"]) for x in r["rows"]] == [
        ("E001", "08:40", "08:00", 40)]
    # E003 9/8은 출근 미태그라 출근 시각 차이에는 나오지 않는다
    assert mcp_server.time_difference("출근", 10, "2026-09-08", "2026-09-08")["status"] == "empty"


def test_out_of_range_is_not_zero_results():
    r = mcp_server.find_issues("2026-10-01", "2026-10-01", issue_type="퇴근 미태그")
    assert r["status"] == "out_of_range" and r["rows"] == []
    assert "2026-09-01 ~ 2026-09-14" in r["message"]


def test_partial_range_is_clipped():
    r = mcp_server.find_issues("2026-08-25", "2026-09-30", issue_type="퇴근 미태그")
    assert r["status"] == "ok"
    assert (r["applied"]["date_from"], r["applied"]["date_to"]) == ("2026-09-01", "2026-09-14")
    assert [x["emp_id"] for x in r["rows"]] == ["E002", "E005", "E009"]


def test_unknown_employee():
    r = mcp_server.employee_records("E099", "2026-09-02", "2026-09-02")
    assert r["status"] == "unknown_employee" and r["rows"] == []
    assert "E001~E012" in r["message"]


@pytest.mark.parametrize("call, reason", [
    (lambda: mcp_server.find_issues(date_from="2026-09-02"), "하나만"),
    (lambda: mcp_server.find_issues("2026-02-30", "2026-02-30"), "실제 날짜"),
    (lambda: mcp_server.find_issues("2026-09-05", "2026-09-02"), "늦음"),
    (lambda: mcp_server.find_issues("2026/09/02", "2026/09/02"), "형식"),
    (lambda: mcp_server.find_issues(issue_type="퇴근"), "issue_type"),
    (lambda: mcp_server.employee_records("E001' OR '1'='1"), "형식"),
    (lambda: mcp_server.time_difference("아침", 10), "time_side"),
    (lambda: mcp_server.time_difference("출근", 0), "min_difference"),
])
def test_invalid_conditions_do_not_query(call, reason, monkeypatch):
    monkeypatch.setattr(mcp_server.nl_query, "run_query", lambda *a: pytest.fail("조회하면 안 됨"))
    r = call()
    assert r["status"] == "invalid" and r["rows"] == []
    assert reason in r["invalid_reason"]


def test_rows_are_capped(monkeypatch):
    monkeypatch.setattr(mcp_server, "MAX_ROWS", 3)
    r = mcp_server.time_difference("출근", 1)
    assert r["total"] > 3 and len(r["rows"]) == 3
