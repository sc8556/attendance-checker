"""평가 채점기 자체 검증. 모델 없이 '정답 응답'은 통과, '틀린 응답'은 실패해야 한다."""

import json
import os
import sys

import ai
import nl_query

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "eval"))
import run_eval  # noqa: E402

with open(os.path.join(run_eval.EVAL_DIR, "questions.json"), encoding="utf-8") as f:
    SPEC = json.load(f)


def answer_with(fields):
    full = dict.fromkeys(ai.FIELDS)
    full.update(fields)
    raw = json.dumps(full, ensure_ascii=False)
    return lambda q: {"raw": raw, "elapsed_seconds": 0.0}


def test_perfect_answers_pass_all(conn):
    for q in SPEC["questions"]:
        fields = dict(q["expected_conditions"])
        if fields["action"] == "clarify":
            fields["question"] = "수기 출근보다 첫 단말 기록이 늦은 경우를 말씀하시나요?"
        result = nl_query.ask(q["question"], conn, extractor=answer_with(fields))
        verdict = run_eval.judge(q, result)
        assert verdict["pass"], (q["id"], verdict)


def test_dropped_mitag_fails(conn):
    q = SPEC["questions"][0]
    fields = dict(q["expected_conditions"], issue_type="퇴근")
    verdict = run_eval.judge(q, nl_query.ask(q["question"], conn, extractor=answer_with(fields)))
    assert not verdict["pass"] and not verdict["conditions_ok"]


def test_wrong_extra_field_fails(conn):
    q = SPEC["questions"][0]
    fields = dict(q["expected_conditions"], employee_id="E002")
    verdict = run_eval.judge(q, nl_query.ask(q["question"], conn, extractor=answer_with(fields)))
    assert not verdict["pass"]


def test_clarify_without_question_fails(conn):
    q = SPEC["questions"][5]
    verdict = run_eval.judge(q, nl_query.ask(q["question"], conn, extractor=answer_with({"action": "clarify", "question": " "})))
    assert not verdict["pass"]


def test_out_of_range_clamped_date_fails(conn):
    q = SPEC["questions"][7]
    fields = dict(q["expected_conditions"], date_from="2026-09-14", date_to="2026-09-14")
    verdict = run_eval.judge(q, nl_query.ask(q["question"], conn, extractor=answer_with(fields)))
    assert not verdict["pass"]
