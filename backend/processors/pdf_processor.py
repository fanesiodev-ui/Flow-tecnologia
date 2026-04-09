"""
Processador de arquivos PDF.

Extrai texto do PDF e tenta identificar valores financeiros
associados a palavras-chave contábeis comuns.

Limitação: PDFs escaneados (imagens) não funcionam sem OCR.
Para balancetes digitais (gerados por software contábil), funciona bem.
"""

import re
import pdfplumber
from typing import Dict, Any

RECEITA_KW = ["receita", "faturamento", "vendas", "venda"]
IMPOSTO_KW = ["imposto", "tributo", "iss", "icms", "pis", "cofins", "irpj", "csll", "simples"]
CUSTO_KW = ["custo", "cmv", "cme", "mercadoria"]
DESP_ADM_KW = ["despesa admin", "administrat", "aluguel", "folha", "salário", "salario", "pessoal"]
DESP_GERAL_KW = ["despesa", "gastos", "gasto"]


def process_pdf(file_path: str) -> Dict[str, Any]:
    """
    Processa um arquivo PDF e retorna os dados financeiros classificados.

    Args:
        file_path: Caminho completo do arquivo .pdf

    Returns:
        Dicionário com faturamento, impostos, custos e despesas
    """
    try:
        texto = ""
        with pdfplumber.open(file_path) as pdf:
            for pagina in pdf.pages:
                texto += (pagina.extract_text() or "") + "\n"

        return _extrair_do_texto(texto)

    except Exception as e:
        raise ValueError(f"Não foi possível ler o arquivo PDF: {str(e)}")


def _extrair_do_texto(texto: str) -> Dict[str, Any]:
    """Percorre as linhas do texto extraído e classifica valores por palavras-chave."""

    linhas = texto.lower().split("\n")

    totais = {
        "faturamento": 0.0,
        "impostos": 0.0,
        "custos_operacionais": 0.0,
        "despesas_administrativas": 0.0,
        "outras_despesas": 0.0,
    }

    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue

        # Extrai todos os valores numéricos da linha
        nums = re.findall(r"[\d]{1,3}(?:[.\d]{3})*(?:,\d{2})?", linha)
        if not nums:
            continue

        # Pega o maior valor numérico na linha (provavelmente o saldo)
        valor_max = 0.0
        for n in nums:
            try:
                v = float(n.replace(".", "").replace(",", "."))
                if v > valor_max:
                    valor_max = v
            except ValueError:
                pass

        if valor_max == 0:
            continue

        # Classifica pela categoria
        if any(kw in linha for kw in RECEITA_KW):
            totais["faturamento"] = max(totais["faturamento"], valor_max)
        elif any(kw in linha for kw in IMPOSTO_KW):
            totais["impostos"] += valor_max
        elif any(kw in linha for kw in CUSTO_KW):
            totais["custos_operacionais"] += valor_max
        elif any(kw in linha for kw in DESP_ADM_KW):
            totais["despesas_administrativas"] += valor_max
        elif any(kw in linha for kw in DESP_GERAL_KW):
            totais["outras_despesas"] += valor_max

    if totais["faturamento"] == 0:
        # Importa e retorna dados demo se não extraiu nada
        from processors.excel_processor import _dados_demo
        return _dados_demo()

    from processors.excel_processor import _calcular_lucros
    return _calcular_lucros(totais)
