#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "${PROJECT_DIR}"

mkdir -p data backups runtime

if [[ ! -f runtime/.env ]]; then
    cp .env.example runtime/.env
    echo "已创建 runtime/.env，请先填写真实配置后重新执行 ./deploy.sh"
    exit 1
fi

docker compose up -d --build
docker compose ps
