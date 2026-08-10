"""Tablero interactivo de mercado laboral para autoridades regionales."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from etl import DEFAULT_AVISOS_FILE, DEFAULT_RAW_DIR, build_model


st.set_page_config(
    page_title="Radar Laboral Regional",
    page_icon=":material/monitoring:",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root { --ink: #18332f; --teal: #087e72; --coral: #e05d44; --paper: #f5f3ed; }
    .stApp { background: var(--paper); color: var(--ink); }
    [data-testid="stHeader"] { background: rgba(245, 243, 237, .92); }
    [data-testid="stMetric"] {
        background: #ffffff; border-top: 4px solid var(--teal); padding: 14px 16px;
        box-shadow: 0 2px 12px rgba(24, 51, 47, .08);
    }
    [data-testid="stMetricValue"] { color: var(--ink); font-family: Georgia, serif; }
    h1, h2, h3 { color: var(--ink); letter-spacing: 0; }
    h1 { font-family: Georgia, serif; }
    .eyebrow { color: var(--coral); font-weight: 700; text-transform: uppercase; }
    .source-note { border-left: 4px solid var(--coral); padding-left: 12px; color: #4f625e; }
    </style>
    """,
    unsafe_allow_html=True,
)


def clp(value: float) -> str:
    return f"${value:,.0f}".replace(",", ".")


