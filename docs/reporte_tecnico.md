# Reporte técnico de la plataforma de BI

## Parte 1 · Análisis y propuesta de mejora

### A. Diagnóstico crítico

El tablero de ejemplo comunica una síntesis útil, pero contiene problemas verificables. Rotula la inversión como “$274.534.765 miles”, mientras la suma de `Monto Vigente Contrato` es $274.534.765; si la fuente está en pesos, “miles” sobredimensiona el total mil veces. También describe que “un tercio” de 120 obras está en ejecución o adjudicado: son 45, equivalentes a 37,5%, por lo que debe expresarse como “cerca de cuatro de cada diez”. El KPI de 5.486 avisos de doce meses no explicita meses de corte ni método; la fuente base completa suma 7.287 entre enero de 2025 y abril de 2026, de modo que la cifra no es auditable desde la interfaz. Las tasas de desocupación y ocupación tampoco tienen fuente, periodo ni tabla entregada, impidiendo reproducirlas.

La línea mensual es apropiada para tendencia, pero debería mostrar corte y unidades. Las tablas extensas de obras requieren agrupación por comuna/estado antes del detalle. Para una autoridad conviene ordenar barras, usar moneda compacta y reservar colores para significado. El ranking mezcla prioridad, demanda y cursos sin explicar si la prioridad proviene exclusivamente de encuesta o de una fórmula; eso puede inducir causalidad inexistente. Una ocupación prioritaria puede tener varios cursos, por lo que sumar después de un join sin controlar granularidad duplicaría atributos de recomendación.

Riesgos: primero, fuentes y presentación acopladas obligan a rehacer cada tablero regional, afectando al equipo mantenedor. Segundo, reemplazos manuales carecen de validaciones y pueden publicar columnas cambiadas o datos parciales, afectando decisiones de compra. Tercero, no se exhiben fecha de actualización, linaje ni controles, afectando a autoridades y auditoría. Cuarto, los 77 nulos salariales del corte base y textos como “55 avisos” pueden sesgar indicadores o romper cargas si se convierten silenciosamente.

### B. Propuesta de reconstrucción

Propongo una arquitectura por capas: fuentes inmutables en `data/raw`; ETL con pandas que valida esquema, normaliza y registra metadatos; productos en `data/processed`; y Streamlit/Plotly como presentación sin lógica de limpieza. `codigo_ciuo` es dimensión conformada para demanda, recomendaciones y cursos; región y periodo permiten reutilizar una sola aplicación. Git aporta trazabilidad y pytest protege reglas críticas. Todo el stack es abierto y evita licencias por usuario.

En producción, un job programado detectaría archivos en SharePoint/Drive mediante API, los copiaría a una zona de entrada, ejecutaría validaciones y publicaría salidas atómicamente solo al aprobar. Un contenedor desplegado detrás de HTTPS y autenticación institucional serviría Streamlit; logs, alertas, secretos gestionados y versionado de artefactos completarían la operación. Una actualización fallida conservaría la versión anterior.

La IA puede sugerir equivalencias para glosas nuevas o anomalías semánticas, pero nunca modificar datos automáticamente. Cada sugerencia debe incluir confianza, dato original y decisión humana; reglas deterministas, catálogo CIUO y pruebas siguen siendo autoridad. Con recursos limitados priorizaría primero ETL automatizado con controles y actualización: corrige la condición crítica, reduce riesgo transversal y crea una base confiable sobre la cual mejorar visualizaciones y desplegar.

Supuestos: montos en CLP; fechas día-mes-año; abreviaturas mensuales en español; CIUO como identificador textual. Limitaciones: datos ficticios de una región, ausencia de fuente para tasas laborales y alta falta de remuneraciones; estas últimas no se imputan.

## Parte 2 · Construcción y guía de entrega

Se eligió la Vía B con Python, pandas, Streamlit y Plotly por reproducibilidad, portabilidad y ausencia de licencias. El anexo ejecutable es `src/app.py`: presenta Panorama, Demanda, Inversión y Capacitación, con filtros de región, periodo, estado, ocupación y fuente. `docs/diseno_estructura.md` contiene el boceto obligatorio, la pregunta de cada sección y su dato. `src/etl.py` es el anexo técnico del cruce y las transformaciones; `tests/test_etl.py` documenta controles ejecutables.

El ETL lee cuatro fuentes base sin alterarlas. En obras, elimina puntos de miles, convierte montos a enteros y parsea fechas con formatos mixtos y día primero. En avisos, convierte textos como “55 avisos”, normaliza meses a una fecha mensual y preserva remuneraciones faltantes como nulos con bandera de calidad. Los encabezados pasan a `snake_case`; textos se recortan; CIUO se conserva como texto. Recomendaciones y cursos se unen por `codigo_ciuo` mediante relación uno-a-muchos validada: una prioridad puede ofrecer varios cursos. Los indicadores incluyen suma de inversión, avisos, vacantes, obras, cursos y cupos.

Las dos visualizaciones principales responden: “¿En qué comunas se concentra la inversión?” mediante barras ordenadas de monto y contratos, y “¿Qué cursos responden a las ocupaciones prioritarias?” mediante cupos y número de cursos según ranking. Demanda y tendencia mensual entregan contexto sin sustituir esas decisiones.

Para la Tarea 4 se puede seleccionar `02_avisos_empleo_ACTUALIZADO_mayo.xlsx` en la barra lateral o ejecutar `python src/etl.py --avisos-file 02_avisos_empleo_ACTUALIZADO_mayo.xlsx`. No se toca código. El modelo cambia de 160 a 170 filas y de abril a mayo de 2026; una prueba confirma que las 160 filas previas y las tablas de obras, recomendaciones y cursos no cambian. En carpeta compartida, un scheduler descargaría la última versión, ejecutaría pruebas/ETL y publicaría solo si pasan.

Limitaciones: no se infieren salarios faltantes, no existen tasas laborales en los archivos y el catálogo no distingue vigencia del curso. La demostración local no incorpora autenticación institucional.

**Declaración de IA:** se utilizó GitHub Copilot como apoyo para inspección, programación, pruebas y redacción. Las reglas y cifras fueron verificadas contra las fuentes mediante código reproducible.