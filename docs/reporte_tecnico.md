# Reporte técnico de la plataforma de BI

## Parte A · Diagnóstico crítico del tablero

### A.1 Calidad de los datos

El tablero de ejemplo comunica una síntesis útil, pero contiene problemas verificables. Rotula la inversión como “$274.534.765 miles”, mientras la suma de `Monto Vigente Contrato` es $274.534.765; si la fuente está en pesos, “miles” sobredimensiona el total mil veces. También describe que “un tercio” de 120 obras está en ejecución o adjudicado: son 45, equivalentes a 37,5%, por lo que debe expresarse como “cerca de cuatro de cada diez”. El KPI de 5.486 avisos de doce meses no explicita meses de corte ni método; la fuente base completa suma 7.287 entre enero de 2025 y abril de 2026, de modo que la cifra no es auditable desde la interfaz. Las tasas de desocupación y ocupación tampoco tienen fuente, periodo ni tabla entregada, impidiendo reproducirlas.

### A.2 Visualizaciones

La línea mensual es apropiada para tendencia, pero debería mostrar corte y unidades. Las tablas extensas de obras requieren agrupación por comuna y estado antes del detalle. Para una autoridad conviene ordenar las barras, usar moneda compacta y reservar los colores para significados consistentes; estos cambios reducen la carga de lectura y facilitan comparar territorios y montos.

### A.3 Consistencia interna

El ranking mezcla prioridad, demanda y cursos sin explicar si la prioridad proviene exclusivamente de encuesta o de una fórmula; esto puede inducir una causalidad inexistente. La discrepancia entre el KPI de 5.486 avisos y los 7.287 avisos verificables en la fuente también impide conciliar las secciones del tablero. Una ocupación prioritaria puede tener varios cursos, por lo que sumar después de un join sin controlar granularidad duplicaría atributos de recomendación y alteraría la comparación entre ranking, demanda y oferta formativa.

### A.4 Limitaciones y riesgos técnicos

Primero, fuentes y presentación acopladas obligan a rehacer cada tablero regional, afectando al equipo mantenedor y haciendo inviable incorporar regiones de manera sostenible. Segundo, reemplazos manuales carecen de validaciones y pueden publicar columnas cambiadas o datos parciales, afectando decisiones de compra de las autoridades. Tercero, no se exhiben fecha de actualización, linaje ni controles, lo que afecta a autoridades y auditoría al impedir evaluar vigencia y confiabilidad. Cuarto, los 77 nulos salariales del corte base y textos como “55 avisos” pueden sesgar indicadores o romper cargas si se convierten silenciosamente, afectando tanto a analistas como a quienes toman decisiones basadas en esos indicadores.

## Parte B · Propuesta de mejora o reconstrucción

### B.1 Flujo de datos mantenible, escalable y actualizable

Propongo una Arquitectura Medallón adaptada (por capas): fuentes inmutables en data/raw (Capa Bronze); ETL con pandas que valida esquemas, normaliza y registra metadatos (Capa Silver); productos curados e integrados en data/processed (Capa Gold); y Streamlit/Plotly en la capa de presentación. codigo_ciuo actúa como una dimensión conformada para demanda, recomendaciones y cursos, mientras que region y periodo son dimensiones obligatorias. Esta estructura permite incorporar nuevas regiones mediante parametrización de datos y archivos de configuración, sin duplicar código ni crear tableros paralelos.

### B.2 Herramientas y tecnologías de código abierto

Utilizaría Python y pandas para el ETL, Streamlit y Plotly para la visualización, pytest para controles de regresión, Git para versionado y un contenedor Docker para despliegue reproducible. Este stack es abierto, ampliamente mantenido, portable y evita licencias por usuario. Para una operación con más volumen, PostgreSQL puede reemplazar los CSV procesados sin modificar la capa de presentación, preservando el control de costos y la arquitectura por capas.

### B.3 Separación entre datos y presentación para múltiples regiones

La capa de presentación no debe modificar fuentes ni contener lógica de limpieza: sólo consume productos validados. El ETL recibe región, periodo y origen como parámetros, y publica tablas con el mismo esquema para todas las regiones. Una configuración por región resuelve ubicaciones de fuentes y reglas locales; así, una sola aplicación y una sola base de código atienden varias regiones sin duplicar el esfuerzo. Git aporta trazabilidad y pytest protege reglas críticas compartidas.

### B.4 Automatización y puesta en producción

En producción, la ingesta y el despliegue se gestionan mediante un pipeline de CI/CD (ej. mediante GitHub Actions o un orquestador de tareas) que detecta nuevos archivos en SharePoint o Drive vía API, ejecuta pruebas unitarias/de calidad (pytest) y actualiza las salidas de forma atómica solo tras aprobar los controles. Un contenedor Docker desplegado tras un proxy HTTPS con autenticación institucional sirve la aplicación de Streamlit para consulta web. La operación se complementa con gestión de secretos, trazabilidad de logs y versionado de artefactos; si los nuevos datos fallan en las validaciones, el pipeline cancela la ejecución y mantiene activa la versión estable anterior, eliminando la dependencia de procesos manuales.

