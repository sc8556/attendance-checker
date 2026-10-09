import json
import re
from urllib.parse import quote

import pytest

import ai
import app as app_module
import seed


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(seed, "DB_PATH", str(tmp_path / "test.db"))
    return app_module.app.test_client()


def fake_extract(q):
    fields = dict.fromkeys(ai.FIELDS)
    fields.update(action="query", query_type="issues", date_from="2026-09-02", date_to="2026-09-02", issue_type="퇴근 미태그")
    return {"raw": json.dumps(fields, ensure_ascii=False), "elapsed_seconds": 0.1}


def test_index_shows_overview(client):
    html = client.get("/").get_data(as_text=True)
    # 전체 카드에 정답 12건과 같은 수가 보인다
    assert re.search(r'id="stat-total".*?>12<', html, re.S)
    assert "E006" in html and "강하은" in html and "단말 16:15 / 수기 17:00 (45분)" in html
    assert "직원01" not in html  # 예전 임시 이름은 쓰지 않는다
    # 처리 중 안내는 숨겨진 채로 있다가 조회할 때만 보인다
    assert re.search(r'<div id="busy"[^>]*\bhidden\b', html)
    # 화면에는 표시 이름만 보인다(내부 이름 '시각 어긋남'은 AI 지시·평가용으로 그대로 둠)
    assert "출근 시간 불일치" in html and "퇴근 시간 불일치" in html
    assert "시각 어긋남" not in html
    # 카드 7개(전체 + 종류 6개)가 아래 표를 걸러 보는 버튼이고, 처음엔 전체가 선택돼 있다
    assert html.count("data-filter=") == 7
    assert re.search(r'data-filter="all"[^>]*aria-pressed="true"', html)
    assert "임시로 만든 직원 10명" in html
    assert "<title>근태 점검</title>" in html


def test_index_assets_and_examples(client):
    html = client.get("/").get_data(as_text=True)
    assert 'href="/static/style.css"' in html
    css = client.get("/static/style.css")
    assert css.status_code == 200
    css.close()
    # 칩에는 짧은 이름이 보이고, 누르면 원래 질문 문장 전체가 간다. 되묻기·기간 밖 예시도 있다.
    questions = [q for _, q in app_module.EXAMPLES]
    assert "늦게 온 직원 보여줘" in questions
    assert "10월 1일 퇴근 미태그 보여줘" in questions
    for label, q in app_module.EXAMPLES:
        assert re.search(rf'href="/\?q={re.escape(quote(q))}"[^>]*>{re.escape(label)}</a>', html)
    # 칩을 눌러도 중복 클릭 방지가 걸리도록, 칩 위치와 스크립트 선택자가 맞아야 한다
    assert 'class="examples"' in html and 'querySelectorAll(".examples a")' in html


def test_theme_toggle(client):
    html = client.get("/").get_data(as_text=True)
    assert 'id="theme-toggle"' in html
    # 저장된 테마를 화면이 그려지기 전에 적용하도록 head 안에서 읽는다(밝은 화면 번쩍임 방지)
    head = html.split("</head>")[0]
    assert "localStorage" in head and "dataset.theme" in head
    resp = client.get("/static/style.css")
    css = resp.get_data(as_text=True)
    resp.close()
    # 기기 설정을 따르되, 직접 고른 값이 있으면 그것을 따른다
    assert "prefers-color-scheme: dark" in css and ':root[data-theme="dark"]' in css


def test_extract_sends_keep_alive(monkeypatch):
    sent = {}

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": "{}"}}

    def fake_post(url, json, timeout):
        sent.update(json)
        return Resp()

    monkeypatch.setattr(ai, "KEEP_ALIVE", "24h")
    monkeypatch.setattr(ai.requests, "post", fake_post)
    ai.extract("질문")
    assert sent["keep_alive"] == "24h"


def test_index_question(client, monkeypatch):
    monkeypatch.setattr(ai, "extract", fake_extract)
    html = client.get("/?q=9월 2일 퇴근 미태그 보여줘").get_data(as_text=True)
    assert "결과 1건" in html and "15:13 IN" in html
    assert "조회 완료" in html  # 결과 위 상태 배지
    # 표에는 이름과 사번이 함께 보인다
    assert re.search(r"이서연.*?E002", html, re.S)


def test_api_ask(client, monkeypatch):
    monkeypatch.setattr(ai, "extract", fake_extract)
    body = client.post("/api/ask", json={"question": "9월 2일 퇴근 미태그"}).get_json()
    assert body["status"] == "ok" and body["rows"][0]["emp_id"] == "E002"
    assert client.post("/api/ask", json={}).status_code == 400
