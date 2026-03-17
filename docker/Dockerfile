FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ ./
RUN npm run build


FROM python:3.13-slim AS backend-runtime

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENV=prod \
    LOG_LEVEL=INFO \
    FRONTEND_ORIGIN= \
    UPDATE_INTERVAL_SECONDS=10

WORKDIR /app/backend

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=backend/uv.lock,target=uv.lock,readonly \
    --mount=type=bind,source=backend/pyproject.toml,target=pyproject.toml,readonly \
    uv sync --frozen --no-dev --no-install-project

COPY backend/src ./src
COPY --from=frontend-builder /app/frontend/dist ./src/static

RUN mkdir -p /app/backend/src/data
VOLUME ["/app/backend/src/data"]

ENV PATH="/app/backend/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]