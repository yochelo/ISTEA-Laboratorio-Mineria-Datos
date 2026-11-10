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
- Dependencias indicadas en `requirements.txt` (incluido DVC)

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
python -m pip install -r requirements.txt
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
