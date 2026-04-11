"""
API principal do ContaFácil SaaS.
Sistema multi-tenant: cada contador acessa apenas seus próprios relatórios.
"""

import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import UPLOAD_DIR, MAX_FILE_SIZE
from database import get_db, criar_tabelas
from models.schemas import FinancialData, WhiteLabelConfig
from models.db_models import Contador, Relatorio
from processors.excel_processor import process_excel
from processors.pdf_processor import process_pdf
from processors.data_analyzer import analisar
from generators.report_generator import ReportGenerator
from auth import hash_senha, verificar_senha, criar_token, get_current_user


# ── Startup ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    criar_tabelas()
    yield


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ContaFácil SaaS",
    description="Gerador de Relatórios Contábeis — Multi-tenant",
    version="3.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


# ── Schemas de entrada ────────────────────────────────────────────────────────

class RegisterInput(BaseModel):
    nome: str
    email: str
    senha: str
    escritorio: str


# ── Rotas base ────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"mensagem": "ContaFácil SaaS v3.1", "login": "/app/login.html", "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/auth/register")
async def register(data: RegisterInput, db: Session = Depends(get_db)):
    """Cria uma nova conta de contador."""
    if db.query(Contador).filter(Contador.email == data.email.lower()).first():
        raise HTTPException(status_code=409, detail="E-mail já cadastrado.")

    contador = Contador(
        nome=data.nome,
        email=data.email.lower(),
        senha_hash=hash_senha(data.senha),
        escritorio=data.escritorio,
    )
    db.add(contador)
    db.commit()
    db.refresh(contador)

    token = criar_token(contador.id, contador.email)
    return JSONResponse({
        "success": True,
        "token": token,
        "contador": {"id": contador.id, "nome": contador.nome, "escritorio": contador.escritorio},
    })


