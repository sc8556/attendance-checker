#!/bin/sh
# Ollama를 컨테이너 내부(127.0.0.1)에서만 띄우고, 준비되면 앱을 실행한다.
set -e
ollama serve &
for i in $(seq 1 60); do
  curl -sf "$OLLAMA_URL/api/version" > /dev/null && break
  sleep 1
done
# 첫 질문이 모델 적재 시간까지 기다리지 않도록 미리 적재(백그라운드)
curl -sf "$OLLAMA_URL/api/generate" -d "{\"model\": \"$OLLAMA_MODEL\", \"keep_alive\": -1}" > /dev/null &
exec gunicorn --bind "0.0.0.0:${PORT}" --workers 1 --threads 4 --timeout 300 app:app
