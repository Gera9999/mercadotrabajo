# Radar Laboral Regional

**Reporte para evaluación:** [Diagnóstico crítico y propuesta de reconstrucción](docs/reporte_tecnico.md). El documento responde explícitamente los criterios de las partes A y B, con una propuesta centrada en escalar el tablero a múltiples regiones y sostenerlo en el tiempo.

Solución Vía B de la prueba técnica: ETL reproducible en Python y tablero interactivo en Streamlit/Plotly para integrar demanda laboral, inversión pública, ocupaciones prioritarias y cursos disponibles. La interfaz utiliza navegación lateral por módulos, indicadores contextualizados y hallazgos dinámicos para apoyar la lectura ejecutiva.

**Aplicación publicada:** [mercadotrabajo.streamlit.app](https://mercadotrabajo.streamlit.app/)

> Todos los datos son ficticios y corresponden a una región de ejemplo.

## Resultado

El proyecto conecta cuatro fuentes base y permite demostrar la actualización central de la Tarea 4 con un quinto archivo que agrega mayo de 2026. El selector **Fuente de avisos** cambia entre el corte original y el actualizado sin modificar código ni rehacer transformaciones.

Indicadores de control del corte base:

| Indicador | Resultado |
|---|---:|
| Obras | 120 |
| Inversión total | $274.534.765 |
| Registros de avisos | 160 |
| Avisos acumulados | 7.287 |
| Ocupaciones prioritarias | 10 |
| Cursos | 17 |

Con la actualización de mayo, los registros de avisos aumentan de 160 a 170 y el máximo periodo pasa de abril a mayo de 2026. Obras, recomendaciones y cursos no cambian.

## Estructura

```text
mercado_del_trabajo/
├── data/
│   ├── raw/                 # Fuentes originales, nunca editadas manualmente
│   └── processed/           # Salidas generadas por el ETL
├── docs/
│   ├── reference/           # Pauta y rúbrica originales
│   ├── diseno_estructura.md
│   ├── matriz_rubrica.md
│   └── reporte_tecnico.md
├── src/
│   ├── etl.py               # Lectura, limpieza, validación, modelo y exportación
│   └── app.py               # Presentación interactiva
├── streamlit_app.py          # Entrada para Streamlit Community Cloud
├── tests/test_etl.py        # Regresión de limpieza y actualización
├── requirements.txt
└── requirements-dev.txt
```

## Instalación

Requiere Python 3.12.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

## Ejecutar el ETL

Corte original:

```powershell
python src/etl.py
```

Actualización de mayo sin tocar el código:

```powershell
python src/etl.py --avisos-file 02_avisos_empleo_ACTUALIZADO_mayo.xlsx
```

También puede parametrizarse con `AVISOS_FILE`. El pipeline genera cinco CSV procesados y `etl_metadata.json` en `data/processed/`.

## Revisar el tablero

```powershell
streamlit run streamlit_app.py
```

Abra `http://localhost:8501`. En la barra lateral:

1. Seleccione **Corte base · abril 2026** y compruebe el último periodo.
2. Cambie a **Corte actualizado · mayo 2026**; el periodo se amplía y la serie, KPI, conclusiones y brechas se recalculan.
3. Use los filtros de región, periodo, estado de obra y ocupación.
4. Revise los hallazgos calculados al final de **Panorama**, **Demanda**, **Inversión** y **Recomendaciones**.
5. Compare concentración territorial en **Inversión** y cupos por cada 100 vacantes en **Recomendaciones**.
6. Abra **Consultar con IA** para hacer una pregunta sobre los indicadores de la vista activa.

## Asistente IA con OpenAI

Cada módulo incluye un chat compacto y contextual. El asistente recibe únicamente un resumen agregado de los filtros activos, responde en español sobre los datos mostrados y tiene instrucciones para rechazar solicitudes de modificación de código, archivos, configuración o temas ajenos al tablero. Sus respuestas son apoyo interpretativo: no alteran el ETL, los datos ni las recomendaciones deterministas.

El punto exacto para configurar la API es la clave `OPENAI_API_KEY` que lee la función `ask_openai()` en `src/app.py`. No escriba la clave dentro del código ni la suba a Git.

Para ejecución local, cree `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY = "su-clave-de-openai"
OPENAI_MODEL = "gpt-4.1-mini"
```

El archivo ya está excluido por `.gitignore`. En Streamlit Community Cloud, abra **App settings → Secrets** y pegue las mismas dos líneas. `OPENAI_MODEL` es opcional; si se omite, la app usa `gpt-4.1-mini`. Sin `OPENAI_API_KEY`, el tablero funciona normalmente y el chat muestra una indicación de configuración.

## Despliegue en Streamlit Community Cloud

En [share.streamlit.io](https://share.streamlit.io/), cree una aplicación con estos parámetros:

| Parámetro | Valor |
|---|---|
| Repositorio | `Gera9999/mercadotrabajo` |
| Rama | `main` |
| Archivo principal | `streamlit_app.py` |

Community Cloud instalará automáticamente las versiones fijadas en `requirements.txt`. El tablero de datos no requiere secretos; solo el asistente opcional necesita `OPENAI_API_KEY` en los secretos de la aplicación.

Los dos cortes de avisos se conservan porque la Tarea 4 exige construir con el archivo original y demostrar que el archivo actualizado agrega mayo sin rehacer el modelo. En una operación productiva, el pipeline seleccionaría automáticamente la última fuente validada y este control podría reservarse para auditoría.

## Verificación

```powershell
python -m pytest -q
python -m compileall -q src tests
```

Las pruebas confirman tipos, fechas, cruce uno-a-muchos por CIUO y que mayo agrega exactamente 10 registros sin alterar las demás fuentes ni los 160 registros anteriores.

## Decisiones de limpieza

- Los montos eliminan el punto usado como separador de miles y se almacenan como enteros.
- Las fechas mezcladas con `/` y `-` se interpretan con día primero y `format="mixed"`.
- Los meses abreviados en español se convierten a una fecha mensual normalizada.
- Valores como `55 avisos` se extraen y validan como enteros.
- Los códigos CIUO se modelan como texto para preservar su rol de identificador.
- Las remuneraciones ausentes se mantienen nulas y se marcan con `remuneracion_informada`; no se inventan valores sin fundamento.
- Recomendaciones y cursos se unen por `codigo_ciuo` con cardinalidad uno-a-muchos validada.

## Actualización y despliegue

Para una carpeta compartida, un job programado descargaría o montaría las fuentes, ejecutaría pruebas y ETL, publicaría las salidas de forma atómica y reiniciaría la app solo si los controles pasan. GitHub Actions, un cron institucional o un orquestador como Prefect pueden ejecutar el proceso. Streamlit Community Cloud sirve para demostración; producción institucional requiere contenedor, autenticación, HTTPS, logs y almacenamiento gestionado.

El análisis completo, limitaciones y propuesta se encuentran en [docs/reporte_tecnico.md](docs/reporte_tecnico.md). El diseño obligatorio está en [docs/diseno_estructura.md](docs/diseno_estructura.md).
