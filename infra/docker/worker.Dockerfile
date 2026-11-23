# Worker image (plan.md §17.2: always-on, no public port).
# Phase 0 is an idle typed stub; the scan engine arrives in Phase 1.
FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN pip install --no-cache-dir uv==0.11.29

COPY services/worker/pyproject.toml services/worker/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY services/worker/mirsad_worker ./mirsad_worker
RUN uv sync --frozen --no-dev

RUN groupadd --gid 10001 mirsad && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin mirsad \
    && chown -R mirsad:mirsad /app
USER mirsad

CMD ["python", "-m", "mirsad_worker"]
