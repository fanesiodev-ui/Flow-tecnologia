"""
Gerador de relatórios PDF profissionais.

Usa a biblioteca ReportLab para criar PDFs com layout premium:
  - Capa com identidade visual do contador (white label)
  - Cards de indicadores financeiros
  - Tabela de composição de despesas
  - Seção de análise com linguagem simples
  - Recomendações estratégicas numeradas

Suporta personalização de cores e nome do escritório contábil.
"""

import io
from datetime import datetime
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)

from models.schemas import FinancialData, Insight, Recommendation, WhiteLabelConfig

# ─── Constantes de layout ─────────────────────────────────────────────────────
PAGE_W, PAGE_H = A4
MARGIN = 1.5 * cm
CONTENT_W = PAGE_W - 2 * MARGIN


# ─── Helpers de formatação ────────────────────────────────────────────────────

def _brl(v: float) -> str:
    """Formata como moeda brasileira: R$ 1.234,56"""
    sinal = "- " if v < 0 else ""
    return f"{sinal}R$ {abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(parte: float, total: float) -> str:
    """Formata como percentual com 1 decimal."""
    if total == 0:
        return "0,0%"
    return f"{(parte / total * 100):.1f}%".replace(".", ",")


def _hex_to_color(h: str) -> colors.Color:
    """Converte hex (#RRGGBB) para objeto Color do ReportLab."""
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return colors.Color(r / 255, g / 255, b / 255)


# ─── Classe principal ─────────────────────────────────────────────────────────

