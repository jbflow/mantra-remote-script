FROM python:3.11-slim

WORKDIR /app

# Install any system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy the mantra-remote-script module
COPY . .

# Install LiveAPI-mock for testing
# This is optional - if not available, remote-script runs standalone
RUN pip install --no-cache-dir pytest 2>/dev/null || true

EXPOSE 9001

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import socket; s = socket.socket(); s.connect(('localhost', 9001)); s.close()" || exit 1

CMD ["python", "-m", "http.server", "9001", "--directory", "."]
