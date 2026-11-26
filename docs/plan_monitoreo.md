# Plan de monitoreo y actuación ante incidentes

Prometheus evalúa las tres reglas de alerta automáticas cada cinco segundos y permite consultar su estado en /alerts. La siguiente tabla establece cómo actuar ante distintos incidentes, tanto los detectados automáticamente como aquellos que requieren una revisión manual. Los sectores responsables y los canales de notificación son propuestas para una futura implementación en producción.

| Incidente | Condición de detección | Severidad | Sector responsable | Canal de notificación propuesto | Acción esperada |
|---|---|---|---|---|---|
| Error 422 aislado | Una respuesta 422 en `/predict` (manual) | Baja | Desarrollo | Registro en logs, sin notificación inmediata | Consultar el log si se reporta un problema. |
| Validaciones fallidas recurrentes | Aumento repetido de 422 respecto del tráfico habitual (manual) | Media | Desarrollo | Ticket | Investigar el origen de los errores, posibles cambios en el formato de las solicitudes y la calidad de los datos recibidos. |
| Latencia elevada sostenida | p95 de inferencia en ventana de cinco minutos > 0,5 s durante diez minutos (automática) | Advertencia | Infraestructura | Ticket o correo operativo | Revisar carga, p95 y recursos del contenedor. |
| Errores 5xx recurrentes | Incremento estimado de al menos dos errores en `/predict` en cinco minutos, sostenido durante cinco minutos (automática) | Advertencia | Backend | Ticket o correo operativo | Correlacionar fallos con logs y diagnosticar el servicio. |
| API inaccesible | `up{job="ml-api"} == 0` durante un minuto (automática) | Crítica | Infraestructura | Aviso a la guardia | Revisar red y contenedor, restablecer y verificar salud e inferencia. |
| Drift elevado persistente | Drift superior al umbral global del 50 % en al menos dos períodos comparables consecutivos (manual, criterio propuesto) | Media | Ciencia de datos | Ticket | Investigar distribuciones y faltantes por segmento, y evaluar desempeño cuando haya etiquetas. |

El umbral de 5xx se eligió para este laboratorio de bajo tráfico. `increase` estima el incremento por ventana y la duración de cinco minutos exige que la condición persista. La ausencia de una serie 5xx es habitual cuando todavía no se han observado errores. Verificar también el estado del target. `up` mide si Prometheus puede recolectar métricas y puede permanecer en 1 aun si el modelo no está listo.

## Procedimiento

1. **Detectar.** Revisar `/alerts` y `/targets` en Prometheus. Usar Grafana para ubicar el inicio y alcance del cambio en tráfico, p95, 5xx, predicciones por versión, scores o 422.
2. **Contener.** Derivar al sector responsable. Ante una caída, comprobar el estado del contenedor y la red. Usar `/ready` para comprobar que hay un modelo listo y `/health` para identificar su versión.
3. **Diagnosticar.** Relacionar el `X-Request-ID` de la respuesta con `request_id` en el log JSON de la API. Correlacionar el momento del fallo con las series de Prometheus. Para drift, usar los reportes por lote de Evidently y cotejar la procedencia, los faltantes y las distribuciones.
4. **Corregir.** Aplicar la corrección identificada y verificar el target, la alerta y la salud del modelo. Comprobar una predicción válida. Si el incidente es de datos, comprobar además una nueva ventana comparable.
5. **Aprender y registrar evidencia.** Guardar tiempos, consultas, identificadores de solicitud relevantes, evidencia de recuperación y acciones acordadas. Revisar los umbrales a partir de la evidencia disponible.

Los comandos y URLs del despliegue Linux están en el [runbook](runbook.md).

## Referencia de drift

La comparación realizada con Evidently 0.6.7 utilizó las 5.634 filas del conjunto de entrenamiento histórico y las 2.500 del lote de producción simulada. Se detectó drift en 11 de 19 predictores (57,89 %), superando el umbral global del 50 %. Las variables numéricas que presentaron mayores cambios fueron `MonthlyCharges` y `tenure`. `TotalCharges` fue la única variable con valores faltantes, con 19 casos en cada conjunto. Se conserva un registro de los hashes de los datos, la partición utilizada y la versión del modelo.

Como el lote simulado no contiene los resultados reales de abandono, todavía no podemos determinar si estos cambios afectan el desempeño del modelo. Se propone revisar los valores faltantes y los cambios en las distribuciones y los scores, especialmente según el tipo de contrato y el servicio de internet. Cuando se disponga de los resultados reales, se podrán evaluar nuevamente la precisión, el recall y los falsos positivos. [Procedencia y decisiones](decisiones_tecnicas.md#dt-013--calidad-de-datos-y-drift-de-variables--2026-11-26) · [Generar el reporte](runbook.md#evidently)

## Mejoras futuras

Como mejoras futuras, se propone incorporar notificaciones por Telegram, WhatsApp o correo electrónico, según la severidad del incidente, y derivarlas a otro responsable si el sector inicialmente asignado no responde.

También se propone automatizar la generación periódica de informes de Evidently e incorporar métricas de drift en Prometheus para visualizarlas desde Grafana.

En la implementación actual, las alertas se consultan directamente en Prometheus y los informes de Evidently se generan por lote.