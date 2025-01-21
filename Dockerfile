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

# Install dependencies
RUN apt-get update && \
    apt-get install -y git && \
    pip install --no-cache-dir -r requirements.txt && \
    git clone https://github.com/NickWaterton/samsung-tv-ws-api.git && \
    cd samsung-tv-ws-api && \
    git checkout 84f4d061c9a9549b04698ae908e82daca3ddfef1 && \
    pip install "." && \
    pip install "samsungtvws[async,encrypted]" && \
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
ENV MAX_UPLOAD_ATTEMPTS=3

# Run the application
CMD ["python", "-u", "-m", "flask", "run", "--host=0.0.0.0"]