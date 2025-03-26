FROM python:3.12-slim AS builder

# Set a non-root user for security
RUN addgroup --system appgroup && adduser --system --group appuser

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Change ownership of the files to the non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser