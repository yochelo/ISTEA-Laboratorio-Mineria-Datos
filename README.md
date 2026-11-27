# Predicción de abandono de clientes

Proyecto académico de Laboratorio de Minería de Datos de ISTEA. El servicio estima el riesgo de abandono de un cliente de telecomunicaciones para ayudar a priorizar acciones de retención. La decisión sobre cómo contactar o asistir al cliente requiere criterio humano.

## Arquitectura

El histórico y los artefactos se versionan con DVC en DagsHub. El entrenamiento y la evaluación del modelo se realizan con Scikit-learn, utilizando el código versionado en Git. MLflow registra los experimentos y la versión aprobada. FastAPI carga una copia local verificada del modelo, incluida en la imagen Docker. GitHub Actions comprueba el proyecto antes de publicar en GHCR. En el despliegue, Prometheus recolecta métricas de la API y Grafana las visualiza. Evidently compara lotes de datos por separado

## Datos y modelo

- **Histórico:** 7.043 registros, con 19 predictores, `customerID` y la etiqueta `Churn`. Se usa para entrenamiento y evaluación.
- **Producción simulada:** 2.500 registros sin `Churn`, reservados para monitoreo. El lote de scoring del profesor se reserva para pruebas de inferencia.
- **Selección:** se evaluaron seis configuraciones de baseline, regresión logística y Random Forest en cinco folds estratificados. Se eligió la regresión logística balanceada con `C=1` por su mayor recall medio entre las opciones con precisión media de al menos 0,50. En el holdout logró recall de 72,31 % y precisión de 48,12 %, con 103 falsos negativos y 290 falsos positivos.
- **Justificación:** se priorizó el recall porque, para este problema, interesa detectar la mayor cantidad posible de clientes que podrían abandonar el servicio. En comparación con el modelo anterior, los falsos negativos disminuyeron de 204 a 103, aunque los falsos positivos aumentaron de 85 a 290. Esto permite detectar más casos de abandono, a cambio de contactar potencialmente a más clientes que no abandonarían el servicio.

