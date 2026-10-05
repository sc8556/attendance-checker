# 앱(Flask) + Ollama + 모델을 이미지 하나에 넣는다. 외부에는 앱 포트(7860)만 연다.
# Ollama는 컨테이너 안의 127.0.0.1:11434에서만 듣는다.

ARG OLLAMA_VERSION=0.35.1
ARG MODEL=qwen3:4b-instruct

# 1단계: Ollama 내려받기(CPU용 라이브러리만 남김) + 모델 내려받기
FROM debian:bookworm-slim AS ollama
ARG OLLAMA_VERSION
ARG MODEL
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl zstd \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL "https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/ollama-linux-amd64.tar.zst" \
      | zstd -d | tar -x -C /usr/local \
    && rm -rf /usr/local/lib/ollama/cuda_* /usr/local/lib/ollama/vulkan
ENV OLLAMA_MODELS=/models
RUN (ollama serve > /tmp/serve.log 2>&1 &) \
    && for i in $(seq 1 30); do curl -sf http://127.0.0.1:11434/api/version && break; sleep 1; done \
    && ollama pull "${MODEL}" \
    && ollama list

# 2단계: 실행 이미지
FROM python:3.12-slim
ARG MODEL
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 user
COPY --from=ollama /usr/local/bin/ollama /usr/local/bin/ollama
COPY --from=ollama /usr/local/lib/ollama /usr/local/lib/ollama
COPY --from=ollama --chown=user /models /models

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=user . .

USER user
ENV HOME=/home/user \
    OLLAMA_MODELS=/models \
    OLLAMA_HOST=127.0.0.1:11434 \
    OLLAMA_URL=http://127.0.0.1:11434 \
    OLLAMA_MODEL=${MODEL} \
    OLLAMA_NUM_PARALLEL=1 \
    OLLAMA_KEEP_ALIVE=-1 \
    ATTENDANCE_DB=/app/attendance.db \
    PORT=7860
# 이미지를 만들 때 seed.py로 DB를 넣는다(설계 원칙 4)
RUN python seed.py

EXPOSE 7860
CMD ["sh", "entrypoint.sh"]
