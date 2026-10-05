"""공식 평가: 승인된 8문항 × 3회 = 24회.

- 같은 모델·지시·설정·데이터로, 매 회차 이전 대화 없이 새 요청을 보낸다.
- 회차별 질문·원본 응답·파싱 결과·DB 조회 결과·통과 여부·응답 시간을 남긴다.
- 결과 폴더는 덮어쓰지 않는다(이전 실패 기록 보존).

실행: python eval/run_eval.py --label 2026-10-05-p3-attempt1
"""

import argparse
import datetime
import hashlib
import json
import os
import platform
import sqlite3
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import ai  # noqa: E402
import nl_query  # noqa: E402
import seed  # noqa: E402

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
WARMUP_QUESTION = "워밍업: 9월 9일 기록 없음 보여줘"


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def data_fingerprint():
    conn = sqlite3.connect(":memory:")
    seed.build(conn)
    blob = "\n".join(conn.iterdump())
    conn.close()
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def git_state():
    def run(*args):
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return {"commit": run("rev-parse", "--short", "HEAD"), "dirty": bool(run("status", "--porcelain"))}


def host_info():
    info = {"platform": platform.platform(), "python": platform.python_version()}
    try:
        with open("/proc/cpuinfo") as f:
            info["cpu"] = next(l.split(":", 1)[1].strip() for l in f if l.startswith("model name"))
        info["cpus"] = os.cpu_count()
        with open("/proc/meminfo") as f:
            info["mem_total_kb"] = int(next(l.split()[1] for l in f if l.startswith("MemTotal")))
    except (OSError, StopIteration):
        pass
    return info


def simplify_rows(query_type, rows):
    if query_type == "issues":
        return [[r["issue_type"], r["emp_id"], r["work_date"]] for r in rows]
    if query_type == "employee_records":
        return [{"emp_id": r["emp_id"], "work_date": r["work_date"], "manual_in": r["manual_in"],
                 "manual_out": r["manual_out"], "logs": [[l["time"], l["direction"]] for l in r["logs"]]} for r in rows]
    if query_type == "time_difference":
        return [[r["emp_id"], r["work_date"], r["terminal_time"], r["manual_time"], r["diff_minutes"]] for r in rows]
    return []


