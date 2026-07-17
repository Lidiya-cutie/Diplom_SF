#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MINIO_BIN="${MINIO_BIN:-/mldata/bin/minio}"
MC_BIN="${MC_BIN:-/mldata/bin/mc}"
DATA_DIR="${MINIO_DATA_DIR:-/mldata/tmp/diplom-sf-minio-data}"
PID_FILE="${MINIO_PID_FILE:-/mldata/tmp/diplom-sf-minio.pid}"
LOG_FILE="${MINIO_LOG_FILE:-/mldata/tmp/diplom-sf-minio.log}"
ADDR="${MINIO_ADDR:-127.0.0.1:9100}"
CONSOLE="${MINIO_CONSOLE:-127.0.0.1:9101}"
USER="${MINIO_ROOT_USER:-diplom_sf}"
PASS="${MINIO_ROOT_PASSWORD:-diplom_sf_secret}"
BUCKET="${MINIO_BUCKET:-diplom-sf}"

mkdir -p "$DATA_DIR" "$(dirname "$PID_FILE")" "$(dirname "$LOG_FILE")"

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "MinIO already running pid=$(cat "$PID_FILE") at http://$ADDR"
else
  export MINIO_ROOT_USER="$USER" MINIO_ROOT_PASSWORD="$PASS"
  nohup "$MINIO_BIN" server "$DATA_DIR" --address "$ADDR" --console-address "$CONSOLE" \
    >"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"
  sleep 2
  echo "MinIO started pid=$(cat "$PID_FILE") api=http://$ADDR console=http://$CONSOLE"
fi

"$MC_BIN" alias set diplom "http://$ADDR" "$USER" "$PASS" >/dev/null
"$MC_BIN" mb -p "diplom/$BUCKET" >/dev/null || true
echo "Bucket ready: s3://$BUCKET (endpoint http://$ADDR)"
echo "DVC env:"
echo "  export AWS_ACCESS_KEY_ID=$USER"
echo "  export AWS_SECRET_ACCESS_KEY=$PASS"
echo "  export AWS_EC2_METADATA_DISABLED=true"
