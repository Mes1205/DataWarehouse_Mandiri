#!/usr/bin/env bash
# Jalankan seluruh dashboard (OLAP cube + backend FastAPI + frontend React)
# dengan satu perintah. Tekan Ctrl+C untuk menghentikan semuanya.
#
# Pemakaian:
#   ./run_dashboard.sh
# Lalu buka: http://localhost:5173

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/dashboard/backend"
FRONTEND_DIR="$ROOT_DIR/dashboard/frontend"
VENV_DIR="$ROOT_DIR/.venv_atoti"

if [ ! -d "$VENV_DIR" ]; then
  echo "Venv $VENV_DIR tidak ditemukan. Buat dulu: python3.11 -m venv .venv_atoti && source .venv_atoti/bin/activate && pip install -r requirements.txt"
  exit 1
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
export ATOTI_HIDE_EULA_MESSAGE=True

# --- Backend (build OLAP cube + serve API) ---
echo ">>> Menjalankan backend (FastAPI + Atoti cube) di http://127.0.0.1:8000 ..."
(cd "$BACKEND_DIR" && uvicorn main:app --port 8000) &
BACKEND_PID=$!

cleanup() {
  echo ""
  echo ">>> Menghentikan backend (PID $BACKEND_PID) ..."
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# --- Tunggu backend siap (cube selesai dibangun) ---
echo ">>> Menunggu cube selesai dibangun (bisa beberapa detik)..."
until curl -s -o /dev/null "http://127.0.0.1:8000/api/filters/options"; do
  sleep 1
done
echo ">>> Backend siap."

# --- Frontend ---
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo ">>> Install dependency frontend (sekali saja)..."
  (cd "$FRONTEND_DIR" && npm install)
fi

echo ">>> Menjalankan frontend di http://localhost:5173 ..."
(cd "$FRONTEND_DIR" && npm run dev)
