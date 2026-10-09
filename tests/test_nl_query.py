"""AI 없이 앱의 검증·처리 규칙을 확인한다. AI 응답은 가짜 extractor로 넣는다."""

import json
import sqlite3

import pytest

import ai
import nl_query


def fake(**fields):
    base = dict.fromkeys(ai.FIELDS)
    base.update(fields)
    raw = json.dumps(base, ensure_ascii=False)
    return lambda q: {"raw": raw, "elapsed_seconds": 0.0}


def ask(conn, **fields):
    return nl_query.ask("질문", conn, extractor=fake(**fields))


def test_issue_query_one_day(conn):
    r = ask(conn, action="query", query_type="issues", date_from="2026-09-02", date_to="2026-09-02", issue_type="퇴근 미태그")
    assert r["status"] == "ok"
    assert [(x["emp_id"], x["work_date"]) for x in r["rows"]] == [("E002", "2026-09-02")]
    assert [l["time"] for l in r["rows"][0]["logs"]] == ["08:02", "11:58", "13:01", "15:00", "15:13"]


def test_omitted_date_applies_full_period(conn):
    r = ask(conn, action="query", query_type="issues", issue_type="퇴근 미태그")
    assert r["status"] == "ok"
    assert (r["applied"]["date_from"], r["applied"]["date_to"]) == ("2026-09-01", "2026-09-14")
    assert r["applied"]["date_note"] == "날짜 생략 → 전체 데모 기간"
    assert [x["emp_id"] for x in r["rows"]] == ["E002", "E005", "E009"]


def test_empty_result_is_not_error(conn):
    r = ask(conn, action="query", query_type="issues", date_from="2026-09-03", date_to="2026-09-03", issue_type="퇴근 미태그")
    assert r["status"] == "empty" and r["rows"] == []


def test_out_of_range(conn):
    r = ask(conn, action="query", query_type="issues", date_from="2026-10-01", date_to="2026-10-01", issue_type="퇴근 미태그")
    assert r["status"] == "out_of_range"
    assert "2026-09-01 ~ 2026-09-14" in r["message"]


def test_employee_records(conn):
    r = ask(conn, action="query", query_type="employee_records", date_from="2026-09-02", date_to="2026-09-02", employee_id="E002")
    assert r["status"] == "ok"
    row = r["rows"][0]
    assert (row["manual_in"], row["manual_out"]) == ("08:00", "17:00")
    assert [(l["time"], l["direction"]) for l in row["logs"]] == [
        ("08:02", "IN"), ("11:58", "OUT"), ("13:01", "IN"), ("15:00", "OUT"), ("15:13", "IN")]


def test_time_difference(conn):
    r = ask(conn, action="query", query_type="time_difference", date_from="2026-09-01", date_to="2026-09-01",
            time_side="출근", min_difference_minutes=30)
    assert r["status"] == "ok"
    assert [(x["emp_id"], x["terminal_time"], x["manual_time"], x["diff_minutes"]) for x in r["rows"]] == [
        ("E001", "08:40", "08:00", 40)]


def test_time_difference_excludes_missing_tag_day(conn):
    # E003 9/8은 출근 미태그(첫 기록 12시대 OUT)라 출근 시각 차이 조회에 나오지 않는다
    r = ask(conn, action="query", query_type="time_difference", date_from="2026-09-08", date_to="2026-09-08",
            time_side="출근", min_difference_minutes=10)
    assert r["status"] == "empty"


@pytest.mark.parametrize("action", ["clarify", "unsupported"])
def test_clarify_and_unsupported_do_not_query(conn, action, monkeypatch):
    monkeypatch.setattr(nl_query, "run_query", lambda *a: pytest.fail("조회하면 안 됨"))
    r = ask(conn, action=action, question="어떤 뜻인가요?")
    assert r["status"] == action and r["rows"] == []


def test_unknown_employee(conn):
    r = ask(conn, action="query", query_type="employee_records", date_from="2026-09-02", date_to="2026-09-02", employee_id="E099")
    assert r["status"] == "unknown_employee"
    assert "E001~E012" in r["message"]  # 안내하는 직원 범위는 실제 직원 목록을 따른다
    # 새로 추가한 직원은 있는 직원으로 조회된다
    r = ask(conn, action="query", query_type="employee_records", date_from="2026-09-02", date_to="2026-09-02", employee_id="E012")
    assert r["status"] == "ok"


@pytest.mark.parametrize("fields, reason", [
    (dict(action="query", query_type="issues", date_from="2026-09-02", date_to=None), "하나만"),
    (dict(action="query", query_type="issues", date_from="2026-02-30", date_to="2026-02-30"), "실제 날짜"),
    (dict(action="query", query_type="issues", date_from="2026-09-05", date_to="2026-09-02"), "늦음"),
    (dict(action="query", query_type="issues", issue_type="퇴근"), "issue_type"),
    (dict(action="query", query_type="issues", time_side="퇴근", issue_type="퇴근 미태그"), "섞임"),
    (dict(action="query", query_type="employee_records"), "직원 번호"),
    (dict(action="query", query_type="time_difference", time_side="출근"), "분 조건"),
    (dict(action="query", query_type="employee_records", employee_id="E001' OR '1'='1"), "형식"),
    (dict(action="query", query_type=None), "query_type"),
    (dict(action="clarify", question=""), "비어"),
    (dict(action="query", query_type="time_difference", time_side="출근", min_difference_minutes=True), "min_difference"),
])
def test_invalid_responses_are_not_zero_results(conn, fields, reason, monkeypatch):
    monkeypatch.setattr(nl_query, "run_query", lambda *a: pytest.fail("조회하면 안 됨"))
    r = ask(conn, **fields)
    assert r["status"] == "invalid"
    assert reason in r["invalid_reason"]


def test_missing_field_and_non_json(conn):
    r = nl_query.ask("q", conn, extractor=lambda q: {"raw": '{"action": "query"}'})
    assert r["status"] == "invalid" and "누락" in r["invalid_reason"]
    r = nl_query.ask("q", conn, extractor=lambda q: {"raw": "SELECT * FROM employees"})
    assert r["status"] == "invalid"


def test_ai_server_down(conn):
    def down(q):
        raise ai.AIError("connection refused")
    r = nl_query.ask("q", conn, extractor=down)
    assert r["status"] == "ai_error" and r["rows"] == []


def test_ai_server_down_real_client(conn):
    """실제 클라이언트가 닫힌 포트에 연결 실패를 AIError로 바꾸는지."""
    r = nl_query.ask("q", conn, extractor=lambda q: ai.extract(q, url="http://127.0.0.1:9"))
    assert r["status"] == "ai_error"


def test_db_error(conn):
    broken = sqlite3.connect(":memory:")  # 표가 없는 DB
    r = ask(broken, action="query", query_type="issues", issue_type="퇴근 미태그")
    assert r["status"] == "db_error" and r["rows"] == []
