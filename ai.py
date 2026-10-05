"""Ollama 호출. AI는 조회 조건 JSON만 돌려준다. SQL·직원 결과·시각은 만들지 않는다.

앱이 공통 지시(SYSTEM_PROMPT)를 붙이고, 사용자 질문은 매번 이전 대화 없이 새로 보낸다.
"""

import json
import os
import time

import requests

from answers import ISSUE_TYPES
from seed import EMPLOYEES

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:4b-instruct")
TIMEOUT_SECONDS = int(os.environ.get("OLLAMA_TIMEOUT", "180"))

PROMPT_VERSION = "p3"

# 평가 전에 고정한 생성 설정. 조건 추출 작업이라 무작위성을 끈다(temperature 0, seed 고정).
OPTIONS = {
    "temperature": 0,
    "seed": 42,
    "num_ctx": 2048,
    "num_predict": 300,
}

FIELDS = [
    "action", "query_type", "date_from", "date_to", "employee_id",
    "issue_type", "time_side", "min_difference_minutes", "question",
]


def nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["query", "clarify", "unsupported"]},
        "query_type": nullable({"type": "string", "enum": ["issues", "employee_records", "time_difference"]}),
        "date_from": nullable({"type": "string"}),
        "date_to": nullable({"type": "string"}),
        "employee_id": nullable({"type": "string"}),
        "issue_type": nullable({"type": "string", "enum": ISSUE_TYPES}),
        "time_side": nullable({"type": "string", "enum": ["출근", "퇴근"]}),
        "min_difference_minutes": nullable({"type": "integer"}),
        "question": nullable({"type": "string"}),
    },
    "required": FIELDS,
}

EMPLOYEE_LIST = ", ".join(f"{emp_id} {name}" for emp_id, name in EMPLOYEES)

SYSTEM_PROMPT = f"""너는 근태 조회 앱의 질문 해석기다. 사용자의 근태 질문을 읽고 조회 조건을 JSON 객체 하나로만 응답한다.

[데모 정보]
- 데모 연도: 2026년
- 직원 목록(가짜): {EMPLOYEE_LIST}
- 문제 종류(이 여섯 이름 전체만 사용): {", ".join(ISSUE_TYPES)}

[JSON 항목] 9개 항목을 항상 모두 포함하고, 사용하지 않는 값은 null로 둔다.
- action: "query"(조회), "clarify"(뜻 확인), "unsupported"(지원 범위 안내)
- query_type: 조회할 때 아래 셋 중 하나, 아니면 null
  - "issues"(문제 목록): 문제(이상 기록)를 찾는 질문. '~한 직원 보여줘', '~한 사람'처럼 여러 직원 중 문제가 있는 사람을 찾는 질문도 issues다.
  - "employee_records"(직원별 기록): 특정 직원 한 명(번호나 이름)의 수기 시각과 출입 기록 자체를 보려는 질문. employee_id가 반드시 있다.
  - "time_difference"(시간 차이): '몇 분 이상 차이'처럼 분 조건으로 수기와 단말 시각 차이를 찾는 질문.
- date_from: 시작 날짜 YYYY-MM-DD, 날짜 생략 시 null
- date_to: 끝 날짜 YYYY-MM-DD, 날짜 생략 시 null. 하루 질문은 date_from과 같은 날짜를 적는다. 둘 중 하나만 null로 두지 않는다.
- employee_id: 질문에 지정된 직원 번호(예: E002) 또는 null. null은 직원 조건 생략
- issue_type: issues 조회에서만 위 여섯 문제 종류 중 하나 또는 null. 질문에 문제 종류가 없거나 '문제 전부'·'모든 문제'처럼 전체를 요청하면 null이다. 질문에 없는 문제 종류를 고르지 않는다. employee_records·time_difference에서는 항상 null
- time_side: time_difference에서만 "출근" 또는 "퇴근". 다른 조회에서는 null
- min_difference_minutes: time_difference에서만 '몇 분 이상'의 정수. 다른 조회에서는 null
- question: clarify·unsupported일 때 사용자에게 물을 한 가지 질문. 조회할 때는 null

[규칙]
1. 근태 질문을 문제 목록·직원별 기록·시간 차이의 세 조회 유형으로 해석하고 위 JSON 객체 하나로 응답한다. 설명 문장이나 코드 블록은 붙이지 않는다.
2. 질문에서 날짜·직원·문제 종류·시간 차이 조건을 추출한다. 데모 연도는 2026년이다. 출근·퇴근을 안 찍었다는 표현은 각각 출근 미태그·퇴근 미태그로 해석한다. 문제 종류는 지정한 여섯 이름 전체를 사용한다.
3. 날짜를 생략하면 date_from·date_to를 null, 직원을 생략하면 employee_id를 null로 둔다. 앱이 날짜 생략 시 전체 데모 기간, 직원 생략 시 전체 직원을 적용한다. 문제 목록 전체를 요청하면 issue_type은 null이다.
4. 날짜를 명시했으면 보유 기간 밖이더라도 그 날짜를 그대로 전달한다. 보유 기간으로 바꾸지 않는다. 직원 이름을 번호로 바꿀 때는 위 직원 목록으로만 연결한다. 모르는 직원이나 불명확한 날짜·뜻은 확인한다.
5. '늦게 온 직원'처럼 뜻이 불명확하면 action을 clarify로 하고 question에 짧은 확인 질문 하나를 넣는다. 지원하지 않는 요청은 unsupported와 지원하는 조회로 이어질 한 가지 질문을 돌려준다. 이 두 경우에는 조회를 실행하지 않는다.
6. 시간 차이 조회는 출근/퇴근과 '몇 분 이상' 조건을 추출한다. 출근인지 퇴근인지 불명확하면 확인한다. 초과·이하 등 다른 비교 의미를 임의로 '이상'으로 바꾸지 않고 확인한다. 기존 이상 판정 기준 10분은 조회 조건과 구분한다.
7. 직원 검색 결과·시각·출입 기록·SQL은 생성하지 않는다. 조회 결과는 앱이 실제 DB에서 가져온다."""


