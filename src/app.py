"""Tablero interactivo de mercado laboral para autoridades regionales."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
    :root {
        --ink: #27334a; --muted: #667085; --orange: #df7748; --orange-soft: #fff1e8;
        --peach: #f8d8c4; --paper: #fffaf6; --line: #eadfd7; --white: #ffffff;
    }
    .stApp { background: var(--paper); color: var(--ink); }
    [data-testid="stHeader"] { background: rgba(255, 250, 246, .92); }
    [data-testid="stSidebar"] { background: #fff3ea; border-right: 1px solid var(--line); }
    [data-testid="stSidebar"] [role="radiogroup"] label {
        border-radius: 6px; padding: .55rem .7rem; margin-bottom: .2rem;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
        background: #f4c8ad; color: #71391f; font-weight: 700;
    }
    .block-container { max-width: 1180px; padding-top: 2.4rem; padding-bottom: 3rem; }
    [data-testid="stMetric"] {
        background: var(--white); border: 1px solid var(--line); border-top: 3px solid var(--orange);
        border-radius: 7px; padding: 14px 16px; min-height: 126px;
        box-shadow: 0 5px 18px rgba(93, 61, 42, .05);
    }
    [data-testid="stMetricValue"] { color: #bb572b; font-family: "Aptos Display", sans-serif; }
    [data-testid="stMetricLabel"] { color: var(--muted); }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255, 255, 255, .82); border-color: var(--line); border-radius: 7px;
    }
    [data-testid="stDataFrame"], [data-testid="stPlotlyChart"] {
        border-radius: 7px; overflow: hidden;
    }
    h1, h2, h3 { color: var(--ink); letter-spacing: 0; }
    h1 { font-family: "Aptos Display", sans-serif; font-size: 2.15rem !important; }
    .eyebrow { color: var(--orange); font-size: .78rem; font-weight: 800; text-transform: uppercase; }
    .source-note {
        border-left: 4px solid var(--orange); background: var(--orange-soft);
        border-radius: 0 6px 6px 0; padding: 9px 12px; color: #714832;
    }
    .view-intro { color: var(--muted); font-size: 1.02rem; margin: -.6rem 0 1.2rem; }
    .findings-title { color: #8e4525; font-size: .78rem; font-weight: 800; text-transform: uppercase; }
    button[kind="secondary"] { border-color: #df9a77; }
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


def render_findings(title: str, findings: list[str]) -> None:
    with st.container(border=True):
        st.markdown(f'<div class="findings-title">{title}</div>', unsafe_allow_html=True)
        for finding in findings:
            st.markdown(f"- {finding}")


def ask_openai(question: str, context: str) -> str:
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", "")
        model = st.secrets.get("OPENAI_MODEL", "gpt-4.1-mini")
    except FileNotFoundError:
        api_key = ""
        model = "gpt-4.1-mini"
    if not api_key:
        raise RuntimeError("Falta configurar OPENAI_API_KEY en los secretos de Streamlit.")

    system_prompt = (
        "Eres el asistente de Radar Laboral Regional. Responde en español, de forma breve y "
        "ejecutiva, usando exclusivamente el contexto agregado entregado. Puedes explicar, "
        "comparar y resumir los indicadores. No entregues ni modifiques código, configuración, "
        "archivos o datos. Rechaza solicitudes ajenas al mercado laboral mostrado y reconoce "
        "cuando el contexto no permite responder. No presentes correlaciones como causalidad."
    )
    payload = json.dumps(
        {
            "model": model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Contexto de la vista:\n{context}\n\nConsulta: {question}"},
            ],
            "max_output_tokens": 350,
        }
    ).encode("utf-8")
    request = Request(
        "https://api.openai.com/v1/responses",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI respondió con estado {error.code}: {detail[:180]}") from error
    except URLError as error:
        raise RuntimeError("No fue posible conectar con OpenAI.") from error

    texts = [
        content.get("text", "")
        for item in result.get("output", [])
        for content in item.get("content", [])
        if content.get("type") == "output_text"
    ]
    return "\n".join(filter(None, texts)) or "No se recibió una respuesta utilizable."


def render_ai_assistant(view_name: str, context: str) -> None:
    history_key = f"chat_history_{view_name.lower()}"
    history = st.session_state.setdefault(history_key, [])
    with st.popover("Consultar con IA", icon=":material/chat_bubble:", width="content"):
        st.caption(f"Asistente contextual · {view_name}")
        st.write("Consulta los indicadores visibles. El asistente no modifica datos ni código.")
        for message in history[-6:]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        question = st.chat_input("Pregunta sobre esta vista", key=f"chat_input_{view_name}")
        if question:
            history.append({"role": "user", "content": question})
            try:
                answer = ask_openai(question, context)
            except RuntimeError as error:
                answer = str(error)
            history.append({"role": "assistant", "content": answer})
            st.rerun()


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
    st.markdown("### RADAR Laboral")
    st.caption("Observatorio Laboral Regional")
    page = st.radio(
        "Navegación principal",
        ("Panorama", "Demanda", "Inversión", "Recomendaciones"),
        format_func=lambda option: {
            "Panorama": "01 · Panorama",
            "Demanda": "02 · Demanda",
            "Inversión": "03 · Inversión",
            "Recomendaciones": "04 · Recomendaciones",
        }[option],
        label_visibility="collapsed",
        key="page_navigation",
    )
    st.divider()
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

view_content = {
    "Panorama": (
        f"Mercado laboral · {region}",
        "Síntesis regional de demanda, inversión y oferta formativa para orientar decisiones.",
    ),
    "Demanda": (
        "Demanda de ocupaciones",
        "Ocupaciones con mayor presencia en los avisos de empleo del periodo seleccionado.",
    ),
    "Inversión": (
        "Inversión en obras públicas",
        "Contratos catastrados por estado de avance y concentración territorial.",
    ),
    "Recomendaciones": (
        "Recomendaciones de capacitación",
        "Prioridad, demanda de portales y oferta de cursos reunidas en una vista accionable.",
    ),
}
view_title, view_description = view_content[page]
st.markdown('<div class="eyebrow">Radar laboral regional</div>', unsafe_allow_html=True)
st.title(view_title)
st.markdown(f'<div class="view-intro">{view_description}</div>', unsafe_allow_html=True)

metric_columns = st.columns(4)
if page == "Panorama":
    metric_columns[0].metric("Avisos en el periodo", integer(avisos_filtered["anuncios_empleo"].sum()))
    metric_columns[1].metric("Vacantes informadas", integer(avisos_filtered["vacantes_empleo"].sum()))
    metric_columns[2].metric("Ocupaciones prioritarias", integer(recommendations_filtered["codigo_ciuo"].nunique()))
    metric_columns[3].metric("Obras catastradas", integer(obras_filtered["nombre_contrato"].nunique()))
elif page == "Demanda":
    metric_columns[0].metric("Avisos", integer(avisos_filtered["anuncios_empleo"].sum()))
    metric_columns[1].metric("Vacantes", integer(avisos_filtered["vacantes_empleo"].sum()))
    metric_columns[2].metric("Ocupaciones", integer(avisos_filtered["codigo_ciuo"].nunique()))
    metric_columns[3].metric("Meses analizados", integer(avisos_filtered["periodo"].nunique()))
elif page == "Inversión":
    metric_columns[0].metric("Contratos", integer(obras_filtered["nombre_contrato"].nunique()))
    metric_columns[1].metric("Monto vigente", clp(obras_filtered["monto_vigente_contrato"].sum()))
    metric_columns[2].metric("En ejecución", integer(obras_filtered["estado"].eq("En Ejecucion").sum()))
    metric_columns[3].metric("Comunas", integer(obras_filtered["comuna"].nunique()))
else:
    metric_columns[0].metric("Ocupaciones priorizadas", integer(recommendations_filtered["codigo_ciuo"].nunique()))
    metric_columns[1].metric("Con cursos", integer(courses_filtered.loc[courses_filtered["curso_disponible"], "codigo_ciuo"].nunique()))
    metric_columns[2].metric("Cursos disponibles", integer(courses_filtered["codigo_plan"].nunique()))
    metric_columns[3].metric("Cupos totales", integer(courses_filtered["cupos"].sum()))

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

if page == "Panorama":
    st.subheader("Señales para decidir")
    conclusion_column, suggestion_column = st.columns([1.15, 1])
    with conclusion_column:
        st.markdown("#### Hallazgos del panorama")
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

if page == "Demanda":
    st.subheader("Avisos y vacantes por ocupación")
    occupations = sorted(avisos_filtered["ocupacion_ciuo08cl_glosa"].unique())
    selected_occupations = st.multiselect(
        "Ocupaciones", occupations, default=occupations, key="occupation_filter"
    )
    demand_detail = avisos_filtered.loc[
        avisos_filtered["ocupacion_ciuo08cl_glosa"].isin(selected_occupations)
    ]
    demand = demand_detail.groupby(
        ["codigo_ciuo", "ocupacion_ciuo08cl_glosa"], as_index=False
    ).agg(
        anuncios=("anuncios_empleo", "sum"),
        vacantes=("vacantes_empleo", "sum"),
        remuneracion_mediana=("remuneracion_mediana", "median"),
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
            color_discrete_map={"anuncios": "#dd794d", "vacantes": "#edb18d"},
        )
        figure.update_layout(
            height=max(430, len(demand) * 42),
            margin=dict(l=10, r=10, t=20, b=10),
            plot_bgcolor="#fffaf6",
            paper_bgcolor="rgba(0,0,0,0)",
            legend_title_text="",
        )
        st.plotly_chart(figure, width="stretch")

        trend_column, detail_column = st.columns([1.1, 1])
        with trend_column:
            st.markdown("#### Evolución mensual")
            demand_monthly = demand_detail.groupby("periodo", as_index=False)[
                "anuncios_empleo"
            ].sum()
            trend = px.line(
                demand_monthly,
                x="periodo",
                y="anuncios_empleo",
                markers=True,
                labels={"periodo": "Mes", "anuncios_empleo": "Avisos"},
                color_discrete_sequence=["#d86f40"],
            )
            trend.update_layout(
                height=360,
                margin=dict(l=10, r=10, t=20, b=10),
                plot_bgcolor="#fffaf6",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(trend, width="stretch")
        with detail_column:
            st.markdown("#### Detalle por ocupación")
            st.dataframe(
                demand.sort_values("anuncios", ascending=False).rename(
                    columns={
                        "codigo_ciuo": "CIUO",
                        "ocupacion_ciuo08cl_glosa": "Ocupación",
                        "anuncios": "Avisos",
                        "vacantes": "Vacantes",
                        "remuneracion_mediana": "Remuneración mediana",
                    }
                ),
                hide_index=True,
                width="stretch",
                column_config={"Remuneración mediana": st.column_config.NumberColumn(format="$%d")},
            )

        demand_leader = demand.iloc[-1]
        demand_floor = demand.iloc[0]
        demand_range = demand["anuncios"].max() - demand["anuncios"].min()
        render_findings(
            "Hallazgos de demanda",
            [
                f"**{demand_leader['ocupacion_ciuo08cl_glosa']}** lidera con {integer(demand_leader['anuncios'])} avisos y {integer(demand_leader['vacantes'])} vacantes.",
                f"La diferencia entre la ocupación con más y menos avisos seleccionados es de **{integer(demand_range)}**.",
                f"**{demand_floor['ocupacion_ciuo08cl_glosa']}** registra el menor volumen dentro de la selección actual.",
            ],
        )

if page == "Inversión":
    st.subheader("Estado y concentración de la cartera")
    if investment.empty:
        st.info("Seleccione al menos un estado de obra para analizar la inversión.")
    else:
        status_summary = (
            obras_filtered.groupby("estado", as_index=False)
            .agg(contratos=("nombre_contrato", "nunique"), monto=("monto_vigente_contrato", "sum"))
            .sort_values("monto")
        )
        state_column, commune_column = st.columns(2)
        with state_column:
            st.markdown("#### Monto por estado de avance")
            state_figure = px.bar(
                status_summary,
                x="monto",
                y="estado",
                orientation="h",
                text_auto=".3s",
                labels={"monto": "Monto vigente (CLP)", "estado": ""},
                color_discrete_sequence=["#dc784b"],
            )
            state_figure.update_layout(
                height=410,
                margin=dict(l=10, r=20, t=20, b=10),
                plot_bgcolor="#fffaf6",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(state_figure, width="stretch")
        with commune_column:
            st.markdown("#### Inversión por comuna")
            commune_figure = px.bar(
                investment.sort_values("inversion"),
                x="inversion",
                y="comuna",
                orientation="h",
                custom_data=["contratos"],
                labels={"inversion": "Monto vigente (CLP)", "comuna": ""},
                color="inversion",
                color_continuous_scale=["#fbe7da", "#e9986f", "#b8512c"],
            )
            commune_figure.update_traces(
                hovertemplate="%{y}<br>Inversión: $%{x:,.0f}<br>Contratos: %{customdata[0]}"
            )
            commune_figure.update_layout(
                height=410,
                coloraxis_showscale=False,
                margin=dict(l=10, r=20, t=20, b=10),
                plot_bgcolor="#fffaf6",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(commune_figure, width="stretch")

        st.markdown("#### Detalle por estado")
        st.dataframe(
            status_summary.sort_values("monto", ascending=False).rename(
                columns={"estado": "Estado", "contratos": "Contratos", "monto": "Monto vigente"}
            ),
            hide_index=True,
            width="stretch",
            column_config={"Monto vigente": st.column_config.NumberColumn(format="$%d")},
        )
        leading_state = status_summary.iloc[-1]
        without_contractor = obras_filtered["estado"].isin(["En Licitacion", "Por Licitar"]).sum()
        render_findings(
            "Hallazgos de inversión",
            [
                f"La selección reúne **{integer(len(obras_filtered))} contratos** por {clp(investment_total)}.",
                f"**{leading_state['estado']}** concentra el mayor monto por {clp(leading_state['monto'])}.",
                f"**{integer(without_contractor)} obras** están en licitación o por licitar dentro del filtro actual.",
                f"**{investment.iloc[0]['comuna']}** lidera la inversión comunal y las tres primeras comunas concentran {percentage(top_three_share)}.",
            ],
        )

if page == "Recomendaciones":
    st.subheader("Ranking de ocupaciones prioritarias")
    st.caption(
        "El orden proviene de la recomendación regional. Avisos, vacantes y cursos son señales "
        "complementarias que no alteran esa prioridad."
    )
    st.dataframe(
        coverage[
            ["orden_prioridad", "glosa_ciuo", "codigo_ciuo", "avisos", "vacantes", "cursos", "cupos"]
        ].rename(
            columns={
                "orden_prioridad": "Prioridad",
                "glosa_ciuo": "Ocupación",
                "codigo_ciuo": "CIUO",
                "avisos": "Avisos",
                "vacantes": "Vacantes",
                "cursos": "Cursos",
                "cupos": "Cupos",
            }
        ),
        hide_index=True,
        width="stretch",
    )

    st.markdown("#### Cobertura de la oferta formativa")
    st.caption(
        "Cupos disponibles por cada 100 vacantes observadas. Es una señal comparativa, no una "
        "estimación automática de matrícula necesaria."
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
        color_continuous_scale=["#b94f2b", "#e99972", "#f8d8c4"],
    )
    figure.update_traces(
        hovertemplate="%{y}<br>CIUO: %{customdata[0]}<br>Prioridad: %{customdata[2]}"
        "<br>Cursos: %{customdata[1]}<br>Cupos: %{customdata[3]}"
        "<br>Vacantes: %{customdata[4]}<br>Cupos por 100 vacantes: %{x:.1f}"
    )
    figure.update_layout(
        height=500,
        coloraxis_colorbar_title="Cobertura",
        margin=dict(l=10, r=10, t=20, b=10),
        plot_bgcolor="#fffaf6",
        paper_bgcolor="rgba(0,0,0,0)",
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
    if coverage["cupos_por_100_vacantes"].notna().any():
        lowest_coverage = coverage.loc[coverage["cupos_por_100_vacantes"].idxmin()]
        largest_offer = coverage.loc[coverage["cupos"].idxmax()]
        covered_occupations = courses_filtered.loc[
            courses_filtered["curso_disponible"], "codigo_ciuo"
        ].nunique()
        render_findings(
            "Hallazgos de recomendaciones",
            [
                f"Las {integer(covered_occupations)} ocupaciones priorizadas tienen al menos un curso disponible.",
                f"**{lowest_coverage['glosa_ciuo']}** presenta la menor cobertura relativa: {lowest_coverage['cupos_por_100_vacantes']:.1f} cupos por 100 vacantes.",
                f"**{largest_offer['glosa_ciuo']}** concentra la mayor oferta con {integer(largest_offer['cupos'])} cupos.",
                "La cobertura orienta la revisión de compra, pero debe contrastarse con empleadores, matrícula y ejecución histórica.",
            ],
        )

assistant_context = (
    f"Vista: {page}. Región: {region}. Periodo: {selected_start:%Y-%m} a {selected_end:%Y-%m}. "
    f"Avisos: {int(avisos_filtered['anuncios_empleo'].sum())}. "
    f"Vacantes: {int(avisos_filtered['vacantes_empleo'].sum())}. "
    f"Obras filtradas: {len(obras_filtered)}. "
    f"Inversión filtrada CLP: {int(obras_filtered['monto_vigente_contrato'].sum())}. "
    f"Ocupaciones prioritarias: {recommendations_filtered['codigo_ciuo'].nunique()}. "
    f"Cursos: {courses_filtered['codigo_plan'].nunique()}. Cupos: {int(courses_filtered['cupos'].sum())}. "
    f"Demanda por ocupación: {demand_by_occupation.to_dict(orient='records')}. "
    f"Cobertura formativa: {coverage.to_dict(orient='records')}. "
    f"Inversión por comuna: {investment.to_dict(orient='records')}."
)
render_ai_assistant(page, assistant_context)

with st.expander("Calidad, alcance y trazabilidad"):
    missing_salaries = int(avisos_filtered["remuneracion_mediana"].isna().sum())
    st.markdown(
        f"- **Fuente física:** `{avisos_file}`\n"
        f"- **Periodo aplicado a demanda y cobertura:** {selected_start:%m-%Y} a {selected_end:%m-%Y}\n"
        f"- **Estados aplicados a inversión:** {len(selected_statuses)} de {len(statuses)}\n"
        f"- **Remuneraciones no informadas en el filtro:** {integer(missing_salaries)}\n"
        "- Prioridades y cupos corresponden al catálogo regional completo; no tienen vigencia temporal en la fuente."
    )