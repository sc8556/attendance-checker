import json

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
    assert "총 <strong>12</strong>건" in html
    assert "E006" in html and "단말 16:15 / 수기 17:00 (45분)" in html
    # 처리 중 안내는 숨겨진 채로 있다가 조회할 때만 보인다
    assert '<p id="busy" class="busy" hidden>' in html


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


def test_api_ask(client, monkeypatch):
    monkeypatch.setattr(ai, "extract", fake_extract)
    body = client.post("/api/ask", json={"question": "9월 2일 퇴근 미태그"}).get_json()
    assert body["status"] == "ok" and body["rows"][0]["emp_id"] == "E002"
    assert client.post("/api/ask", json={}).status_code == 400
