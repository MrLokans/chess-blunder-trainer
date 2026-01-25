# Multi-stage Dockerfile for Blunder Tutor with Stockfish 17
# Compiles Stockfish from source with architecture-specific optimizations

# Stage 1: Build Stockfish from source
FROM ubuntu:22.04 AS stockfish-builder

ARG TARGETARCH

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ca-certificates \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Clone Stockfish 17
RUN git clone --depth 1 --branch sf_17 \
    https://github.com/official-stockfish/Stockfish.git /stockfish

WORKDIR /stockfish/src

# Build for appropriate architecture with optimizations
RUN if [ "$TARGETARCH" = "amd64" ]; then \
        make -j$(nproc) profile-build ARCH=x86-64-modern COMP=gcc; \
    elif [ "$TARGETARCH" = "arm64" ]; then \
        make -j$(nproc) profile-build ARCH=armv8 COMP=gcc; \
    else \
        make -j$(nproc) profile-build ARCH=general-64 COMP=gcc; \
    fi

# Stage 2: Build Python dependencies
FROM python:3.13-slim AS python-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY blunder_tutor ./blunder_tutor
COPY templates ./templates
RUN uv sync --frozen --no-dev

# Stage 3: Final runtime image
FROM python:3.13-slim

# Install runtime dependencies
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
    CMD wget --no-verbose --tries=1 --spider http://localhost:8000/health || exit 1

# Start the application
CMD ["python", "-m", "uvicorn", "blunder_tutor.web.app:create_app_factory", \
     "--factory", "--host", "0.0.0.0", "--port", "8000"]