class ReportGenerator:
    """
    Gera relatórios PDF a partir dos dados financeiros e configurações white label.

    Uso:
        gen = ReportGenerator(white_label_config)
        gen.generate(financial_data, insights, recommendations, "/caminho/relatorio.pdf")
    """

    def __init__(self, config: WhiteLabelConfig):
        self.config = config
        self.cor_primaria = _hex_to_color(config.primary_color)
        self.cor_secundaria = _hex_to_color(config.secondary_color)
        self._criar_estilos()

    # ── Estilos de texto ──────────────────────────────────────────────────────

    def _criar_estilos(self):
        """Cria todos os estilos de parágrafo usados no relatório."""
        P = self.cor_primaria

        self.s_capa_empresa = ParagraphStyle(
            "CapaEmpresa",
            fontName="Helvetica-Bold", fontSize=22,
            textColor=colors.white, alignment=TA_CENTER, spaceAfter=6,
        )
        self.s_capa_periodo = ParagraphStyle(
            "CapaPeriodo",
            fontName="Helvetica", fontSize=13,
            textColor=colors.Color(0.83, 0.88, 1.0), alignment=TA_CENTER, spaceAfter=4,
        )
        self.s_capa_sub = ParagraphStyle(
            "CapaSub",
            fontName="Helvetica-Oblique", fontSize=10,
            textColor=colors.Color(0.72, 0.78, 0.95), alignment=TA_CENTER,
        )
        self.s_secao = ParagraphStyle(
            "Secao",
            fontName="Helvetica-Bold", fontSize=13,
            textColor=P, spaceBefore=16, spaceAfter=8,
        )
        self.s_corpo = ParagraphStyle(
            "Corpo",
            fontName="Helvetica", fontSize=10,
            textColor=colors.Color(0.22, 0.22, 0.25),
            leading=17, spaceAfter=6,
        )
        self.s_card_label = ParagraphStyle(
            "CardLabel",
            fontName="Helvetica", fontSize=8,
            textColor=colors.Color(0.45, 0.45, 0.52), alignment=TA_CENTER,
        )
        self.s_card_valor_azul = ParagraphStyle(
            "CardValorAzul",
            fontName="Helvetica-Bold", fontSize=17,
            textColor=P, alignment=TA_CENTER,
        )
        self.s_card_valor_vermelho = ParagraphStyle(
            "CardValorVerm",
            fontName="Helvetica-Bold", fontSize=17,
            textColor=colors.Color(0.75, 0.12, 0.12), alignment=TA_CENTER,
        )
        self.s_card_valor_verde = ParagraphStyle(
            "CardValorVerde",
            fontName="Helvetica-Bold", fontSize=17,
            textColor=colors.Color(0.08, 0.52, 0.22), alignment=TA_CENTER,
        )
        self.s_card_sub = ParagraphStyle(
            "CardSub",
            fontName="Helvetica", fontSize=8,
            textColor=colors.Color(0.5, 0.5, 0.56), alignment=TA_CENTER,
        )
        self.s_tabela_header = ParagraphStyle(
            "TabHeader",
            fontName="Helvetica-Bold", fontSize=9,
            textColor=colors.white, alignment=TA_CENTER,
        )
        self.s_tabela_cel = ParagraphStyle(
            "TabCel",
            fontName="Helvetica", fontSize=9,
            textColor=colors.Color(0.2, 0.2, 0.25),
        )
        self.s_tabela_cel_dir = ParagraphStyle(
            "TabCelDir",
            fontName="Helvetica", fontSize=9,
            textColor=colors.Color(0.2, 0.2, 0.25), alignment=TA_RIGHT,
        )
        self.s_tabela_total = ParagraphStyle(
            "TabTotal",
            fontName="Helvetica-Bold", fontSize=9,
            textColor=colors.Color(0.1, 0.1, 0.18),
        )
        self.s_tabela_total_dir = ParagraphStyle(
            "TabTotalDir",
            fontName="Helvetica-Bold", fontSize=9,
            textColor=colors.Color(0.1, 0.1, 0.18), alignment=TA_RIGHT,
        )
        self.s_insight_titulo_pos = ParagraphStyle(
            "InsTitPos",
            fontName="Helvetica-Bold", fontSize=10,
            textColor=colors.Color(0.05, 0.48, 0.18), spaceAfter=3,
        )
        self.s_insight_titulo_warn = ParagraphStyle(
            "InsTitWarn",
            fontName="Helvetica-Bold", fontSize=10,
            textColor=colors.Color(0.62, 0.38, 0.0), spaceAfter=3,
        )
        self.s_insight_titulo_crit = ParagraphStyle(
            "InsTitCrit",
            fontName="Helvetica-Bold", fontSize=10,
            textColor=colors.Color(0.68, 0.1, 0.1), spaceAfter=3,
        )
        self.s_insight_desc = ParagraphStyle(
            "InsDesc",
            fontName="Helvetica", fontSize=9,
            textColor=colors.Color(0.24, 0.24, 0.3), leading=14,
        )
        self.s_rec_titulo = ParagraphStyle(
            "RecTit",
            fontName="Helvetica-Bold", fontSize=10,
            textColor=P, spaceAfter=3,
        )
        self.s_rec_desc = ParagraphStyle(
            "RecDesc",
            fontName="Helvetica", fontSize=9,
            textColor=colors.Color(0.24, 0.24, 0.3), leading=14,
        )
        self.s_rodape = ParagraphStyle(
            "Rodape",
            fontName="Helvetica", fontSize=8,
            textColor=colors.Color(0.5, 0.5, 0.55), alignment=TA_CENTER,
            leading=12,
        )

    # ── Ponto de entrada principal ────────────────────────────────────────────

    def generate(
        self,
        data: FinancialData,
        insights: List[Insight],
        recommendations: List[Recommendation],
        output_path: str,
    ) -> str:
        """
        Gera o PDF completo e salva em output_path.

        Returns:
            Caminho do arquivo PDF gerado.
        """
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=MARGIN,
            bottomMargin=MARGIN,
        )

        historia = []
        historia.extend(self._capa(data))
        historia.extend(self._resumo(data))
        historia.extend(self._cards_indicadores(data))
        historia.extend(self._tabela_despesas(data))
        if insights:
            historia.extend(self._secao_insights(insights))
        if recommendations:
            historia.extend(self._secao_recomendacoes(recommendations))
        historia.extend(self._rodape())

        doc.build(historia)

        with open(output_path, "wb") as f:
            f.write(buf.getvalue())

        return output_path

    # ── Seções do relatório ───────────────────────────────────────────────────

    def _capa(self, data: FinancialData) -> list:
        """Capa com banner colorido e identidade do contador."""
        el = []
        el.append(Spacer(1, 0.3 * cm))

        # Banner principal (tabela com fundo na cor primária)
        linhas = [
            [Paragraph(
                "RELATÓRIO FINANCEIRO GERENCIAL",
                ParagraphStyle("BannerTag", fontName="Helvetica-Bold", fontSize=8,
                               textColor=colors.Color(0.78, 0.84, 1.0), alignment=TA_CENTER,
                               spaceAfter=16),
            )],
            [Paragraph(data.empresa_nome.upper(), self.s_capa_empresa)],
            [Paragraph(f"Período: {data.periodo}", self.s_capa_periodo)],
            [Spacer(1, 0.25 * cm)],
            [Paragraph("Relatório Gerencial Simplificado", self.s_capa_sub)],
            [Spacer(1, 0.1 * cm)],
        ]

        banner = Table(linhas, colWidths=[CONTENT_W])
        banner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), self.cor_primaria),
            ("TOPPADDING", (0, 0), (-1, 0), 20),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 20),
            ("LEFTPADDING", (0, 0), (-1, -1), 24),
            ("RIGHTPADDING", (0, 0), (-1, -1), 24),
            ("TOPPADDING", (0, 1), (-1, -2), 4),
            ("BOTTOMPADDING", (0, 1), (-1, -2), 4),
        ]))
        el.append(banner)
        el.append(Spacer(1, 0.35 * cm))

        # Linha de meta-informações
        hoje = datetime.now().strftime("%d/%m/%Y")
        meta = (
            f"Elaborado por: <b>{self.config.accountant_name}</b>"
            f"&nbsp;&nbsp;·&nbsp;&nbsp;{self.config.company_name}"
            f"&nbsp;&nbsp;·&nbsp;&nbsp;Gerado em {hoje}"
        )
        el.append(Paragraph(meta, ParagraphStyle(
            "Meta", fontName="Helvetica", fontSize=8.5,
            textColor=colors.Color(0.5, 0.5, 0.56), alignment=TA_CENTER,
        )))
        el.append(HRFlowable(
            width="100%", thickness=1,
            color=colors.Color(0.87, 0.87, 0.92),
            spaceBefore=10, spaceAfter=12,
        ))
        return el

    def _resumo(self, data: FinancialData) -> list:
        """Parágrafo introdutório do relatório."""
        el = []
        el.append(Paragraph("📊 Resumo Financeiro do Período", self.s_secao))
        texto = (
            f"Este relatório apresenta o desempenho financeiro da empresa "
            f"<b>{data.empresa_nome}</b> referente ao período de <b>{data.periodo}</b>. "
            f"As informações foram organizadas de forma clara e objetiva para facilitar "
            f"a compreensão dos resultados e apoiar as tomadas de decisão do negócio."
        )
        el.append(Paragraph(texto, self.s_corpo))
        return el

    def _cards_indicadores(self, data: FinancialData) -> list:
        """Três cards lado a lado com os principais indicadores."""
        el = []
        el.append(Paragraph("💡 Indicadores Principais", self.s_secao))

        fat = data.faturamento
        imp = data.impostos
        luc = data.lucro_liquido
        margem = (luc / fat * 100) if fat > 0 else 0
        p_imp = (imp / fat * 100) if fat > 0 else 0

        cw = CONTENT_W / 3

        # Cada card ocupa 1/3 da largura, 3 linhas: label, valor, subtítulo
        dados_cards = [
            # Linha 1 — Labels
            [
                Paragraph("FATURAMENTO TOTAL", self.s_card_label),
                Paragraph("IMPOSTOS PAGOS", self.s_card_label),
                Paragraph("LUCRO LÍQUIDO", self.s_card_label),
            ],
            # Linha 2 — Valores
            [
                Paragraph(_brl(fat), self.s_card_valor_azul),
                Paragraph(_brl(imp), self.s_card_valor_vermelho),
                Paragraph(_brl(luc), self.s_card_valor_verde),
            ],
            # Linha 3 — Subtítulos
            [
                Paragraph("Tudo que sua empresa vendeu", self.s_card_sub),
                Paragraph(f"{p_imp:.1f}% do faturamento", self.s_card_sub),
                Paragraph(f"Margem de {margem:.1f}%", self.s_card_sub),
            ],
        ]

        tabela_cards = Table(dados_cards, colWidths=[cw, cw, cw])
        tabela_cards.setStyle(TableStyle([
            # Fundos de cada card
            ("BACKGROUND", (0, 0), (0, -1), colors.Color(0.94, 0.96, 1.0)),
            ("BACKGROUND", (1, 0), (1, -1), colors.Color(1.0, 0.94, 0.94)),
            ("BACKGROUND", (2, 0), (2, -1), colors.Color(0.91, 0.99, 0.94)),
            # Linha colorida no topo de cada card
            ("LINEABOVE", (0, 0), (0, 0), 4, self.cor_primaria),
            ("LINEABOVE", (1, 0), (1, 0), 4, colors.Color(0.75, 0.12, 0.12)),
            ("LINEABOVE", (2, 0), (2, 0), 4, colors.Color(0.08, 0.52, 0.22)),
            # Separador branco entre cards
            ("LINEAFTER", (0, 0), (0, -1), 5, colors.white),
            ("LINEAFTER", (1, 0), (1, -1), 5, colors.white),
            # Espaçamentos
            ("TOPPADDING", (0, 0), (-1, 0), 14),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("TOPPADDING", (0, 1), (-1, 1), 4),
            ("BOTTOMPADDING", (0, 1), (-1, 1), 4),
            ("TOPPADDING", (0, 2), (-1, 2), 2),
            ("BOTTOMPADDING", (0, 2), (-1, 2), 14),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))

        el.append(tabela_cards)
        el.append(Spacer(1, 0.4 * cm))
        return el

    def _tabela_despesas(self, data: FinancialData) -> list:
        """Tabela detalhada da composição de despesas."""
        el = []
        el.append(Paragraph("📋 Composição das Despesas", self.s_secao))

        fat = data.faturamento

        # Cabeçalho
        linhas = [[
            Paragraph("Categoria", self.s_tabela_header),
            Paragraph("Valor", self.s_tabela_header),
            Paragraph("% Faturamento", self.s_tabela_header),
            Paragraph("O que é?", self.s_tabela_header),
        ]]

        itens = [
            ("💰  Impostos e Tributos", data.impostos, "Encargos obrigatórios por lei"),
            ("🏭  Custos de Operação", data.custos_operacionais, "Materiais, insumos e produção"),
            ("🏢  Despesas Administrativas", data.despesas_administrativas, "Estrutura e gestão do negócio"),
            ("📦  Outras Despesas", data.outras_despesas, "Demais gastos variados"),
        ]

        for nome, valor, obs in itens:
            if valor > 0:
                linhas.append([
                    Paragraph(nome, self.s_tabela_cel),
                    Paragraph(_brl(valor), self.s_tabela_cel_dir),
                    Paragraph(_pct(valor, fat), self.s_tabela_cel_dir),
                    Paragraph(obs, self.s_tabela_cel),
                ])

        total_desp = (
            data.impostos + data.custos_operacionais
            + data.despesas_administrativas + data.outras_despesas
        )
        linhas.append([
            Paragraph("TOTAL DE DESPESAS", self.s_tabela_total),
            Paragraph(_brl(total_desp), self.s_tabela_total_dir),
            Paragraph(_pct(total_desp, fat), self.s_tabela_total_dir),
            Paragraph("", self.s_tabela_cel),
        ])

        # Separador visual lucro líquido
        linhas.append([
            Paragraph("LUCRO LÍQUIDO", ParagraphStyle(
                "LiqTit", fontName="Helvetica-Bold", fontSize=9,
                textColor=colors.Color(0.08, 0.52, 0.22),
            )),
            Paragraph(_brl(data.lucro_liquido), ParagraphStyle(
                "LiqVal", fontName="Helvetica-Bold", fontSize=9,
                textColor=colors.Color(0.08, 0.52, 0.22), alignment=TA_RIGHT,
            )),
            Paragraph(_pct(data.lucro_liquido, fat), ParagraphStyle(
                "LiqPct", fontName="Helvetica-Bold", fontSize=9,
                textColor=colors.Color(0.08, 0.52, 0.22), alignment=TA_RIGHT,
            )),
            Paragraph("O que sobrou para a empresa", self.s_tabela_cel),
        ])

        cw = [CONTENT_W * 0.35, CONTENT_W * 0.22, CONTENT_W * 0.17, CONTENT_W * 0.26]
        tabela = Table(linhas, colWidths=cw)

        estilo = [
            # Cabeçalho
            ("BACKGROUND", (0, 0), (-1, 0), self.cor_primaria),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            # Linhas do corpo (alternadas)
            ("TOPPADDING", (0, 1), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            # Linha de total
            ("BACKGROUND", (0, -2), (-1, -2), colors.Color(0.92, 0.93, 0.98)),
            ("LINEABOVE", (0, -2), (-1, -2), 0.8, self.cor_primaria),
            # Linha de lucro líquido
            ("BACKGROUND", (0, -1), (-1, -1), colors.Color(0.90, 0.99, 0.93)),
            ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.Color(0.08, 0.52, 0.22)),
            ("LINEBELOW", (0, -1), (-1, -1), 0.8, colors.Color(0.08, 0.52, 0.22)),
            # Grid geral
            ("GRID", (0, 0), (-1, -1), 0.3, colors.Color(0.87, 0.87, 0.93)),
        ]

        # Linhas alternadas no corpo
        for i in range(1, len(linhas) - 2):
            if i % 2 == 0:
                estilo.append(("BACKGROUND", (0, i), (-1, i), colors.Color(0.97, 0.97, 1.0)))

        tabela.setStyle(TableStyle(estilo))
        el.append(tabela)
        el.append(Spacer(1, 0.4 * cm))
        return el

    def _secao_insights(self, insights: List[Insight]) -> list:
        """Cards coloridos com análise dos dados em linguagem simples."""
        el = []
        el.append(Paragraph("🔍 O Que os Números Estão Dizendo", self.s_secao))
        el.append(Paragraph(
            "Nossa análise dos dados deste período identificou os seguintes pontos importantes:",
            self.s_corpo,
        ))

        mapa_tipo = {
            "positivo": (
                colors.Color(0.91, 1.0, 0.94),
                colors.Color(0.08, 0.60, 0.25),
                self.s_insight_titulo_pos,
            ),
            "atencao": (
                colors.Color(1.0, 0.97, 0.87),
                colors.Color(0.80, 0.52, 0.0),
                self.s_insight_titulo_warn,
            ),
            "critico": (
                colors.Color(1.0, 0.92, 0.92),
                colors.Color(0.78, 0.12, 0.12),
                self.s_insight_titulo_crit,
            ),
        }

        for ins in insights:
            bg, borda, s_titulo = mapa_tipo.get(ins.tipo, mapa_tipo["atencao"])

            card = Table(
                [
                    [Paragraph(f"{ins.icone}  <b>{ins.titulo}</b>", s_titulo)],
                    [Paragraph(ins.descricao, self.s_insight_desc)],
                ],
                colWidths=[CONTENT_W - 1.4 * cm],
            )
            card.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, 0), 10),
                ("TOPPADDING", (0, 1), (-1, 1), 3),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
                ("LINEBEFORE", (0, 0), (0, -1), 5, borda),
            ]))
            el.append(KeepTogether(card))
            el.append(Spacer(1, 0.28 * cm))

        return el

    def _secao_recomendacoes(self, recs: List[Recommendation]) -> list:
        """Cards numerados com recomendações estratégicas."""
        el = []
        el.append(Paragraph("🎯 Recomendações para o Seu Negócio", self.s_secao))
        el.append(Paragraph(
            "Com base na análise acima, estas são as ações recomendadas para melhorar os resultados:",
            self.s_corpo,
        ))

        mapa_prioridade = {
            "alta":  ("🔴 Alta Prioridade",  colors.Color(0.70, 0.05, 0.05)),
            "media": ("🟡 Média Prioridade", colors.Color(0.62, 0.42, 0.0)),
            "baixa": ("🟢 Baixa Prioridade", colors.Color(0.08, 0.52, 0.2)),
        }

        for i, rec in enumerate(recs, 1):
            label_texto, label_cor = mapa_prioridade.get(rec.prioridade, mapa_prioridade["media"])

            card = Table(
                [
                    [
                        Paragraph(f"<b>{i}. {rec.titulo}</b>", self.s_rec_titulo),
                        Paragraph(label_texto, ParagraphStyle(
                            "PLabel", fontName="Helvetica-Bold", fontSize=8,
                            textColor=label_cor, alignment=TA_RIGHT,
                        )),
                    ],
                    [
                        Paragraph(rec.descricao, self.s_rec_desc),
                        "",
                    ],
                ],
                colWidths=[CONTENT_W * 0.66, CONTENT_W * 0.34],
            )
            card.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.Color(0.97, 0.97, 1.0)),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, 0), 10),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
                ("SPAN", (0, 1), (1, 1)),
                ("LINEBELOW", (0, 0), (-1, 0), 0.4, colors.Color(0.88, 0.88, 0.94)),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.Color(0.88, 0.88, 0.94)),
                ("LINEBEFORE", (0, 0), (0, -1), 4, self.cor_primaria),
            ]))
            el.append(KeepTogether(card))
            el.append(Spacer(1, 0.22 * cm))

        return el

    def _rodape(self) -> list:
        """Rodapé com disclaimer e informações do contador."""
        el = []
        el.append(Spacer(1, 0.5 * cm))
        el.append(HRFlowable(
            width="100%", thickness=1,
            color=colors.Color(0.87, 0.87, 0.93),
            spaceBefore=5, spaceAfter=10,
        ))
        el.append(Paragraph(
            f"Relatório elaborado por <b>{self.config.company_name}</b> &nbsp;·&nbsp; "
            f"As análises e recomendações são orientativas e não substituem uma consultoria "
            f"contábil especializada. Para mais informações, consulte seu contador.",
            self.s_rodape,
        ))
        return el
