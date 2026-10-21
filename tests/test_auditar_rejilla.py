"""La auditoría de N2 usa solo un archivo ficticio, nunca el kit real."""

import copy

import pandas as pd
import pytest

from src.evaluacion import auditar_rejilla, congelar_n2


@pytest.fixture
def entradas(tmp_path, monkeypatch):
    fuente = tmp_path / "ejemplo.csv"
    fuente.write_text("dato sintético", encoding="utf-8")
    monkeypatch.setattr(congelar_n2, "_revision_codigo", lambda _: {"sha256_archivos": {}})
    congelamiento = {"kit": {"csv_sha256": congelar_n2._sha256(fuente)},
                    "codigo": {"commit_corte": "prueba", "sha256_archivos": {}},
                    "sitios": {"SIM-PRUEBA": {}}}
    manifiesto = {"fuente": str(fuente), "rejilla": [{"nombre": "energia_+10"},
                                                    {"nombre": "cambio_con_efecto"}],
                  "inicios_h": [6], "corridas": []}
    filas = []
    for condicion, semilla in [("base", None), *(("ruido", s) for s in range(1, 6))]:
        ficha = {"site_id": "SIM-PRUEBA", "nombre": "energia_+10", "desfase_h": 6,
                 "inicio": "2026-10-15 06:00:00+00:00", "recorrido_h": 0}
        omitida = {"site_id": "SIM-PRUEBA", "nombre": "cambio_con_efecto",
                   "desfase_h": 6, "omitida": "no hay lugar limpio"}
        manifiesto["corridas"].append({"condicion": condicion, "semilla": semilla,
                                       "inyecciones": [ficha], "omitidas": [omitida]})
        for metodo in auditar_rejilla.METODOS:
            filas.append({**ficha, "condicion": condicion, "semilla": semilla, "metodo": metodo})
    return manifiesto, pd.DataFrame(filas), congelamiento


def test_audita_posiciones_y_denominadores_incluyendo_omitidas(entradas):
    auditoria, resumen = auditar_rejilla.auditar(*entradas)
    assert len(auditoria) == 12  # dos posiciones por cada una de las seis corridas
    assert len(resumen) == 12
    assert set(resumen["planeadas"]) == {1}
    assert set(resumen["ejecutadas"]) == {0, 1}
    assert set(resumen["omitidas"]) == {0, 1}


def test_rechaza_resultado_faltante_y_fila_ajena(entradas):
    manifiesto, tabla, congelamiento = entradas
    with pytest.raises(ValueError, match="Faltan resultados"):
        auditar_rejilla.auditar(manifiesto, tabla.iloc[:-1], congelamiento)
    extra = pd.concat([tabla, tabla.iloc[[0]].assign(semilla=99)], ignore_index=True)
    with pytest.raises(ValueError, match="ajenos"):
        auditar_rejilla.auditar(manifiesto, extra, congelamiento)


def test_rechaza_omisiones_que_cambian_con_el_ruido(entradas):
    manifiesto, tabla, congelamiento = entradas
    cambiado = copy.deepcopy(manifiesto)
    cambiado["corridas"][1]["omitidas"][0]["omitida"] = "otro motivo"
    # El motivo puede aclararse por semilla; las posiciones y omisiones no.
    auditar_rejilla.auditar(cambiado, tabla, congelamiento)
    cambiado["corridas"][1]["inyecciones"][0]["inicio"] = "2026-10-15 07:00:00+00:00"
    with pytest.raises(ValueError, match="El ruido cambió"):
        auditar_rejilla.auditar(cambiado, tabla, congelamiento)
