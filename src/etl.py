"""ETL reproducible para las fuentes del tablero de mercado laboral."""

from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
DEFAULT_AVISOS_FILE = "02_avisos_empleo_CRUDO.xlsx"

MONTHS = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}

OBRAS_COLUMNS = {
    "Servicio",
    "Region",
    "Comuna",
    "Tipo Obra",
    "Nombre Contrato",
    "Estado",
    "Monto Vigente Contrato",
    "F Inicio",
    "F Termino",
}

AVISOS_COLUMNS = {
    "Region",
    "Anio",
    "Mes",
    "Ocupacion CIUO08CL codigo",
    "Ocupacion CIUO08CL glosa",
    "N anuncios de empleo web",
    "N vacantes de empleo web",
    "Remuneracion mediana",
}


def snake_case(value: str) -> str:
    """Convierte una etiqueta a snake_case ASCII estable."""
    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", ascii_value.lower()).strip("_")


def normalize_text(series: pd.Series) -> pd.Series:
    """Limpia espacios sin eliminar tildes ni alterar el significado."""
    return series.astype("string").str.replace(r"\s+", " ", regex=True).str.strip()


def require_columns(frame: pd.DataFrame, expected: set[str], source: Path) -> None:
    missing = expected.difference(frame.columns)
    if missing:
        raise ValueError(f"{source.name}: faltan columnas requeridas: {sorted(missing)}")


def numeric_from_text(series: pd.Series, field: str) -> pd.Series:
    extracted = series.astype("string").str.extract(r"(-?\d+(?:[.,]\d+)*)", expand=False)
    cleaned = extracted.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    numeric = pd.to_numeric(cleaned, errors="coerce")
    invalid = series.notna() & numeric.isna()
    if invalid.any():
        examples = series.loc[invalid].astype(str).unique()[:5].tolist()
        raise ValueError(f"{field}: valores no convertibles: {examples}")
    return numeric


def clean_obras(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, sep=";", dtype="string")
    require_columns(frame, OBRAS_COLUMNS, path)
    frame.columns = [snake_case(column) for column in frame.columns]

    text_columns = [
        "servicio",
        "region",
        "comuna",
        "tipo_obra",
        "nombre_contrato",
        "estado",
    ]
    for column in text_columns:
        frame[column] = normalize_text(frame[column])

    frame["monto_vigente_contrato"] = numeric_from_text(
        frame["monto_vigente_contrato"], "monto_vigente_contrato"
    ).astype("Int64")
    for column in ("f_inicio", "f_termino"):
        frame[column] = pd.to_datetime(
            frame[column], format="mixed", dayfirst=True, errors="coerce"
        )
        if frame[column].isna().any():
            raise ValueError(f"{path.name}: hay fechas invalidas en {column}")

    if (frame["f_termino"] < frame["f_inicio"]).any():
        raise ValueError(f"{path.name}: hay contratos cuya fecha de termino precede al inicio")
    return frame


def clean_avisos(path: Path) -> pd.DataFrame:
    frame = pd.read_excel(path)
    require_columns(frame, AVISOS_COLUMNS, path)
    frame.columns = [snake_case(column) for column in frame.columns]

    frame["region"] = normalize_text(frame["region"])
    frame["ocupacion_ciuo08cl_glosa"] = normalize_text(frame["ocupacion_ciuo08cl_glosa"])
    frame["codigo_ciuo"] = frame.pop("ocupacion_ciuo08cl_codigo").astype("Int64").astype("string")
    frame["anuncios_empleo"] = numeric_from_text(
        frame.pop("n_anuncios_de_empleo_web"), "n_anuncios_de_empleo_web"
    ).astype("Int64")
    frame["vacantes_empleo"] = pd.to_numeric(
        frame.pop("n_vacantes_de_empleo_web"), errors="coerce"
    ).astype("Int64")
    if frame["vacantes_empleo"].isna().any():
        raise ValueError(f"{path.name}: hay vacantes no convertibles a numero")

    month_number = normalize_text(frame["mes"]).str.lower().map(MONTHS)
    if month_number.isna().any():
        invalid_months = frame.loc[month_number.isna(), "mes"].unique().tolist()
        raise ValueError(f"{path.name}: meses no reconocidos: {invalid_months}")
    frame["periodo"] = pd.to_datetime(
        {"year": frame["anio"], "month": month_number, "day": 1}, errors="coerce"
    )
    if frame["periodo"].isna().any():
        raise ValueError(f"{path.name}: hay periodos invalidos")

    frame["remuneracion_mediana"] = pd.to_numeric(
        frame["remuneracion_mediana"], errors="coerce"
    ).astype("Float64")
    frame["remuneracion_informada"] = frame["remuneracion_mediana"].notna()

    key = ["region", "periodo", "codigo_ciuo"]
    if frame.duplicated(key).any():
        raise ValueError(f"{path.name}: hay claves duplicadas para {key}")
    return frame.drop(columns=["mes"]).sort_values(key).reset_index(drop=True)


