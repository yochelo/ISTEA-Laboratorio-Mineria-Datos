#!/usr/bin/env bash
set -euo pipefail

imagen="$1"
test "$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.source"}}' "$imagen")" = "$GITHUB_SERVER_URL/$GITHUB_REPOSITORY"
test "$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$imagen")" = "$GITHUB_SHA"

docker run --rm --network none --entrypoint find "$imagen" /app -type f \
  | sort > "$RUNNER_TEMP/contenido-imagen"
{ git ls-files 'app/*.py' app/model_manifest.json requirements-serving.txt
  printf '%s\n' models/churn_model.joblib
} | sed 's|^|/app/|' | sort > "$RUNNER_TEMP/contenido-esperado"
diff -u "$RUNNER_TEMP/contenido-esperado" "$RUNNER_TEMP/contenido-imagen"

docker image inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$imagen" \
  | cut -d= -f1 | sed '/^$/d' > "$RUNNER_TEMP/variables-imagen"
if grep -Ei 'SECRET|PASSWORD|TOKEN|CREDENTIAL|API_KEY|^AWS_|^DAGSHUB_|^MLFLOW_' "$RUNNER_TEMP/variables-imagen"; then
  exit 1
fi
printf 'Contenido de aplicación y configuración de entorno verificados.\n'
