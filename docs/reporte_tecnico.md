# Reporte técnico de la plataforma de BI

## Parte A · Diagnóstico crítico del tablero

### Calidad, visualización y consistencia

El tablero de ejemplo presenta problemas verificables. Rotula la inversión como "$274.534.765 miles", aunque la suma de `Monto Vigente Contrato` es $274.534.765; si la fuente está en pesos, la etiqueta multiplica el total por mil. También llama "un tercio" a 45 de 120 obras en ejecución o adjudicadas: equivale a 37,5%, más cercano a cuatro de cada diez. El KPI de 5.486 avisos no declara periodo ni método, mientras la fuente completa suma 7.287 entre enero de 2025 y abril de 2026. Las tasas laborales no indican fuente ni corte, por lo que no son auditables.

La tendencia mensual es pertinente, pero requiere unidad y fecha de corte. Las obras deben resumirse por comuna y estado antes del detalle; barras ordenadas, moneda compacta y colores con significado constante facilitan comparar territorios y montos durante una proyección. El ranking mezcla prioridad, demanda y cursos sin explicar si la prioridad procede de encuesta o fórmula. Además, una ocupación puede tener varios cursos: una unión sin controlar cardinalidad duplicaría registros y distorsionaría la comparación.

### Riesgos y propuesta

Fuentes y presentación acopladas obligan a reconstruir cada región; reemplazos manuales pueden publicar datos parciales; y sin fecha, linaje ni controles las autoridades y auditoría no pueden juzgar vigencia. Los salarios nulos y textos como "55 avisos" pueden sesgar indicadores o romper cargas si se convierten silenciosamente.

La propuesta usa una arquitectura por capas: fuentes inmutables en `data/raw` (Bronze), ETL validado con pandas (Silver), tablas curadas en `data/processed` (Gold) y Streamlit/Plotly para presentar. `codigo_ciuo` es la dimensión común entre demanda, recomendaciones y cursos; región y periodo son dimensiones obligatorias. Python, pandas, Streamlit, Plotly, pytest, Git y Docker son abiertos, portables y sin licencias por usuario. PostgreSQL puede reemplazar los CSV procesados al crecer el volumen, sin cambiar la interfaz.

La presentación solo consume productos validados; el ETL recibe región, periodo y fuente como parámetros, habilitando una aplicación común para varias regiones. En una carpeta institucional, un scheduler ejecutaría ETL y pruebas tras cada actualización; si falla esquema, tipo o consistencia, conserva la versión anterior. El despliegue objetivo es un servicio Docker con HTTPS, autenticación institucional y fecha de actualización visible.

La IA puede sugerir equivalencias de glosas o anomalías, siempre con confianza, dato original y aprobación humana. El asistente del tablero solo recibe agregados activos, no archivos ni herramientas, y reconoce cuando el contexto es insuficiente. Con recursos limitados, la prioridad es un ETL automatizado y parametrizado: reduce el riesgo transversal y habilita mejoras visuales sobre datos confiables.

## Parte 2 · Construcción y guía de entrega

Se eligió la Vía B con Python, pandas, Streamlit y Plotly: permite limpieza repetible, visualización reproducible y software abierto. El anexo ejecutable es `src/app.py`; contiene Panorama, Demanda, Inversión y Recomendaciones, filtros de región, periodo, estado, ocupación y fuente, y hallazgos calculados. `docs/diseno_estructura.md` es el boceto argumentado: muestra secciones, preguntas, datos y flujo. `src/etl.py` contiene transformaciones y cruces; `tests/test_etl.py` documenta controles ejecutables.

El ETL conecta las cuatro fuentes sin editarlas. En obras transforma puntos de miles a monto numérico y normaliza fechas; en avisos extrae números desde textos, normaliza meses y preserva salarios ausentes como nulos con marca de calidad. Recomendaciones y cursos se relacionan por `codigo_ciuo` en una relación uno-a-muchos validada, porque una ocupación puede ofrecer varios cursos. Los indicadores son inversión, avisos, vacantes, obras, cursos y cupos. Las visualizaciones clave responden dónde se concentra la inversión por comuna y qué cursos cubren las ocupaciones priorizadas.

Para actualizar la Tarea 4 se selecciona `02_avisos_empleo_ACTUALIZADO_mayo.xlsx` o se ejecuta `python src/etl.py --avisos-file 02_avisos_empleo_ACTUALIZADO_mayo.xlsx`; no se cambia código. El modelo pasa de 160 a 170 filas y de abril a mayo de 2026. La prueba verifica que las 160 filas previas, obras, recomendaciones y cursos no cambien. En una carpeta compartida, el scheduler descargaría la fuente, ejecutaría pruebas y ETL, y publicaría solo si pasan.

Supuestos: montos en CLP, fechas día-mes-año, abreviaturas mensuales en español y CIUO textual. Limitaciones: datos ficticios de una región, falta de fuente para tasas laborales, remuneraciones ausentes sin imputar y catálogo sin vigencia de cursos. La demostración local no incorpora autenticación institucional.

**Declaración de IA:** se utilizó GitHub Copilot para inspección, programación, pruebas y redacción; reglas y cifras fueron verificadas con código reproducible.