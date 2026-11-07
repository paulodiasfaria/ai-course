# Contentor da API. O contexto de build é a pasta modulos/ (ver docker-compose.yml),
# para copiar o comum.py do módulo 11: o prompt tem de ser exatamente o do treino.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN pip install "fastapi>=0.115" "uvicorn[standard]" httpx pydantic anthropic
WORKDIR /app
COPY 11-fine-tuning-e-alinhamento/use-case/comum.py .
COPY 12-inferencia-eficiente-e-llmops/use-case/servidor.py .
RUN useradd --create-home api && mkdir /dados && chown api /dados
USER api
ENV METRICAS_DB=/dados/metricas.db
EXPOSE 8080
CMD ["uvicorn", "servidor:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
