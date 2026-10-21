"""Audita los denominadores de U2 contra el kit y el detector fijados en N2.

Lee los resultados por inyección de Guille y deja bajo data/ una fila por
posición planeada, incluso cuando no hubo un lugar limpio donde inyectar.
No publica filas del kit ni modifica los números oficiales.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.evaluacion import congelar_n2

RAIZ = Path(__file__).resolve().parents[2]
METODOS = {"dripsafe", "reglas_kit"}
SEMILLAS = (1, 2, 3, 4, 5)


def _semilla(valor) -> int | None:
    return None if valor is None or pd.isna(valor) else int(valor)


def _clave(sitio, nombre, desfase) -> tuple[str, str, int]:
    return str(sitio), str(nombre), int(desfase)


def auditar(manifiesto: dict, por_inyeccion: pd.DataFrame, congelamiento: dict
            ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Valida cobertura, omisiones, métodos y aislamiento entre corridas."""
    fuente = Path(manifiesto["fuente"])
    if not fuente.is_file():
        raise ValueError("La fuente de la rejilla no existe; repetir U2 con --kit")
    if congelamiento["kit"]["csv_sha256"] != congelar_n2._sha256(fuente):
        raise ValueError("La rejilla no proviene del kit fijado en N2")
    revision = congelamiento["codigo"]["commit_corte"]
    if congelar_n2._revision_codigo(revision)["sha256_archivos"] != \
            congelamiento["codigo"]["sha256_archivos"]:
        raise ValueError("El código actual no coincide con el congelamiento N2")

    sitios = set(congelamiento["sitios"])
    nombres = {f["nombre"] for f in manifiesto["rejilla"]}
    inicios = {int(h) for h in manifiesto["inicios_h"]}
    if len(nombres) != len(manifiesto["rejilla"]) or len(inicios) != len(manifiesto["inicios_h"]):
        raise ValueError("La rejilla tiene nombres o inicios repetidos")
    esperadas = {(sitio, nombre, h) for sitio in sitios for nombre in nombres for h in inicios}
    corridas = manifiesto["corridas"]
    condiciones = [(c["condicion"], _semilla(c["semilla"])) for c in corridas]
    if condiciones != [("base", None), *(("ruido", s) for s in SEMILLAS)]:
        raise ValueError("Se requiere una corrida base y las cinco semillas de ruido 1–5")

    tabla = por_inyeccion.copy()
    if not {"condicion", "semilla", "site_id", "nombre", "desfase_h", "metodo", "inicio", "recorrido_h"} <= set(tabla):
        raise ValueError("La tabla por inyección no contiene sus claves y métodos")
    tabla["semilla"] = tabla["semilla"].map(_semilla)
    tabla["desfase_h"] = tabla["desfase_h"].astype(int)
    filas = []
    patron_base = None
    esperados_globales = set()
    for corrida in corridas:
        condicion, semilla = corrida["condicion"], _semilla(corrida["semilla"])
        fichas = [("ejecutada", f) for f in corrida["inyecciones"]]
        fichas += [("omitida", f) for f in corrida["omitidas"]]
        claves = [_clave(f["site_id"], f["nombre"], f["desfase_h"]) for _, f in fichas]
        if len(claves) != len(set(claves)) or set(claves) != esperadas:
            raise ValueError(f"Faltan posiciones o hay duplicados en {condicion}/{semilla}")
        patron = {clave: (estado, f.get("inicio"), f.get("recorrido_h"))
                  for clave, (estado, f) in zip(claves, fichas)}
        if patron_base is None:
            patron_base = patron
        elif patron != patron_base:
            raise ValueError("El ruido cambió lugares, desplazamientos u omisiones")

        filtro = (tabla["condicion"] == condicion) & (
            tabla["semilla"].isna() if semilla is None else tabla["semilla"] == semilla)
        resultados = tabla[filtro]
        claves_resultados = [(*_clave(f.site_id, f.nombre, f.desfase_h), f.metodo)
                            for f in resultados.itertuples()]
        esperados_resultados = {(*clave, metodo) for clave, (estado, _) in zip(claves, fichas)
                                if estado == "ejecutada" for metodo in METODOS}
        esperados_globales.update((condicion, semilla, *k) for k in esperados_resultados)
        if len(claves_resultados) != len(set(claves_resultados)) or set(claves_resultados) != esperados_resultados:
            raise ValueError(f"Faltan resultados, hay extras o métodos duplicados en {condicion}/{semilla}")
        for estado, ficha in fichas:
            clave = _clave(ficha["site_id"], ficha["nombre"], ficha["desfase_h"])
            if estado == "omitida" and not ficha.get("omitida"):
                raise ValueError(f"La omisión {clave} no explica su motivo")
            if estado == "ejecutada":
                r = resultados[(resultados["site_id"] == clave[0]) &
                               (resultados["nombre"] == clave[1]) &
                               (resultados["desfase_h"] == clave[2])]
                if (pd.to_datetime(r["inicio"], utc=True) != pd.Timestamp(ficha["inicio"])).any() or \
                        (r["recorrido_h"].astype(int) != int(ficha["recorrido_h"])).any():
                    raise ValueError(f"El resultado no coincide con la posición inyectada: {clave}")
            filas.append({"condicion": condicion, "semilla": semilla, "site_id": clave[0],
                          "nombre": clave[1], "desfase_h": clave[2], "estado": estado,
                          "motivo_omision": ficha.get("omitida", ""),
                          "inicio": ficha.get("inicio", ""),
                          "recorrido_h": ficha.get("recorrido_h")})

    resultados_globales = [(f.condicion, _semilla(f.semilla),
                            *_clave(f.site_id, f.nombre, f.desfase_h), f.metodo)
                           for f in tabla.itertuples()]
    if len(resultados_globales) != len(set(resultados_globales)) or \
            set(resultados_globales) != esperados_globales:
        raise ValueError("La tabla contiene resultados ajenos a las seis corridas auditadas")

    auditoria = pd.DataFrame(filas).sort_values(
        ["condicion", "semilla", "site_id", "nombre", "desfase_h"], na_position="first")
    resumen = auditoria.groupby(["condicion", "semilla", "site_id", "nombre"], dropna=False).agg(
        planeadas=("estado", "size"), ejecutadas=("estado", lambda s: int((s == "ejecutada").sum())),
        omitidas=("estado", lambda s: int((s == "omitida").sum()))).reset_index()
    if not (resumen["planeadas"] == len(inicios)).all():
        raise ValueError("Los denominadores por sitio y escenario no coinciden con los inicios")
    return auditoria, resumen


