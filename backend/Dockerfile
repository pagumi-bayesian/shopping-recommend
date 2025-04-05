# Stage 1: Build dependencies using uv
FROM python:3.12-slim as builder

WORKDIR /app

# Install uv
RUN pip install uv

# Copy only requirements.txt first to leverage Docker cache
COPY requirements.txt requirements.txt

# Install dependencies using uv
# --system オプションはシステム全体にインストールする (仮想環境不要)
# --no-cache は uv pip install ではデフォルトで有効
RUN uv pip install --system --no-cache -r requirements.txt

# Stage 2: Final image
FROM python:3.12-slim

WORKDIR /app

# Create a non-root user and group
RUN groupadd --system --gid 1001 appgroup && \
    useradd --system --uid 1001 --gid appgroup appuser

# Copy installed dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
# .dockerignore ファイルで不要なファイルを除外することを推奨
COPY . .

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose the port the app runs on (Cloud Run dynamically sets this via $PORT)
# EXPOSE 8080 is common practice but Cloud Run ignores it and uses $PORT
EXPOSE 8080

# Run the application using uvicorn
# Use the $PORT environment variable provided by Cloud Run, default to 8000 if not set
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
