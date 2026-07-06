FROM python:3.11-slim

LABEL maintainer="HandsControl Team"
LABEL description="HandsControl — Controla tu PC con Gestos, Voz e IA Local"
LABEL version="1.0.0"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libxcb-cursor0 \
    libxcb-xinerama0 \
    portaudio19-dev \
    libportaudio2 \
    libasound2-dev \
    alsa-utils \
    pulseaudio \
    ffmpeg \
    libavcodec-extra \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash handscontrol

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R handscontrol:handscontrol /app

USER handscontrol

ENV DISPLAY=:0
ENV PULSE_SERVER=unix:/run/user/1000/pulse/native
ENV PYTHONUNBUFFERED=1
ENV OLLAMA_HOST=http://host.docker.internal:11434

CMD ["python", "main.py"]
