# Predicción de Churn de Clientes

Proyecto desarrollado para la materia **Laboratorio de Minería de Datos** (ISTEA).

El objetivo es construir un flujo reproducible de análisis, entrenamiento y evaluación de modelos de clasificación para predecir la baja de clientes (*churn*), y exponer el modelo seleccionado mediante una API REST.

## Estructura del proyecto

- `data/`: datos históricos del proyecto, versionados con DVC.
- `notebooks/`: análisis exploratorio inicial.
- `src/data/`: carga de datos.
- `src/features/`: preprocesamiento de variables.
- `src/training/`: entrenamiento y comparación de modelos.
- `src/evaluation/`: evaluación de modelos.
- `models/`: modelo entrenado seleccionado.
- `reports/`: métricas del pipeline.
- `tests/`: pruebas automáticas del procesamiento, modelo y API.
- `app/`: aplicación FastAPI, validación de entradas e inferencia.
- `Dockerfile`, `.dockerignore`, `compose.yaml`: ejecución en contenedor.

## Requisitos

Para ejecutar el proyecto localmente:

- Python 3.11
- Git
- Dependencias indicadas en `requirements-ci.txt` para desarrollo y pruebas (incluido DVC)

Para ejecutar la API mediante contenedores:

- Docker con Docker Compose

## Instalación local (Windows CMD)

Clonar el repositorio e ingresar:

```cmd
git clone https://github.com/yochelo/ISTEA-Laboratorio-Mineria-Datos.git
cd ISTEA-Laboratorio-Mineria-Datos
```

Crear y activar el entorno virtual:

```cmd
python -m venv .venv
.venv\Scripts\activate
```

Instalar dependencias:

```cmd
python -m pip install -r requirements-ci.txt
```

## Obtener datos y modelo (DVC)

Los datos y artefactos están versionados con DVC y almacenados en DagsHub. Se necesitan permisos de lectura y credenciales locales para acceder al almacenamiento remoto.

Configurar un token personal de DagsHub en la configuración **local** de DVC (no incluir tokens reales en archivos versionados):

```cmd
dvc remote modify origin --local access_key_id TU_TOKEN
dvc remote modify origin --local secret_access_key TU_TOKEN
```

Descargar los datos y artefactos:

```cmd
dvc pull -r origin
```

Esto permite disponer, entre otros archivos, de `models/churn_model.joblib`, necesario para iniciar la API. Las credenciales locales no deben subirse a GitHub.

## Pipeline reproducible

El pipeline se define en `dvc.yaml`. Para ejecutarlo:

```cmd
dvc repro
```

Entrena y evalúa los modelos a partir del dataset histórico y genera:

- `models/churn_model.joblib`: pipeline de preprocesamiento y clasificación seleccionado.
- `reports/metrics.json`: métricas de evaluación.

Para consultar las métricas:

```cmd
dvc metrics show
```

Las métricas son accuracy, precision, recall y F1-score (para la clase `Yes`).

## Modelo y experimentos

Se compararon `DummyClassifier` (baseline), `LogisticRegression` y `RandomForestClassifier`. Se seleccionó **Logistic Regression** por su mejor recall para la clase `Yes` entre los modelos evaluados.

El preprocesamiento y el clasificador se guardan juntos como un `Pipeline` de scikit-learn en `models/churn_model.joblib`.

El entrenamiento registra parámetros y métricas en **MLflow**. Para visualizar los experimentos locales:

```cmd
mlflow ui --port 5000
```

Abrir http://localhost:5000. El modelo seleccionado se registró en el **Model Registry local** como `ISTEA_Churn_LogisticRegression` (versión 1).

### Tracking y Model Registry remoto (DagsHub)

El proyecto también registra experimentos en el servidor MLflow de DagsHub:

https://dagshub.com/yochelo/ISTEA-Laboratorio-Mineria-Datos.mlflow/

En el experimento remoto `ISTEA_Churn` se registraron tres ejecuciones (`Baseline`, `Logistic Regression` y `Random Forest`), con sus parámetros y métricas. El modelo `churn_pipeline` está vinculado a la ejecución de Logistic Regression y registrado en el **Model Registry remoto** como `ISTEA_Churn_LogisticRegression`, **versión 1**.

