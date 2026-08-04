FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

COPY backend/requirements-docker.txt ./
COPY backend/.docker-wheels ./docker-wheels
COPY backend/app ./app
COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY data_demo ./data_demo

RUN if test -f /app/docker-wheels/.complete; then \
        pip install --no-cache-dir --no-index --find-links=/app/docker-wheels -r requirements-docker.txt; \
    else \
        pip install --no-cache-dir --index-url="${PIP_INDEX_URL}" --default-timeout=120 --retries=5 -r requirements-docker.txt; \
    fi \
    && rm -rf /app/docker-wheels

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python -m app.db.seed && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
