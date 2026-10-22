#!/bin/bash
# DripSafe · abre la demo con doble clic (macOS).
#
# Hace, en orden:
#   1. Busca el repo (junto a este archivo o en ~/hackathon/dripsafe).
#   2. Crea el entorno .venv e instala dependencias si no existen (solo esa vez necesita internet).
#   3. Comprueba que el kit CIFOX esté en la laptop.
#   4. Si faltan las alertas del detector, las genera con el kit.
#      No corre src.pipeline: eso regeneraría numeros_oficiales.json y borraría la firma del balance.
#   5. Detiene cualquier dashboard viejo en el puerto 8501 (su caché guarda datos viejos).
#   6. Arranca el dashboard y lo abre en el navegador.
# Para cerrar: Ctrl+C en esta ventana o cerrarla.

PUERTO=8501
URL="http://localhost:$PUERTO"

titulo() { printf '\n\033[1;36m▸ %s\033[0m\n' "$1"; }
aviso()  { printf '\033[1;33m⚠ %s\033[0m\n' "$1"; }
falla()  { printf '\n\033[1;31m✗ %s\033[0m\n\n' "$1"; read -r -p "Presiona Enter para cerrar..."; exit 1; }

# 1 · Repo: la carpeta de este archivo; si lo copiaron al Escritorio, la ruta de siempre.
AQUI="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$AQUI/app/main.py" ]; then
    REPO="$AQUI"
elif [ -f "$HOME/hackathon/dripsafe/app/main.py" ]; then
    REPO="$HOME/hackathon/dripsafe"
else
    falla "No encontré el repo de DripSafe. Deja este archivo dentro de la carpeta dripsafe."
fi
cd "$REPO" || falla "No pude entrar a $REPO"
printf '\033[1mDripSafe · demo\033[0m  (DATOS SIMULADOS)\nRepo: %s\n' "$REPO"

# 2 · Entorno de Python
PY="$REPO/.venv/bin/python"
if [ ! -x "$PY" ]; then
    titulo "Creando el entorno de Python (solo la primera vez, necesita internet)"
    BASE="$(command -v python3.12 || command -v python3)"
    [ -n "$BASE" ] || falla "No hay Python instalado. Instala Python 3.12 desde python.org."
    "$BASE" -m venv .venv || falla "No pude crear .venv"
    "$PY" -m pip install -q -r requirements.txt || falla "No pude instalar las dependencias. ¿Hay internet?"
fi
"$PY" -c "import streamlit, pandas, plotly" 2>/dev/null || {
    titulo "Instalando dependencias que faltan"
    "$PY" -m pip install -q -r requirements.txt || falla "No pude instalar las dependencias. ¿Hay internet?"
}

# 3 · Kit CIFOX (confidencial, fuera del repo)
KIT_DIR="${DRIPSAFE_KIT:-$HOME/hackathon/Kit Stack Tecnológico/Para participantes/Código y recursos}"
KIT_CSV="$KIT_DIR/data/operaciones_simuladas.csv"
if [ -f "$KIT_CSV" ]; then
    titulo "Kit encontrado"
else
    aviso "No encontré el kit en: $KIT_DIR"
    aviso "El dashboard mostrará DATOS DE EJEMPLO. No presentes así."
fi

# 4 · Alertas del detector (solo si faltan)
if [ -f "$KIT_CSV" ] && [ ! -f data/resultados/alertas.csv ]; then
    titulo "Generando las alertas del detector con el kit"
    "$PY" -m src.datos.cargar --kit "$KIT_CSV" --salida data/procesado/telemetria.csv \
        || falla "No pude cargar el kit."
    "$PY" -m src.modelo.detector --entrada data/procesado/telemetria.csv \
        --salida data/resultados/alertas.csv --sin-medir \
        || falla "El detector falló."
fi

# 5 · Dashboard viejo fuera
VIEJOS="$(lsof -ti tcp:$PUERTO -sTCP:LISTEN 2>/dev/null)"
if [ -n "$VIEJOS" ]; then
    titulo "Cerrando el dashboard anterior"
    kill $VIEJOS 2>/dev/null
    sleep 1
fi

# 6 · Arrancar y abrir
titulo "Arrancando el dashboard"
"$PY" -m streamlit run app/main.py --server.headless true --server.port "$PUERTO" &
SERVIDOR=$!
trap 'kill $SERVIDOR 2>/dev/null; echo; echo "Dashboard detenido."; exit 0' INT TERM HUP

for _ in $(seq 1 60); do
    curl -s "$URL/_stcore/health" >/dev/null 2>&1 && break
    kill -0 $SERVIDOR 2>/dev/null || falla "El dashboard no arrancó. Revisa los mensajes de arriba."
    sleep 0.5
done
curl -s "$URL/_stcore/health" >/dev/null 2>&1 || falla "El dashboard tardó demasiado en arrancar."

open "$URL"
printf '\n\033[1;32m✓ Listo: %s\033[0m\n' "$URL"
echo "  Para el pitch: botón de TV (arriba a la derecha) = modo presentación."
echo "  Para cerrar: Ctrl+C o cierra esta ventana."
wait $SERVIDOR
