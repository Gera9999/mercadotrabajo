# Diseño de estructura del tablero

## Boceto funcional

```mermaid
flowchart TB
    N[Navegación lateral: Panorama · Demanda · Inversión · Recomendaciones]
    F[Filtros: región · corte · periodo · estado · ocupación]
    K[KPI con alcance: avisos · inversión · prioridades · cupos]
    P[Panorama: conclusiones + sugerencias + tendencia]
    D[Demanda: avisos y vacantes por ocupación]
    I[Inversión: monto y contratos por comuna]
    C[Recomendaciones: prioridad + cursos + brecha cupos/vacantes]
    A[Asistente IA contextual de solo consulta]
    Q[Nota de calidad y fuente activa]
    N --> F
    F --> K
    K --> P
    P --> D
    D --> I
    I --> C
    C --> A
    A --> Q
```

## Criterio de organización

La autoridad navega por cuatro módulos persistentes y recibe una síntesis comparable mediante KPI y tendencia. Luego puede profundizar desde la señal de mercado hacia dos decisiones: dónde se concentra la inversión y si la oferta formativa cubre las prioridades. Los filtros permanecen en una barra lateral estable para no competir con los gráficos durante una proyección. Cada vista termina con hallazgos reproducibles y ofrece un chat compacto para consultar únicamente sus agregados.

| Sección | Pregunta | Fuente y medida |
|---|---|---|
| Panorama | ¿Qué cambió y qué conviene revisar primero? | Variación de avisos; concentración de inversión; menor cobertura |
| Demanda | ¿Qué ocupaciones concentran avisos y vacantes? | Avisos, agrupados por CIUO y periodo |
| Inversión | ¿En qué comunas se concentra la inversión? | Suma de monto vigente y número de contratos |
| Recomendaciones | ¿Qué cursos responden a las prioridades y dónde hay menor cobertura? | Recomendaciones 1:N cursos por CIUO; cupos por cada 100 vacantes y nivel |

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