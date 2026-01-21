FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for RDKit
RUN apt-get update && apt-get install -y \
    libboost-all-dev \
    libcairo2 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY website/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy src directory (for imports that might still reference it)
COPY src/ /app/src/

# Copy backend application code (includes thermodynamics.py, protonation_engine.py, docking_integration.py)
COPY website/backend/ /app/

# Version marker - change this to force rebuild
ENV APP_VERSION=v2.0.0-ensemble

# Expose port (Railway uses $PORT env var)
EXPOSE 8080

# Run the application (Railway will override PORT)
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} 