# ========================================================
# DOT AI - Autonomous Code Editor Container
# Powered by NVIDIA NIM (Nemotron 3.5 Super VL 120B)
# ========================================================

FROM python:3.11-slim

# Install system dependencies (build-essential for C grep, git, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Compile native Linux C search engine if source present
RUN if [ -f "native_c/fast_search.c" ]; then \
    gcc -O3 native_c/fast_search.c -o native_c/fast_search_linux || true; \
    fi

# Create default workspace mount point
RUN mkdir -p /workspace
VOLUME ["/workspace"]

# Expose Web IDE port and Live Preview Server port
EXPOSE 8080
EXPOSE 8765

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Launch Web IDE Server
CMD ["python", "web_app.py", "--host", "0.0.0.0", "--port", "8080", "--workspace", "/workspace"]
