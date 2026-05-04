FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for yt-dlp (ffmpeg for merging audio+video)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create downloads directory
RUN mkdir -p downloads

EXPOSE 8000

CMD ["python", "main.py"]
