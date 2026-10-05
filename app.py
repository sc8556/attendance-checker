import os
import sqlite3

from flask import Flask, jsonify, render_template, request

import checks
import nl_query
import seed
from answers import ISSUE_TYPES

app = Flask(__name__)

EXAMPLES = [
    "9월 2일 퇴근 미태그 보여줘",
    "E002의 9월 2일 기록 보여줘",
    "9월 1일 출근 시간이 30분 이상 차이 나는 직원 보여줘",
    "퇴근 미태그 보여줘",
]


def get_conn():
    if not os.path.exists(seed.DB_PATH):
        seed.main()
    return sqlite3.connect(f"file:{seed.DB_PATH}?mode=ro", uri=True)


def overview(conn):
    results = checks.find_all(conn)
    groups = {t: [r for r in results if r["issue_type"] == t] for t in ISSUE_TYPES}
    return results, groups


@app.route("/")
def index():
    question = request.args.get("q", "").strip()[:200]
    conn = get_conn()
    try:
        answer = nl_query.ask(question, conn) if question else None
        results, groups = overview(conn)
    finally:
        conn.close()
    return render_template(
        "index.html", question=question, answer=answer, results=results, groups=groups,
        examples=EXAMPLES, demo_start=seed.DEMO_START, demo_end=seed.DEMO_END,
        threshold=checks.TIME_DIFF_MINUTES,
    )


@app.route("/api/ask", methods=["POST"])
def api_ask():
    question = ((request.get_json(silent=True) or {}).get("question") or "").strip()[:200]
    if not question:
        return jsonify({"error": "question이 필요합니다"}), 400
    conn = get_conn()
    try:
        return jsonify(nl_query.ask(question, conn))
    finally:
        conn.close()


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
