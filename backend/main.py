"""
API principal do Gerador Inteligente de Relatórios Contábeis.

Endpoints:
  POST /api/generate-report  — Upload de balancete → gera PDF
  POST /api/demo-report      — Gera relatório com dados de exemplo
  GET  /api/download/{id}    — Download do PDF gerado
  GET  /health               — Status da API

Para rodar:
    cd backend
    uvicorn main:app --reload
"""

import os
import uuid
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import UPLOAD_DIR, REPORTS_DIR, MAX_FILE_SIZE
from models.schemas import FinancialData, WhiteLabelConfig
from processors.excel_processor import process_excel
from processors.pdf_processor import process_pdf
from processors.data_analyzer import analisar
from generators.report_generator import ReportGenerator

# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Gerador Inteligente de Relatórios Contábeis",
    description="Transforma balancetes em relatórios profissionais para clientes",
    version="1.0.0",
)

# Permite que o frontend (rodando em outra porta) acesse a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve o frontend estático em /app
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


# ─────────────────────────────────────────────────────────────────────────────
# Rotas de utilidade
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "mensagem": "API do Gerador de Relatórios Contábeis",
        "versao": "1.0.0",
        "frontend": "/app",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────────────────────
# Geração de relatório a partir de arquivo real
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/generate-report")
async def generate_report(
    file: UploadFile = File(..., description="Balancete em Excel (.xlsx) ou PDF"),
    empresa_nome: str = Form(..., description="Nome da empresa do cliente"),
    periodo: str = Form(..., description="Período de referência, ex: Março/2024"),
    accountant_name: str = Form(default="Seu Contador", description="Nome do contador"),
    company_name: str = Form(default="Contabilidade Profissional", description="Nome do escritório"),
    primary_color: str = Form(default="#1E40AF", description="Cor principal (#RRGGBB)"),
    secondary_color: str = Form(default="#7C3AED", description="Cor secundária (#RRGGBB)"),
):
    """
    Processa um balancete (Excel ou PDF) e gera um relatório PDF profissional.

    - Aceita arquivos .xlsx, .xls e .pdf
    - Extrai automaticamente faturamento, impostos, custos e despesas
    - Gera análise com linguagem simples + recomendações
    - Retorna URL para download do PDF gerado
    """

    # Valida extensão
    nome_arquivo = (file.filename or "").lower()
    if not any(nome_arquivo.endswith(ext) for ext in (".xlsx", ".xls", ".pdf")):
        raise HTTPException(
            status_code=400,
            detail="Formato não suportado. Envie um arquivo .xlsx, .xls ou .pdf",
        )

    # Valida tamanho
    conteudo = await file.read()
    if len(conteudo) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo muito grande. Limite: {MAX_FILE_SIZE // (1024*1024)} MB",
        )

    # Salva arquivo temporariamente
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(nome_arquivo)[1]
    upload_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")

    with open(upload_path, "wb") as f:
        f.write(conteudo)

    try:
        # 1. Processa o arquivo
        if nome_arquivo.endswith(".pdf"):
            dados_brutos = process_pdf(upload_path)
        else:
            dados_brutos = process_excel(upload_path)

        # 2. Monta modelo de dados
        dados_financeiros = FinancialData(
            empresa_nome=empresa_nome,
            periodo=periodo,
            faturamento=dados_brutos.get("faturamento", 0),
            impostos=dados_brutos.get("impostos", 0),
            custos_operacionais=dados_brutos.get("custos_operacionais", 0),
            despesas_administrativas=dados_brutos.get("despesas_administrativas", 0),
            outras_despesas=dados_brutos.get("outras_despesas", 0),
            lucro_bruto=dados_brutos.get("lucro_bruto", 0),
            lucro_liquido=dados_brutos.get("lucro_liquido", 0),
        )

        # 3. Gera análise inteligente
        insights, recomendacoes = analisar(dados_brutos)

        # 4. Configuração white label
        white_label = WhiteLabelConfig(
            company_name=company_name,
            accountant_name=accountant_name,
            primary_color=primary_color,
            secondary_color=secondary_color,
        )

        # 5. Gera PDF
        report_id = str(uuid.uuid4())
        report_path = os.path.join(REPORTS_DIR, f"relatorio_{report_id}.pdf")

        gerador = ReportGenerator(white_label)
        gerador.generate(dados_financeiros, insights, recomendacoes, report_path)

        return JSONResponse({
            "success": True,
            "report_id": report_id,
            "download_url": f"/api/download/{report_id}",
            "message": "Relatório gerado com sucesso!",
            "summary": {
                "empresa": empresa_nome,
                "periodo": periodo,
                "faturamento": dados_financeiros.faturamento,
                "lucro_liquido": dados_financeiros.lucro_liquido,
                "total_insights": len(insights),
                "total_recomendacoes": len(recomendacoes),
            },
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {str(e)}")

    finally:
        # Remove arquivo temporário sempre
        if os.path.exists(upload_path):
            os.remove(upload_path)


# ─────────────────────────────────────────────────────────────────────────────
# Relatório de demonstração (sem upload de arquivo)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/demo-report")
async def demo_report(
    empresa_nome: str = Form(default="Empresa Modelo LTDA"),
    periodo: str = Form(default="Março/2024"),
    accountant_name: str = Form(default="Contabilidade Profissional"),
    company_name: str = Form(default="Escritório Modelo"),
    primary_color: str = Form(default="#1E40AF"),
    secondary_color: str = Form(default="#7C3AED"),
):
    """
    Gera um relatório PDF de demonstração com dados fictícios.
    Útil para mostrar o sistema para clientes sem precisar de um arquivo real.
    """
    dados_financeiros = FinancialData(
        empresa_nome=empresa_nome,
        periodo=periodo,
        faturamento=150_000.0,
        impostos=18_000.0,
        custos_operacionais=45_000.0,
        despesas_administrativas=25_000.0,
        outras_despesas=12_000.0,
        lucro_bruto=105_000.0,
        lucro_liquido=50_000.0,
    )

    dados_brutos = {
        "faturamento": 150_000.0,
        "impostos": 18_000.0,
        "custos_operacionais": 45_000.0,
        "despesas_administrativas": 25_000.0,
        "outras_despesas": 12_000.0,
    }

    insights, recomendacoes = analisar(dados_brutos)

    white_label = WhiteLabelConfig(
        company_name=company_name,
        accountant_name=accountant_name,
        primary_color=primary_color,
        secondary_color=secondary_color,
    )

    report_id = str(uuid.uuid4())
    report_path = os.path.join(REPORTS_DIR, f"relatorio_{report_id}.pdf")

    gerador = ReportGenerator(white_label)
    gerador.generate(dados_financeiros, insights, recomendacoes, report_path)

    return JSONResponse({
        "success": True,
        "report_id": report_id,
        "download_url": f"/api/download/{report_id}",
        "message": "Relatório demo gerado com sucesso!",
    })


# ─────────────────────────────────────────────────────────────────────────────
# Download do PDF gerado
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/download/{report_id}")
async def download_report(report_id: str):
    """
    Retorna o PDF gerado para download.

    O report_id é retornado pelo endpoint /api/generate-report ou /api/demo-report.
    """
    # Sanitiza o ID para evitar path traversal
    if not all(c.isalnum() or c == "-" for c in report_id):
        raise HTTPException(status_code=400, detail="ID de relatório inválido")

    report_path = os.path.join(REPORTS_DIR, f"relatorio_{report_id}.pdf")

    if not os.path.exists(report_path):
        raise HTTPException(
            status_code=404,
            detail="Relatório não encontrado. Pode ter expirado — gere novamente.",
        )

    return FileResponse(
        report_path,
        media_type="application/pdf",
        filename=f"relatorio_contabil_{report_id[:8]}.pdf",
        headers={"Content-Disposition": f'attachment; filename="relatorio_contabil_{report_id[:8]}.pdf"'},
    )
