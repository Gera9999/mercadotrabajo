# Diseño de estructura del tablero

## Boceto funcional

```mermaid
flowchart TB
    F[Barra lateral: región · corte · periodo · estado · ocupación]
    K[KPI: avisos · vacantes · inversión · obras · cupos]
    P[Panorama: tendencia mensual + top de demanda]
    D[Demanda: avisos y vacantes por ocupación]
    I[Inversión: monto y contratos por comuna]
    C[Capacitación: prioridad + cursos + cupos + detalle]
    Q[Nota de calidad y fuente activa]
    F --> K
    K --> P
    P --> D
    D --> I
    I --> C
    C --> Q
```

## Criterio de organización

La autoridad primero recibe una síntesis comparable mediante KPI y tendencia. Luego puede profundizar desde la señal de mercado hacia dos decisiones: dónde se concentra la inversión y si la oferta formativa cubre las prioridades. Los filtros permanecen en una barra lateral estable para no competir con los gráficos durante una proyección.

| Sección | Pregunta | Fuente y medida |
|---|---|---|
| Panorama | ¿Cuál es la magnitud y evolución de las señales? | Avisos por mes; total de inversión; obras; cupos |
| Demanda | ¿Qué ocupaciones concentran avisos y vacantes? | Avisos, agrupados por CIUO y periodo |
| Inversión | ¿En qué comunas se concentra la inversión? | Suma de monto vigente y número de contratos |
| Capacitación | ¿Qué cursos responden a las prioridades? | Recomendaciones 1:N cursos por CIUO; cupos y nivel |

## Flujo de datos

```mermaid
flowchart LR
    A[data/raw: fuentes inmutables] --> B[src/etl.py]
    B --> C{Validaciones}
    C -->|Pasan| D[data/processed]
    C -->|Fallan| E[Error trazable; no publicar]
    D --> F[src/app.py]
    F --> G[Streamlit web]
    H[Archivo nuevo / carpeta compartida] --> A
    I[Scheduler / CI] --> B
```

La capa de presentación no modifica fuentes. La región es una dimensión y el archivo de avisos es un parámetro, por lo que la misma aplicación puede escalar sin duplicar tableros.