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

Abrir http://localhost:5000. El modelo seleccionado se registró en el **Model Registry local** como `ISTEA_Churn_LogisticRegression` (versión 1). La conexión del tracking de MLflow a DagsHub todavía está pendiente; DagsHub ya se utiliza para el almacenamiento remoto DVC.

## API REST con FastAPI

Con el entorno virtual activado y el modelo descargado, iniciar desde la raíz del proyecto:

```cmd
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Endpoints disponibles:

- `GET /health`: devuelve `{"status":"ok"}`.
- `POST /predict`: recibe los datos de un cliente y devuelve `prediction` (`Yes` o `No`) y `probability` (probabilidad estimada de `Yes`).

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

Para ese ejemplo, el modelo probado devuelve `prediction: "Yes"` y una probabilidad aproximada de `0.8826`. Los datos incompletos o inválidos reciben un error de validación HTTP 422.

## Pruebas automáticas

Desde la raíz del proyecto, con el entorno virtual activado:

```cmd
python -m pytest tests/ -v
```

Se incluyen seis tests de carga de datos, preprocesamiento, modelo y endpoints API (`/health`, `/predict` y validación de entradas).

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

Compose expone el puerto 8001 del equipo hacia el 8000 del contenedor. Para detener y eliminar los contenedores y la red creados por Compose (sin borrar la imagen ni los archivos del proyecto):

```cmd
docker compose down
```

## Análisis exploratorio

El análisis exploratorio inicial se encuentra en `notebooks/01_eda.ipynb`. El flujo reproducible de entrenamiento fue trasladado al código modular de `src/`.

## Tecnologías utilizadas

Python, pandas, scikit-learn, joblib, pytest, FastAPI, Uvicorn, MLflow, Docker, Docker Compose, Git/GitHub, DVC y DagsHub.
