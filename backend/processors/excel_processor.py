"""
Processador de arquivos Excel (.xlsx / .xls).

Lê balancetes em formato Excel e extrai os dados financeiros
agrupando em categorias: faturamento, impostos, custos, despesas.

Estratégia:
  1. Tenta identificar o cabeçalho automaticamente
  2. Classifica cada linha por palavras-chave
  3. Se não encontrar dados reais, retorna dados de demonstração
"""

import pandas as pd
from typing import Dict, Any

# Palavras-chave para classificar cada conta contábil
RECEITA_KW = ["receita", "faturamento", "vendas", "venda", "receitas operacionais", "servico", "serviço"]
IMPOSTO_KW = ["imposto", "tributo", "iss", "icms", "pis", "cofins", "irpj", "csll", "simples", "inss", "ipi"]
CUSTO_KW = ["custo", "cmv", "cme", "cpm", "mercadoria", "produto vendido", "material", "estoque"]
DESP_ADM_KW = ["despesa admin", "administrativa", "aluguel", "telefone", "internet", "agua", "energia", "luz"]
DESP_PESSOAL_KW = ["salario", "salário", "folha", "pessoal", "funcionario", "remuneracao", "prolabore", "ferias"]
DESP_GERAL_KW = ["despesa", "despesas", "gasto", "gastos", "variavel", "variável"]


def process_excel(file_path: str) -> Dict[str, Any]:
    """
    Processa um arquivo Excel e retorna os dados financeiros classificados.

    Args:
        file_path: Caminho completo do arquivo .xlsx ou .xls

    Returns:
        Dicionário com faturamento, impostos, custos e despesas
    """
    try:
        xl = pd.ExcelFile(file_path)
        sheet = xl.sheet_names[0]

        # Lê sem cabeçalho para inspecionar
        df_raw = pd.read_excel(file_path, sheet_name=sheet, header=None)
        header_row = _detectar_cabecalho(df_raw)

        # Lê com o cabeçalho correto
        df = pd.read_excel(file_path, sheet_name=sheet, header=header_row)
        df.columns = [str(c).strip().lower() for c in df.columns]

        return _extrair_totais(df)

    except Exception as e:
        raise ValueError(f"Não foi possível ler o arquivo Excel: {str(e)}")


def _detectar_cabecalho(df: pd.DataFrame) -> int:
    """Encontra a linha que contém os títulos das colunas."""
    termos = ["conta", "descri", "historico", "saldo", "debito", "credito", "valor", "código"]
    for i, row in df.iterrows():
        linha = " ".join([str(v).lower() for v in row.values if pd.notna(v)])
        if any(t in linha for t in termos):
            return i
    return 0  # fallback: primeira linha


def _extrair_totais(df: pd.DataFrame) -> Dict[str, Any]:
    """Classifica cada linha e acumula os totais por categoria."""

    # Identifica coluna de descrição e coluna de valor
    col_desc = _achar_coluna(df.columns, ["descri", "conta", "historico", "nome", "título"])
    col_val = _achar_coluna(df.columns, ["saldo", "valor", "total", "resultado", "credito", "crédito"])

    # Fallback: primeira coluna texto e primeira coluna numérica
    if col_desc is None:
        for c in df.columns:
            if df[c].dtype == object:
                col_desc = c
                break
    if col_val is None:
        for c in df.columns:
            if pd.api.types.is_numeric_dtype(df[c]):
                col_val = c
                break

    totais = {
        "faturamento": 0.0,
        "impostos": 0.0,
        "custos_operacionais": 0.0,
        "despesas_administrativas": 0.0,
        "outras_despesas": 0.0,
    }

    if col_desc is None or col_val is None:
        return _dados_demo()

    for _, row in df.iterrows():
        desc = str(row.get(col_desc, "")).lower().strip()
        if not desc or desc in ("nan", "none", ""):
            continue

        valor = _para_float(row.get(col_val))
        if valor == 0:
            continue

        valor = abs(valor)  # Balancetes podem ter valores negativos por convenção

        if any(kw in desc for kw in RECEITA_KW):
            totais["faturamento"] += valor
        elif any(kw in desc for kw in IMPOSTO_KW):
            totais["impostos"] += valor
        elif any(kw in desc for kw in CUSTO_KW):
            totais["custos_operacionais"] += valor
        elif any(kw in desc for kw in DESP_ADM_KW) or any(kw in desc for kw in DESP_PESSOAL_KW):
            totais["despesas_administrativas"] += valor
        elif any(kw in desc for kw in DESP_GERAL_KW):
            totais["outras_despesas"] += valor

    # Sem faturamento = não conseguiu extrair; usa demo
    if totais["faturamento"] == 0:
        return _dados_demo()

    return _calcular_lucros(totais)


def _achar_coluna(colunas, termos):
    """Retorna o nome da primeira coluna que contém algum dos termos."""
    for col in colunas:
        for t in termos:
            if t in str(col).lower():
                return col
    return None


def _para_float(valor) -> float:
    """Converte um valor (string ou número) para float."""
    if pd.isna(valor):
        return 0.0
    try:
        return float(str(valor).replace("R$", "").replace(".", "").replace(",", ".").strip())
    except (ValueError, TypeError):
        return 0.0


def _calcular_lucros(totais: dict) -> dict:
    """Calcula lucro bruto e líquido a partir dos totais."""
    fat = totais["faturamento"]
    totais["lucro_bruto"] = fat - totais["custos_operacionais"]
    total_deducoes = (
        totais["impostos"]
        + totais["custos_operacionais"]
        + totais["despesas_administrativas"]
        + totais["outras_despesas"]
    )
    totais["lucro_liquido"] = fat - total_deducoes
    return totais


def _dados_demo() -> dict:
    """
    Retorna dados de exemplo para quando a extração automática não funciona.
    Útil para testar o sistema ou quando o formato do arquivo é desconhecido.
    """
    return _calcular_lucros(
        {
            "faturamento": 150_000.0,
            "impostos": 18_000.0,
            "custos_operacionais": 45_000.0,
            "despesas_administrativas": 25_000.0,
            "outras_despesas": 12_000.0,
        }
    )
