# ---- Runtime image for oldap-tools ----
FROM python:3.12-slim

# No .pyc files, better logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Optional: curl for debugging inside container
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install your tool from PyPI
ARG OLDAP_TOOLS_VERSION=0.1.4
RUN pip install --no-cache-dir oldap-tools==${OLDAP_TOOLS_VERSION}

# Default entrypoint
ENTRYPOINT ["oldap-tools"]

# Default command (can be overridden)
CMD ["--help"]