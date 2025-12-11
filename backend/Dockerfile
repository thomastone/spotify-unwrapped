FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT="/opt/venv"
ENV PATH="/opt/venv/bin:$PATH" 

COPY pyproject.toml uv.lock* ./

RUN if [ -f uv.lock ]; then \
        uv sync --frozen --no-cache; \
    else \
        uv sync --no-cache; \
    fi

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]