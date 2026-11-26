# Plan de monitoreo y actuación ante incidentes

Prometheus evalúa las tres reglas automáticas cada cinco segundos y muestra sus estados en `/alerts`. Los demás criterios de la matriz orientan la revisión manual. Los sectores son hipotéticos y los canales externos se proponen para una eventual operación productiva.

| Incidente | Condición de detección | Severidad | Sector responsable | Canal de notificación propuesto | Acción esperada |
|---|---|---|---|---|---|
| Error 422 aislado | Una respuesta 422 en `/predict` (manual) | Baja | Desarrollo | Registro en logs, sin notificación inmediata | Consultar el log si se reporta un problema. |
| Validaciones fallidas recurrentes | Aumento repetido de 422 respecto del tráfico habitual (manual) | Media | Desarrollo | Ticket | Investigar origen, cambios de contrato y calidad de las entradas. |
| Latencia elevada sostenida | p95 de inferencia en ventana de cinco minutos > 0,5 s durante diez minutos (automática) | Advertencia | Infraestructura | Ticket o correo operativo | Revisar carga, p95 y recursos del contenedor. |
| Errores 5xx recurrentes | Incremento estimado de al menos dos errores en `/predict` en cinco minutos, sostenido durante cinco minutos (automática) | Advertencia | Backend | Ticket o correo operativo | Correlacionar fallos con logs y diagnosticar el servicio. |
| API inaccesible | `up{job="ml-api"} == 0` durante un minuto (automática) | Crítica | Infraestructura | Aviso a la guardia | Revisar red y contenedor, restablecer y verificar salud e inferencia. |
| Drift elevado persistente | Resultado global de drift en al menos dos ventanas comparables consecutivas (manual, criterio propuesto) | Media | Ciencia de datos | Ticket | Investigar distribuciones y faltantes por segmento, y evaluar desempeño cuando haya etiquetas. |

El umbral de 5xx se eligió para este laboratorio de bajo tráfico. `increase` estima el incremento por ventana y la duración de cinco minutos exige que la condición persista. La ausencia de una serie 5xx es habitual cuando todavía no se han observado errores. Verificar también el estado del target. `up` mide si Prometheus puede recolectar métricas y puede permanecer en 1 aun si el modelo no está listo.

## Procedimiento

1. **Detectar.** Revisar `/alerts` y `/targets` en Prometheus. Usar Grafana para ubicar el inicio y alcance del cambio en tráfico, p95, 5xx, predicciones por versión, scores o 422.
2. **Contener.** Derivar al sector responsable. Ante una caída, comprobar el estado del contenedor y la red. Usar `/ready` para comprobar que hay un modelo listo y `/health` para identificar su versión.
3. **Diagnosticar.** Relacionar el `X-Request-ID` de la respuesta con `request_id` en el log JSON de la API. Correlacionar el momento del fallo con las series de Prometheus. Para drift, usar los reportes por lote de Evidently y cotejar la procedencia, los faltantes y las distribuciones.
4. **Corregir.** Aplicar la corrección identificada y verificar el target, la alerta y la salud del modelo. Comprobar una predicción válida. Si el incidente es de datos, comprobar además una nueva ventana comparable.
5. **Aprender y registrar evidencia.** Guardar tiempos, consultas, identificadores de solicitud relevantes, evidencia de recuperación y acciones acordadas. Revisar los umbrales a partir de la evidencia disponible.

## Mejoras futuras

Evaluar avisos por Telegram, WhatsApp o correo, con selección según severidad y escalamiento si el sector inicial no responde. Automatizar la generación periódica de informes de Evidently y evaluar la publicación de métricas agregadas de drift en Prometheus y Grafana. Actualmente, las alertas se consultan en Prometheus y el análisis de Evidently se ejecuta por lote.
