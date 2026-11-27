# Runbook de operación del laboratorio

El despliegue y las pruebas de funcionamiento se realizaron con Ubuntu 24.04.5 sobre WSL 2, Docker Engine nativo 29.10.1 y Compose v5.8.0. El motor de Docker funciona de manera independiente de Docker Desktop. También se comprobaron los procedimientos de actualización y rollback de la imagen. Queda pendiente confirmar la aceptación académica de WSL 2 como entorno Linux para la entrega.

## Preparar y arrancar el stack

Para realizar el despliegue se necesita Docker Engine en ejecución, una versión de Compose compatible con !reset y !override, acceso a GHCR y los puertos locales 18001, 19090 y 13000 disponibles. El despliegue requiere siete archivos, conservando sus rutas. En el entorno comprobado se copiaron así desde el checkout de Windows. Si se utiliza otro equipo, modificar la variable origen indicando la ubicación de los archivos

```bash
origen=/mnt/c/ISTEA/Laboratorio
destino="$HOME/istea-churn-linux"
for archivo in \
  compose.yaml compose.linux.yaml \
  prometheus/prometheus.yml prometheus/alerts.yml \
  grafana/provisioning/datasources/prometheus.yaml \
  grafana/provisioning/dashboards/istea.yaml \
  grafana/dashboards/churn-monitoring.json; do
  install -D -m 0644 "$origen/$archivo" "$destino/$archivo" || break
done
```

Desde el directorio de despliegue, usar el socket nativo. `sudo` corresponde a la configuración comprobada de acceso al socket. Ingresar la contraseña en la terminal si se solicita. Para un nuevo despliegue, preparar primero `compose.final.yaml` siguiendo la sección de actualización. Ejecutar los bloques en la misma sesión y resolver cualquier error antes de continuar.

```bash
cd "$HOME/istea-churn-linux"
motor=(sudo docker --host unix:///var/run/docker.sock)
compose=("${motor[@]}" compose -p istea-churn-linux -f compose.yaml -f compose.final.yaml)
ss -H -ltn '( sport = :18001 or sport = :19090 or sport = :13000 )'
"${compose[@]}" config --quiet
"${compose[@]}" config --images
"${compose[@]}" pull
"${compose[@]}" up -d --no-build --pull never --wait
"${compose[@]}" ps
```

Revisar también esos puertos en Windows si se usa WSL. `pull` recupera la imagen pública de GHCR por el digest de la copia operativa y las dos imágenes de observabilidad. [compose.linux.yaml](../compose.linux.yaml) conserva la configuración anterior para rollback.

## Comprobaciones y diagnóstico

```bash
for ruta in live ready health docs; do
  curl -fsS -o /dev/null -w "$ruta: %{http_code}\n" "http://127.0.0.1:18001/$ruta"
done
curl -fsS http://127.0.0.1:18001/health
curl -fsS http://127.0.0.1:19090/-/ready
curl -fsS http://127.0.0.1:13000/api/health
"${compose[@]}" exec -T churn-api sha256sum /app/models/churn_model.joblib
"${compose[@]}" logs --tail 100 --no-color churn-api
read -r -p 'X-Request-ID: ' solicitud
"${compose[@]}" logs --no-color churn-api | grep -F -- "$solicitud"
```

Los endpoints de estado permiten realizar distintas comprobaciones:

| Endpoint | Función |
|---|---|
| `/live` | Comprueba que la API está en ejecución. |
| `/ready` | Comprueba que el modelo está disponible para realizar predicciones. |
| `/health` | Informa el estado del servicio y la versión del modelo cuando está disponible. |

Se espera `ISTEA_Churn/1` en salud y el SHA-256 del [manifiesto del modelo](../app/model_manifest.json). Desde Swagger, repetir [la entrada válida](../tests/fixtures/predict_request_valid.json) y [la inválida](../tests/fixtures/predict_request_invalid.json). La válida devuelve 200, clase `Yes`, score `0.9155293197461535` y riesgo `HIGH`. La inválida devuelve 422. Usar la cabecera `X-Request-ID` para correlacionar ambos casos en los logs.

| Síntoma | Comprobación |
|---|---|
| HTTP 422 | Revisar `detail` y buscar el evento `validation_rejected` por UUID. Corregir la entrada antes de reintentar. |
| HTTP 500 | Buscar `inference_failed` por UUID y revisar el estado y versión del servicio. |
| HTTP 503 o fallo de readiness | Buscar `model_unavailable` en logs de arranque y cotejar el digest, el SHA-256 y el manifiesto. |
| API inaccesible | Revisar `compose ps`, el puerto local y el estado del target. Consultar los logs antes de intervenir. |
| Latencia alta | Usar el panel p95 y revisar `duration_seconds` en logs. Correlacionar el cambio con tráfico, reinicios y hora de inicio. |

