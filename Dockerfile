FROM python:3.11-slim

# disable buffering and prevent bytecode generation
# to keep containers immutable
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# installs system-level dependencies required by some python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8000

# Create entrypoint script
RUN echo '#!/bin/sh\nalembic upgrade head\nuvicorn app.main:app --host 0.0.0.0 --port 8000' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]