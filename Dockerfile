FROM python:3.12-slim-bookworm

WORKDIR /app

# Install system dependencies (combined from both stages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    tini \
    wget \
    gnupg \
    lsb-release \
    ca-certificates \
    curl \
    unzip \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    xdg-utils \
    tesseract-ocr \
    libtesseract-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxext6 \
    libxi6 \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Create output, logs, and weights directories
RUN mkdir -p /app/logs /app/weights /app/output/images

# Create a virtual environment
RUN python -m venv .venv
ENV PATH="/app/.venv/bin:$PATH"

# Upgrade pip
RUN pip install --upgrade pip

# Install PyTorch first
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu torch==2.2.0+cpu torchvision==0.17.0+cpu torchaudio==2.2.0+cpu

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Detectron2 separately from GitHub with build isolation disabled
RUN pip install --no-cache-dir --no-build-isolation "git+https://github.com/facebookresearch/detectron2.git"

# Download weights
RUN wget -q -O /app/weights/config.yml https://www.dropbox.com/s/f3b12qc4hc0yh4m/config.yml?dl=1 \
    && wget -q -O /app/weights/model_final.pth https://www.dropbox.com/s/dgy9c10wykk4lq4/model_final.pth?dl=1

# Copy the rest of the project source code
COPY . .

# Install the project itself
RUN pip install --no-cache-dir .

# Set up volumes for logs and weights
VOLUME ["/app/logs", "/app/weights", "/app/output"]

# Set the entrypoint to the installed command with logging enabled
# Use tini as the entrypoint to handle signals properly
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command to run the server (executed by tini)
CMD ["mcp-server-fetch", "--log-level", "INFO", "--log-file", "/app/logs/mcp-fetch.log"]