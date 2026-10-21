"""Mete ataques y fallas simulados en la telemetría (contrato 1 → contrato 2).

Solo para los datos sintéticos de un sitio (src/sinteticos.py). Sobre el kit se
usa src/ataques/correr_rejilla.py (docs/06 §5).

La primera parte de los datos (por defecto, la mitad) queda intacta y se marca
como «entrenamiento»: es lo que el modelo aprende como normal. Los escenarios
van en la otra parte, cada uno en su propia ventana y con huecos normales entre
ellos para poder contar falsas alarmas.

Uso:
    python -m src.ataques.inyectar --entrada data/sinteticos/telemetria.csv \\
        --salida data/escenarios/telemetria_escenarios.csv

Genera también <salida>.manifiesto.json con las ventanas exactas.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src import contrato
from src.ataques.escenarios import CATALOGO, POR_NOMBRE, Contexto


def _colocar(n_filas_escenario, inicio_hueco, fin_hueco, ts, hora_inicio, rng):
    """Elige dónde empieza un escenario dentro de su hueco [inicio_hueco, fin_hueco)."""
    ultimo = fin_hueco - n_filas_escenario
    if ultimo < inicio_hueco:
        return None
    candidatos = np.arange(inicio_hueco, ultimo + 1)
    if hora_inicio is not None:
        a_la_hora = candidatos[(ts.iloc[candidatos].dt.hour == hora_inicio).to_numpy()]
        if len(a_la_hora):
            candidatos = a_la_hora
    return int(rng.choice(candidatos))


def inyectar(df: pd.DataFrame, nombres=None, semilla: int = 42, fraccion_limpia: float = 0.5):
    """Regresa (telemetría con escenarios, manifiesto). No modifica `df`."""
    problemas = contrato.validar(df)
    if problemas:
        raise ValueError("La entrada no cumple el contrato: " + "; ".join(problemas))

    rng = np.random.default_rng(semilla)
    out = df.copy().reset_index(drop=True)
    for col in out.columns:
        if col not in ("timestamp", "bomba_encendida"):
            out[col] = out[col].astype(float)
    ctx = Contexto(rng=rng, horas=contrato.intervalo_horas(out), original=out.copy())
    n = len(out)
    corte = int(n * fraccion_limpia)

    out["etiqueta_escenario"] = ""
    out["etiqueta_tipo"] = "normal"
    out["etiqueta_tecnica"] = ""
    out["etiqueta_particion"] = np.where(np.arange(n) < corte, "entrenamiento", "evaluacion")

    elegidos = [POR_NOMBRE[x] for x in nombres] if nombres else list(CATALOGO)
    aplicables, omitidos = [], []
    for e in elegidos:
        faltan = [c for c in e.requiere if c not in out.columns]
        if faltan:
            omitidos.append({"nombre": e.nombre, "motivo": f"faltan columnas {faltan}"})
        else:
            aplicables.append(e)
    aplicables = [aplicables[i] for i in rng.permutation(len(aplicables))]
    filas_de = {e.nombre: max(1, int(round(e.horas / ctx.horas))) for e in aplicables}

    # Si no caben todos, se quitan primero los más largos.
    while aplicables and sum(filas_de[e.nombre] for e in aplicables) > n - corte:
        largo = max(aplicables, key=lambda e: filas_de[e.nombre])
        aplicables.remove(largo)
        omitidos.append({"nombre": largo.nombre, "motivo": "no cabe: hay pocos datos para tantos escenarios"})

    # Cada escenario recibe un hueco de su tamaño más una parte igual de horas normales.
    # Así nunca se enciman y quedan horas normales entre ellos para contar falsas alarmas.
    libre = (n - corte) - sum(filas_de[e.nombre] for e in aplicables)
    extra = libre // max(1, len(aplicables))
    ventanas = []
    ini_h = corte
    for e in aplicables:
        filas = filas_de[e.nombre]
        fin_h = ini_h + filas + extra
        inicio = _colocar(filas, ini_h, fin_h, out["timestamp"], e.hora_inicio, rng)
        ini_h = fin_h
        idx = out.index[inicio:inicio + filas]
        e.aplicar(out, idx, ctx)
        out.loc[idx, "etiqueta_escenario"] = e.nombre
        out.loc[idx, "etiqueta_tipo"] = e.tipo
        out.loc[idx, "etiqueta_tecnica"] = e.tecnica
        ventanas.append({
            "nombre": e.nombre, "tipo": e.tipo, "tecnica": e.tecnica,
            "nombre_tecnica": e.nombre_tecnica,
            "inicio": str(out.loc[idx[0], "timestamp"]),
            "fin": str(out.loc[idx[-1], "timestamp"]),
            "filas": filas, "descripcion": e.descripcion, "huella": e.huella,
        })

    ventanas.sort(key=lambda v: v["inicio"])
    manifiesto = {
        "semilla": semilla,
        "fraccion_limpia": fraccion_limpia,
        "minutos_por_intervalo": round(ctx.horas * 60, 2),
        "filas": n,
        "inicio_evaluacion": str(out.loc[corte, "timestamp"]) if corte < n else None,
        "escenarios": ventanas,
        "omitidos": omitidos,
    }
    return out, manifiesto


def main():
    p = argparse.ArgumentParser(description="Inyecta ataques y fallas simulados en la telemetría.")
    p.add_argument("--entrada", required=True, help="CSV con el formato del contrato 1")
    p.add_argument("--salida", default="data/escenarios/telemetria_escenarios.csv")
    p.add_argument("--escenarios", help="nombres separados por coma (por defecto, todos)")
    p.add_argument("--semilla", type=int, default=42)
    p.add_argument("--fraccion-limpia", type=float, default=0.5,
                   help="parte inicial sin escenarios, para entrenar (0 a 1)")
    a = p.parse_args()

    nombres = a.escenarios.split(",") if a.escenarios else None
    out, manifiesto = inyectar(contrato.leer(a.entrada), nombres, a.semilla, a.fraccion_limpia)

    salida = Path(a.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(salida, index=False)
    ruta_manifiesto = salida.with_suffix(".manifiesto.json")
    ruta_manifiesto.write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{len(out)} filas → {salida}")
    for v in manifiesto["escenarios"]:
        print(f"  {v['inicio']}  {v['tipo']:6}  {v['tecnica'] or '-':12}  {v['nombre']}")
    for o in manifiesto["omitidos"]:
        print(f"  OMITIDO {o['nombre']}: {o['motivo']}")
    print(f"Manifiesto → {ruta_manifiesto}")


if __name__ == "__main__":
    main()