def integer(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def percentage(value: float) -> str:
    return f"{value:.1f}%".replace(".", ",")


def source_label(filename: str) -> str:
    if "ACTUALIZADO" in filename.upper():
        return "Corte actualizado · mayo 2026"
    return "Corte base · abril 2026"


def reset_period_filter() -> None:
    st.session_state.pop("period_filter", None)


@st.cache_data(show_spinner="Actualizando modelo...")
def load_model(
    raw_dir: str,
    avisos_file: str,
    source_signature: tuple[tuple[str, int], ...],
) -> dict[str, pd.DataFrame]:
    return build_model(Path(raw_dir), avisos_file)


def get_source_signature(raw_dir: Path, avisos_file: str) -> tuple[tuple[str, int], ...]:
    source_names = (
        "01_obras_publicas_CRUDO.csv",
        avisos_file,
        "03_recomendaciones_LIMPIO.csv",
        "04_cursos_disponibles_LIMPIO.csv",
    )
    return tuple((name, (raw_dir / name).stat().st_mtime_ns) for name in source_names)


available_files = sorted(path.name for path in DEFAULT_RAW_DIR.glob("02_avisos_empleo*.xlsx"))
if not available_files:
    st.error("No se encontraron archivos de avisos en data/raw.")
    st.stop()

default_index = available_files.index(DEFAULT_AVISOS_FILE) if DEFAULT_AVISOS_FILE in available_files else 0
with st.sidebar:
    st.header("Filtros")
    if st.button("Restablecer filtros", icon=":material/restart_alt:", width="stretch"):
        for key in ("source_filter", "region_filter", "period_filter", "status_filter"):
            st.session_state.pop(key, None)
        st.rerun()
    avisos_file = st.selectbox(
        "Fuente de avisos",
        available_files,
        index=default_index,
        format_func=source_label,
        help="Cambie al archivo de mayo para demostrar la actualización sin modificar código.",
        key="source_filter",
        on_change=reset_period_filter,
    )

model = load_model(
    str(DEFAULT_RAW_DIR),
    avisos_file,
    get_source_signature(DEFAULT_RAW_DIR, avisos_file),
)
obras = model["obras"]
avisos = model["avisos"]
recomendaciones = model["recomendaciones"]
recomendacion_cursos = model["recomendacion_cursos"]

regions = sorted(set(obras["region"]).intersection(avisos["region"], recomendaciones["region"]))
with st.sidebar:
    region = st.selectbox("Región", regions, key="region_filter")
    date_min, date_max = avisos["periodo"].min().date(), avisos["periodo"].max().date()
    period = st.date_input(
        "Periodo de avisos",
        value=(date_min, date_max),
        min_value=date_min,
        max_value=date_max,
        key="period_filter",
    )
    statuses = sorted(obras.loc[obras["region"].eq(region), "estado"].unique())
    selected_statuses = st.multiselect(
        "Estado de obra", statuses, default=statuses, key="status_filter"
    )

if isinstance(period, tuple) and len(period) == 2:
    selected_start, selected_end = pd.Timestamp(period[0]), pd.Timestamp(period[1])
else:
    selected_start = selected_end = pd.Timestamp(period)

avisos_filtered = avisos.loc[
    avisos["region"].eq(region)
    & avisos["periodo"].between(selected_start, selected_end)
].copy()
obras_filtered = obras.loc[
    obras["region"].eq(region) & obras["estado"].isin(selected_statuses)
].copy()
recommendations_filtered = recomendaciones.loc[recomendaciones["region"].eq(region)].copy()
courses_filtered = recomendacion_cursos.loc[recomendacion_cursos["region"].eq(region)].copy()

st.markdown('<div class="eyebrow">Inteligencia para capacitación</div>', unsafe_allow_html=True)
st.title("Radar Laboral Regional")
st.caption(f"{region} · Datos ficticios de demostración")

metric_columns = st.columns(4)
metric_columns[0].metric("Avisos en el periodo", integer(avisos_filtered["anuncios_empleo"].sum()))
metric_columns[1].metric("Inversión seleccionada", clp(obras_filtered["monto_vigente_contrato"].sum()))
metric_columns[2].metric("Ocupaciones prioritarias", integer(recommendations_filtered["codigo_ciuo"].nunique()))
metric_columns[3].metric("Cupos disponibles", integer(courses_filtered["cupos"].sum()))
metric_columns[0].caption(f"{selected_start:%m-%Y} a {selected_end:%m-%Y}")
metric_columns[1].caption(
    f"{len(selected_statuses)} de {len(statuses)} estados de obra"
)
metric_columns[2].caption("Ranking regional vigente")
metric_columns[3].caption("Catálogo completo disponible")

st.markdown(
    f'<p class="source-note"><strong>{source_label(avisos_file)}</strong> · '
    f'Último mes disponible: <strong>{avisos["periodo"].max():%m-%Y}</strong>.</p>',
    unsafe_allow_html=True,
)

monthly = avisos_filtered.groupby("periodo", as_index=False)["anuncios_empleo"].sum()
latest_change = None
if len(monthly) >= 2 and monthly.iloc[-2]["anuncios_empleo"]:
    latest_change = (
        monthly.iloc[-1]["anuncios_empleo"] / monthly.iloc[-2]["anuncios_empleo"] - 1
    ) * 100

investment = (
    obras_filtered.groupby("comuna", as_index=False)
    .agg(inversion=("monto_vigente_contrato", "sum"), contratos=("nombre_contrato", "nunique"))
    .sort_values("inversion", ascending=False)
)
investment_total = investment["inversion"].sum()
leader_share = investment.iloc[0]["inversion"] / investment_total * 100 if investment_total else 0
top_three_share = investment.head(3)["inversion"].sum() / investment_total * 100 if investment_total else 0

demand_by_occupation = avisos_filtered.groupby("codigo_ciuo", as_index=False).agg(
    avisos=("anuncios_empleo", "sum"), vacantes=("vacantes_empleo", "sum")
)
coverage = (
    courses_filtered.groupby(["orden_prioridad", "codigo_ciuo", "glosa_ciuo"], as_index=False)
    .agg(cupos=("cupos", "sum"), cursos=("codigo_plan", "nunique"))
    .merge(demand_by_occupation, on="codigo_ciuo", how="left")
    .fillna({"avisos": 0, "vacantes": 0})
    .sort_values("orden_prioridad")
)
coverage["cupos_por_100_vacantes"] = coverage["cupos"].div(
    coverage["vacantes"].replace(0, pd.NA)
).mul(100)

tab_panorama, tab_demanda, tab_inversion, tab_capacitacion = st.tabs(
    ["Panorama", "Demanda", "Inversión", "Capacitación"]
)

with tab_panorama:
    st.subheader("Señales para decidir")
    conclusion_column, suggestion_column = st.columns([1.15, 1])
    with conclusion_column:
        st.markdown("#### Conclusiones del corte")
        if latest_change is not None:
            direction = "aumentaron" if latest_change >= 0 else "disminuyeron"
            st.markdown(
                f"- Los avisos del último mes **{direction} {percentage(abs(latest_change))}** "
                "respecto del mes anterior."
            )
        if not investment.empty:
            st.markdown(
                f"- **{investment.iloc[0]['comuna']}** lidera la inversión con "
                f"{percentage(leader_share)} del total seleccionado; las tres primeras comunas "
                f"concentran {percentage(top_three_share)}."
            )
        if not coverage.empty and coverage["cupos_por_100_vacantes"].notna().any():
            lowest_coverage = coverage.loc[coverage["cupos_por_100_vacantes"].idxmin()]
            st.markdown(
                f"- **{lowest_coverage['glosa_ciuo']}** presenta la menor cobertura: "
                f"{str(round(lowest_coverage['cupos_por_100_vacantes'], 1)).replace('.', ',')} "
                "cupos por cada 100 vacantes."
            )
    with suggestion_column:
        st.markdown("#### Sugerencias para la decisión")
        if not coverage.empty and coverage["cupos_por_100_vacantes"].notna().any():
            lowest_coverage = coverage.loc[coverage["cupos_por_100_vacantes"].idxmin()]
            st.markdown(
                f"1. Evaluar ampliar la oferta para **{lowest_coverage['glosa_ciuo']}**, "
                "contrastando esta señal con empleadores antes de comprar nuevos cupos."
            )
        if not investment.empty:
            st.markdown(
                f"2. Priorizar el seguimiento de cartera en **{', '.join(investment.head(3)['comuna'])}**, "
                "que reúnen la mayor inversión seleccionada."
            )

    left, right = st.columns([1.15, 1])
    with left:
        st.markdown("#### Evolución mensual de avisos")
        if monthly.empty:
            st.info("No hay avisos para el periodo seleccionado.")
        else:
            figure = px.line(
                monthly,
                x="periodo",
                y="anuncios_empleo",
                markers=True,
                labels={"periodo": "Mes", "anuncios_empleo": "Avisos"},
                color_discrete_sequence=["#087e72"],
            )
            figure.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(figure, width="stretch")
    with right:
        top_demand = (
            avisos_filtered.groupby(["codigo_ciuo", "ocupacion_ciuo08cl_glosa"], as_index=False)[
                "anuncios_empleo"
            ]
            .sum()
            .nlargest(5, "anuncios_empleo")
        )
        st.markdown("#### Mayor demanda observada")
        st.dataframe(
            top_demand.rename(
                columns={
                    "codigo_ciuo": "CIUO",
                    "ocupacion_ciuo08cl_glosa": "Ocupación",
                    "anuncios_empleo": "Avisos",
                }
            ),
            hide_index=True,
            width="stretch",
        )

with tab_demanda:
    st.subheader("Demanda por ocupación")
    occupations = sorted(avisos_filtered["ocupacion_ciuo08cl_glosa"].unique())
    selected_occupations = st.multiselect(
        "Ocupaciones", occupations, default=occupations, key="occupation_filter"
    )
    demand = avisos_filtered.loc[
        avisos_filtered["ocupacion_ciuo08cl_glosa"].isin(selected_occupations)
    ]
    demand = demand.groupby("ocupacion_ciuo08cl_glosa", as_index=False).agg(
        anuncios=("anuncios_empleo", "sum"), vacantes=("vacantes_empleo", "sum")
    )
    demand = demand.sort_values("anuncios")
    if demand.empty:
        st.info("Seleccione al menos una ocupación para comparar su demanda.")
    else:
        figure = px.bar(
            demand,
            x=["anuncios", "vacantes"],
            y="ocupacion_ciuo08cl_glosa",
            orientation="h",
            barmode="group",
            labels={"value": "Cantidad", "variable": "Indicador", "ocupacion_ciuo08cl_glosa": ""},
            color_discrete_map={"anuncios": "#087e72", "vacantes": "#e05d44"},
        )
        figure.update_layout(height=max(430, len(demand) * 42), margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(figure, width="stretch")

with tab_inversion:
    st.subheader("¿En qué comunas se concentra la inversión?")
    if investment.empty:
        st.info("Seleccione al menos un estado de obra para analizar la inversión.")
    else:
        st.markdown(
            f"**{investment.iloc[0]['comuna']}** concentra {percentage(leader_share)} del monto; "
            f"las tres comunas líderes reúnen {percentage(top_three_share)}."
        )
        figure = px.bar(
            investment.sort_values("inversion"),
            x="inversion",
            y="comuna",
            orientation="h",
            text="contratos",
            custom_data=["contratos"],
            labels={"inversion": "Monto vigente (CLP)", "comuna": ""},
            color="inversion",
            color_continuous_scale=["#d9e8df", "#087e72", "#18332f"],
        )
        figure.update_traces(
            texttemplate="%{text} contratos",
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}<br>Inversión: $%{x:,.0f}<br>Contratos: %{customdata[0]}",
        )
        figure.update_layout(
            height=500, coloraxis_showscale=False, margin=dict(l=10, r=90, t=20, b=10)
        )
        st.plotly_chart(figure, width="stretch")

with tab_capacitacion:
    st.subheader("¿Qué cursos responden a las prioridades?")
    st.caption(
        "Cobertura = cupos disponibles por cada 100 vacantes observadas en el periodo seleccionado. "
        "Es una señal comparativa, no una estimación de matrícula necesaria."
    )
    figure = px.bar(
        coverage.sort_values("cupos_por_100_vacantes", ascending=False),
        x="cupos_por_100_vacantes",
        y="glosa_ciuo",
        orientation="h",
        color="cupos_por_100_vacantes",
        custom_data=["codigo_ciuo", "cursos", "orden_prioridad", "cupos", "vacantes"],
        labels={
            "cupos_por_100_vacantes": "Cupos por 100 vacantes",
            "glosa_ciuo": "",
        },
        color_continuous_scale=["#e05d44", "#f0c36e", "#087e72"],
    )
    figure.update_traces(
        hovertemplate="%{y}<br>CIUO: %{customdata[0]}<br>Prioridad: %{customdata[2]}"
        "<br>Cursos: %{customdata[1]}<br>Cupos: %{customdata[3]}"
        "<br>Vacantes: %{customdata[4]}<br>Cupos por 100 vacantes: %{x:.1f}"
    )
    figure.update_layout(
        height=500, coloraxis_colorbar_title="Cobertura", margin=dict(l=10, r=10, t=20, b=10)
    )
    st.plotly_chart(figure, width="stretch")
    st.markdown("#### Cursos disponibles")
    st.dataframe(
        courses_filtered[
            ["orden_prioridad", "glosa_ciuo", "codigo_plan", "nombre_plan", "nivel", "cupos"]
        ].rename(
            columns={
                "orden_prioridad": "Prioridad",
                "glosa_ciuo": "Ocupación",
                "codigo_plan": "Plan",
                "nombre_plan": "Curso",
                "nivel": "Nivel",
                "cupos": "Cupos",
            }
        ),
        hide_index=True,
        width="stretch",
    )

with st.expander("Calidad, alcance y trazabilidad"):
    missing_salaries = int(avisos_filtered["remuneracion_mediana"].isna().sum())
    st.markdown(
        f"- **Fuente física:** `{avisos_file}`\n"
        f"- **Periodo aplicado a demanda y cobertura:** {selected_start:%m-%Y} a {selected_end:%m-%Y}\n"
        f"- **Estados aplicados a inversión:** {len(selected_statuses)} de {len(statuses)}\n"
        f"- **Remuneraciones no informadas en el filtro:** {integer(missing_salaries)}\n"
        "- Prioridades y cupos corresponden al catálogo regional completo; no tienen vigencia temporal en la fuente."
    )