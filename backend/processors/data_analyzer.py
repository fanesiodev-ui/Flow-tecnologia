"""
Módulo de análise inteligente dos dados financeiros.

Gera automaticamente:
  - Insights (observações sobre saúde financeira)
  - Recomendações estratégicas

Tudo em linguagem simples, evitando termos técnicos contábeis.
O empresário deve entender sem precisar de conhecimento contábil.
"""

from typing import List, Tuple, Dict
from models.schemas import Insight, Recommendation


def analisar(dados: Dict) -> Tuple[List[Insight], List[Recommendation]]:
    """
    Analisa os dados financeiros e gera insights e recomendações.

    Args:
        dados: Dicionário com faturamento, impostos, lucros, etc.

    Returns:
        Tupla com (lista de insights, lista de recomendações)
    """
    insights: List[Insight] = []
    recomendacoes: List[Recommendation] = []

    fat = dados.get("faturamento", 0)
    if fat == 0:
        return insights, recomendacoes

    imp = dados.get("impostos", 0)
    custos = dados.get("custos_operacionais", 0)
    desp_adm = dados.get("despesas_administrativas", 0)
    outras = dados.get("outras_despesas", 0)
    lucro = dados.get("lucro_liquido", 0)

    # Percentuais em relação ao faturamento
    margem = (lucro / fat) * 100
    p_imp = (imp / fat) * 100
    p_custos = (custos / fat) * 100
    p_desp = ((desp_adm + outras) / fat) * 100
    total_gastos = imp + custos + desp_adm + outras
    p_total_gastos = (total_gastos / fat) * 100

    # ─── INSIGHTS ────────────────────────────────────────────────────────────

    # 1. Margem de lucro
    if margem >= 20:
        insights.append(Insight(
            tipo="positivo",
            icone="📈",
            titulo="Ótima margem de lucro!",
            descricao=(
                f"Sua empresa teve uma margem de lucro de {margem:.1f}% neste período. "
                f"Isso é excelente — significa que para cada R$ 100 vendidos, "
                f"sobram R$ {margem:.0f} de lucro para o negócio. Continue assim!"
            ),
        ))
    elif 10 <= margem < 20:
        insights.append(Insight(
            tipo="atencao",
            icone="⚠️",
            titulo="Margem de lucro moderada",
            descricao=(
                f"Sua empresa teve uma margem de lucro de {margem:.1f}%. "
                f"É um resultado razoável, mas há espaço para melhorar. "
                f"Revisar custos e aumentar o ticket médio pode aumentar essa margem."
            ),
        ))
    elif 0 <= margem < 10:
        insights.append(Insight(
            tipo="critico",
            icone="🚨",
            titulo="Margem de lucro baixa — atenção!",
            descricao=(
                f"Sua margem de lucro está em apenas {margem:.1f}%. "
                f"Isso significa que quase toda a receita está sendo consumida por gastos. "
                f"É importante agir agora: revise seus preços e corte custos desnecessários."
            ),
        ))
    else:
        insights.append(Insight(
            tipo="critico",
            icone="🚨",
            titulo="Prejuízo no período",
            descricao=(
                f"Neste período, os gastos superaram o faturamento em {abs(margem):.1f}%. "
                f"Sua empresa está tendo prejuízo. É urgente revisar todos os custos "
                f"e avaliar o modelo de precificação com seu contador."
            ),
        ))

    # 2. Carga tributária
    if p_imp > 25:
        insights.append(Insight(
            tipo="critico",
            icone="💸",
            titulo="Carga de impostos muito alta",
            descricao=(
                f"Os impostos representam {p_imp:.1f}% do seu faturamento "
                f"(R$ {imp:,.2f}). Esse percentual está acima da média. "
                f"Pode ser o momento certo para revisar o regime tributário com seu contador."
            ),
        ))
    elif 15 < p_imp <= 25:
        insights.append(Insight(
            tipo="atencao",
            icone="💰",
            titulo="Carga tributária elevada",
            descricao=(
                f"Seus impostos somaram {p_imp:.1f}% do faturamento neste mês. "
                f"Vale conversar com seu contador sobre planejamento tributário "
                f"para verificar se existe um regime mais vantajoso para o seu negócio."
            ),
        ))
    else:
        insights.append(Insight(
            tipo="positivo",
            icone="✅",
            titulo="Carga tributária sob controle",
            descricao=(
                f"Seus impostos representaram {p_imp:.1f}% do faturamento — "
                f"dentro de um nível saudável para o seu porte. Bom trabalho!"
            ),
        ))

    # 3. Custos operacionais
    if p_custos > 60:
        insights.append(Insight(
            tipo="critico",
            icone="🏭",
            titulo="Custo operacional muito alto",
            descricao=(
                f"Seus custos de operação (materiais, produção etc.) representam "
                f"{p_custos:.1f}% do faturamento. Esse número está alto e compromete "
                f"diretamente o seu lucro. Mapeie seus processos e busque eficiência."
            ),
        ))
    elif 40 < p_custos <= 60:
        insights.append(Insight(
            tipo="atencao",
            icone="📊",
            titulo="Custos operacionais acima do ideal",
            descricao=(
                f"Seus custos operacionais estão em {p_custos:.1f}% do faturamento. "
                f"Há espaço para redução — negociar com fornecedores e otimizar "
                f"processos pode ajudar a melhorar essa proporção."
            ),
        ))
    elif custos > 0:
        insights.append(Insight(
            tipo="positivo",
            icone="🎯",
            titulo="Eficiência operacional boa",
            descricao=(
                f"Seus custos operacionais estão em {p_custos:.1f}% do faturamento — "
                f"um bom nível de eficiência. Isso indica que seu negócio está "
                f"bem estruturado operacionalmente."
            ),
        ))

    # 4. Despesas gerais
    if p_desp > 30:
        insights.append(Insight(
            tipo="atencao",
            icone="🏢",
            titulo="Despesas administrativas elevadas",
            descricao=(
                f"Suas despesas de gestão e estrutura somam {p_desp:.1f}% do faturamento. "
                f"Analise quais são as maiores despesas e veja se há oportunidades "
                f"de redução sem comprometer a operação."
            ),
        ))

    # ─── RECOMENDAÇÕES ───────────────────────────────────────────────────────

    # Recomendação 1: planejamento tributário (se impostos altos)
    if p_imp > 15:
        recomendacoes.append(Recommendation(
            titulo="Revise o regime tributário",
            descricao=(
                "Com sua carga tributária atual, pode ser vantajoso verificar se o "
                "Simples Nacional, Lucro Presumido ou Lucro Real seria mais adequado. "
                "Converse com seu contador para simular qual regime gera menos impostos."
            ),
            prioridade="alta" if p_imp > 22 else "media",
        ))

    # Recomendação 2: precificação (se margem baixa)
    if margem < 15:
        recomendacoes.append(Recommendation(
            titulo="Revise a precificação dos produtos/serviços",
            descricao=(
                "Uma margem de lucro baixa pode indicar que seus preços não cobrem "
                "adequadamente os custos. Calcule o preço mínimo de cada produto/serviço "
                "com seu contador e ajuste onde necessário."
            ),
            prioridade="alta" if margem < 5 else "media",
        ))

    # Recomendação 3: redução de custos (se custos altos)
    if p_custos > 50:
        recomendacoes.append(Recommendation(
            titulo="Reduza custos operacionais",
            descricao=(
                "Seus custos de operação estão consumindo grande parte da receita. "
                "Mapeie seus principais fornecedores, negocie prazos e preços, "
                "e identifique processos que podem ser otimizados para gastar menos."
            ),
            prioridade="alta",
        ))

    # Recomendação 4: controle de despesas
    if p_total_gastos > 85:
        recomendacoes.append(Recommendation(
            titulo="Implemente controle de gastos mensal",
            descricao=(
                "Com mais de 85% do faturamento sendo consumido por gastos, "
                "é essencial criar um orçamento mensal. Defina limites para cada "
                "categoria de despesa e acompanhe semanalmente."
            ),
            prioridade="alta",
        ))

    # Recomendação 5: reserva financeira (sempre)
    recomendacoes.append(Recommendation(
        titulo="Construa uma reserva de emergência",
        descricao=(
            "Empresas saudáveis mantêm uma reserva equivalente a 3 a 6 meses "
            "de custos fixos. Isso protege o negócio em períodos de baixo faturamento "
            "e evita o endividamento em situações imprevistas."
        ),
        prioridade="media",
    ))

    # Recomendação 6: DRE mensal (sempre)
    recomendacoes.append(Recommendation(
        titulo="Acompanhe o DRE todo mês",
        descricao=(
            "Este relatório é o ponto de partida. Acompanhar o resultado financeiro "
            "mensalmente permite tomar decisões rápidas e corretas, antes que "
            "os problemas se tornem grandes demais."
        ),
        prioridade="baixa",
    ))

    return insights, recomendacoes
