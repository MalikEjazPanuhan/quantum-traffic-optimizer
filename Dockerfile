FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Copy the entry point
COPY run.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

# Expose port
EXPOSE 7860

# Run the app
CMD ["python", "run.py"]
