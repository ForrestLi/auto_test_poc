# Base image with Python matching pyproject (python = "^3.8")
FROM python:3.8-slim

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps (build tools for possible native deps like quickfix)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tini \
    build-essential \
    git \
    pkg-config \
    libssl-dev \
    swig \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Configure Poetry to install into the system env (no venv inside container)
RUN poetry config virtualenvs.create false

# Workdir
WORKDIR /app

# Copy project definition first for caching
COPY pyproject.toml /app/

# Install ALL dependencies (main + dev)
RUN poetry install --no-interaction --no-ansi --with dev

# Add pytest-html for HTML report (not listed in pyproject dev deps)
RUN pip install --no-cache-dir pytest-html

# Copy the rest of the project
COPY . /app

# Expose default FIX server port
EXPOSE 9876

# Use tini as init for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command keeps container alive; services override this in docker-compose
CMD ["python", "-m", "http.server", "8000"]
