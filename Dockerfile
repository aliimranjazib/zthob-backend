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

ARG GIT_COMMIT=unknown
ARG GIT_BRANCH=unknown
ARG GIT_COMMIT_DATE=unknown
ENV GIT_COMMIT=${GIT_COMMIT}
ENV GIT_BRANCH=${GIT_BRANCH}
ENV GIT_COMMIT_DATE=${GIT_COMMIT_DATE}

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies from builder
COPY --from=builder /install /usr/local

# Copy project files
COPY . .

# Create logs and static directories
RUN mkdir -p logs staticfiles media

# Expose port
EXPOSE 8000

# Set executable permission for start script (if we had one)
# For now, we'll use a direct command or entrypoint in docker-compose

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
