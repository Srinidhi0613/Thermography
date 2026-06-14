#!/usr/bin/env bash
# ============================================================
# Thermography Compliance AI — Quick Start Script
# ============================================================

set -e

GREEN='\033[0;32m'
ORANGE='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${ORANGE}"
echo "  ╔════════════════════════════════════════════╗"
echo "  ║   🔥 Thermography Compliance AI v2.0       ║"
echo "  ║   Industrial Monitoring Platform           ║"
echo "  ╚════════════════════════════════════════════╝"
echo -e "${NC}"

# Check Python
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}❌ Python 3 not found. Install from https://python.org${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python 3 found: $(python3 --version)${NC}"

# Create venv if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate
source venv/bin/activate 2>/dev/null || . venv/Scripts/activate 2>/dev/null

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Copy .env if not exists
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${ORANGE}⚠️  Created .env from .env.example. Edit it for MongoDB Atlas.${NC}"
fi

# Check Ollama
echo ""
if command -v ollama &>/dev/null; then
    echo -e "${GREEN}✓ Ollama found${NC}"
    echo "  Starting Ollama in background..."
    ollama serve &>/dev/null &
    sleep 2
    echo "  Pulling Llama 3 (this may take a few minutes on first run)..."
    ollama pull llama3 2>/dev/null && echo -e "${GREEN}✓ Llama 3 ready${NC}" || echo -e "${ORANGE}⚠️  Llama 3 pull failed - AI will use fallback mode${NC}"
else
    echo -e "${ORANGE}⚠️  Ollama not found. AI will run in fallback mode.${NC}"
    echo "  To install: curl -fsSL https://ollama.ai/install.sh | sh"
fi

echo ""
echo -e "${GREEN}🚀 Starting Thermography Compliance AI...${NC}"
echo -e "   Open: ${GREEN}http://localhost:8000${NC}"
echo ""

cd backend
python3 main.py
