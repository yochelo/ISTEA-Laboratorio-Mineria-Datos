# Decisiones técnicas

Registro del proyecto ISTEA Laboratorio de Minería de Datos. Recoge el diseño de la Etapa 1A, la evidencia local de la Etapa 1B y las decisiones aprobadas en la Etapa 1C.

## DT-001 · Datos y preprocesamiento · 2026-11-25

- **Contexto.** El paquete del profesor incluye datos históricos, producción simulada y un lote de scoring. Solo el histórico contiene la etiqueta `Churn`.
- **Decisión adoptada.** Usar el histórico para entrenamiento y evaluación, reservar producción simulada para monitoreo y excluir `customerID` de los predictores. El diseño reutiliza el pipeline existente para tratar los faltantes y ajustar las transformaciones dentro de cada fold.
- **Criterio de evaluación.** El pipeline declara el histórico como entrada y las pruebas verifican la exclusión del identificador y el ajuste del preprocesamiento dentro de cada fold.
- **Resultado observado.** La Etapa 0 confirmó igualdad de SHA-256 entre el histórico del profesor y el CSV local. En la Etapa 1B los seis candidatos compartieron las mismas particiones de validación y el preprocesador se ajustó dentro de cada fold.
- **Evidencia.** [Puntero DVC del histórico](../data/raw/customer_churn_historical.csv.dvc), [partición y predictores](../src/training/train.py) y [preprocesamiento](../src/features/build_preprocessor.py).
- **Limitación.** La evaluación histórica no mide desempeño en producción. El lote de producción simulada carece de etiquetas.

## DT-002 · Comparación y selección · 2026-11-25

