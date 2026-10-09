"""개발용 점검. 공식 8문항과 다른 질문으로 지시·코드를 점검한다. 공식 평가 점수에 합산하지 않는다.

실행: python eval/dev_check.py  → eval/dev/dev-<시각>.jsonl 에 기록
"""

import datetime
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ai  # noqa: E402
import nl_query  # noqa: E402
import seed  # noqa: E402

# (질문, 기대 상태, 기대 조건 일부)
DEV_QUESTIONS = [
    ("9월 4일 기록 없는 직원 알려줘", "ok", {"query_type": "issues", "date_from": "2026-09-04", "issue_type": "기록 없음"}),
    ("9월 11일에 퇴근 체크 안 한 사람", "ok", {"query_type": "issues", "date_from": "2026-09-11", "issue_type": "퇴근 미태그"}),
    ("조현우 9월 10일 출입 기록", "ok", {"query_type": "employee_records", "employee_id": "E007", "date_from": "2026-09-10"}),
    ("9월 8일 퇴근 시각이 수기와 40분 이상 다른 직원", "ok", {"query_type": "time_difference", "time_side": "퇴근", "min_difference_minutes": 40}),
    ("출근 미태그 전체 보여줘", "ok", {"query_type": "issues", "date_from": None, "issue_type": "출근 미태그"}),
    ("근무 태도가 안 좋은 직원 알려줘", "clarify|unsupported", {}),
    ("9월 7일 중복 기록 있어?", "empty", {"query_type": "issues", "date_from": "2026-09-07", "issue_type": "중복 기록"}),
    ("8월 31일 기록 없음 보여줘", "out_of_range", {"date_from": "2026-08-31", "issue_type": "기록 없음"}),
    ("9월 1일부터 3일까지 문제 전부 보여줘", "ok", {"query_type": "issues", "date_from": "2026-09-01", "date_to": "2026-09-03", "issue_type": None}),
    ("E005 급여 계산해줘", "unsupported|clarify", {}),
    ("9월 14일 출근 시간이 15분 이상 차이 나는 사람", "ok", {"query_type": "time_difference", "time_side": "출근", "min_difference_minutes": 15}),
    ("박지훈 9월 3일에 무슨 문제 있었어?", "ok", {"query_type": "issues", "employee_id": "E003", "date_from": "2026-09-03"}),
    # 공식 1차 평가 실패(하루 질문의 date_to null) 이후 추가한 개발 질문
    ("9월 11일 출근 시간이 25분 이상 차이 나는 직원 보여줘", "empty", {"query_type": "time_difference", "date_from": "2026-09-11", "date_to": "2026-09-11", "time_side": "출근", "min_difference_minutes": 25}),
    ("12월 24일 출근 미태그 보여줘", "out_of_range", {"date_from": "2026-12-24", "date_to": "2026-12-24", "issue_type": "출근 미태그"}),
    ("9월 14일 시각 어긋남(출근) 보여줘", "ok", {"date_from": "2026-09-14", "date_to": "2026-09-14", "issue_type": "시각 어긋남(출근)"}),
    ("E010 9월 14일 출입 기록", "ok", {"query_type": "employee_records", "employee_id": "E010", "date_from": "2026-09-14", "date_to": "2026-09-14"}),
]


def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dev")
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(out_dir, f"dev-{stamp}-{ai.PROMPT_VERSION}.jsonl")
    conn = sqlite3.connect(":memory:")
    seed.build(conn)
    ok_count = 0
    with open(path, "w", encoding="utf-8") as f:
        for q, want_status, want in DEV_QUESTIONS:
            r = nl_query.ask(q, conn)
            parsed = r["parsed"] or {}
            status_ok = r["status"] in want_status.split("|")
            cond_ok = all(parsed.get(k) == v for k, v in want.items())
            ok = status_ok and cond_ok
            ok_count += ok
            f.write(json.dumps({"prompt_version": ai.PROMPT_VERSION, "question": q, "pass": ok, "status": r["status"],
                                "raw": r["ai"] and r["ai"]["raw"], "elapsed": r["ai"] and r["ai"]["elapsed_seconds"],
                                "invalid_reason": r["invalid_reason"], "rows": len(r["rows"])}, ensure_ascii=False) + "\n")
            print(f"{'OK ' if ok else 'NG '} {r['status']:<16} {r['ai'] and r['ai']['elapsed_seconds']}s  {q}")
            if not ok:
                print("     raw:", (r["ai"] or {}).get("raw", "").replace("\n", " "), "|", r["invalid_reason"])
    print(f"{ok_count}/{len(DEV_QUESTIONS)}  → {path}")


if __name__ == "__main__":
    main()
