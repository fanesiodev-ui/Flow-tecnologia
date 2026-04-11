"""
Schemas de dados do sistema.
Define os modelos usados para validar e transportar dados entre as camadas.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class WhiteLabelConfig(BaseModel):
    """Configurações de marca do contador (white label)"""
    company_name: str = Field(default="Contabilidade Profissional", description="Nome do escritório contábil")
    accountant_name: str = Field(default="Seu Contador", description="Nome do contador responsável")
    primary_color: str = Field(default="#1E40AF", description="Cor principal em hexadecimal (ex: #1E40AF)")
    secondary_color: str = Field(default="#7C3AED", description="Cor secundária em hexadecimal")
    logo_base64: Optional[str] = Field(default=None, description="Logo em base64 (opcional)")


class FinancialData(BaseModel):
    """Dados financeiros extraídos do balancete"""
    empresa_nome: str = Field(description="Nome da empresa do cliente")
    periodo: str = Field(description="Período de referência (ex: Março/2024)")
    faturamento: float = Field(default=0.0, description="Receita total bruta")
    impostos: float = Field(default=0.0, description="Total de impostos e tributos")
    custos_operacionais: float = Field(default=0.0, description="Custos de operação (CMV, materiais)")
    despesas_administrativas: float = Field(default=0.0, description="Despesas administrativas")
    outras_despesas: float = Field(default=0.0, description="Outras despesas")
    lucro_bruto: float = Field(default=0.0, description="Lucro bruto (receita - custos diretos)")
    lucro_liquido: float = Field(default=0.0, description="Lucro líquido após todas as deduções")
    # Dados de balanço patrimonial (para indicadores financeiros)
    ativo_circulante: float = Field(default=0.0, description="Ativo circulante (caixa, recebíveis, estoques)")
    passivo_circulante: float = Field(default=0.0, description="Passivo circulante (dívidas de curto prazo)")
    ativo_total: float = Field(default=0.0, description="Ativo total da empresa")
    passivo_total: float = Field(default=0.0, description="Passivo total da empresa")


class Insight(BaseModel):
    """Insight gerado pela análise dos dados"""
    tipo: str = Field(description="Tipo: 'positivo', 'atencao' ou 'critico'")
    icone: str = Field(description="Emoji representando o insight")
    titulo: str = Field(description="Título curto do insight")
    descricao: str = Field(description="Descrição em linguagem simples para o empresário")


class Recommendation(BaseModel):
    """Recomendação estratégica baseada nos dados"""
    titulo: str = Field(description="Título da recomendação")
    descricao: str = Field(description="Descrição detalhada da ação recomendada")
    prioridade: str = Field(description="Prioridade: 'alta', 'media' ou 'baixa'")


class GenerateReportResponse(BaseModel):
    """Resposta da API após geração do relatório"""
    success: bool
    report_id: str
    download_url: str
    message: str
    summary: Optional[dict] = None
