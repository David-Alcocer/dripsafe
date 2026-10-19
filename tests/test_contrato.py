from src import contrato
from src.sinteticos import generar


def test_sinteticos_cumplen_el_contrato():
    df = generar(dias=2)
    assert contrato.validar(df) == []


def test_sinteticos_tienen_un_pue_creible():
    df = generar(dias=2)
    pue = df["kw_total"].sum() / df["kw_ti"].sum()
    assert 1.2 < pue < 1.5


def test_misma_semilla_mismos_datos():
    assert generar(dias=1, semilla=7).equals(generar(dias=1, semilla=7))


def test_validar_detecta_columna_obligatoria_faltante():
    df = generar(dias=1).drop(columns=["kw_ti"])
    assert any("kw_ti" in p for p in contrato.validar(df))


def test_validar_detecta_columnas_fuera_del_contrato():
    df = generar(dias=1).assign(columna_rara=0)
    assert any("columna_rara" in p for p in contrato.validar(df))


def test_el_modelo_nunca_ve_etiquetas():
    df = generar(dias=1).assign(etiqueta_tipo="normal")
    columnas = contrato.columnas_del_modelo(df)
    assert "etiqueta_tipo" not in columnas
    assert "timestamp" not in columnas
    assert "kw_ti" in columnas
