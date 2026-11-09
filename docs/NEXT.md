# 이어서 할 내용 (2026-11-09 기준)

다른 PC의 Claude Code에서 바로 이어서 할 수 있게 적어 둔 메모. 공개 저장소이므로 회사, 소속, 실존 인물, 내부 주소는 적지 않는다. 데이터는 가짜 데이터만 쓴다.

다른 PC의 Claude Code에서 처음 할 말: 『docs/NEXT.md와 docs/mcp-학습메모.md를 읽고, 이어서 할 일 1번부터 도와줘』

## 현재 상태

- 브랜치 `mcp-server`. `main` 위에 커밋 3개
  - 3c041b6 MCP 서버 추가. `mcp_server.py`(도구 4개, 읽기 전용), `tests/test_mcp_server.py`(27개), `requirements-mcp.txt`
  - c420c80 README에 「MCP 서버로 쓰기」 절과 Claude Code 시연 캡처 4장
  - e0e085f README 한계에 MCP 연결 방식(stdio, 같은 PC의 AI 도구 하나) 추가
- 테스트 79개 통과(기존 52 + MCP 27). `uv run pytest -q`
- 캡처: `docs/images/04-mcp-01-result.png`, `04-mcp-02-tool-call.png`, `04-mcp-03-out-of-range.png`, `04-mcp.gif`
- 원격 반영 여부는 `git log origin/mcp-server`로 확인. 없으면 아직 push 전
- 기존 파일(`checks.py`, `queries.py`, `nl_query.py`, `app.py`)은 한 줄도 바꾸지 않음

## 다른 PC에서 시작하는 법

```bash
git clone https://github.com/sc8556/attendance-checker.git   # 이미 있으면 git pull
cd attendance-checker
git checkout mcp-server
uv venv
uv pip install -r requirements.txt -r requirements-dev.txt -r requirements-mcp.txt
uv run python seed.py     # 가짜 DB 만들기
uv run pytest -q          # 79 passed 가 나와야 함
```

Claude Code에 MCP 등록. 저장소 폴더에서 실행한다.

```bash
claude mcp add attendance -- uv --directory <저장소 폴더 전체 경로> run python mcp_server.py
claude mcp list           # attendance: ... ✔ Connected
```

연결 확인. 저장소 폴더에서 `claude`를 켜고 "9월 2일 퇴근 미태그 보여줘"라고 묻는다. `data_range` 다음에 `find_issues(date_from="2026-09-02", date_to="2026-09-02", issue_type="퇴근 미태그")`가 불리고 E002 9/2 한 건이 돌아오면 된다. ctrl+o를 누르면 도구에 넘긴 조건과 돌아온 JSON이 보인다.

## 이어서 할 일 (우선순위 순)

1. `docs/2026-11-09-mcp-design.md` 채우기. 뼈대만 있고 내용은 비어 있음. AI가 아니라 작성자가 직접 쓰는 것이 목적. 구현하면서 실제로 정한 근거만 적는다
2. `mcp_server.py`와 `tests/test_mcp_server.py`를 읽고, 한 군데를 일부러 바꿔(예: `MAX_ROWS` 값, `mode=ro` 제거) 테스트가 깨지는 것을 확인한 뒤 되돌리기. 코드를 손으로 만져 보는 단계
3. `main`에 합칠지 결정. 합치면 README 맨 위 소개(MCP 문장)도 `main`에 반영됨
4. 선택: README 맨 위에 「어디를 보면 되는지」 한 줄. SQL은 `checks.py`·`queries.py`, 서버는 `app.py`·`mcp_server.py`, 검증은 `tests/`·`eval/`
5. 선택: README의 「직원 이름은 모두 지어낸 이름」 문장과 E011 이름이 맞지 않는 점 정리
6. 선택: `docs/2026-09-27-attendance-checker-design.md`에 남은 특정 업체명 2곳(64행, 136행)을 「출입 단말 업체」 같은 일반 용어로 바꾸기

## 안 하기로 한 것과 이유

- MCP에 자연어 질문 도구를 넣지 않음. AI 도구가 이미 LLM이라 조건만 넣으면 됨. 자연어 해석은 웹 앱의 Ollama 경로가 맡음
- 쓰기 도구 없음. 읽기 전용 원칙(SQLite `mode=ro`, readOnlyHint)
- 원격 HTTP 전송 없음. 개인 PC 시연 범위라 stdio만
- 도구는 5개를 넘기지 않음. 지금 4개

## 이 저장소를 설명할 때 답할 질문 5개

각 질문 아래 「답 메모:」에 작성자가 직접 적는다.

1. AI가 만든 코드를 어떻게 검증했나
   - 답 메모:
2. 왜 AI에게 SQL을 쓰게 하지 않았나
   - 답 메모:
3. MCP를 왜 붙였나
   - 답 메모:
4. 실패한 적은 (AI 평가 1차 18/24, Claude Code의 자동 권한 검사가 push를 막아 사람이 직접 push한 것)
   - 답 메모:
5. Python·SQL을 직접 쓸 수 있나
   - 답 메모:

## 지킬 것

- 공개 저장소. 회사, 소속, 실존 인물, 내부 주소를 적지 않는다. 커밋 전에 회사 용어 검색 0건 확인
- 가짜 데이터(`seed.py`)만 쓴다. 새 데이터 파일을 만들지 않는다
- AI는 SQL을 쓰지 않고 조건만 뽑는다. 조회는 앱의 고정 SQL이 한다. MCP 도구도 같다
- 문체는 README와 같게. 한국어 개조식, 줄표 없음
