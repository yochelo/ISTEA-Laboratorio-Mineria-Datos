#!/usr/bin/env bash
set -euo pipefail

contenedor="$(docker run --rm -d -p 127.0.0.1::8000 "$1")"
trap 'docker stop "$contenedor" >/dev/null' EXIT
puerto="$(docker port "$contenedor" 8000/tcp)"
docker exec "$contenedor" sha256sum /app/models/churn_model.joblib \
  | grep -Fx "$MODELO_SHA256  /app/models/churn_model.joblib"
python tests/smoke_http.py "http://$puerto"
