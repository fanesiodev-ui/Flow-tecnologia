#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# ContaFácil — Script de inicialização
# ──────────────────────────────────────────────────────────────────────────────
#
# Uso:
#   chmod +x run.sh
#   ./run.sh
#
# O que faz:
#   1. Cria um ambiente virtual Python (se não existir)
#   2. Instala as dependências do backend
#   3. Gera um balancete de exemplo
#   4. Inicia o servidor FastAPI
#   5. Abre o frontend no navegador (se possível)
# ──────────────────────────────────────────────────────────────────────────────

set -e  # Para em caso de erro

# Cores para output
VERDE='\033[0;32m'
AZUL='\033[0;34m'
AMARELO='\033[1;33m'
NC='\033[0m' # Sem cor

echo -e "${AZUL}"
echo "  ╔═══════════════════════════════════════════╗"
echo "  ║   ContaFácil — Gerador de Relatórios      ║"
echo "  ║   Sistema SaaS para Contadores            ║"
echo "  ╚═══════════════════════════════════════════╝"
echo -e "${NC}"

# ── 1. Verifica Python ────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 não encontrado. Instale o Python 3.9+ e tente novamente."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
echo -e "✅ ${PYTHON_VERSION} encontrado"

# ── 2. Ambiente virtual ───────────────────────────────────────────
VENV_DIR="backend/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo -e "\n${AMARELO}Criando ambiente virtual...${NC}"
    python3 -m venv "$VENV_DIR"
fi

# Ativa o ambiente virtual
source "$VENV_DIR/bin/activate"
echo -e "✅ Ambiente virtual ativado"

# ── 3. Instala dependências ───────────────────────────────────────
echo -e "\n${AMARELO}Instalando dependências...${NC}"
pip install -r backend/requirements.txt -q --no-warn-script-location
echo -e "✅ Dependências instaladas"

# ── 4. Cria balancete de exemplo ──────────────────────────────────
if [ ! -f "samples/balancete_exemplo.xlsx" ]; then
    echo -e "\n${AMARELO}Criando balancete de exemplo...${NC}"
    python3 samples/criar_balancete.py
fi

# ── 5. Inicia o servidor ──────────────────────────────────────────
echo -e "\n${VERDE}═══════════════════════════════════════════════${NC}"
echo -e "${VERDE}  🚀 Servidor iniciando...${NC}"
echo -e "${VERDE}═══════════════════════════════════════════════${NC}"
echo ""
echo -e "  📡 API Backend:  ${AZUL}http://localhost:8000${NC}"
echo -e "  🌐 Frontend:     ${AZUL}http://localhost:8000/app${NC}"
echo -e "  📖 Docs da API:  ${AZUL}http://localhost:8000/docs${NC}"
echo ""
echo -e "  ${AMARELO}Pressione Ctrl+C para parar o servidor${NC}"
echo ""

# Abre o browser automaticamente (funciona no macOS e Linux com desktop)
sleep 2 && (
    if command -v open &>/dev/null; then
        open "http://localhost:8000/app"
    elif command -v xdg-open &>/dev/null; then
        xdg-open "http://localhost:8000/app"
    fi
) &

# Inicia o FastAPI a partir do diretório backend
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