### B.5 Uso de inteligencia artificial con resguardos

La IA puede sugerir equivalencias para glosas nuevas o anomalías semánticas durante la limpieza, acelerando la clasificación y el hallazgo de valores sospechosos. Nunca debe modificar datos automáticamente: cada sugerencia debe incluir confianza, dato original y decisión humana. Las reglas deterministas, el catálogo CIUO, el registro de decisiones y las pruebas siguen siendo la autoridad para no comprometer calidad ni trazabilidad.

Como mejora concreta adicional, cada módulo incorpora un asistente conversacional no invasivo que explica, resume y compara los indicadores visibles según los filtros activos. Solo recibe agregados de la vista, no acceso a archivos, ETL ni herramientas; su instrucción de sistema limita las respuestas al mercado laboral presentado, prohíbe modificar código o datos y exige reconocer cuando el contexto es insuficiente. Esto reduce la barrera de lectura para autoridades sin reemplazar los hallazgos reproducibles ni convertir una respuesta generativa en evidencia. La clave se gestiona mediante secretos de Streamlit, nunca en el repositorio; sin ella, el tablero conserva toda su funcionalidad analítica.

### B.6 Mejora prioritaria con recursos limitados

Con recursos limitados priorizaría primero un ETL automatizado con controles y actualización parametrizada por región. Corrige la condición crítica de sostenibilidad, reduce el riesgo transversal de datos erróneos y evita replicar trabajo al incorporar nuevas regiones. También crea una base confiable sobre la cual mejorar visualizaciones y desplegar el servicio institucional.

Supuestos: montos en CLP; fechas día-mes-año; abreviaturas mensuales en español; CIUO como identificador textual. Limitaciones: datos ficticios de una región, ausencia de fuente para tasas laborales y alta falta de remuneraciones; estas últimas no se imputan.

## Parte 2 · Construcción y guía de entrega

Se eligió la Vía B con Python, pandas, Streamlit y Plotly por reproducibilidad, portabilidad y ausencia de licencias. El anexo ejecutable es `src/app.py`: presenta Panorama, Demanda, Inversión y Recomendaciones mediante navegación lateral, con filtros de región, periodo, estado, ocupación y fuente. Cada módulo cierra con hallazgos calculados y dispone de un asistente contextual opcional. `docs/diseno_estructura.md` contiene el boceto obligatorio, la pregunta de cada sección y su dato. `src/etl.py` es el anexo técnico del cruce y las transformaciones; `tests/test_etl.py` documenta controles ejecutables.

El ETL lee cuatro fuentes base sin alterarlas. En obras, elimina puntos de miles, convierte montos a enteros y parsea fechas con formatos mixtos y día primero. En avisos, convierte textos como “55 avisos”, normaliza meses a una fecha mensual y preserva remuneraciones faltantes como nulos con bandera de calidad. Los encabezados pasan a `snake_case`; textos se recortan; CIUO se conserva como texto. Recomendaciones y cursos se unen por `codigo_ciuo` mediante relación uno-a-muchos validada: una prioridad puede ofrecer varios cursos. Los indicadores incluyen suma de inversión, avisos, vacantes, obras, cursos y cupos.

Las dos visualizaciones principales responden: “¿En qué comunas se concentra la inversión?” mediante barras ordenadas de monto y contratos, y “¿Qué cursos responden a las ocupaciones prioritarias?” mediante cupos y número de cursos según ranking. Demanda y tendencia mensual entregan contexto sin sustituir esas decisiones.

Para la Tarea 4 se puede seleccionar `02_avisos_empleo_ACTUALIZADO_mayo.xlsx` en la barra lateral o ejecutar `python src/etl.py --avisos-file 02_avisos_empleo_ACTUALIZADO_mayo.xlsx`. No se toca código. El modelo cambia de 160 a 170 filas y de abril a mayo de 2026; una prueba confirma que las 160 filas previas y las tablas de obras, recomendaciones y cursos no cambian. En carpeta compartida, un scheduler descargaría la última versión, ejecutaría pruebas/ETL y publicaría solo si pasan.

Limitaciones: no se infieren salarios faltantes, no existen tasas laborales en los archivos y el catálogo no distingue vigencia del curso. La demostración local no incorpora autenticación institucional.

**Declaración de IA:** se utilizó GitHub Copilot como apoyo para inspección, programación, pruebas y redacción. Las reglas y cifras fueron verificadas contra las fuentes mediante código reproducible.
