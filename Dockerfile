FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy application files
COPY app.py global_config.py ollama_connector.py sd_connector.py ./
COPY static/ ./static/
COPY templates/ ./templates/
COPY requirements.txt .

# Create config directory
RUN mkdir -p /app/config

# Install dependencies (uses a specific commit from samsungtvws (art-updates branch)
RUN apt-get update && \
    apt-get install -y git && \
    pip install --no-cache-dir -r requirements.txt && \
    git clone https://github.com/xchwarze/samsung-tv-ws-api.git && \
    cd samsung-tv-ws-api && \
    git checkout 2e6c8ad28c38cc28f053e7efa8f4905c8d304f8a && \
    pip install "./[async,encrypted]" && \
    cd .. && \
    rm -rf samsung-tv-ws-api && \
    apt-get remove -y git && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Volume for config
VOLUME [ "/app/config" ]

# Expose port
EXPOSE 5000

# Set environment variable to run Flask on all interfaces
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV LOG_LEVEL=WARNING

# Run the application
CMD ["python", "-u", "-m", "flask", "run", "--host=0.0.0.0"]