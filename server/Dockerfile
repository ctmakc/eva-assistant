FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for audio processing and whisper
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download Whisper model on build (small model for speed/quality balance)
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p /app/data/profiles /app/data/memory /app/data/credentials /app/data/audio

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