def load_clean_source(path: Path, expected: set[str]) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype="string")
    require_columns(frame, expected, path)
    frame.columns = [snake_case(column) for column in frame.columns]
    for column in frame.select_dtypes(include="string"):
        frame[column] = normalize_text(frame[column])
    return frame


def build_model(raw_dir: Path, avisos_file: str) -> dict[str, pd.DataFrame]:
    obras = clean_obras(raw_dir / "01_obras_publicas_CRUDO.csv")
    avisos = clean_avisos(raw_dir / avisos_file)
    recomendaciones = load_clean_source(
        raw_dir / "03_recomendaciones_LIMPIO.csv",
        {"region", "codigo_ciuo", "glosa_ciuo", "orden_prioridad"},
    )
    cursos = load_clean_source(
        raw_dir / "04_cursos_disponibles_LIMPIO.csv",
        {"codigo_plan", "nombre_plan", "nivel", "cupos", "codigo_ciuo"},
    )

    recomendaciones["codigo_ciuo"] = recomendaciones["codigo_ciuo"].astype("string")
    recomendaciones["orden_prioridad"] = pd.to_numeric(
        recomendaciones["orden_prioridad"], errors="raise"
    ).astype("Int64")
    cursos["codigo_ciuo"] = cursos["codigo_ciuo"].astype("string")
    cursos["cupos"] = pd.to_numeric(cursos["cupos"], errors="raise").astype("Int64")

    recomendacion_cursos = recomendaciones.merge(
        cursos,
        on="codigo_ciuo",
        how="left",
        validate="one_to_many",
        indicator=True,
    )
    recomendacion_cursos["curso_disponible"] = recomendacion_cursos["_merge"].eq("both")
    recomendacion_cursos = recomendacion_cursos.drop(columns="_merge")

    return {
        "obras": obras,
        "avisos": avisos,
        "recomendaciones": recomendaciones,
        "cursos": cursos,
        "recomendacion_cursos": recomendacion_cursos,
    }


def write_outputs(
    model: dict[str, pd.DataFrame], output_dir: Path, avisos_file: str
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in model.items():
        frame.to_csv(output_dir / f"{name}.csv", index=False, encoding="utf-8-sig")

    metrics: dict[str, object] = {
        "archivo_avisos": avisos_file,
        "filas": {name: len(frame) for name, frame in model.items()},
        "periodo_avisos_min": model["avisos"]["periodo"].min().date().isoformat(),
        "periodo_avisos_max": model["avisos"]["periodo"].max().date().isoformat(),
        "total_inversion": int(model["obras"]["monto_vigente_contrato"].sum()),
        "total_anuncios": int(model["avisos"]["anuncios_empleo"].sum()),
        "remuneraciones_no_informadas": int(
            model["avisos"]["remuneracion_mediana"].isna().sum()
        ),
    }
    (output_dir / "etl_metadata.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return metrics


def run_pipeline(raw_dir: Path, output_dir: Path, avisos_file: str) -> dict[str, object]:
    model = build_model(raw_dir, avisos_file)
    return write_outputs(model, output_dir, avisos_file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--avisos-file",
        default=os.getenv("AVISOS_FILE", DEFAULT_AVISOS_FILE),
        help="Nombre del archivo de avisos dentro de raw-dir.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    result = run_pipeline(arguments.raw_dir, arguments.output_dir, arguments.avisos_file)
    print(json.dumps(result, ensure_ascii=False, indent=2))