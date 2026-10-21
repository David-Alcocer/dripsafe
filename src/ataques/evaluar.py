"""Mide qué escenarios detecta el modelo (contratos 2 + 3 → deteccion_por_escenario.csv).

Solo para los escenarios sintéticos de un sitio (docs/06, apéndice A). La
evaluación sobre el kit la hace src/ataques/correr_rejilla.py con la función por
episodio de Nico (D17).

Para cada escenario responde: ¿lo detectó?, ¿cuánto tardó? y ¿qué parte de la
ventana marcó? También cuenta las falsas alarmas en las horas normales. Esta
tabla es la evidencia del criterio «Impacto en ciberseguridad».

Uso:
    python -m src.ataques.evaluar \\
        --escenarios data/escenarios/telemetria_escenarios.csv \\
        --alertas data/resultados/alertas.csv
"""

import argparse
from pathlib import Path

import pandas as pd

from src import contrato

# Qué tipo sugerido cuenta como clasificación correcta para cada tipo real.
TIPO_ESPERADO = {"ataque": "posible_ataque", "falla": "ineficiencia"}


def evaluar(escenarios: pd.DataFrame, alertas: pd.DataFrame):
    """Regresa (tabla por escenario, resumen de falsas alarmas)."""
    df = escenarios.merge(alertas, on="timestamp", how="left", validate="one_to_one")
    df["anomalia"] = df["anomalia"].fillna(False).astype(bool)
    # Al leer el CSV, los textos vacíos llegan como NaN.
    for col in ["etiqueta_escenario", "etiqueta_tecnica"]:
        df[col] = df[col].fillna("")
    df = df[df["etiqueta_particion"] == "evaluacion"]

    filas = []
    for nombre, v in df[df["etiqueta_escenario"] != ""].groupby("etiqueta_escenario", sort=False):
        alertadas = v[v["anomalia"]]
        detectado = len(alertadas) > 0
        minutos = (alertadas["timestamp"].iloc[0] - v["timestamp"].iloc[0]).total_seconds() / 60 if detectado else None
        tipo = v["etiqueta_tipo"].iloc[0]
        fila = {
            "escenario": nombre,
            "tipo": tipo,
            "tecnica": v["etiqueta_tecnica"].iloc[0],
            "detectado": detectado,
            "minutos_hasta_alerta": minutos,
            "cobertura_pct": round(100 * len(alertadas) / len(v), 1),
        }
        if "tipo_sugerido" in df.columns and detectado:
            correctas = (alertadas["tipo_sugerido"] == TIPO_ESPERADO[tipo]).mean()
            fila["clasificacion_correcta_pct"] = round(100 * correctas, 1)
        filas.append(fila)

    normales = df[df["etiqueta_tipo"] == "normal"]
    dias_normales = len(normales) * contrato.intervalo_horas(escenarios) / 24
    falsas = int(normales["anomalia"].sum())
    resumen = {
        "escenarios_detectados": sum(f["detectado"] for f in filas),
        "escenarios_totales": len(filas),
        "falsas_alarmas": falsas,
        "falsas_alarmas_por_dia": round(falsas / dias_normales, 2) if dias_normales else None,
        "falsas_alarmas_pct": round(100 * falsas / len(normales), 2) if len(normales) else None,
    }
    return pd.DataFrame(filas), resumen


def main():
    p = argparse.ArgumentParser(description="Evalúa la detección por escenario.")
    p.add_argument("--escenarios", default="data/escenarios/telemetria_escenarios.csv")
    p.add_argument("--alertas", default="data/resultados/alertas.csv")
    p.add_argument("--salida", default="data/resultados/deteccion_por_escenario.csv")
    a = p.parse_args()

    tabla, resumen = evaluar(contrato.leer(a.escenarios), contrato.leer(a.alertas))
    Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(a.salida, index=False)
    print(tabla.to_string(index=False))
    print(f"\nDetectados: {resumen['escenarios_detectados']} de {resumen['escenarios_totales']} · "
          f"falsas alarmas: {resumen['falsas_alarmas']} ({resumen['falsas_alarmas_por_dia']} por día)")
    print(f"Tabla → {a.salida}")


if __name__ == "__main__":
    main()
