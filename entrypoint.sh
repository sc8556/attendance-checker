#!/bin/sh
# Ollama를 컨테이너 내부(127.0.0.1)에서만 띄우고, 준비되면 앱을 실행한다.
set -e
ollama serve &
for i in $(seq 1 60); do
  curl -sf "$OLLAMA_URL/api/version" > /dev/null && break
  sleep 1
done
# 첫 질문이 모델 적재 + 공통 지시(약 1,600토큰) 읽기를 기다리지 않도록,
# 평가 문항이 아닌 질문 하나를 앱과 같은 방식으로 보내 미리 데운다(백그라운드).
# Ollama가 공통 지시 부분을 캐시해 두므로 이후 질문은 사용자 질문 부분만 새로 읽는다.
python -c "import ai; ai.extract('9월 5일 기록 없음 보여줘')" > /dev/null 2>&1 &
exec gunicorn --bind "0.0.0.0:${PORT}" --workers 1 --threads 4 --timeout 300 app:app
