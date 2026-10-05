"""자연어 질문 → AI 조건 JSON → 앱 검증 → 고정 SQL 조회.

결과 상태(status)를 구분한다. 결과 없음(empty)과 기간 밖·해석 실패·AI/DB 오류를 섞지 않는다.
"""

import json
import re
import sqlite3
from datetime import date

import ai
import queries
from answers import ISSUE_TYPES
from seed import DEMO_END, DEMO_START

ACTIONS = {"query", "clarify", "unsupported"}
QUERY_TYPES = {"issues", "employee_records", "time_difference"}
TIME_SIDES = {"출근", "퇴근"}
EMP_PATTERN = re.compile(r"^E\d{3}$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

QUERY_TYPE_LABELS = {"issues": "문제 목록", "employee_records": "직원별 기록", "time_difference": "시간 차이"}

SUPPORTED_HELP = (
    "지원하는 조회: ① 문제 목록(날짜·문제 종류·직원) ② 직원별 수기 시각과 출입 기록(직원·날짜) "
    "③ 수기와 단말 시각 차이(날짜·출근/퇴근·몇 분 이상). 데이터 기간은 "
    f"{DEMO_START}~{DEMO_END}입니다."
)

MESSAGES = {
    "empty": "해당 조건의 기록이 없습니다.",
    "ai_error": "AI 서버에 연결하지 못해 질문을 해석하지 못했습니다. 잠시 후 다시 시도해 주세요. (조회 결과 0건이 아닙니다)",
    "db_error": "DB 조회 중 오류가 발생했습니다. (조회 결과 0건이 아닙니다)",
}


class InvalidResponse(Exception):
    pass


def _check_date(value, name):
    if not isinstance(value, str) or not DATE_PATTERN.match(value):
        raise InvalidResponse(f"{name} 형식 오류: {value!r}")
    try:
        date.fromisoformat(value)
    except ValueError:
        raise InvalidResponse(f"{name}이 실제 날짜가 아님: {value!r}")


def parse(raw):
    """AI 원본 응답을 검사해 조건 dict를 돌려준다. 문제가 있으면 InvalidResponse."""
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        raise InvalidResponse("JSON이 아님")
    if not isinstance(data, dict):
        raise InvalidResponse("JSON 객체가 아님")
    if set(data) != set(ai.FIELDS):
        raise InvalidResponse(f"항목 불일치: 누락 {sorted(set(ai.FIELDS) - set(data))}, 추가 {sorted(set(data) - set(ai.FIELDS))}")

    action = data["action"]
    if action not in ACTIONS:
        raise InvalidResponse(f"action 값 오류: {action!r}")
    if action in ("clarify", "unsupported"):
        if not isinstance(data["question"], str) or not data["question"].strip():
            raise InvalidResponse(f"{action}인데 question이 비어 있음")
        return data

    qt = data["query_type"]
    if qt not in QUERY_TYPES:
        raise InvalidResponse(f"query_type 값 오류: {qt!r}")

    d_from, d_to = data["date_from"], data["date_to"]
    if (d_from is None) != (d_to is None):
        raise InvalidResponse("날짜 두 항목 중 하나만 있음")
    if d_from is not None:
        _check_date(d_from, "date_from")
        _check_date(d_to, "date_to")
        if d_from > d_to:
            raise InvalidResponse("시작 날짜가 끝 날짜보다 늦음")

    emp = data["employee_id"]
    if emp is not None and (not isinstance(emp, str) or not EMP_PATTERN.match(emp)):
        raise InvalidResponse(f"employee_id 형식 오류: {emp!r}")
    if data["issue_type"] is not None and data["issue_type"] not in ISSUE_TYPES:
        raise InvalidResponse(f"issue_type 값 오류: {data['issue_type']!r}")
    side = data["time_side"]
    if side is not None and side not in TIME_SIDES:
        raise InvalidResponse(f"time_side 값 오류: {side!r}")
    mins = data["min_difference_minutes"]
    if mins is not None and (isinstance(mins, bool) or not isinstance(mins, int) or not 0 < mins <= 1440):
        raise InvalidResponse(f"min_difference_minutes 값 오류: {mins!r}")

    # 조회 유형과 조건의 조합
    if qt == "issues" and (side is not None or mins is not None):
        raise InvalidResponse("문제 목록 조회에 시간 차이 조건이 섞임")
    if qt == "employee_records":
        if emp is None:
            raise InvalidResponse("직원별 기록 조회에 직원 번호가 없음")
        if data["issue_type"] is not None or side is not None or mins is not None:
            raise InvalidResponse("직원별 기록 조회에 문제 종류·시간 차이 조건이 섞임")
    if qt == "time_difference":
        if side is None or mins is None:
            raise InvalidResponse("시간 차이 조회에 출근/퇴근 또는 분 조건이 없음")
        if data["issue_type"] is not None:
            raise InvalidResponse("시간 차이 조회에 문제 종류가 섞임")
    return data


def applied_conditions(cond):
    """화면에 보여줄 실제 적용 조건. 생략된 값은 기본값과 함께 표시한다."""
    omitted_date = cond["date_from"] is None
    applied = {
        "query_type": cond["query_type"],
        "date_from": DEMO_START if omitted_date else cond["date_from"],
        "date_to": DEMO_END if omitted_date else cond["date_to"],
        "date_note": "날짜 생략 → 전체 데모 기간" if omitted_date else None,
        "employee_id": cond["employee_id"],
        "issue_type": cond["issue_type"],
        "time_side": cond["time_side"],
        "min_difference_minutes": cond["min_difference_minutes"],
    }
    labels = [("조회", QUERY_TYPE_LABELS[cond["query_type"]]),
              ("기간", f"{applied['date_from']} ~ {applied['date_to']}" + (" (날짜 생략 → 전체 데모 기간)" if omitted_date else "")),
              ("직원", cond["employee_id"] or "전체 직원")]
    if cond["query_type"] == "issues":
        labels.append(("문제 종류", cond["issue_type"] or "전체"))
    if cond["query_type"] == "time_difference":
        labels.append(("조건", f"{cond['time_side']} 시각 차이 {cond['min_difference_minutes']}분 이상"))
    applied["labels"] = labels
    return applied


def run_query(conn, applied):
    qt = applied["query_type"]
    if qt == "issues":
        return queries.issues(conn, applied["date_from"], applied["date_to"], applied["employee_id"], applied["issue_type"])
    if qt == "employee_records":
        return queries.employee_records(conn, applied["employee_id"], applied["date_from"], applied["date_to"])
    return queries.time_difference(conn, applied["time_side"], applied["min_difference_minutes"],
                                   applied["date_from"], applied["date_to"], applied["employee_id"])


def ask(question, conn, extractor=None):
    extractor = extractor or ai.extract
    result = {"question": question, "status": None, "message": None, "ai": None,
              "parsed": None, "invalid_reason": None, "applied": None, "rows": []}
    try:
        result["ai"] = extractor(question)
    except ai.AIError as exc:
        result.update(status="ai_error", message=MESSAGES["ai_error"], invalid_reason=str(exc))
        return result

    try:
        cond = parse(result["ai"]["raw"])
    except InvalidResponse as exc:
        result.update(status="invalid", invalid_reason=str(exc),
                      message=f"AI 응답을 조회 조건으로 해석하지 못했습니다({exc}). 질문을 바꿔 다시 시도해 주세요. (조회 결과 0건이 아닙니다)")
        return result
    result["parsed"] = cond

    if cond["action"] == "clarify":
        result.update(status="clarify", message=cond["question"])
        return result
    if cond["action"] == "unsupported":
        result.update(status="unsupported", message=f"{cond['question']} {SUPPORTED_HELP}")
        return result

    applied = applied_conditions(cond)
    result["applied"] = applied
    if applied["date_from"] < DEMO_START or applied["date_to"] > DEMO_END:
        result.update(status="out_of_range",
                      message=f"요청한 기간({applied['date_from']} ~ {applied['date_to']})은 보유 기간"
                              f"({DEMO_START} ~ {DEMO_END}) 밖입니다. 이 기간 안의 날짜로 다시 질문해 주세요.")
        return result

    try:
        if applied["employee_id"] and not queries.employee_exists(conn, applied["employee_id"]):
            result.update(status="unknown_employee",
                          message=f"{applied['employee_id']} 직원은 데모 직원 목록(E001~E010)에 없습니다.")
            return result
        rows = run_query(conn, applied)
    except sqlite3.Error as exc:
        result.update(status="db_error", message=MESSAGES["db_error"], invalid_reason=str(exc))
        return result

    result["rows"] = rows
    if rows:
        result.update(status="ok", message=f"{len(rows)}건")
    else:
        result.update(status="empty", message=MESSAGES["empty"])
    return result