Para enviar ejecuciones nuevas desde Python, se debe configurar `MLFLOW_TRACKING_URI` con la URL anterior y la autenticación de MLflow mediante `MLFLOW_TRACKING_USERNAME` y `MLFLOW_TRACKING_PASSWORD` en el entorno local, antes de entrenar. Se puede usar un token personal de DagsHub como contraseña. **No almacenar tokens ni credenciales en Git, archivos versionados o imágenes Docker.** Si no se configura el tracking remoto, MLflow utiliza su configuración local.

La API actual carga el archivo `models/churn_model.joblib` recuperado con DVC. **Todavía no carga el modelo directamente desde el Registry remoto**, por lo que la versión registrada en DagsHub y el artefacto desplegado deben mantenerse coherentes.

## API REST con FastAPI

Con el entorno virtual activado y el modelo descargado, iniciar desde la raíz del proyecto:

```cmd
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Endpoints disponibles:

- `GET /health`: devuelve `{"status":"ok"}`.
- `POST /predict`: recibe las características de un cliente validadas con Pydantic y devuelve `prediction` (`Yes` o `No`), `probability` (probabilidad estimada de `Yes`), `risk_level` (`LOW`, `MEDIUM`, `HIGH`) y `model_version` (identificador declarado de versión). La respuesta también se valida mediante Pydantic.

Documentación interactiva Swagger: http://localhost:8000/docs

Ejemplo de entrada para `POST /predict`:

```json
{
  "gender": "Female",
  "SeniorCitizen": 0,
  "Partner": "No",
  "Dependents": "No",
  "tenure": 2,
  "PhoneService": "Yes",
  "MultipleLines": "No",
  "InternetService": "Fiber optic",
  "OnlineSecurity": "No",
  "OnlineBackup": "No",
  "DeviceProtection": "No",
  "TechSupport": "No",
  "StreamingTV": "No",
  "StreamingMovies": "No",
  "Contract": "Month-to-month",
  "PaperlessBilling": "Yes",
  "PaymentMethod": "Electronic check",
  "MonthlyCharges": 75.5,
  "TotalCharges": 151.0
}
```

Para ese ejemplo, la respuesta comprobada en Swagger con Docker Compose fue HTTP 200:

```json
{
  "prediction": "Yes",
  "probability": 0.8826254980782651,
  "risk_level": "HIGH",
  "model_version": "1"
}
```

Se definieron umbrales iniciales de riesgo: **LOW** para probabilidad menor que 0.30, **MEDIUM** desde 0.30 y menor que 0.70, y **HIGH** desde 0.70. Son umbrales ilustrativos de negocio, no calibrados ni optimizados mediante validación. La clasificación `Yes/No` proviene de `model.predict` y puede no coincidir con el corte entre niveles de riesgo.

La versión `"1"` se declara explícitamente en `app/inference.py` para identificar el modelo candidato de esta etapa; no se recupera dinámicamente del Registry. En un cambio de artefacto habrá que actualizar y comprobar ese identificador.

Las solicitudes con campos obligatorios ausentes o valores que infringen las restricciones declaradas reciben HTTP 422.

## Pruebas automáticas

Desde la raíz del proyecto, con el entorno virtual activado:

```cmd
python -m pytest tests/ -v
```

Se incluyen seis tests de carga de datos, preprocesamiento, modelo y endpoints API (`/health`, `/predict` y validación de entradas). El test de predicción verifica los cuatro campos obligatorios, sus tipos básicos, la versión declarada y la coherencia del nivel de riesgo con los umbrales.

## Docker y Docker Compose

Antes de construir la imagen, descargar el modelo con DVC si aún no existe localmente. El `Dockerfile` incorpora `models/churn_model.joblib` dentro de la imagen: el contenedor **no entrena** el modelo.

Desde la raíz del proyecto:

```cmd
docker compose up -d --build
```

Consultar el estado del servicio:

```cmd
docker compose ps
```

La API queda publicada en:

- Salud: http://localhost:8001/health
- Swagger: http://localhost:8001/docs

Compose expone el puerto 8001 del equipo hacia el 8000 del contenedor. Para consultar logs básicos de ejecución:

```cmd
docker compose logs churn-api
```

Para detener y eliminar los contenedores y la red creados por Compose (sin borrar la imagen ni los archivos del proyecto):

```cmd
docker compose down
```

## Estado de la segunda entrega

El servicio se probó con Docker Compose y respondió HTTP 200 en `/predict` con los cuatro campos exigidos. Los seis tests locales finalizaron correctamente y el contrato de salida se define con Pydantic. **Pendiente de cierre:** marcar con el tag Git `entrega-2` el commit definitivo verificado.

## Análisis exploratorio

El análisis exploratorio inicial se encuentra en `notebooks/01_eda.ipynb`. El flujo reproducible de entrenamiento fue trasladado al código modular de `src/`.

## Tecnologías utilizadas

Python, pandas, scikit-learn, joblib, pytest, FastAPI, Uvicorn, MLflow, Docker, Docker Compose, Git/GitHub, DVC y DagsHub.

## Calidad de datos y drift

Desde la raíz del repositorio, preparar un entorno Python 3.11 independiente. El siguiente ejemplo es para PowerShell y presupone que `python` apunta a Python 3.11.

```powershell
$monitoringEnv = Join-Path $env:LOCALAPPDATA 'istea-churn-monitoring-venv'
python -m venv $monitoringEnv
$monitoringPython = Join-Path $monitoringEnv 'Scripts/python.exe'
& $monitoringPython -m pip install -r monitoring/requirements.txt
$env:EVIDENTLY_DISABLE_TELEMETRY = '1'
& $monitoringPython -m monitoring.drift_report
```

El análisis requiere los CSV históricos y de producción en las rutas declaradas por sus punteros DVC. Si el CSV de producción todavía no está en el remoto, puede materializarse con `dvc checkout data/production/customer_churn_current.csv.dvc` desde una caché que tenga el objeto. También puede recuperarse del paquete original del profesor y comprobarse contra su checksum.

Abrir `reports/drift_report.html` en el navegador. En el mismo directorio quedan `drift_report.json` con el resultado nativo de Evidently y `drift_provenance.json` con hashes, partición y modelo de referencia. Los tres archivos se regeneran al ejecutar el análisis. El lote de producción carece de etiquetas de churn.

## Alertas operativas

Levantar el stack con `docker compose up -d`. Consultar los estados en [Alertas de Prometheus](http://localhost:9090/alerts), la recolección en [Targets](http://localhost:9090/targets) y el dashboard en [Grafana](http://localhost:3000). Los criterios y el procedimiento de incidente están en el [plan de monitoreo](docs/plan_monitoreo.md).

Con el stack activo, validar la configuración cargada y ejecutar las pruebas sintéticas desde PowerShell:

```powershell
docker compose exec prometheus promtool check config /etc/prometheus/prometheus.yml
docker run --rm --network none --mount "type=bind,source=$PWD/prometheus,target=/etc/prometheus,readonly" --entrypoint /bin/promtool prom/prometheus:v3.5.0 test rules /etc/prometheus/alerts.test.yml
```

Para una demostración controlada de disponibilidad, detener solo `churn-api` con `docker compose stop churn-api`. Observar la alerta hasta que esté en estado `firing` y ejecutar `docker compose up -d churn-api`. Comprobar que el target vuelve a `UP` y revisar `/ready` y `/health`. Al finalizar, ejecutar `docker compose down` para conservar los volúmenes.

## Preparación de CI

Después del checkout de la revisión a verificar, preparar Python 3.11 y ejecutar los pasos en este orden:

```bash
python -m pip install -r requirements-ci.txt
python -m pip check
dvc pull -r origin data/raw/customer_churn_historical.csv.dvc train data/production/customer_churn_current.csv.dvc
python -m pytest -q
docker build --progress=plain -t istea-churn-api:ci .
```

Configurar el paso de `dvc pull` con las variables `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY`, vinculadas a los secretos propuestos `DAGSHUB_DVC_ACCESS_KEY_ID` y `DAGSHUB_DVC_SECRET_ACCESS_KEY`. DVC usa el endpoint S3 de DagsHub definido en `.dvc/config`. Usar credenciales con lectura del repositorio, limitadas al paso de recuperación. [Autenticación de remotos S3 en DVC](https://doc.dvc.org/user-guide/data-management/remote-storage/amazon-s3#environment-variables)

La suite completa usa el CSV histórico y `models/churn_model.joblib`. El target `train` de `dvc pull` recupera el joblib y `reports/metrics.json` según el lock aprobado. El CSV de producción completa la recuperación de evidencias y se usa en el análisis por lotes. Para el build, el Dockerfile copia el joblib, la API y su manifiesto de identidad, e instala `requirements-serving.txt`.

En el futuro runner Linux se deben validar las ruedas de Python 3.11, el acceso de red a DagsHub y el arranque del contenedor. Git conserva CRLF en `requirements.txt` y en los cuatro módulos Python que DVC registra como dependencias de `train`. El build y la publicación versionada en GHCR deben depender del éxito de pytest. Las pruebas HTTP de CI deberán usar datos disponibles en el checkout, por ejemplo el caso válido empleado por la suite. El directorio externo del profesor está disponible en este laboratorio Windows.

Para la etapa de publicación, usar una etiqueta vinculada al SHA de Git y reservar `GITHUB_TOKEN` con `packages: write` para el job de publicación. El checkout requiere `contents: read`. [Publicación de imágenes con GitHub Actions](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images)

### Integración continua en GitHub Actions

El [workflow de integración continua](.github/workflows/ci.yml) se activa con un push a `entrega-final`. En Ubuntu 24.04 instala Python 3.11.9, recupera los cuatro artefactos de DVC y verifica la huella del modelo y el estado del pipeline. Pytest y las verificaciones de Prometheus deben aprobar para que empiece el build. El último paso prueba por HTTP los ejemplos del profesor con el contenedor construido y lo retira al terminar.

Antes del primer push, abrir **Settings → Secrets and variables → Actions → New repository secret**. Crear `DAGSHUB_DVC_ACCESS_KEY_ID` y `DAGSHUB_DVC_SECRET_ACCESS_KEY` con las credenciales existentes que dan acceso de lectura al remoto DagsHub. Las credenciales se exponen únicamente a `dvc pull`. El smoke test admite una diferencia absoluta de `1e-12` en la probabilidad para tolerar redondeo de punto flotante entre plataformas.

El YAML declara `workflow_dispatch`. GitHub habilita el evento cuando el archivo está en la rama predeterminada. Mientras `main` conserve la segunda entrega, usar el disparador por push de `entrega-final` y consultar el resultado en **Actions**. [Requisito de la rama predeterminada](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch)

La primera ejecución por push a `entrega-final` aprobó la recuperación DVC, las 90 pruebas, promtool, el build y el smoke test de `ISTEA_Churn/1`. [Ejecución de GitHub Actions](https://github.com/yochelo/ISTEA-Laboratorio-Mineria-Datos/actions/runs/45897092423)

### Imagen candidata en GHCR

El workflow publica la imagen que aprobó el smoke test y usa un segundo runner para descargarla por digest y repetir la comprobación. La candidata pública verificada corresponde a `sha-1e3ab250c3c29d52ee723a5b533fc1f4cc2d3179`. Su manifiesto admite descarga anónima.

```bash
docker pull ghcr.io/yochelo/istea-laboratorio-mineria-datos@sha256:bb4533c45d25fe198ab5495a60904c469a36fc1dc339ce45fe59268408864079
```

[Paquete GHCR](https://github.com/yochelo/ISTEA-Laboratorio-Mineria-Datos/pkgs/container/istea-laboratorio-mineria-datos) · [Ejecución aprobada](https://github.com/yochelo/ISTEA-Laboratorio-Mineria-Datos/actions/runs/45899392635)
