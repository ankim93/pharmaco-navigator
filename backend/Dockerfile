# Stage 1: Builder — compile C extensions against Alpine headers
FROM python:3.12-alpine AS builder

RUN apk add --no-cache gcc musl-dev libffi-dev postgresql-dev

WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt


# Stage 2: Runner — minimal Alpine image with unprivileged appuser
FROM python:3.12-alpine AS runner

RUN apk add --no-cache libffi libpq postgresql-client

RUN addgroup -S appgroup && adduser -S appuser -G appgroup

RUN mkdir -p /var/log/pharmaco_audit && \
    chown -R appuser:appgroup /var/log/pharmaco_audit

COPY --from=builder /root/.local /home/appuser/.local

WORKDIR /app
COPY . .
RUN chown -R appuser:appgroup /app

USER appuser

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
