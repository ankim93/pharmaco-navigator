# Stage 1 - Builder: Compiles Python wheels and installs all dependencies in an isolated prefix.
FROM python:3.11.4-alpine AS builder

# Install build-time system dependencies required to compile native extensions
RUN apk add --no-cache \
        gcc \
        musl-dev \
        postgresql-dev \
        libffi-dev

# Upgrade pip/wheel in the builder only
RUN pip install --upgrade pip wheel

WORKDIR /build

# Copy only the dependency manifest first to maximise Docker layer caching.
COPY requirements.txt .

# Install to a local prefix that can be cleanly copied to the runner stage.
# --no-cache-dir keeps the image lean; --user installs to /root/.local.
RUN pip install \
        --no-cache-dir \
        --user \
        --requirement requirements.txt

# Stage 2 - Runner: Minimal Alpine image that contains only runtime artefacts.
FROM python:3.11.4-alpine AS runner

# Runtime system dependency: libpq is needed by psycopg2 at runtime.
RUN apk add --no-cache \
        libpq \
        postgresql-client

# Create an unprivileged application user to avoid running as root.
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

# Pull compiled site-packages from the builder stage.
COPY --from=builder /root/.local /home/appuser/.local

# Copy application source code.
COPY app/ ./app/

# Ensure the unprivileged user owns the working directory and the audit log directory.
RUN chown -R appuser:appgroup /app /home/appuser/.local \
    && mkdir -p /var/log/pharmaco_audit \
    && chown appuser:appgroup /var/log/pharmaco_audit

USER appuser

# Make sure the user-local bin directory (uvicorn, etc.) is on PATH.
ENV PATH="/home/appuser/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
