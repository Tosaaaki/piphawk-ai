FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        git \
        sqlite3 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Apple Silicon 向けにビルドする場合は下記のように `--platform` を指定してください
# docker build --platform linux/amd64 -t piphawk-ai:dev .

COPY pyproject.toml /app/pyproject.toml
# プロジェクト全体をコピーして必要なパッケージを確実に含める
COPY . /app

# PyTorch を CPU 版でインストール
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.3.0
#   └─ +cpu は不要。インデックスを CPU 専用に切り替えれば CPU ホイールが解決される。
#   もし失敗する場合は単に  `pip install torch==2.3.0` でも CPU 版が入ります。
# pyproject.toml を利用してパッケージをインストール
RUN pip install --no-cache-dir .

# ensure logs directory exists
RUN mkdir -p /app/backend/logs

ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tokyo
ENV PYTHONPATH=/app

CMD ["python", "-m", "piphawk_ai.main", "job"]
