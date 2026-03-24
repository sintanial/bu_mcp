# bu_mcp: Python + browser-use + Chromium (Debian) for local headless sessions.
# API keys only via environment / env_file — never bake secrets into the image.

FROM python:3.12-slim-bookworm

ARG VERSION=0.1.0

LABEL org.opencontainers.image.title="bu-mcp" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.description="bu_mcp: MCP Streamable HTTP server (browser-use). Default path /mcp. README: https://github.com/sintanial/browser-use-mcp/blob/main/README.md | Tools: https://github.com/sintanial/browser-use-mcp/blob/main/TOOLS.md | Agents: https://github.com/sintanial/browser-use-mcp/blob/main/AGENTS.md" \
      org.opencontainers.image.url="https://hub.docker.com/r/sintanial/bu-mcp" \
      org.opencontainers.image.source="https://github.com/sintanial/browser-use-mcp" \
      org.opencontainers.image.documentation="https://github.com/sintanial/browser-use-mcp/blob/main/README.md" \
      org.opencontainers.image.vendor="sintanial"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    BROWSER_USE_SETUP_LOGGING=false \
    IN_DOCKER=true

# Chromium + runtime libs (system chromium matches browser-use expectations on Linux).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        chromium \
        dbus \
        fontconfig \
        fonts-dejavu-core \
        fonts-freefont-ttf \
        fonts-liberation \
        fonts-noto-color-emoji \
        fonts-noto-core \
        libasound2 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libatspi2.0-0 \
        libcairo2 \
        libcups2 \
        libdbus-1-3 \
        libdrm2 \
        libgbm1 \
        libglib2.0-0 \
        libgtk-3-0 \
        libnspr4 \
        libnss3 \
        libpango-1.0-0 \
        libx11-6 \
        libxcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxkbcommon0 \
        libxrandr2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY bu_mcp ./bu_mcp

RUN pip install --upgrade pip \
    && pip install .

# Persistent Chromium profile for local mode (optional volume mount).
ENV BU_MCP_LOCAL_USER_DATA_DIR=/data/bu-mcp-profile

RUN mkdir -p /data/bu-mcp-profile

ENV BU_MCP_HOST=0.0.0.0 \
    BU_MCP_PORT=8765 \
    BU_MCP_HTTP_PATH=/mcp

EXPOSE 8765

# MCP Streamable HTTP (default path /mcp).
CMD ["bu-mcp"]
