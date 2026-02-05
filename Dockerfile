FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY *.py .

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 5000

# Run
CMD ["python", "main.py"]
