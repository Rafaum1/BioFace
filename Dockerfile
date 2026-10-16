FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# dlib needs a C++ compiler and CMake when pip builds it in the container.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt ./requirements-docker.txt
RUN pip install --upgrade pip && pip install -r requirements-docker.txt

COPY app ./app
COPY run.py ./run.py

EXPOSE 5000

CMD ["python", "run.py"]