@app.post("/auth/login")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login com e-mail e senha — retorna token JWT."""
    contador = db.query(Contador).filter(Contador.email == form.username.lower()).first()
    if not contador or not verificar_senha(form.password, contador.senha_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")

    token = criar_token(contador.id, contador.email)
    return JSONResponse({
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "contador": {"id": contador.id, "nome": contador.nome, "escritorio": contador.escritorio},
    })


@app.get("/auth/me")
async def me(atual: Contador = Depends(get_current_user)):
    """Retorna dados do contador logado."""
    return JSONResponse({
        "id": atual.id,
        "nome": atual.nome,
        "email": atual.email,
        "escritorio": atual.escritorio,
        "cor_primaria": atual.cor_primaria,
    })


# ── Geração de relatório (protegido) ─────────────────────────────────────────

@app.post("/api/generate-report")
async def generate_report(
    file: UploadFile = File(...),
    empresa_nome: str = Form(...),
    periodo: str = Form(...),
    db: Session = Depends(get_db),
    atual: Contador = Depends(get_current_user),
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
            company_name=atual.escritorio,
            accountant_name=atual.nome,
            primary_color=atual.cor_primaria,
        )

        report_id = str(uuid.uuid4())
        report_filename = f"relatorio_{report_id}.pdf"
        report_path = os.path.join(UPLOAD_DIR, report_filename)
        ReportGenerator(white_label).generate(dados_financeiros, insights, recomendacoes, report_path)

        # Lê o PDF gerado e guarda no banco — o arquivo local pode ser descartado
        with open(report_path, "rb") as f:
            pdf_bytes = f.read()
        os.remove(report_path)

        fat = dados_financeiros.faturamento
        margem = (dados_financeiros.lucro_liquido / fat * 100) if fat > 0 else 0

        registro = Relatorio(
            contador_id=atual.id,
            empresa_nome=empresa_nome, periodo=periodo,
            arquivo_pdf=report_filename,
            pdf_bytes=pdf_bytes,
            faturamento=dados_financeiros.faturamento,
            impostos=dados_financeiros.impostos,
            custos_operacionais=dados_financeiros.custos_operacionais,
            despesas_administrativas=dados_financeiros.despesas_administrativas,
            outras_despesas=dados_financeiros.outras_despesas,
            lucro_liquido=dados_financeiros.lucro_liquido,
            margem_lucro=round(margem, 2),
            nome_escritorio=atual.escritorio,
            nome_contador=atual.nome,
            cor_primaria=atual.cor_primaria,
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
                "empresa": empresa_nome, "periodo": periodo,
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


@app.post("/api/demo-report")
async def demo_report(
    empresa_nome: str = Form(default="Empresa Modelo LTDA"),
    periodo: str = Form(default="Abril/2025"),
    db: Session = Depends(get_db),
    atual: Contador = Depends(get_current_user),
):
    dados_financeiros = FinancialData(
        empresa_nome=empresa_nome, periodo=periodo,
        faturamento=150_000.0, impostos=18_000.0,
        custos_operacionais=45_000.0, despesas_administrativas=25_000.0,
        outras_despesas=12_000.0, lucro_bruto=105_000.0, lucro_liquido=50_000.0,
        ativo_circulante=95_000.0, passivo_circulante=52_000.0,
        ativo_total=220_000.0, passivo_total=88_000.0,
    )
    dados_brutos = {
        "faturamento": 150_000.0, "impostos": 18_000.0,
        "custos_operacionais": 45_000.0, "despesas_administrativas": 25_000.0,
        "outras_despesas": 12_000.0,
    }

    insights, recomendacoes = analisar(dados_brutos)
    white_label = WhiteLabelConfig(
        company_name=atual.escritorio,
        accountant_name=atual.nome,
        primary_color=atual.cor_primaria,
    )

    report_id = str(uuid.uuid4())
    report_filename = f"relatorio_{report_id}.pdf"
    report_path = os.path.join(UPLOAD_DIR, report_filename)
    ReportGenerator(white_label).generate(dados_financeiros, insights, recomendacoes, report_path)

    with open(report_path, "rb") as f:
        pdf_bytes = f.read()
    os.remove(report_path)

    registro = Relatorio(
        contador_id=atual.id,
        empresa_nome=empresa_nome, periodo=periodo,
        arquivo_pdf=report_filename,
        pdf_bytes=pdf_bytes,
        faturamento=150_000.0, impostos=18_000.0,
        custos_operacionais=45_000.0, despesas_administrativas=25_000.0,
        outras_despesas=12_000.0, lucro_liquido=50_000.0, margem_lucro=33.3,
        nome_escritorio=atual.escritorio, nome_contador=atual.nome,
        cor_primaria=atual.cor_primaria,
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


# ── Download (protegido — só o dono do relatório) ─────────────────────────────

@app.get("/api/download/{report_id}")
async def download_report(
    report_id: str,
    db: Session = Depends(get_db),
    atual: Contador = Depends(get_current_user),
):
    if not all(c.isalnum() or c == "-" for c in report_id):
        raise HTTPException(status_code=400, detail="ID inválido")

    report_filename = f"relatorio_{report_id}.pdf"

    registro = db.query(Relatorio).filter(
        Relatorio.arquivo_pdf == report_filename,
        Relatorio.contador_id == atual.id,
    ).first()

    if not registro or not registro.pdf_bytes:
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")

    return Response(
        content=registro.pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="relatorio_{report_id[:8]}.pdf"'},
    )


# ── Histórico (isolado por tenant) ────────────────────────────────────────────

@app.get("/api/historico")
async def listar_historico(
    limite: int = 50,
    empresa: Optional[str] = None,
    db: Session = Depends(get_db),
    atual: Contador = Depends(get_current_user),
):
    query = (
        db.query(Relatorio)
        .filter(Relatorio.contador_id == atual.id)
        .order_by(Relatorio.criado_em.desc())
    )
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
            "tem_pdf": bool(r.pdf_bytes),
            "arquivo_pdf": r.arquivo_pdf,
        }
        for r in registros
    ])


@app.get("/api/historico/resumo")
async def resumo_historico(
    db: Session = Depends(get_db),
    atual: Contador = Depends(get_current_user),
):
    total = db.query(Relatorio).filter(Relatorio.contador_id == atual.id).count()
    empresas = (
        db.query(Relatorio.empresa_nome)
        .filter(Relatorio.contador_id == atual.id)
        .distinct().count()
    )
    return JSONResponse({"total_relatorios": total, "total_empresas": empresas})


@app.delete("/api/relatorio/{relatorio_id}")
async def deletar_relatorio(
    relatorio_id: int,
    db: Session = Depends(get_db),
    atual: Contador = Depends(get_current_user),
):
    registro = db.query(Relatorio).filter(
        Relatorio.id == relatorio_id,
        Relatorio.contador_id == atual.id,
    ).first()
    if not registro:
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")

    db.delete(registro)
    db.commit()
    return JSONResponse({"success": True, "message": "Relatório removido."})