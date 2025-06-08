FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        git \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Apple Silicon 向けにビルドする場合は下記のように `--platform` を指定してください
# docker build --platform linux/amd64 -t piphawk-ai:dev .

COPY pyproject.toml /app/pyproject.toml
COPY piphawk_ai /app/piphawk_ai
COPY ./backend ./analysis ./indicators ./config \
     ./risk ./monitoring ./strategies ./regime ./piphawk-ui ./tests \
     /app/

# PyTorch を CPU 版でインストール
RUN pip install --no-cache-dir torch==2.3.0+cpu -f https://download.pytorch.org/whl/cpu
# pyproject.toml を利用してパッケージをインストール
RUN pip install --no-cache-dir .

# create an empty SQLite database if not provided
RUN touch /app/trades.db

ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo

CMD ["python", "-m", "piphawk_ai.main", "job"]