- **Registro:** [ISTEA_Churn/1](https://dagshub.com/yochelo/ISTEA-Laboratorio-Mineria-Datos.mlflow/#/models/ISTEA_Churn/versions/1), vinculado al [run final](https://dagshub.com/yochelo/ISTEA-Laboratorio-Mineria-Datos.mlflow/#/experiments/0/runs/778771c7af9e40dcb771cc5becfc9142). La API verifica el SHA-256 contra el [manifiesto del modelo](app/model_manifest.json) antes de cargarlo.

La [Model Card](docs/model_card.md) reúne la comparación completa, los límites del modelo y su uso recomendado.

## Desarrollo local

Requiere Git y Python 3.11.9.

Clonar el repositorio desde Windows PowerShell:

```powershell
git clone -b entrega-final https://github.com/yochelo/ISTEA-Laboratorio-Mineria-Datos.git
cd ISTEA-Laboratorio-Mineria-Datos
```

Crear el entorno virtual e instalar las dependencias:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-ci.txt
python -m pip check
```

Para acceder al remoto `origin` de DVC, usar las credenciales vigentes de DagsHub mediante `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY` en el entorno, o mediante la configuración local e ignorada de DVC. El servidor de MLflow se selecciona con `MLFLOW_TRACKING_URI`. Las credenciales de tracking se configuran en el entorno si se necesita consultar o registrar experimentos.

```powershell
dvc pull -r origin data/raw/customer_churn_historical.csv.dvc train data/production/customer_churn_current.csv.dvc
dvc status --json
python -m pytest -q
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

dvc pull descarga ambos CSV, el joblib y `reports/metrics.json`. La suite vigente tiene **90 pruebas aprobadas** en la ejecución de CI enlazada abajo. Con el modelo recuperado también se puede iniciar el stack de desarrollo con `docker compose up -d --build`. La API de ese stack usa `127.0.0.1:8001`.

El entrenamiento es un recorrido separado. `dvc repro train` puede ajustar el modelo y registrar nuevos runs cuando DVC detecta cambios. Para usar el artefacto aprobado alcanza con `dvc pull`. El [pipeline DVC](dvc.yaml), el [lock](dvc.lock) y los [parámetros](params.yaml) documentan la ejecución.

### Contrato de la API

Swagger está en `/docs`. Para probar `POST /predict`, copiar en Swagger [el ejemplo válido](tests/fixtures/predict_request_valid.json) y [el inválido](tests/fixtures/predict_request_invalid.json). El primero devuelve HTTP 200 con `prediction`, `probability`, `risk_level`, `model_version` y `request_id`. El segundo devuelve HTTP 422. La cabecera `X-Request-ID` identifica ambas respuestas y permite buscar sus eventos en los logs.

- `/live` comprueba que la aplicación responde. `/ready` comprueba que el modelo está cargado. `/health` informa el estado y, cuando el modelo está disponible, su identidad;
- `LOW` indica score menor que 0,30. `MEDIUM` va desde 0,30 hasta menos de 0,70. `HIGH` empieza en 0,70. Los cortes son ilustrativos y El score permite estimar el riesgo de abandono, aunque no se ha comprobado su calibración como probabilidad.

## CI y despliegue desde GHCR

El [workflow](.github/workflows/ci.yml) se ejecuta con pushes a `entrega-final`. Recupera los artefactos mediante DVC, verifica el hash del modelo, ejecuta pytest y promtool, y construye y prueba la imagen. La ejecución aprobada confirmó que la auditoría de contenido se ejecuta antes del push a GHCR y que un segundo runner descarga el mismo digest y repite la auditoría y el smoke test. [GitHub Actions](https://github.com/yochelo/ISTEA-Laboratorio-Mineria-Datos/actions/runs/45912957905)

La descarga DVC usa `DAGSHUB_DVC_ACCESS_KEY_ID` y `DAGSHUB_DVC_SECRET_ACCESS_KEY` solo en ese paso. GHCR usa `GITHUB_TOKEN`. Las imágenes se identifican por revisión OCI, tag con SHA completo y digest. [Paquete GHCR](https://github.com/yochelo/ISTEA-Laboratorio-Mineria-Datos/pkgs/container/istea-laboratorio-mineria-datos)

El despliegue Linux usa [Compose base](compose.yaml) y la copia operativa `compose.final.yaml`, generada según el [runbook](docs/runbook.md). El [override versionado](compose.linux.yaml) conserva el digest anterior para rollback. El laboratorio se validó en Ubuntu sobre WSL 2 con Docker Engine nativo independiente de Docker Desktop. La aceptación académica de WSL 2 como host Linux distinto sigue pendiente.

Se comprobó la actualización de la API a una nueva imagen, el rollback a la versión anterior y el restablecimiento de la imagen actualizada, sin interrumpir los servicios de Prometheus y Grafana. Consultar la [release v1.0.0](https://github.com/yochelo/ISTEA-Laboratorio-Mineria-Datos/releases/tag/v1.0.0) para obtener la revisión OCI, el digest definitivo y la configuración de despliegue.

### Acceso a los servicios

Una vez iniciado el stack correspondiente, se puede acceder
a los servicios desde las siguientes direcciones:

| Servicio | Desarrollo con Docker | Despliegue Linux |
|---|---|---|
| Swagger | http://localhost:8001/docs | http://localhost:18001/docs |
| Prometheus | http://localhost:9090 | http://localhost:19090 |
| Grafana | http://localhost:3000 | http://localhost:13000 |

## Monitoreo

Prometheus recolecta métricas cada cinco segundos y cuenta
con tres alertas configuradas: indisponibilidad de la API,
latencia elevada y errores del servidor.

Grafana muestra seis paneles que permiten visualizar el
tráfico, la latencia, los errores y los scores del modelo.

Evidently compara los datos de entrenamiento con el lote
simulado y genera reportes en HTML y JSON, junto con
información sobre los datos utilizados. La comparación
detectó drift en **11 de 19 predictores (57,89 %)**,
superando el umbral establecido del 50 %. Esto indica
un cambio en la distribución de los datos, pero no
necesariamente una pérdida de capacidad predictiva.
Para comprobarlo, necesitaríamos conocer los resultados
reales de abandono de los clientes del lote actual.

- [Runbook de arranque, diagnóstico, monitoreo y recuperación](docs/runbook.md)
- [Plan de monitoreo y actuación ante incidentes](docs/plan_monitoreo.md)
- [Decisiones técnicas y evidencia](docs/decisiones_tecnicas.md)
