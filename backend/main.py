"""
API principal do Gerador Inteligente de Relatórios Contábeis.

Endpoints:
  POST /api/generate-report       — Upload de balancete → gera PDF
  POST /api/demo-report           — Gera relatório com dados de exemplo
  GET  /api/download/{id}         — Download do PDF gerado
  GET  /api/historico             — Lista todos os relatórios gerados
  GET  /api/historico/{empresa}   — Relatórios de uma empresa específica
  DELETE /api/relatorio/{id}      — Remove um relatório do histórico
  GET  /health                    — Status da API

Para rodar:
    cd backend
    uvicorn main:app --reload
"""

import os
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from config import UPLOAD_DIR, REPORTS_DIR, MAX_FILE_SIZE
from database import get_db, criar_tabelas
from models.schemas import FinancialData, WhiteLabelConfig
from models.db_models import Relatorio
from processors.excel_processor import process_excel
from processors.pdf_processor import process_pdf
from processors.data_analyzer import analisar
from generators.report_generator import ReportGenerator

# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Gerador Inteligente de Relatórios Contábeis",
    description="Transforma balancetes em relatórios profissionais para clientes",
    version="2.0.0",
)

# Cria as tabelas do banco ao iniciar
@app.on_event("startup")
def startup():
    criar_tabelas()

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
# Utilitários
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"mensagem": "API ContaFácil v2.0", "frontend": "/app", "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────────────────────
# Geração de relatório com arquivo real
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/generate-report")
async def generate_report(
    file: UploadFile = File(...),
    empresa_nome: str = Form(...),
    periodo: str = Form(...),
    accountant_name: str = Form(default="Seu Contador"),
    company_name: str = Form(default="Contabilidade Profissional"),
    primary_color: str = Form(default="#1E40AF"),
    secondary_color: str = Form(default="#7C3AED"),
    db: Session = Depends(get_db),
):
    nome_arquivo = (file.filename or "").lower()
    if not any(nome_arquivo.endswith(ext) for ext in (".xlsx", ".xls", ".pdf")):
        raise HTTPException(status_code=400, detail="Formato não suportado. Use .xlsx, .xls ou .pdf")

    conteudo = await file.read()
    if len(conteudo) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Arquivo muito grande. Máximo 10 MB.")

    file_id = str(uuid.uuid4())
    ext = os.path.splitext(nome_arquivo)[1]
    upload_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")

    with open(upload_path, "wb") as f:
        f.write(conteudo)

    try:
        dados_brutos = process_pdf(upload_path) if nome_arquivo.endswith(".pdf") else process_excel(upload_path)

        dados_financeiros = FinancialData(
            empresa_nome=empresa_nome, periodo=periodo,
            faturamento=dados_brutos.get("faturamento", 0),
            impostos=dados_brutos.get("impostos", 0),
            custos_operacionais=dados_brutos.get("custos_operacionais", 0),
            despesas_administrativas=dados_brutos.get("despesas_administrativas", 0),
            outras_despesas=dados_brutos.get("outras_despesas", 0),
            lucro_bruto=dados_brutos.get("lucro_bruto", 0),
            lucro_liquido=dados_brutos.get("lucro_liquido", 0),
        )

        insights, recomendacoes = analisar(dados_brutos)
        white_label = WhiteLabelConfig(
            company_name=company_name, accountant_name=accountant_name,
            primary_color=primary_color, secondary_color=secondary_color,
        )

        report_id = str(uuid.uuid4())
        report_path = os.path.join(REPORTS_DIR, f"relatorio_{report_id}.pdf")
        ReportGenerator(white_label).generate(dados_financeiros, insights, recomendacoes, report_path)

        # ── Salva no banco de dados ──
        fat = dados_financeiros.faturamento
        margem = (dados_financeiros.lucro_liquido / fat * 100) if fat > 0 else 0

        registro = Relatorio(
            empresa_nome=empresa_nome,
            periodo=periodo,
            arquivo_pdf=report_path,
            faturamento=dados_financeiros.faturamento,
            impostos=dados_financeiros.impostos,
            custos_operacionais=dados_financeiros.custos_operacionais,
            despesas_administrativas=dados_financeiros.despesas_administrativas,
            outras_despesas=dados_financeiros.outras_despesas,
            lucro_liquido=dados_financeiros.lucro_liquido,
            margem_lucro=round(margem, 2),
            nome_escritorio=company_name,
            nome_contador=accountant_name,
            cor_primaria=primary_color,
        )
        db.add(registro)
        db.commit()
        db.refresh(registro)

        return JSONResponse({
            "success": True,
            "report_id": report_id,
            "db_id": registro.id,
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
        raise HTTPException(status_code=500, detail=f"Erro ao processar: {str(e)}")
    finally:
        if os.path.exists(upload_path):
            os.remove(upload_path)


# ─────────────────────────────────────────────────────────────────────────────
# Relatório demo
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/demo-report")
async def demo_report(
    empresa_nome: str = Form(default="Empresa Modelo LTDA"),
    periodo: str = Form(default="Março/2024"),
    accountant_name: str = Form(default="Contabilidade Profissional"),
    company_name: str = Form(default="Escritório Modelo"),
    primary_color: str = Form(default="#1E40AF"),
    secondary_color: str = Form(default="#7C3AED"),
    db: Session = Depends(get_db),
):
    dados_financeiros = FinancialData(
        empresa_nome=empresa_nome, periodo=periodo,
        faturamento=150_000.0, impostos=18_000.0,
        custos_operacionais=45_000.0, despesas_administrativas=25_000.0,
        outras_despesas=12_000.0, lucro_bruto=105_000.0, lucro_liquido=50_000.0,
    )
    dados_brutos = {
        "faturamento": 150_000.0, "impostos": 18_000.0,
        "custos_operacionais": 45_000.0, "despesas_administrativas": 25_000.0,
        "outras_despesas": 12_000.0,
    }

    insights, recomendacoes = analisar(dados_brutos)
    white_label = WhiteLabelConfig(
        company_name=company_name, accountant_name=accountant_name,
        primary_color=primary_color, secondary_color=secondary_color,
    )

    report_id = str(uuid.uuid4())
    report_path = os.path.join(REPORTS_DIR, f"relatorio_{report_id}.pdf")
    ReportGenerator(white_label).generate(dados_financeiros, insights, recomendacoes, report_path)

    # Salva no banco
    registro = Relatorio(
        empresa_nome=empresa_nome, periodo=periodo,
        arquivo_pdf=report_path, faturamento=150_000.0,
        impostos=18_000.0, custos_operacionais=45_000.0,
        despesas_administrativas=25_000.0, outras_despesas=12_000.0,
        lucro_liquido=50_000.0, margem_lucro=33.3,
        nome_escritorio=company_name, nome_contador=accountant_name,
        cor_primaria=primary_color,
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)

    return JSONResponse({
        "success": True,
        "report_id": report_id,
        "db_id": registro.id,
        "download_url": f"/api/download/{report_id}",
        "message": "Relatório demo gerado com sucesso!",
    })


# ─────────────────────────────────────────────────────────────────────────────
# Download
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/download/{report_id}")
async def download_report(report_id: str):
    if not all(c.isalnum() or c == "-" for c in report_id):
        raise HTTPException(status_code=400, detail="ID inválido")

    report_path = os.path.join(REPORTS_DIR, f"relatorio_{report_id}.pdf")
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")

    return FileResponse(
        report_path, media_type="application/pdf",
        filename=f"relatorio_contabil_{report_id[:8]}.pdf",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Histórico de relatórios (banco de dados)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/historico")
async def listar_historico(
    limite: int = 50,
    empresa: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Retorna o histórico de relatórios gerados.
    Parâmetros:
      - limite: quantos registros retornar (padrão 50)
      - empresa: filtrar por nome da empresa (busca parcial)
    """
    query = db.query(Relatorio).order_by(Relatorio.criado_em.desc())

    if empresa:
        query = query.filter(Relatorio.empresa_nome.ilike(f"%{empresa}%"))

    registros = query.limit(limite).all()

    return JSONResponse([
        {
            "id": r.id,
            "empresa_nome": r.empresa_nome,
            "periodo": r.periodo,
            "faturamento": r.faturamento,
            "lucro_liquido": r.lucro_liquido,
            "margem_lucro": r.margem_lucro,
            "nome_escritorio": r.nome_escritorio,
            "criado_em": r.criado_em.strftime("%d/%m/%Y %H:%M") if r.criado_em else "",
            "tem_pdf": os.path.exists(r.arquivo_pdf) if r.arquivo_pdf else False,
            "arquivo_pdf": r.arquivo_pdf,
        }
        for r in registros
    ])


@app.get("/api/historico/resumo")
async def resumo_historico(db: Session = Depends(get_db)):
    """Retorna estatísticas gerais do uso do sistema."""
    total = db.query(Relatorio).count()
    empresas = db.query(Relatorio.empresa_nome).distinct().count()

    return JSONResponse({
        "total_relatorios": total,
        "total_empresas": empresas,
    })


@app.delete("/api/relatorio/{relatorio_id}")
async def deletar_relatorio(relatorio_id: int, db: Session = Depends(get_db)):
    """Remove um relatório do histórico (e o arquivo PDF se existir)."""
    registro = db.query(Relatorio).filter(Relatorio.id == relatorio_id).first()

    if not registro:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")

    # Remove o arquivo PDF se existir
    if registro.arquivo_pdf and os.path.exists(registro.arquivo_pdf):
        os.remove(registro.arquivo_pdf)

    db.delete(registro)
    db.commit()

    return JSONResponse({"success": True, "message": "Relatório removido com sucesso."})