def judge(q, result):
    parsed = result["parsed"]
    if parsed is None:
        # 앱이 거부한 응답도 실패 원인을 읽을 수 있도록 원본 JSON으로 불일치를 보여준다(통과 판정에는 쓰지 않음)
        try:
            parsed = json.loads((result["ai"] or {}).get("raw") or "")
        except json.JSONDecodeError:
            parsed = {}
        if not isinstance(parsed, dict):
            parsed = {}
    exp = q["expected_conditions"]
    mismatches = {k: {"expected": v, "actual": parsed.get(k, "<없음>")} for k, v in exp.items() if parsed.get(k, "<없음>") != v}
    if exp.get("action") == "clarify" and not (isinstance(parsed.get("question"), str) and parsed["question"].strip()):
        mismatches["question"] = {"expected": "비어 있지 않은 확인 질문", "actual": parsed.get("question")}
    conditions_ok = result["parsed"] is not None and not mismatches

    status_ok = result["status"] == q["expected_status"]

    query_type = (result["applied"] or {}).get("query_type")
    actual_rows = simplify_rows(query_type, result["rows"])
    rows_ok = actual_rows == q["expected_rows"]
    if "expected_applied_period" in q:
        applied = result["applied"] or {}
        rows_ok = rows_ok and [applied.get("date_from"), applied.get("date_to")] == q["expected_applied_period"]

    return {
        "conditions_ok": conditions_ok, "condition_mismatches": mismatches,
        "status_ok": status_ok, "rows_ok": rows_ok, "actual_rows": actual_rows,
        "pass": conditions_ok and status_ok and rows_ok,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True, help="결과 폴더 이름. 이미 있으면 중단(덮어쓰기 금지)")
    parser.add_argument("--note", default="", help="이번 회차 실행 이유·변경 사항")
    parser.add_argument("--supplementary-sampling", action="store_true",
                        help="보조 실험(공식 점수 아님): Qwen 권장 샘플링(temperature 0.7, top_p 0.8, top_k 20), seed 고정 없음")
    args = parser.parse_args()
    if args.supplementary_sampling:
        ai.OPTIONS.pop("seed", None)
        ai.OPTIONS.update(temperature=0.7, top_p=0.8, top_k=20)

    out_dir = os.path.join(EVAL_DIR, "results", args.label)
    if os.path.exists(out_dir):
        sys.exit(f"{out_dir} 이미 있음. 이전 기록을 덮어쓰지 않습니다. 새 label을 쓰세요.")

    qpath = os.path.join(EVAL_DIR, "questions.json")
    with open(qpath, encoding="utf-8") as f:
        spec = json.load(f)

    git = git_state()
    if git["dirty"]:
        sys.exit("커밋되지 않은 변경이 있습니다. 평가 버전을 고정하려면 먼저 커밋하세요.")

    conn = sqlite3.connect(":memory:")
    seed.build(conn)

    warmup = ai.extract(WARMUP_QUESTION)
    meta = {
        "label": args.label,
        "official": not args.supplementary_sampling,
        "note": args.note,
        "started_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "git": git,
        "model": ai.model_info(),
        "prompt_version": ai.PROMPT_VERSION,
        "prompt_fingerprint": ai.prompt_fingerprint(),
        "options": ai.OPTIONS,
        "questions_version": spec["version"],
        "questions_sha256": sha256_file(qpath),
        "data_fingerprint": data_fingerprint(),
        "host": host_info(),
        "warmup": {"question": WARMUP_QUESTION, "note": "모델 적재용. 점수에 포함하지 않음", **warmup},
    }

    os.makedirs(out_dir)
    runs = []
    with open(os.path.join(out_dir, "runs.jsonl"), "w", encoding="utf-8") as f:
        run_no = 0
        for rnd in range(1, spec["repeats"] + 1):
            for q in spec["questions"]:
                run_no += 1
                result = nl_query.ask(q["question"], conn)
                verdict = judge(q, result)
                rec = {
                    "run": run_no, "round": rnd, "question_id": q["id"], "label": q["label"],
                    "question": q["question"],
                    "raw_response": result["ai"]["raw"] if result["ai"] else None,
                    "parsed": result["parsed"], "invalid_reason": result["invalid_reason"],
                    "status": result["status"], "message": result["message"],
                    "applied": {k: v for k, v in (result["applied"] or {}).items() if k != "labels"} or None,
                    "db_result": verdict.pop("actual_rows"),
                    **verdict,
                    "timing": {k: v for k, v in (result["ai"] or {}).items() if k != "raw"},
                }
                runs.append(rec)
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
                print(f"#{run_no:02d} R{rnd} Q{q['id']} {'PASS' if rec['pass'] else 'FAIL'} "
                      f"{rec['status']:<14} {rec['timing'].get('elapsed_seconds')}s  {q['question']}")

    meta["finished_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    passed = sum(r["pass"] for r in runs)
    elapsed = sorted(r["timing"]["elapsed_seconds"] for r in runs if r["timing"].get("elapsed_seconds") is not None)
    meta["summary"] = {
        "passed": passed, "total": len(runs),
        "elapsed_seconds": {"min": elapsed[0], "median": elapsed[len(elapsed) // 2], "max": elapsed[-1],
                            "mean": round(sum(elapsed) / len(elapsed), 3)} if elapsed else None,
        "failed_runs": [r["run"] for r in runs if not r["pass"]],
    }
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    write_summary(out_dir, meta, runs, spec)
    print(f"\n{passed}/{len(runs)} 통과 → {out_dir}")


def write_summary(out_dir, meta, runs, spec):
    s = meta["summary"]
    lines = [
        f"# 평가 결과 {meta['label']}" + ("" if meta["official"] else " (보조 실험 · 공식 점수 아님)"),
        "",
        f"- 결과: **{s['passed']}/{s['total']} 회차 통과**",
        f"- 모델: `{meta['model']['model']}` (digest `{meta['model']['digest'][:12]}`), Ollama {meta['model']['ollama_version']}",
        f"- 지시 버전: {meta['prompt_version']} (지문 `{meta['prompt_fingerprint']}`), 문항 {meta['questions_version']} (`{meta['questions_sha256']}`), 데이터 `{meta['data_fingerprint']}`, 코드 `{meta['git']['commit']}`",
        f"- 생성 설정: `{json.dumps(meta['options'], ensure_ascii=False)}`",
        f"- 실행 환경: {meta['host'].get('cpu', '?')}, {meta['host'].get('cpus', '?')} CPU, 메모리 {round(meta['host'].get('mem_total_kb', 0) / 1024 / 1024, 1)} GiB",
        f"- 응답 시간(초, AI 호출 왕복): 최소 {s['elapsed_seconds']['min']} / 중앙 {s['elapsed_seconds']['median']} / 평균 {s['elapsed_seconds']['mean']} / 최대 {s['elapsed_seconds']['max']}",
        f"- 시작 {meta['started_at']} · 종료 {meta['finished_at']}",
        f"- 메모: {meta['note'] or '-'}",
        "",
        "| 회차 | 라운드 | 문항 | 질문 | 상태 | 조건 | 상태 일치 | DB 결과 | 통과 | 시간(초) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    o = lambda b: "O" if b else "X"
    for r in runs:
        lines.append(f"| {r['run']} | {r['round']} | {r['question_id']} | {r['question']} | {r['status']} | {o(r['conditions_ok'])} | "
                     f"{o(r['status_ok'])} | {o(r['rows_ok'])} | **{'PASS' if r['pass'] else 'FAIL'}** | {r['timing'].get('elapsed_seconds')} |")
    fails = [r for r in runs if not r["pass"]]
    lines += ["", "## 실패 회차", ""]
    if not fails:
        lines.append("없음")
    for r in fails:
        lines += [f"### 회차 {r['run']} (Q{r['question_id']} {r['question']})",
                  f"- 상태: {r['status']} / 해석 실패 이유: {r['invalid_reason']}",
                  f"- 조건 불일치: `{json.dumps(r['condition_mismatches'], ensure_ascii=False)}`",
                  f"- 원본 응답: `{(r['raw_response'] or '').replace(chr(10), ' ')}`", ""]
    with open(os.path.join(out_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
