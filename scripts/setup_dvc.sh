#!/usr/bin/env bash
# Initialize DVC, track full CSVs, push to local + MinIO S3-compatible remotes.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PATH="${VENV_BIN:-/mldata/venvs/diplom_sf/bin}:$PATH"
export TMPDIR="${TMPDIR:-/mldata/tmp}"
export AWS_EC2_METADATA_DISABLED=true
export AWS_ACCESS_KEY_ID="${MINIO_ROOT_USER:-diplom_sf}"
export AWS_SECRET_ACCESS_KEY="${MINIO_ROOT_PASSWORD:-diplom_sf_secret}"

bash "$ROOT/scripts/start_minio.sh"

if [[ ! -d .dvc ]]; then
  dvc init
fi

mkdir -p .dvc-storage
dvc remote add -f -d localremote .dvc-storage || true
dvc remote modify localremote url ../.dvc-storage
dvc remote add -f minio s3://diplom-sf/dvc || true
dvc remote modify minio endpointurl http://127.0.0.1:9100
dvc remote modify minio region us-east-1
dvc remote default localremote
dvc config core.no_scm false

for f in geo_data_0.csv geo_data_1.csv geo_data_2.csv; do
  if [[ -f "$f" ]]; then
    dvc add "$f"
  fi
done

dvc push -r localremote
dvc push -r minio

echo "DVC remotes ready: localremote (.dvc-storage) + minio (s3://diplom-sf/dvc)."
