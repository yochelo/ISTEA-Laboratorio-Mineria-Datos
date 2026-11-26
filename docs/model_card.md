# Model Card · ISTEA_Churn/1

## Propósito y uso

Modelo de clasificación binaria que estima el riesgo de abandono (Churn=Yes) de clientes de una empresa de telecomunicaciones. El score y el nivel de riesgo ayudan a priorizar acciones de retención con criterio humano. El modelo no debe utilizarse para penalizar automáticamente a clientes, negarles servicios ni aplicar condiciones comerciales desfavorables.

## Datos y preprocesamiento

Los datos provienen del paquete académico del profesor. Su README y su licencia los identifican como sintéticos, sin información personal real y destinados a uso educativo dentro del curso. Los conjuntos cumplen funciones distintas.

| Conjunto | Filas | Uso |
|---|---:|---|
| Histórico | 7.043 | Contiene `Churn`. Se usaron 5.634 filas para entrenamiento y validación cruzada, y 1.409 para holdout. El 26,37 % del histórico pertenece a la clase positiva. |
| Producción simulada | 2.500 | Simula un período posterior y carece de `Churn`. Se usa para calidad y drift. |
| Scoring | 100 | Carece de etiqueta y se reserva para pruebas de inferencia. |

El pipeline excluye `customerID` y usa 19 predictores. Los numéricos son `tenure`, `MonthlyCharges` y `TotalCharges`. Los categóricos cubren género, condición de persona mayor, pareja y dependientes, telefonía, internet y sus complementos, contrato, facturación y forma de pago. Se imputan numéricos por mediana y se escalan. Las categorías se imputan por moda y se codifican con one-hot. El preprocesador se ajusta dentro de cada fold. [Implementación](../src/features/build_preprocessor.py)

## Comparación y selección

Se usó una partición estratificada 80/20, semilla 42, con cinco folds estratificados sobre el conjunto de entrenamiento. El criterio fue maximizar el recall medio con precisión media de al menos 0,50. Los empates se resuelven por F1 y luego por el orden de simplicidad configurado. Las cifras son medias de los runs definitivos de MLflow.

| Configuración | Accuracy CV | Precisión CV | Recall CV | F1 CV | ROC-AUC CV |
|---|---:|---:|---:|---:|---:|
| Baseline de clase mayoritaria | 0,7364 | 0,0000 | 0,0000 | 0,0000 | 0,5000 |
| Regresión logística | 0,8012 | 0,6705 | 0,4835 | 0,5617 | 0,8278 |
| **Regresión logística balanceada, C=1** | **0,7416** | **0,5067** | **0,7684** | **0,6104** | **0,8277** |
| Regresión logística balanceada, C=0,1 | 0,7389 | 0,5033 | 0,7630 | 0,6063 | 0,8278 |
| Random Forest | 0,7923 | 0,6569 | 0,4444 | 0,5301 | 0,8008 |
| Random Forest balanceado | 0,7710 | 0,5612 | 0,6040 | 0,5816 | 0,8004 |

En el conjunto de evaluación, el modelo seleccionado obtuvo **accuracy 0,7211**, **precisión 0,4812**, **recall 0,7231**, **F1 0,5779** y **ROC-AUC 0,8117**. El mínimo de precisión establecido como criterio de selección se aplica a la validación cruzada. [Run final y matriz de holdout](https://dagshub.com/yochelo/ISTEA-Laboratorio-Mineria-Datos.mlflow/#/experiments/0/runs/778771c7af9e40dcb771cc5becfc9142)

| Clase real | Predicción No | Predicción Yes |
|---|---:|---:|
| No | 747 | 290 |
| Yes | 103 | 269 |

En el mismo holdout, frente al modelo de entrega-2, el recall pasó de 45,16 % a 72,31 %, los falsos negativos disminuyeron de 204 a 103 y los falsos positivos aumentaron de 85 a 290. Esto permitió detectar 101 casos adicionales de abandono, aunque también se generaron 205 falsos positivos adicionales. Para este problema, se priorizó detectar clientes en riesgo de abandono, aun cuando esto pueda implicar más contactos innecesarios. Sin conocer los costos reales de retención y abandono, no podemos determinar cuál sería el equilibrio económicamente más conveniente.

## Niveles de riesgo y límites

| Nivel | Intervalo de score | Filas en holdout | Casos con churn | Abandono observado |
|---|---|---:|---:|---:|
| LOW | Menor que 0,30 | 584 | 38 | 6,51 % |
| MEDIUM | De 0,30 a menos de 0,70 | 523 | 149 | 28,49 % |
| HIGH | Desde 0,70 | 302 | 185 | 61,26 % |

Los niveles son cortes ilustrativos y la clasificación binaria proviene de `predict()`. Los conteos describen grupos definidos por score dentro del mismo holdout. La ponderación de clases puede afectar la interpretación del score y No se comprobó la calibración del modelo. El holdout se reutilizó para comparar con la segunda entrega. No hay validación temporal ni evaluación de desempeño por subgrupos demográficos. [DT-006](decisiones_tecnicas.md#dt-006--estados-http-y-niveles-de-riesgo--2026-11-25)

## Identidad y revisión

La versión `ISTEA_Churn/1` apunta al run `778771c7af9e40dcb771cc5becfc9142`, entrenado desde `df24557f88252f76fba52bb0da7549509399dac4`. El joblib del Registry, el de DVC y el del contenedor desplegado coincidieron con el SHA-256 `be71d167d616f72260f4b04181971c6b76ff9f8a86cd20d32bbf7991eee7937e`. La API verifica el SHA-256 antes de cargar el modelo. [Registro](https://dagshub.com/yochelo/ISTEA-Laboratorio-Mineria-Datos.mlflow/#/models/ISTEA_Churn/versions/1) · [Manifiesto](../app/model_manifest.json)

Evidently detectó cambios en 11 de 19 predictores del lote simulado. Revisar faltantes, distribuciones y scores por contrato y servicio de internet si el drift se repite en ventanas comparables. Cuando se disponga de los resultados reales de abandono, medir recall, precisión y falsos positivos antes de decidir cambios. [Plan de monitoreo](plan_monitoreo.md)