- **Contexto.** El código de la segunda entrega compara tres modelos sobre el mismo holdout y selecciona Logistic Regression por nombre.
- **Hipótesis inicial.** Ponderar la clase minoritaria podría reducir los falsos negativos. La regularización puede modificar el equilibrio entre recall y precision.
- **Decisión adoptada.** Comparar seis configuraciones de las familias existentes en cinco folds estratificados con la misma semilla y particiones. Mantener el split 80/20 con semilla 42 y la regla de clasificación de `predict()`. Seleccionar por recall medio entre candidatos con precision media de al menos 0,50, con desempate por F1 y simplicidad. Reajustar al ganador sobre todo el entrenamiento y evaluarlo en el holdout.
- **Criterio de evaluación.** Comparar accuracy, precision, recall, F1, ROC-AUC y matrices de confusión con los mismos folds. Justificar la elección y sus falsos negativos antes de consultar el test.
- **Resultado observado.** La regresión logística con `class_weight="balanced"` y `C=1` obtuvo el mayor recall medio entre los candidatos elegibles. Sobre el mismo holdout de `entrega-2`, el recall pasó de 45,16 % a 72,31 %. Los falsos negativos bajaron de 204 a 103 y los falsos positivos subieron de 85 a 290.
- **Ratificación en la Etapa 1C.** Se acepta la precision de 0,4812 del holdout. El piso de 0,50 se aplica a la media de validación cruzada. Se conserva la configuración seleccionada y la regla de selección aprobada. El holdout se usa exclusivamente para informar el desempeño final.
- **Evidencia.** Experimento local `ISTEA_Churn`, run ganador `5b521ee4632742528e0f6e69edc14350` y run de holdout `d203aaf89f8a4c558c3616a1671c1edb`. Los runs de candidatos contienen `validation.json`. El run final contiene `holdout_confusion_matrix.json`. [Parámetros](../params.yaml) y [pruebas](../tests/test_training.py).
- **Ejecución definitiva · 2026-11-25.** El ganador y las métricas de validación y holdout coincidieron con la Etapa 1B. Se verificaron cinco folds únicos por candidato. El baseline conserva registros repetidos de los mismos pasos en el mismo run debido a la reanudación. [Validación del ganador](https://dagshub.com/yochelo/ISTEA-Laboratorio-Mineria-Datos.mlflow/#/experiments/0/runs/eae4f71c2f884254ada305938f0b8417) · [Run final y matriz de holdout](https://dagshub.com/yochelo/ISTEA-Laboratorio-Mineria-Datos.mlflow/#/experiments/0/runs/778771c7af9e40dcb771cc5becfc9142)
- **Limitaciones.** El holdout ya se utilizó en la entrega anterior. Permite comparar ambas versiones, con valor limitado como evaluación inédita. La ausencia de costos comerciales reales impide establecer una configuración económicamente óptima. La ponderación modifica la función objetivo y puede afectar la interpretación de las probabilidades como riesgo absoluto. La justificación de los niveles de riesgo en serving deberá considerar esta limitación y la calibración del modelo.

## DT-003 · Reproducibilidad y linaje · 2026-11-25

- **Contexto.** La auditoría encontró que el lock conserva la huella de un script de entrenamiento anterior. La versión registrada y el archivo servido tienen identidades independientes.
- **Decisión adoptada.** Mantener un stage DVC, fijar las dependencias relevantes y regenerar el lock con DVC. Usar Git para identificar la revisión base y MLflow para conservar el diff de entrenamiento mientras el código esté sin commit. DVC versiona datos y salidas. El nombre aprobado para el futuro registro es `ISTEA_Churn`. La publicación requiere autorización posterior.
- **Criterio de evaluación.** El estado DVC queda limpio tras la ejecución. La versión registrada resuelve al run y al commit esperados. El archivo de serving recuperado desde DVC y el adjunto de la versión registrada comparten SHA-256.
- **Resultado observado.** DVC regeneró el lock y confirmó que el stage quedó al día. El archivo adjunto al modelo en MLflow local y el artefacto DVC coincidieron byte a byte. Se preservaron los objetos de la segunda entrega.
- **Ejecución definitiva.** El primer commit identifica el código, los parámetros y las dependencias. La corrida se inicia desde un checkout limpio de ese commit y MLflow registra su SHA. Un commit posterior incorpora el `dvc.lock` regenerado y referencia el SHA de entrenamiento y el run final. Los binarios y las métricas se conservan como objetos DVC.
- **Evidencia.** [Stage DVC](../dvc.yaml) y [lock](../dvc.lock). La corrida de referencia está en el tracking temporal local `istea-etapa1b-e21c65c3-verified`. Su run final `d203aaf89f8a4c558c3616a1671c1edb` conserva `training_source.diff` y enlaza el modelo MLflow `m-79eff5ead27d470ebe18701ded5f0c65`.
- **Verificación en la Etapa 1C.** La instalación desde [requirements.txt](../requirements.txt) en un entorno virtual independiente de Windows con Python 3.11.9 completó `pip check` y la [suite de pruebas](../tests/) con éxito. MLflow resolvió los URI local y remoto a partir de `MLFLOW_TRACKING_URI`.
- **Verificación definitiva · 2026-11-25.** Los siete runs de DagsHub registraron el SHA de entrenamiento `df24557f88252f76fba52bb0da7549509399dac4` con código limpio. El cliente nativo recuperó el paquete MLflow `m-fa3f9127d08e47d6ae9f1e490dc14c3e`, con firma de 19 entradas, el modelo `skops` y el adjunto `extra_files/churn_model.joblib`. El adjunto coincide byte a byte con la salida del stage DVC. [Run final de DagsHub](https://dagshub.com/yochelo/ISTEA-Laboratorio-Mineria-Datos.mlflow/#/experiments/0/runs/778771c7af9e40dcb771cc5becfc9142) · [Lock definitivo](../dvc.lock)
- **Limitaciones.** La instalación fija las dependencias declaradas y deja que pip resuelva las transitivas restantes. La publicación de los objetos DVC y del modelo en Model Registry permanece pendiente.

## DT-004 · Identidad del modelo servido · 2026-11-25

- **Contexto.** FastAPI carga un archivo local y expone una versión fija. Sustituir el archivo puede mantener la misma versión declarada.
- **Propuesta de diseño.** Conservar la carga local y acompañarla con un manifiesto que declare la versión exacta del Registry y el SHA-256 esperado. Verificar el digest antes de deserializar y exponer la identidad verificada.
- **Criterio de evaluación.** El artefacto correcto inicia el servicio y reproduce una predicción de referencia. Un archivo sustituido falla antes de deserializarse.
- **Resultado observado.** La Etapa 0 confirmó que el modelo de la imagen existente coincide byte a byte con el local. La verificación al arranque queda pendiente de la subetapa de serving.
- **Evidencia de partida.** [Carga del modelo](../app/model_loader.py), [versión declarada](../app/inference.py) y [empaquetado de la imagen](../Dockerfile).
- **Trade-off.** El arranque puede funcionar sin conexión al Registry. Cada cambio de modelo exige actualizar de forma coordinada el artefacto y su manifiesto.
