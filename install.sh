#!/usr/bin/env bash
set -e

echo "======================================================================"
echo "   Instalador de PowerBI MCP Server y Skills para Claude"
echo "======================================================================"
echo ""

if command -v uv &> /dev/null; then
    echo "[*] Usando uv como gestor de paquetes..."
    uv sync
    echo "[*] Configurando Servidor MCP y Skills para Claude..."
    uv run python scripts/install.py
elif command -v python3 &> /dev/null; then
    echo "[*] uv no encontrado, usando python3..."
    python3 scripts/install.py
else
    echo "[ERROR] No se encontro uv ni python3 instalados."
    echo "Por favor instala uv (curl -LsSf https://astral.sh/uv/install.sh | sh) o Python 3.11+"
    exit 1
fi

echo ""
echo "======================================================================"
echo "   Instalacion completada con exito. Reinicia Claude Desktop/Code."
echo "======================================================================"