def main() -> None:
    p = argparse.ArgumentParser(description="Audita las posiciones y denominadores de la rejilla N2")
    p.add_argument("--manifiesto", type=Path, default=Path("data/escenarios/rejilla.manifiesto.json"))
    p.add_argument("--inyecciones", type=Path, default=Path("data/resultados/rejilla_por_inyeccion.csv"))
    p.add_argument("--congelamiento", type=Path, default=Path("resultados/n2_congelamiento.json"))
    p.add_argument("--salida", type=Path, default=Path("data/resultados"))
    args = p.parse_args()
    manifiesto = json.loads(args.manifiesto.read_text(encoding="utf-8"))
    congelamiento = json.loads(args.congelamiento.read_text(encoding="utf-8"))
    tabla = pd.read_csv(args.inyecciones)
    auditoria, resumen = auditar(manifiesto, tabla, congelamiento)
    args.salida.mkdir(parents=True, exist_ok=True)
    auditoria.to_csv(args.salida / "n2_auditoria_rejilla.csv", index=False)
    resumen.to_csv(args.salida / "n2_auditoria_denominadores.csv", index=False)
    por_corrida = auditoria.groupby(["condicion", "semilla"], dropna=False)["estado"].value_counts().unstack(fill_value=0)
    print(por_corrida.to_string())
    print(f"Auditoría N2 → {args.salida}/n2_auditoria_*.csv")


if __name__ == "__main__":
    main()
