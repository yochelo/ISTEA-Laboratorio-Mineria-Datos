
# Predicción de Churn de Clientes

Proyecto desarrollado para la materia Laboratorio de Minería de Datos

El objetivo es construir un flujo reproducible para analizar datos históricos
de clientes y entrenar un modelo de clasificación que permita predecir el churn.

## Estructura del proyecto

- `data/`: datos utilizados por el proyecto.
- `notebooks/`: análisis exploratorio y experimentación inicial.
- `src/data/`: funciones para carga y preparación de datos.
- `src/features/`: preprocesamiento de variables.
- `src/training/`: entrenamiento de modelos.
- `src/evaluation/`: evaluación de modelos.
- `src/inference/`: reservado para la etapa de inferencia.
- `models/`: modelos entrenados.
- `reports/`: métricas generadas por el pipeline.
- `tests/`: pruebas del proyecto.
- `app/`: reservado para la aplicación.

## Requisitos

- Python 3
- Git
- DVC

Las dependencias de Python se encuentran en `requirements.txt`.

## Instalación

Clonar el repositorio:

    git clone https://github.com/yochelo/ISTEA-Laboratorio-Mineria-Datos.git

Ingresar al proyecto:

    cd ISTEA-Laboratorio-Mineria-Datos

Crear un entorno virtual:

    python -m venv .venv

Activarlo en Windows:

    .venv\Scripts\activate

Instalar las dependencias:

    pip install -r requirements.txt

## Obtener los datos

Los datos y artefactos del proyecto se encuentran versionados con DVC y
almacenados en DagsHub.

Para acceder al almacenamiento DVC es necesario contar con permisos de lectura
sobre el repositorio en DagsHub y configurar las credenciales de acceso de
forma local.

Las credenciales de acceso no se almacenan en el repositorio, sino que deben configurarse localmente con un token personal
de DagsHub:

    dvc remote modify origin --local access_key_id TU_TOKEN
    dvc remote modify origin --local secret_access_key TU_TOKEN

Estas credenciales se almacenan únicamente en la configuración local de DVC
y no se versionan con Git.

Una vez configurado el acceso, los datos y artefactos pueden descargarse con:

    dvc pull -r origin



## Ejecutar el pipeline

El pipeline reproducible está definido en `dvc.yaml`.

Para ejecutarlo:

    dvc repro

El proceso utiliza el dataset histórico y ejecuta el entrenamiento y la
evaluación de los modelos.

Como resultado se generan:

- `models/churn_model.joblib`: pipeline entrenado seleccionado.
- `reports/metrics.json`: métricas de evaluación del modelo.

## Consultar las métricas

Las métricas registradas por DVC pueden consultarse con:

    dvc metrics show

Actualmente se registran:

- Accuracy
- Precision
- Recall
- F1-score

## Análisis exploratorio

El análisis exploratorio inicial se encuentra en:

    notebooks/01_eda.ipynb

El notebook se utilizó como espacio de exploración y experimentación.
El flujo reproducible de entrenamiento fue posteriormente trasladado al
código modular ubicado en `src/`.

## Modelo

Durante la experimentación se compararon:

- DummyClassifier como baseline.
- LogisticRegression.
- RandomForestClassifier.

El modelo seleccionado actualmente es Logistic Regression.

El preprocesamiento y el clasificador forman parte de un único Pipeline de
scikit-learn, que se guarda completo en `models/churn_model.joblib`.

## Tecnologías utilizadas

- Python
- pandas
- scikit-learn
- joblib
- Git / GitHub
- DVC
- DagsHub
