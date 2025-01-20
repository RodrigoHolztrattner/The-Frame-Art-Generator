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
RUN pip install --no-cache-dir -r requirements.txt

# Volume for config
VOLUME [ "/app/config" ]

# Expose port
EXPOSE 5000

# Set environment variable to run Flask on all interfaces
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Run the application
CMD ["python", "-u", "-m", "flask", "run", "--host=0.0.0.0"]