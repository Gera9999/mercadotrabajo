# Matriz de cumplimiento de rúbrica

| Criterio | Evidencia | Estado |
|---|---|---|
| 1.A Diagnóstico crítico | `docs/reporte_tecnico.md`: errores del tablero, visualizaciones, consistencia y cuatro riesgos con afectados | Cumple |
| 1.B Propuesta | Flujo escalable, software abierto, separación, automatización, despliegue, IA con resguardos y priorización | Cumple |
| 1.B IA aplicada | Chat contextual por módulo; solo consulta agregados, no modifica datos/código y gestiona la API mediante secretos | Mejora adicional |
| 2.1 Limpieza | `src/etl.py`: monto numérico, fechas mixtas, meses, textos numéricos y validaciones | Cumple |
| 2.1 Visualizaciones | `src/app.py`: navegación por cuatro módulos, KPI, inversión por estado/comuna, demanda, cobertura y hallazgos dinámicos | Cumple |
| 2.1 Actualización | Selector parametrizado; prueba 160→170 filas, abril→mayo, sin variar fuentes no afectadas | Cumple |
| 2.2 Modelo | `merge(... validate="one_to_many")` por CIUO; indicadores de inversión, avisos, vacantes y cupos | Cumple |
| 2.3 Estructura | `docs/diseno_estructura.md`: boceto, preguntas, datos y justificación | Cumple |
| 2.4 Reporte | `docs/reporte_tecnico.md`: anexos, supuestos, actualización y limitaciones | Cumple |

## Controles ejecutables

| Control | Resultado esperado |
|---|---|
| `python -m pytest -q` | 2 pruebas aprobadas |
| `python -m compileall -q src tests` | Sin errores |
| ETL base | 160 avisos; máximo 2026-04; inversión $274.534.765 |
| ETL mayo | 170 avisos; máximo 2026-05; inversión sin cambios |