Desde Ubuntu o Windows, abrir [targets](http://localhost:19090/targets), [alertas](http://localhost:19090/alerts) y el [dashboard de Grafana](http://localhost:13000/d/istea-churn-monitoring). El job `ml-api` debe estar en `UP`. Para una consulta puntual, ejecutar en Prometheus `up{job="ml-api"}` o `sum by (status) (http_requests_total{route="/predict"})`. Ante alertas, seguir el [plan de actuación](plan_monitoreo.md).

## Evidently

Generar el informe en el **entorno de desarrollo**, desde la raíz del checkout y con los CSV recuperados por DVC. Ejemplo comprobado con Python 3.11 en PowerShell:

```powershell
$entorno = Join-Path $env:LOCALAPPDATA 'istea-churn-monitoring-venv'
python -m venv $entorno
$pythonMonitoreo = Join-Path $entorno 'Scripts/python.exe'
& $pythonMonitoreo -m pip install -r monitoring/requirements.txt
$env:EVIDENTLY_DISABLE_TELEMETRY = '1'
& $pythonMonitoreo -m monitoring.drift_report
```

Abrir reports/drift_report.html en el navegador para visualizar los resultados. Los archivos drift_report.json y drift_provenance.json permiten consultar los resultados y verificar qué datos se utilizaron para generar el informe. Antes de comparar distintos períodos, revisar los valores faltantes, las variables afectadas por drift y los hashes de los archivos. Los informes se generan localmente y no se publican sin autorización.

## Actualización y rollback por digest

Consultar la [release v1.0.0](https://github.com/yochelo/ISTEA-Laboratorio-Mineria-Datos/releases/tag/v1.0.0) para obtener el digest definitivo y la copia operativa `compose.final.yaml`. Para generarla manualmente, conservar `compose.linux.yaml` y crear el nuevo archivo solo si todavía no existe. Si ya existe, verificar su digest antes de reutilizarlo.

```bash
cd "$HOME/istea-churn-linux"
motor=(sudo docker --host unix:///var/run/docker.sock)
patron='^ghcr\.io/yochelo/istea-laboratorio-mineria-datos@sha256:[0-9a-f]{64}$'
if read -r -p 'Referencia completa de la imagen por digest: ' imagen &&
  [[ "$imagen" =~ $patron ]]; then
  test ! -e compose.final.yaml &&
    sed -E "s|^    image: ghcr\\.io/yochelo/istea-laboratorio-mineria-datos@sha256:[0-9a-f]{64}$|    image: $imagen|" \
      compose.linux.yaml > compose.final.yaml
else
  printf '%s\n' 'Ingresar la referencia de GHCR del proyecto con un digest SHA-256 de 64 caracteres hexadecimales.' >&2
  false
fi
```

Verificar la referencia efectiva y actualizar solo la API:

```bash
compose=("${motor[@]}" compose -p istea-churn-linux -f compose.yaml -f compose.final.yaml)
"${compose[@]}" config --images | grep -Fx -- "$imagen" &&
  "${compose[@]}" pull churn-api &&
  "${compose[@]}" up -d --no-deps --no-build --pull never --wait churn-api
```

Repetir salud, hash, las dos solicitudes y el estado del target. Para volver a la imagen anterior conservada localmente:

```bash
anterior=("${motor[@]}" compose -p istea-churn-linux -f compose.yaml -f compose.linux.yaml)
"${anterior[@]}" config --images |
  grep -Fx -- 'ghcr.io/yochelo/istea-laboratorio-mineria-datos@sha256:bb4533c45d25fe198ab5495a60904c469a36fc1dc339ce45fe59268408864079' &&
  "${anterior[@]}" up -d --no-deps --no-build --pull never --wait churn-api
```

Repetir los controles tras la recuperación. Para restablecer la imagen nueva ya descargada, ejecutar `"${compose[@]}" up -d --no-deps --no-build --pull never --wait churn-api` con la copia operativa y volver a comprobar la API. Prometheus y Grafana siguieron en ejecución durante la prueba.

Para detener el stack preservando sus datos, ejecutar `"${compose[@]}" down`, sin `--volumes`.
