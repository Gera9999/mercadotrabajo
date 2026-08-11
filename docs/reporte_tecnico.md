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



### VERSION 2

### Parte 1 · Diagnóstico y propuesta de mejora

### A. Diagnóstico crítico del tablero

### A.1 Calidad de los datos

El tablero comunica una síntesis útil, pero presenta problemas verificables. Rotula la inversión como “$274.534.765 miles”, mientras la suma de Monto Vigente Contrato es $274.534.765; si la fuente está en pesos, el término “miles” sobredimensiona el total mil veces. También señala que “un tercio” de 120 obras está en ejecución o adjudicado, cuando son 45 (37,5%), por lo que corresponde indicar “cerca de cuatro de cada diez”. El KPI de 5.486 avisos no explicita periodo ni método de cálculo; la fuente completa suma 7.287 entre enero de 2025 y abril de 2026, por lo que la cifra no es auditable desde la interfaz. Las tasas de ocupación y desocupación tampoco presentan fuente ni periodo, lo que impide reproducirlas.

### A.2 Visualizaciones

La línea mensual es adecuada para mostrar tendencia, pero debe explicitar unidades y corte temporal. Las tablas extensas de obras requieren agregación previa por comuna y estado antes del detalle. Para usuarios de decisión conviene ordenar barras, usar formato de moneda compacta y asignar colores con significado consistente. Estos ajustes reducen carga cognitiva y facilitan la comparación.

### A.3 Consistencia interna

El ranking mezcla prioridad, demanda y cursos sin explicar si la prioridad proviene de encuesta o de una fórmula, lo que puede inducir interpretaciones erróneas. La discrepancia entre los 5.486 avisos del KPI y los 7.287 de la fuente impide conciliar secciones. Además, una ocupación puede tener varios cursos; si se unen tablas sin controlar granularidad, se duplican registros y se distorsiona la comparación entre ranking, demanda y oferta formativa.

### A.4 Limitaciones y riesgos técnicos

Las fuentes y la presentación están acopladas, obligando a rehacer tableros por región. Los reemplazos manuales carecen de validaciones, con riesgo de publicar datos incompletos. No se informa fecha de actualización ni linaje de datos, lo que afecta confiabilidad. Finalmente, valores nulos y textos no normalizados pueden sesgar indicadores o romper procesos si no se controlan.

### B. Propuesta de mejora o reconstrucción

### B.1 Flujo de datos mantenible y escalable

Se propone una arquitectura por capas (tipo Medallón): fuentes crudas inmutables (Bronze), procesos ETL que validan y normalizan (Silver), y datos curados integrados (Gold), con una capa de presentación independiente. codigo_ciuo actúa como dimensión común, junto con región y periodo. Esto permite incorporar nuevas regiones sin duplicar lógica ni crear tableros paralelos.

### B.2 Herramientas y tecnologías

Se utilizaría Python y pandas para ETL, Streamlit y Plotly para visualización, pytest para pruebas, Git para versionado y Docker para despliegue reproducible. Es un stack abierto, sin licencias por usuario y portable. Si el volumen crece, PostgreSQL puede reemplazar archivos procesados sin alterar la capa de visualización.

### B.3 Separación entre datos y presentación

La presentación no debe modificar datos ni contener lógica de limpieza: solo consume productos validados. El ETL recibe parámetros (región, periodo, fuente) y publica tablas homogéneas. Una configuración por región permite escalar sin duplicar código. Esta separación mejora mantenibilidad y permite interfaces adaptables a distintos dispositivos.

### B.4 Automatización y puesta en producción

Las fuentes se alojan en repositorios institucionales organizados por región y periodo. Un proceso programado ejecuta el ETL, valida esquemas y consistencia, y solo publica resultados si los controles se cumplen. En caso contrario, se mantiene la versión anterior. La aplicación se despliega en contenedores accesibles vía web, con autenticación institucional y visualización de fecha de actualización.

### B.5 Uso de inteligencia artificial con resguardos

La IA puede asistir en la detección de inconsistencias o clasificación de datos, pero no debe modificar información automáticamente. Cada sugerencia debe ser validada por un humano y registrada. Las reglas deterministas y controles siguen siendo la base de la calidad. Como apoyo, se puede incorporar un asistente que explique indicadores usando datos agregados, sin acceso a fuentes ni capacidad de modificación.

### B.6 Mejora prioritaria

Con recursos limitados, la prioridad es implementar un ETL automatizado con validaciones y parametrización por región. Esto reduce el riesgo de errores, mejora la sostenibilidad y permite escalar. Además, establece una base confiable para futuras mejoras en visualización y despliegue.

Supuestos y limitaciones

Se asume uso de CLP, fechas en formato día-mes-año y CIUO como identificador textual. Las limitaciones incluyen datos ficticios de una región, ausencia de fuentes para tasas laborales y alta cantidad de valores faltantes en remuneraciones, los cuales no se imputan.


## Parte 2 · Construcción y guía de entrega

Se eligió la Vía B con Python, pandas, Streamlit y Plotly por reproducibilidad, portabilidad y ausencia de licencias. El anexo ejecutable es `src/app.py`: presenta Panorama, Demanda, Inversión y Recomendaciones mediante navegación lateral, con filtros de región, periodo, estado, ocupación y fuente. Cada módulo cierra con hallazgos calculados y dispone de un asistente contextual opcional. `docs/diseno_estructura.md` contiene el boceto obligatorio, la pregunta de cada sección y su dato. `src/etl.py` es el anexo técnico del cruce y las transformaciones; `tests/test_etl.py` documenta controles ejecutables.

El ETL lee cuatro fuentes base sin alterarlas. En obras, elimina puntos de miles, convierte montos a enteros y parsea fechas con formatos mixtos y día primero. En avisos, convierte textos como “55 avisos”, normaliza meses a una fecha mensual y preserva remuneraciones faltantes como nulos con bandera de calidad. Los encabezados pasan a `snake_case`; textos se recortan; CIUO se conserva como texto. Recomendaciones y cursos se unen por `codigo_ciuo` mediante relación uno-a-muchos validada: una prioridad puede ofrecer varios cursos. Los indicadores incluyen suma de inversión, avisos, vacantes, obras, cursos y cupos.

Las dos visualizaciones principales responden: “¿En qué comunas se concentra la inversión?” mediante barras ordenadas de monto y contratos, y “¿Qué cursos responden a las ocupaciones prioritarias?” mediante cupos y número de cursos según ranking. Demanda y tendencia mensual entregan contexto sin sustituir esas decisiones.

Para la Tarea 4 se puede seleccionar `02_avisos_empleo_ACTUALIZADO_mayo.xlsx` en la barra lateral o ejecutar `python src/etl.py --avisos-file 02_avisos_empleo_ACTUALIZADO_mayo.xlsx`. No se toca código. El modelo cambia de 160 a 170 filas y de abril a mayo de 2026; una prueba confirma que las 160 filas previas y las tablas de obras, recomendaciones y cursos no cambian. En carpeta compartida, un scheduler descargaría la última versión, ejecutaría pruebas/ETL y publicaría solo si pasan.

Limitaciones: no se infieren salarios faltantes, no existen tasas laborales en los archivos y el catálogo no distingue vigencia del curso. La demostración local no incorpora autenticación institucional.

**Declaración de IA:** se utilizó GitHub Copilot como apoyo para inspección, programación, pruebas y redacción. Las reglas y cifras fueron verificadas contra las fuentes mediante código reproducible.
