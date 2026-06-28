# Stage 1: Build dependencies
FROM python:3.12-slim as builder

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Final image
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies from builder
COPY --from=builder /install /usr/local

# Copy Arabic PDF fonts and project files
COPY fonts/ fonts/
COPY . .

# Create logs and static directories
RUN mkdir -p logs staticfiles media

# Bake deployment metadata after source copy so build cache cannot reuse stale commit env.
ARG GIT_COMMIT=unknown
ARG GIT_BRANCH=unknown
ARG GIT_COMMIT_DATE=unknown
ENV GIT_COMMIT=${GIT_COMMIT} \
    GIT_BRANCH=${GIT_BRANCH} \
    GIT_COMMIT_DATE=${GIT_COMMIT_DATE}
RUN test -n "$GIT_COMMIT" && test "$GIT_COMMIT" != "unknown" \
    && printf '%s' "$GIT_COMMIT" > /app/.deploy-commit

# Expose port
EXPOSE 8000

# Set executable permission for start script (if we had one)
# For now, we'll use a direct command or entrypoint in docker-compose

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
