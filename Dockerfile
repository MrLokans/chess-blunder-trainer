# syntax=docker/dockerfile:1.7
# Multi-stage Dockerfile for Blunder Tutor with Stockfish 18
# Compiles Stockfish from source with architecture-specific optimizations

# Stage 1: Build Stockfish from source
# This stage is independent of app code - changes to Python code won't invalidate this cache
FROM ubuntu:24.04 AS stockfish-builder

ARG TARGETARCH
ARG STOCKFISH_VERSION=sf_18

# Install build dependencies with cache mount for apt
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ca-certificates \
    wget

# Clone Stockfish - version is pinned via ARG for cache-friendliness
RUN git clone --depth 1 --branch ${STOCKFISH_VERSION} \
    https://github.com/official-stockfish/Stockfish.git /stockfish

WORKDIR /stockfish/src

# Build for appropriate architecture with optimizations
# Using cache mount for ccache could help but Stockfish uses its own build system
RUN if [ "$TARGETARCH" = "amd64" ]; then \
        make -j$(nproc) profile-build ARCH=x86-64-modern COMP=gcc; \
    elif [ "$TARGETARCH" = "arm64" ]; then \
        make -j$(nproc) profile-build ARCH=armv8 COMP=gcc; \
    else \
        make -j$(nproc) profile-build ARCH=general-64 COMP=gcc; \
    fi

# Stage 2: Export dependencies to requirements.txt (separate stage for better caching)
FROM python:3.13-slim AS deps-exporter

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install uv

WORKDIR /app

# Only copy lockfile - this layer only changes when dependencies change
COPY uv.lock pyproject.toml ./

# Export dependencies to requirements.txt (no source code needed)
RUN uv export --frozen --no-dev --no-hashes --no-emit-project -o requirements.txt

# Stage 3: Build Python dependencies
FROM python:3.13-slim AS python-builder

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install uv

WORKDIR /app

# Copy exported requirements - only changes when dependencies change
COPY --from=deps-exporter /app/requirements.txt ./

# Install dependencies from requirements.txt (no source code dependency)
# This layer is cached unless requirements.txt changes
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv && \
    uv pip install -r requirements.txt

# Copy application code after dependencies are installed
COPY pyproject.toml uv.lock README.md ./
COPY blunder_tutor ./blunder_tutor
COPY templates ./templates

# Install the project itself (fast - dependencies already installed)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --no-deps .

# Stage 4: Final runtime image
FROM python:3.13-slim

# Install runtime dependencies
# Note: cache mounts don't help in final stage since we need to clean up apt lists
# to keep the image small, and cleanup negates the cache benefit
RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy Stockfish binary from builder
COPY --from=stockfish-builder /stockfish/src/stockfish /usr/local/bin/stockfish

# Copy Python virtual environment
COPY --from=python-builder /app/.venv /app/.venv

# Copy application code
COPY . /app
WORKDIR /app

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV STOCKFISH_BINARY=/usr/local/bin/stockfish
ENV PYTHONUNBUFFERED=1

# Create data directory for persistence
RUN mkdir -p /app/data

EXPOSE 8000

# Health check using dedicated /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null http://localhost:8000/health || exit 1

# Start the application (run migrations first, then start uvicorn)
CMD ["sh", "-c", "python -m blunder_tutor.migrations && exec python -m uvicorn blunder_tutor.web.app:create_app_factory --factory --host 0.0.0.0 --port 8000"]
