# Stage 1: Builder
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Install system build dependencies (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements file for caching dependency installation
COPY requirements.txt .

# Create a virtual environment
RUN python -m venv .venv
ENV PATH="/app/.venv/bin:$PATH"

# Upgrade pip
RUN pip install --upgrade pip

# Install project dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project source code
COPY . .

# Install the project itself (this will install the mcp-server-fetch script)
RUN pip install --no-cache-dir .

# Stage 2: Final image
FROM python:3.12-slim-bookworm

WORKDIR /app

# Create a logs directory
RUN mkdir -p /app/logs

# Copy the built app (including the virtual environment) from the builder stage
COPY --from=builder /app /app

# Ensure the virtual environment's binaries are in the PATH
ENV PATH="/app/.venv/bin:$PATH"

# Set up volume for logs
VOLUME ["/app/logs"]

# Set the entrypoint to the installed command with logging enabled
ENTRYPOINT ["mcp-server-fetch", "--log-level", "INFO", "--log-file", "/app/logs/mcp-fetch.log"]

# Default command can be overridden
CMD []