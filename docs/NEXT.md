# 이어서 할 내용 (2026-11-25 기준)

다른 PC의 Claude Code에서 바로 이어서 할 수 있게 적어 둔 메모. 공개 저장소이므로 회사, 소속, 실존 인물, 내부 주소는 적지 않는다. 데이터는 가짜 데이터만 쓴다.

Ollama가 있는 PC의 Claude Code에서 처음 할 말: 『docs/NEXT.md를 읽고, 「다음 할 일」 1번부터 도와줘』

## 코드 공부 이어서 하기 (2026-11-25)

- 오늘 본 흐름은 `nl_query.ask()`가 `ai.extract()`로 모델을 호출하고, 응답의 `raw`를 `parse()`에 넘기는 부분까지. `raw`는 JSON 형식의 문자열이고, `parse()`는 이를 파이썬 딕셔너리로 변환한 뒤 필수 항목과 값을 검사함.
- 오류 흐름도 확인함. `resp.raise_for_status()`가 HTTP 오류를 알리면 `extract()`가 `AIError`를 발생시키고 `ask()`가 받아 처리함. 조회 조건 검증에 실패하면 `parse()`에서 `InvalidResponse`가 발생함.
- 다음에 시작할 함수는 [`applied_conditions(cond)`](../nl_query.py#L110). “퇴근 미태그 보여줘”를 예로, `parsed`에서는 날짜가 둘 다 `None`인데 `applied`에서는 왜 9월 1일과 14일이 되는지 한 줄씩 따라가기. 그다음 `run_query()`에서 이 조건을 어느 조회 함수에 넘기는지 확인하기.

## 다음 할 일 (2026-11-25 결정)

브랜치는 `e011-fake-name`에서 한다. `mcp-server`가 아님(E011 이름 변경 커밋이 이 브랜치에만 있음).

1. 6차 AI 평가(24회). E011 이름 변경으로 AI 지시가 p7에서 p8로 바뀌었기 때문. Ollama와 모델 준비 후 실행
   ```bash
   ollama pull qwen3:4b-instruct
   uv run python eval/run_eval.py --label <실행 날짜>-p8-attempt6 --note "E011·E012의 데모 이름 변경. 지시 p7→p8. 공식 문항·기대값·통과 기준 변경 없음."
   ```
   결과는 `eval/results/<label>/`에 생김. 실패해도 기록은 지우지 않는다
2. README 고치기. 평가 표 6차 줄의 「아직 실행 전」을 결과(예: 24/24)로 바꾸고, 맨 위 표의 「(5차)」를 결과에 맞게 고침. 결과 폴더와 함께 커밋
3. `main`에 합치기. `e011-fake-name`을 `main`에 합치고 push는 작성자가 직접 함. 합치면 공개용 설계 문서와 MCP 절이 저장소 첫 화면에 반영됨

정한 것: git 기록에 남은 옛 설계 문서와 실명은 지우지 않고 그대로 둠(2026-11-25)

## 지난 상태 (2026-11-09)

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
git checkout e011-fake-name
uv venv
uv pip install -r requirements.txt -r requirements-dev.txt -r requirements-mcp.txt
uv run python seed.py     # 가짜 DB 만들기. 이미 있던 PC도 E011 이름이 바뀌었으니 다시 실행
uv run pytest -q          # 80 passed 가 나와야 함
```

Claude Code에 MCP 등록. 저장소 폴더에서 실행한다.

```bash
claude mcp add attendance -- uv --directory <저장소 폴더 전체 경로> run python mcp_server.py
claude mcp list           # attendance: ... ✔ Connected
```

연결 확인. 저장소 폴더에서 `claude`를 켜고 "9월 2일 퇴근 미태그 보여줘"라고 묻는다. `data_range` 다음에 `find_issues(date_from="2026-09-02", date_to="2026-09-02", issue_type="퇴근 미태그")`가 불리고 E002 9/2 한 건이 돌아오면 된다. ctrl+o를 누르면 도구에 넘긴 조건과 돌아온 JSON이 보인다.

## 이어서 할 일 (우선순위 순)

1. 완료(2026-11-25): `docs/2026-11-09-mcp-design.md` 채우기. 작성자 인터뷰 답으로 채운 뒤(2026-11-17) 작성자가 문장마다 확인하고 고침
2. 완료(2026-11-25): 코드를 일부러 바꿔(`mode=ro` 제거, `TIME_DIFF_MINUTES` 10→50) 테스트가 깨지는 것을 확인한 뒤 되돌림. 결과는 설계 메모 「테스트로 확인한 것」
3. 결정(2026-11-25): 6차 평가 뒤 `main`에 합침. 위 「다음 할 일」 참고
4. 선택: README 맨 위에 「어디를 보면 되는지」 한 줄. SQL은 `checks.py`·`queries.py`, 서버는 `app.py`·`mcp_server.py`, 검증은 `tests/`·`eval/`
5. 완료(2026-11-25): E011 이름을 지어낸 이름(송지호)으로 바꿈. AI 지시가 p8로 바뀌어 6차 평가(24회)는 위 「다음 할 일」 1번
6. 완료(2026-11-17): `docs/2026-09-27-attendance-checker-design.md`를 공개용으로 다시 씀. 업체명, 소속, 실제 업무 내용, AI 대화 기록을 빼고 결정과 근거만 남김. 이전 내용은 git 기록에는 남아 있음

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
