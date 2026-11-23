# API image (plan.md §17.2: Railway/Render/Oracle deploy from Dockerfile).
# Base pinned by digest; uv pinned to the version used locally.
FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN pip install --no-cache-dir uv==0.11.29

# Dependency layer first (rebuilds only when the lockfile changes).
COPY services/api/pyproject.toml services/api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY services/api/app ./app
RUN uv sync --frozen --no-dev

# Least privilege (plan.md §21 risk 7: non-root containers).
RUN groupadd --gid 10001 mirsad && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin mirsad \
    && chown -R mirsad:mirsad /app
USER mirsad

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
