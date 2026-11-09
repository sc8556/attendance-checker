"""MCP 서버. 화면(app.py)·자연어 질문(/api/ask)과 같은 판정을 Claude Code 같은 AI 도구에서 쓰게 한다.

도구는 조회 조건만 받고, 조회는 queries.py·checks.py에 미리 만들어 둔 SQL이 한다. AI가 SQL을 쓰지 않는다.
조건 검사는 nl_query.ask()에 그대로 맡긴다. 도구가 받은 조건을 AI(Ollama) 응답과 같은 JSON으로 만들어
넘기므로, 날짜 형식·보유 기간·직원 존재·문제 종류 검사를 두 벌 만들지 않고 한 곳에서 한다.

실행: uv run python mcp_server.py   (stdio, stdout은 MCP 통신에만 쓴다)
"""

import contextlib
import json
import os
import sqlite3
import sys

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

import ai
import nl_query
import seed
from answers import ISSUE_TYPES
from checks import TIME_DIFF_MINUTES

MAX_ROWS = 500  # 한 번에 돌려주는 행 수 상한

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)

server = MCPServer(
    "attendance",
    instructions=(
        "근태 점검 데모. 수기 근태 기록과 출입 단말 기록을 대조한다. 가짜 데이터(직원 12명, "
        f"{seed.DEMO_START}~{seed.DEMO_END} 평일)만 있다. 날짜·직원·문제 종류가 확실하지 않으면 "
        "data_range를 먼저 부른다. 도구는 모두 읽기 전용이다."
    ),
)


def connect():
    """읽기 전용 연결. DB가 없으면 seed.py로 만든다. seed의 출력은 stderr로 보낸다(stdout은 MCP 통신용)."""
    if not os.path.exists(seed.DB_PATH):
        with contextlib.redirect_stdout(sys.stderr):
            seed.main()
    return sqlite3.connect(f"file:{seed.DB_PATH}?mode=ro", uri=True)


def run(query_type, **cond):
    """조건을 AI 응답과 같은 JSON으로 만들어 nl_query.ask()에 넘긴다. 검사·조회·상태 구분을 전부 재사용한다."""
    fields = dict.fromkeys(ai.FIELDS)
    fields.update(action="query", query_type=query_type, **cond)
    raw = json.dumps(fields, ensure_ascii=False)
    conn = connect()
    try:
        result = nl_query.ask(f"mcp {query_type}", conn, extractor=lambda _question: {"raw": raw})
    finally:
        conn.close()
    rows = result["rows"]
    return {
        "status": result["status"],
        "message": result["message"],
        "invalid_reason": result["invalid_reason"],
        "applied": result["applied"],
        "total": len(rows),
        "rows": rows[:MAX_ROWS],
    }


@server.tool(annotations=READ_ONLY)
def data_range() -> dict:
    """데이터 기간, 근무일, 직원 목록, 문제 종류 목록을 돌려준다. 다른 도구의 조건을 정하기 전에 먼저 부른다.

    날짜는 YYYY-MM-DD, 직원은 E001 형식의 사번, 문제 종류는 issue_types 안의 값만 쓸 수 있다.
    """
    return {
        "date_from": seed.DEMO_START,
        "date_to": seed.DEMO_END,
        "work_dates": seed.WORK_DATES,
        "employees": [{"emp_id": emp_id, "name": name} for emp_id, name in seed.EMPLOYEES],
        "issue_types": ISSUE_TYPES,
        "time_sides": sorted(nl_query.TIME_SIDES),
        "time_diff_minutes": TIME_DIFF_MINUTES,
        "max_rows": MAX_ROWS,
    }


@server.tool(annotations=READ_ONLY)
def find_issues(date_from: str | None = None, date_to: str | None = None,
                emp_id: str | None = None, issue_type: str | None = None) -> dict:
    """수기 근태 기록과 출입 단말 기록을 대조해 문제가 있는 기록을 찾는다.

    date_from, date_to: YYYY-MM-DD. 둘 다 주거나 둘 다 생략한다(생략하면 데이터 기간 전체).
    emp_id: 사번(E001 형식). 생략하면 전체 직원.
    issue_type: 문제 종류. data_range의 issue_types 중 하나. 생략하면 6종 전부.
    status: ok(결과 있음) / empty(조건에 맞는 기록 없음, 0건) / out_of_range(요청 기간이 데이터 기간 밖) /
    unknown_employee(없는 직원) / invalid(조건 형식 오류, invalid_reason 참고). 0건과 조건 오류를 섞지 않는다.
    rows: 문제 종류, 사번, 날짜, 상세, 그날 출입 기록.
    """
    return run("issues", date_from=date_from, date_to=date_to, employee_id=emp_id, issue_type=issue_type)


@server.tool(annotations=READ_ONLY)
def employee_records(emp_id: str, date_from: str | None = None, date_to: str | None = None) -> dict:
    """한 직원의 날짜별 수기 출퇴근 시각과 출입 단말 기록 전부를 돌려준다.

    emp_id: 사번(E001 형식). 필수.
    date_from, date_to: YYYY-MM-DD. 둘 다 주거나 둘 다 생략한다(생략하면 데이터 기간 전체).
    status 값은 find_issues와 같다.
    """
    return run("employee_records", employee_id=emp_id, date_from=date_from, date_to=date_to)


@server.tool(annotations=READ_ONLY)
def time_difference(side: str, min_diff: int, date_from: str | None = None, date_to: str | None = None,
                    emp_id: str | None = None) -> dict:
    """수기 시각과 단말 시각의 차이가 min_diff분 이상인 기록을 찾는다.

    단말 시각은 출근이면 그날 첫 기록, 퇴근이면 마지막 기록. 같은 쪽 미태그인 날은 제외한다.
    side: "출근" 또는 "퇴근". min_diff: 1~1440(분).
    date_from, date_to: YYYY-MM-DD. 둘 다 주거나 둘 다 생략한다(생략하면 데이터 기간 전체).
    emp_id: 사번(E001 형식). 생략하면 전체 직원.
    status 값은 find_issues와 같다.
    """
    return run("time_difference", time_side=side, min_difference_minutes=min_diff,
               date_from=date_from, date_to=date_to, employee_id=emp_id)


if __name__ == "__main__":
    server.run("stdio")