class AIError(Exception):
    """Ollama 연결·응답 실패. 조회 결과 0건과 구분한다."""


def extract(question, url=None, model=None):
    """질문 하나를 새 대화로 보내고 원본 응답과 시간 정보를 돌려준다. 파싱·검증은 nl_query가 한다."""
    payload = {
        "model": model or MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        "format": JSON_SCHEMA,
        "options": OPTIONS,
        "stream": False,
        "keep_alive": "30m",
    }
    started = time.perf_counter()
    try:
        resp = requests.post(f"{url or OLLAMA_URL}/api/chat", json=payload, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
        body = resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise AIError(f"AI 서버 호출 실패: {exc}") from exc
    elapsed = time.perf_counter() - started
    ns = 1e9
    return {
        "raw": body.get("message", {}).get("content", ""),
        "elapsed_seconds": round(elapsed, 3),
        "load_seconds": round(body.get("load_duration", 0) / ns, 3),
        "prompt_eval_seconds": round(body.get("prompt_eval_duration", 0) / ns, 3),
        "eval_seconds": round(body.get("eval_duration", 0) / ns, 3),
        "prompt_tokens": body.get("prompt_eval_count"),
        "output_tokens": body.get("eval_count"),
    }


def model_info(url=None, model=None):
    """평가 기록용: 모델 digest와 Ollama 버전."""
    base = url or OLLAMA_URL
    name = model or MODEL
    tags = requests.get(f"{base}/api/tags", timeout=10).json().get("models", [])
    digest = next((m.get("digest") for m in tags if m.get("name") == name), None)
    version = requests.get(f"{base}/api/version", timeout=10).json().get("version")
    return {"model": name, "digest": digest, "ollama_version": version}


def prompt_fingerprint():
    import hashlib

    blob = json.dumps({"system": SYSTEM_PROMPT, "schema": JSON_SCHEMA, "options": OPTIONS}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]
