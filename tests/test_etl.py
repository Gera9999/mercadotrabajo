from pathlib import Path

import pandas as pd

from src.etl import build_model


RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def test_base_sources_are_cleaned_and_related() -> None:
    model = build_model(RAW_DIR, "02_avisos_empleo_CRUDO.xlsx")

    assert len(model["obras"]) == 120
    assert len(model["avisos"]) == 160
    assert pd.api.types.is_integer_dtype(model["obras"]["monto_vigente_contrato"])
    assert pd.api.types.is_datetime64_any_dtype(model["obras"]["f_inicio"])
    assert model["avisos"]["anuncios_empleo"].isna().sum() == 0
    assert model["recomendacion_cursos"]["curso_disponible"].all()
    assert len(model["recomendacion_cursos"]) == 17


def test_may_update_adds_only_expected_period() -> None:
    base = build_model(RAW_DIR, "02_avisos_empleo_CRUDO.xlsx")
    updated = build_model(RAW_DIR, "02_avisos_empleo_ACTUALIZADO_mayo.xlsx")

    assert len(updated["avisos"]) == len(base["avisos"]) + 10
    assert updated["avisos"]["periodo"].max() == pd.Timestamp("2026-05-01")
    assert updated["avisos"].loc[updated["avisos"]["periodo"].eq("2026-05-01")].shape[0] == 10

    for table in ("obras", "recomendaciones", "cursos", "recomendacion_cursos"):
        pd.testing.assert_frame_equal(base[table], updated[table])

    keys = ["region", "anio", "periodo", "codigo_ciuo"]
    comparison = base["avisos"].merge(updated["avisos"], on=keys, suffixes=("_base", "_updated"))
    assert len(comparison) == 160
    for column in ("anuncios_empleo", "vacantes_empleo", "remuneracion_mediana"):
        pd.testing.assert_series_equal(
            comparison[f"{column}_base"],
            comparison[f"{column}_updated"],
            check_names=False,
        )