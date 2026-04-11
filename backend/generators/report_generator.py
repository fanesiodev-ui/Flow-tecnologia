"""
Gerador de relatórios PDF profissionais — ContaFácil.
Layout corporativo com ReportLab.
"""

import io
from datetime import datetime
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable, KeepTogether,
)

from models.schemas import FinancialData, Insight, Recommendation, WhiteLabelConfig

# ── Layout ────────────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = A4
MARGIN_H = 1.8 * cm
MARGIN_V = 1.5 * cm
CONTENT_W = PAGE_W - 2 * MARGIN_H

# ── Paleta neutra fixa ────────────────────────────────────────────────────────
CINZA_TEXTO    = colors.Color(0.16, 0.17, 0.20)
CINZA_SUB      = colors.Color(0.42, 0.44, 0.50)
CINZA_BORDA    = colors.Color(0.85, 0.86, 0.90)
CINZA_FUNDO    = colors.Color(0.96, 0.97, 0.98)
CINZA_ALT      = colors.Color(0.99, 0.99, 1.00)
VERDE_OK       = colors.Color(0.05, 0.47, 0.18)
VERDE_BG       = colors.Color(0.90, 0.98, 0.92)
AMARELO_OK     = colors.Color(0.58, 0.36, 0.00)
AMARELO_BG     = colors.Color(0.99, 0.96, 0.84)
VERMELHO_OK    = colors.Color(0.65, 0.08, 0.08)
VERMELHO_BG    = colors.Color(0.99, 0.91, 0.91)
BRANCO         = colors.white


def _brl(v: float) -> str:
    sinal = "-" if v < 0 else ""
    return f"{sinal}R$ {abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(parte: float, total: float) -> str:
    if total == 0:
        return "—"
    return f"{(parte / total * 100):.1f}%".replace(".", ",")


def _hex_to_color(h: str) -> colors.Color:
    h = h.lstrip("#")
    return colors.Color(int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)


# ── Classe principal ──────────────────────────────────────────────────────────

class ReportGenerator:

    def __init__(self, config: WhiteLabelConfig):
        self.config = config
        self.COR   = _hex_to_color(config.primary_color)   # cor primária
        self.COR2  = _hex_to_color(config.secondary_color) # cor secundária
        self._estilos()

    # ── Estilos ───────────────────────────────────────────────────────────────

    def _estilos(self):
        C = self.COR

        # Capa
        self.s_tag = ParagraphStyle("Tag",
            fontName="Helvetica-Bold", fontSize=7.5, letterSpacing=2,
            textColor=colors.Color(0.75, 0.82, 1.0), alignment=TA_CENTER)
        self.s_empresa = ParagraphStyle("Empresa",
            fontName="Helvetica-Bold", fontSize=24,
            textColor=BRANCO, alignment=TA_CENTER, leading=28)
        self.s_periodo = ParagraphStyle("Periodo",
            fontName="Helvetica", fontSize=12,
            textColor=colors.Color(0.80, 0.87, 1.0), alignment=TA_CENTER)
        self.s_meta = ParagraphStyle("Meta",
            fontName="Helvetica", fontSize=8,
            textColor=CINZA_SUB, alignment=TA_CENTER, leading=13)

        # Seções
        self.s_titulo_sec = ParagraphStyle("TitSec",
            fontName="Helvetica-Bold", fontSize=9.5, letterSpacing=0.8,
            textColor=C, spaceBefore=0, spaceAfter=0)

        # Corpo
        self.s_corpo = ParagraphStyle("Corpo",
            fontName="Helvetica", fontSize=9.5,
            textColor=CINZA_TEXTO, leading=16, spaceAfter=4)

        # Cards de indicador
        self.s_card_label = ParagraphStyle("CLabel",
            fontName="Helvetica-Bold", fontSize=7, letterSpacing=0.5,
            textColor=CINZA_SUB, alignment=TA_CENTER)
        self.s_card_val = ParagraphStyle("CVal",
            fontName="Helvetica-Bold", fontSize=18,
            textColor=C, alignment=TA_CENTER, leading=22)
        self.s_card_val_r = ParagraphStyle("CValR",
            fontName="Helvetica-Bold", fontSize=18,
            textColor=VERMELHO_OK, alignment=TA_CENTER, leading=22)
        self.s_card_val_g = ParagraphStyle("CValG",
            fontName="Helvetica-Bold", fontSize=18,
            textColor=VERDE_OK, alignment=TA_CENTER, leading=22)
        self.s_card_sub = ParagraphStyle("CSub",
            fontName="Helvetica", fontSize=7.5,
            textColor=CINZA_SUB, alignment=TA_CENTER)

        # Tabelas
        self.s_th = ParagraphStyle("TH",
            fontName="Helvetica-Bold", fontSize=8, letterSpacing=0.3,
            textColor=BRANCO, alignment=TA_CENTER)
        self.s_th_l = ParagraphStyle("THL",
            fontName="Helvetica-Bold", fontSize=8, letterSpacing=0.3,
            textColor=BRANCO, alignment=TA_LEFT)
        self.s_tc = ParagraphStyle("TC",
            fontName="Helvetica", fontSize=9, textColor=CINZA_TEXTO)
        self.s_tc_r = ParagraphStyle("TCR",
            fontName="Helvetica", fontSize=9,
            textColor=CINZA_TEXTO, alignment=TA_RIGHT)
        self.s_tc_b = ParagraphStyle("TCB",
            fontName="Helvetica-Bold", fontSize=9, textColor=CINZA_TEXTO)
        self.s_tc_br = ParagraphStyle("TCBR",
            fontName="Helvetica-Bold", fontSize=9,
            textColor=CINZA_TEXTO, alignment=TA_RIGHT)
        self.s_tc_g = ParagraphStyle("TCG",
            fontName="Helvetica-Bold", fontSize=9, textColor=VERDE_OK)
        self.s_tc_gr = ParagraphStyle("TCGR",
            fontName="Helvetica-Bold", fontSize=9,
            textColor=VERDE_OK, alignment=TA_RIGHT)

        # Insights
        self.s_ins_tit_ok  = ParagraphStyle("ITok",  fontName="Helvetica-Bold", fontSize=9, textColor=VERDE_OK,    spaceAfter=2)
        self.s_ins_tit_wa  = ParagraphStyle("ITwa",  fontName="Helvetica-Bold", fontSize=9, textColor=AMARELO_OK,  spaceAfter=2)
        self.s_ins_tit_cr  = ParagraphStyle("ITcr",  fontName="Helvetica-Bold", fontSize=9, textColor=VERMELHO_OK, spaceAfter=2)
        self.s_ins_desc     = ParagraphStyle("IDesc", fontName="Helvetica", fontSize=8.5,
                                             textColor=CINZA_TEXTO, leading=13)

        # Recomendações
        self.s_rec_tit  = ParagraphStyle("RTit",  fontName="Helvetica-Bold", fontSize=9, textColor=C, spaceAfter=2)
        self.s_rec_desc = ParagraphStyle("RDesc", fontName="Helvetica", fontSize=8.5,
                                         textColor=CINZA_TEXTO, leading=13)
        self.s_prioridade = ParagraphStyle("Prio", fontName="Helvetica-Bold", fontSize=7.5,
                                           alignment=TA_RIGHT)

        # Indicadores financeiros
        self.s_ind_nome = ParagraphStyle("IndN", fontName="Helvetica-Bold", fontSize=9, textColor=CINZA_TEXTO)
        self.s_ind_form = ParagraphStyle("IndF", fontName="Helvetica-Oblique", fontSize=7.5, textColor=CINZA_SUB)
        self.s_ind_ref  = ParagraphStyle("IndR", fontName="Helvetica", fontSize=7.5, textColor=CINZA_SUB)

        # Rodapé
        self.s_rodape = ParagraphStyle("Rod", fontName="Helvetica", fontSize=7.5,
                                       textColor=CINZA_SUB, alignment=TA_CENTER, leading=11)

    # ── Helpers de layout ─────────────────────────────────────────────────────

    def _titulo_secao(self, texto: str) -> list:
        """Retorna cabeçalho de seção com barra colorida à esquerda."""
        inner = Table(
            [[Paragraph(texto.upper(), self.s_titulo_sec)]],
            colWidths=[CONTENT_W - 0.5 * cm],
        )
        inner.setStyle(TableStyle([
            ("LEFTPADDING",  (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING",   (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
            ("BACKGROUND",   (0, 0), (-1, -1), CINZA_FUNDO),
            ("LINEBEFORE",   (0, 0), (0, -1),  4, self.COR),
            ("LINEBELOW",    (0, -1),(-1, -1),  0.5, CINZA_BORDA),
        ]))
        return [Spacer(1, 0.35 * cm), inner, Spacer(1, 0.25 * cm)]

    # ── Ponto de entrada ──────────────────────────────────────────────────────

    def generate(self, data: FinancialData, insights: List[Insight],
                 recommendations: List[Recommendation], output_path: str) -> str:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=A4,
            leftMargin=MARGIN_H, rightMargin=MARGIN_H,
            topMargin=MARGIN_V, bottomMargin=MARGIN_V,
        )

        story = []
        story.extend(self._capa(data))
        story.extend(self._resumo(data))
        story.extend(self._cards_indicadores(data))
        story.extend(self._indicadores_financeiros(data))
        story.extend(self._tabela_despesas(data))
        if insights:
            story.extend(self._secao_insights(insights))
        if recommendations:
            story.extend(self._secao_recomendacoes(recommendations))
        story.extend(self._rodape())

        doc.build(story)
        with open(output_path, "wb") as f:
            f.write(buf.getvalue())
        return output_path

    # ── Seções ────────────────────────────────────────────────────────────────

    def _capa(self, data: FinancialData) -> list:
        el = []

        # Banner
        banner_rows = [
            [Paragraph("RELATORIO FINANCEIRO GERENCIAL", self.s_tag)],
            [Spacer(1, 0.15 * cm)],
            [Paragraph(data.empresa_nome.upper(), self.s_empresa)],
            [Spacer(1, 0.1 * cm)],
            [Paragraph(f"Periodo de Referencia:  {data.periodo}", self.s_periodo)],
            [Spacer(1, 0.3 * cm)],
        ]
        banner = Table(banner_rows, colWidths=[CONTENT_W])
        banner.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), self.COR),
            ("TOPPADDING",    (0, 0), (-1, 0),  22),
            ("BOTTOMPADDING", (0, -1),(-1, -1), 22),
            ("TOPPADDING",    (0, 1), (-1, -2),  3),
            ("BOTTOMPADDING", (0, 1), (-1, -2),  3),
            ("LEFTPADDING",   (0, 0), (-1, -1), 28),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 28),
        ]))
        el.append(banner)
        el.append(Spacer(1, 0.3 * cm))

        # Linha de metadados
        hoje = datetime.now().strftime("%d/%m/%Y")
        el.append(Paragraph(
            f"Elaborado por  <b>{self.config.accountant_name}</b>"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;{self.config.company_name}"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;Emitido em {hoje}",
            self.s_meta,
        ))
        el.append(HRFlowable(width="100%", thickness=0.8,
                              color=CINZA_BORDA, spaceBefore=8, spaceAfter=4))
        return el

    def _resumo(self, data: FinancialData) -> list:
        el = []
        el.extend(self._titulo_secao("Resumo do Periodo"))
        texto = (
            f"Este relatorio apresenta o desempenho financeiro de "
            f"<b>{data.empresa_nome}</b> referente ao periodo de <b>{data.periodo}</b>. "
            f"As informacoes foram organizadas de forma objetiva para apoiar "
            f"a tomada de decisao e o acompanhamento dos resultados do negocio."
        )
        el.append(Paragraph(texto, self.s_corpo))
        return el

    def _cards_indicadores(self, data: FinancialData) -> list:
        el = []
        el.extend(self._titulo_secao("Indicadores Principais"))

        fat = data.faturamento
        imp = data.impostos
        luc = data.lucro_liquido
        margem = (luc / fat * 100) if fat > 0 else 0
        p_imp  = (imp / fat * 100) if fat > 0 else 0

        cw = CONTENT_W / 3

        dados = [
            [
                Paragraph("FATURAMENTO TOTAL",  self.s_card_label),
                Paragraph("IMPOSTOS PAGOS",     self.s_card_label),
                Paragraph("LUCRO LIQUIDO",       self.s_card_label),
            ],
            [
                Paragraph(_brl(fat), self.s_card_val),
                Paragraph(_brl(imp), self.s_card_val_r),
                Paragraph(_brl(luc), self.s_card_val_g),
            ],
            [
                Paragraph("Receita bruta do periodo",      self.s_card_sub),
                Paragraph(f"{p_imp:.1f}% do faturamento".replace(".", ","), self.s_card_sub),
                Paragraph(f"Margem de {margem:.1f}%".replace(".", ","),     self.s_card_sub),
            ],
        ]

        GAP = 4  # gap branco entre cards
        tab = Table(dados, colWidths=[cw, cw, cw])
        tab.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (0, -1), colors.Color(0.95, 0.97, 1.00)),
            ("BACKGROUND",    (1, 0), (1, -1), colors.Color(1.00, 0.95, 0.95)),
            ("BACKGROUND",    (2, 0), (2, -1), colors.Color(0.93, 0.99, 0.95)),
            ("LINEABOVE",     (0, 0), (0, 0),  3, self.COR),
            ("LINEABOVE",     (1, 0), (1, 0),  3, VERMELHO_OK),
            ("LINEABOVE",     (2, 0), (2, 0),  3, VERDE_OK),
            ("LINEAFTER",     (0, 0), (0, -1), GAP, BRANCO),
            ("LINEAFTER",     (1, 0), (1, -1), GAP, BRANCO),
            ("TOPPADDING",    (0, 0), (-1, 0),  12),
            ("BOTTOMPADDING", (0, 0), (-1, 0),   4),
            ("TOPPADDING",    (0, 1), (-1, 1),   6),
            ("BOTTOMPADDING", (0, 1), (-1, 1),   4),
            ("TOPPADDING",    (0, 2), (-1, 2),   2),
            ("BOTTOMPADDING", (0, 2), (-1, 2),  12),
            ("LEFTPADDING",   (0, 0), (-1, -1),  8),
            ("RIGHTPADDING",  (0, 0), (-1, -1),  8),
        ]))
        el.append(tab)
        el.append(Spacer(1, 0.35 * cm))
        return el

    def _indicadores_financeiros(self, data: FinancialData) -> list:
        el = []
        el.extend(self._titulo_secao("Indicadores Financeiros"))

        # Liquidez Corrente
        if data.passivo_circulante > 0:
            liq_v = data.ativo_circulante / data.passivo_circulante
            liq_s = f"{liq_v:.2f}".replace(".", ",")
            if liq_v >= 1.5:
                l_st, l_bg, l_cor = "Saudavel",  VERDE_BG,    VERDE_OK
            elif liq_v >= 1.0:
                l_st, l_bg, l_cor = "Atencao",   AMARELO_BG,  AMARELO_OK
            else:
                l_st, l_bg, l_cor = "Critico",   VERMELHO_BG, VERMELHO_OK
            l_ref = "Referencia: acima de 1,50"
        else:
            liq_s, l_st, l_bg, l_cor = "N/D", "—", CINZA_FUNDO, CINZA_SUB
            l_ref = "Dados de balanco nao disponíveis"

        # Endividamento Geral
        if data.ativo_total > 0:
            end_v = (data.passivo_total / data.ativo_total) * 100
            end_s = f"{end_v:.1f}%".replace(".", ",")
            if end_v < 40:
                e_st, e_bg, e_cor = "Saudavel",  VERDE_BG,    VERDE_OK
            elif end_v <= 60:
                e_st, e_bg, e_cor = "Atencao",   AMARELO_BG,  AMARELO_OK
            else:
                e_st, e_bg, e_cor = "Critico",   VERMELHO_BG, VERMELHO_OK
            e_ref = "Referencia: abaixo de 40%"
        else:
            end_s, e_st, e_bg, e_cor = "N/D", "—", CINZA_FUNDO, CINZA_SUB
            e_ref = "Dados de balanco nao disponíveis"

        # Rentabilidade
        if data.faturamento > 0:
            ren_v = (data.lucro_liquido / data.faturamento) * 100
            ren_s = f"{ren_v:.1f}%".replace(".", ",")
            if ren_v >= 20:
                r_st, r_bg, r_cor = "Saudavel",  VERDE_BG,    VERDE_OK
            elif ren_v >= 10:
                r_st, r_bg, r_cor = "Atencao",   AMARELO_BG,  AMARELO_OK
            else:
                r_st, r_bg, r_cor = "Critico",   VERMELHO_BG, VERMELHO_OK
            r_ref = "Referencia: acima de 20%"
        else:
            ren_s, r_st, r_bg, r_cor = "N/D", "—", CINZA_FUNDO, CINZA_SUB
            r_ref = "Dados insuficientes"

        def _val(txt, cor):
            return Paragraph(f"<b>{txt}</b>", ParagraphStyle(
                "IVal", fontName="Helvetica-Bold", fontSize=14,
                textColor=cor, alignment=TA_CENTER))

        def _sta(txt, cor):
            return Paragraph(f"<b>{txt}</b>", ParagraphStyle(
                "ISta", fontName="Helvetica-Bold", fontSize=8.5,
                textColor=cor, alignment=TA_CENTER))

        CW = [CONTENT_W * 0.36, CONTENT_W * 0.18, CONTENT_W * 0.18, CONTENT_W * 0.28]

        linhas = [
            [
                Paragraph("INDICADOR",   self.s_th_l),
                Paragraph("VALOR",       self.s_th),
                Paragraph("SITUACAO",    self.s_th),
                Paragraph("REFERENCIA",  self.s_th_l),
            ],
            [
                [Paragraph("Liquidez Corrente",        self.s_ind_nome),
                 Paragraph("Ativo Circ. / Passivo Circ.", self.s_ind_form)],
                _val(liq_s, l_cor), _sta(l_st, l_cor),
                Paragraph(l_ref, self.s_ind_ref),
            ],
            [
                [Paragraph("Endividamento Geral",      self.s_ind_nome),
                 Paragraph("Passivo Total / Ativo Total", self.s_ind_form)],
                _val(end_s, e_cor), _sta(e_st, e_cor),
                Paragraph(e_ref, self.s_ind_ref),
            ],
            [
                [Paragraph("Indice de Rentabilidade",  self.s_ind_nome),
                 Paragraph("Lucro Liquido / Faturamento", self.s_ind_form)],
                _val(ren_s, r_cor), _sta(r_st, r_cor),
                Paragraph(r_ref, self.s_ind_ref),
            ],
        ]

        tab = Table(linhas, colWidths=CW)
        estilo = [
            # Cabeçalho
            ("BACKGROUND",    (0, 0), (-1, 0),   self.COR),
            ("TOPPADDING",    (0, 0), (-1, 0),   8),
            ("BOTTOMPADDING", (0, 0), (-1, 0),   8),
            # Col descrição (fundo neutro)
            ("BACKGROUND",    (0, 1), (0, -1),   CINZA_FUNDO),
            # Cols valor/situação (fundo do indicador)
            ("BACKGROUND",    (1, 1), (2, 1),    l_bg),
            ("BACKGROUND",    (1, 2), (2, 2),    e_bg),
            ("BACKGROUND",    (1, 3), (2, 3),    r_bg),
            # Col referência (fundo neutro alt)
            ("BACKGROUND",    (3, 1), (3, -1),   CINZA_ALT),
            # Alinhamento vertical
            ("VALIGN",        (0, 0), (-1, -1),  "MIDDLE"),
            # Padding uniforme
            ("TOPPADDING",    (0, 1), (-1, -1),  10),
            ("BOTTOMPADDING", (0, 1), (-1, -1),  10),
            ("LEFTPADDING",   (0, 0), (-1, -1),  10),
            ("RIGHTPADDING",  (0, 0), (-1, -1),  10),
            # Grid
            ("GRID",          (0, 0), (-1, -1),  0.4, CINZA_BORDA),
            ("LINEBELOW",     (0, -1),(-1, -1),  1.5, self.COR),
        ]
        tab.setStyle(TableStyle(estilo))

        el.append(tab)
        el.append(Spacer(1, 0.35 * cm))
        return el

    def _tabela_despesas(self, data: FinancialData) -> list:
        el = []
        el.extend(self._titulo_secao("Composicao das Despesas"))

        fat = data.faturamento
        CW = [CONTENT_W * 0.38, CONTENT_W * 0.22, CONTENT_W * 0.15, CONTENT_W * 0.25]

        linhas = [[
            Paragraph("CATEGORIA",      self.s_th_l),
            Paragraph("VALOR (R$)",     self.s_th),
            Paragraph("% FAT.",         self.s_th),
            Paragraph("DESCRICAO",      self.s_th_l),
        ]]

        itens = [
            ("Impostos e Tributos",       data.impostos,                "Encargos obrigatorios por lei"),
            ("Custos de Operacao",        data.custos_operacionais,     "Materiais, insumos e producao"),
            ("Despesas Administrativas",  data.despesas_administrativas,"Estrutura e gestao do negocio"),
            ("Outras Despesas",           data.outras_despesas,         "Demais gastos variados"),
        ]

        for nome, valor, obs in itens:
            if valor > 0:
                linhas.append([
                    Paragraph(nome, self.s_tc),
                    Paragraph(_brl(valor), self.s_tc_r),
                    Paragraph(_pct(valor, fat), self.s_tc_r),
                    Paragraph(obs, self.s_tc),
                ])

        total = sum(v for _, v, _ in itens)
        linhas.append([
            Paragraph("TOTAL DE DESPESAS", self.s_tc_b),
            Paragraph(_brl(total),          self.s_tc_br),
            Paragraph(_pct(total, fat),     self.s_tc_br),
            Paragraph("",                   self.s_tc),
        ])
        linhas.append([
            Paragraph("LUCRO LIQUIDO", self.s_tc_g),
            Paragraph(_brl(data.lucro_liquido), self.s_tc_gr),
            Paragraph(_pct(data.lucro_liquido, fat), self.s_tc_gr),
            Paragraph("Resultado final do periodo", self.s_tc),
        ])

        tab = Table(linhas, colWidths=CW)
        n = len(linhas)
        estilo = [
            ("BACKGROUND",    (0, 0), (-1, 0),   self.COR),
            ("TOPPADDING",    (0, 0), (-1, 0),   8),
            ("BOTTOMPADDING", (0, 0), (-1, 0),   8),
            ("TOPPADDING",    (0, 1), (-1, -1),  7),
            ("BOTTOMPADDING", (0, 1), (-1, -1),  7),
            ("LEFTPADDING",   (0, 0), (-1, -1),  10),
            ("RIGHTPADDING",  (0, 0), (-1, -1),  10),
            ("VALIGN",        (0, 0), (-1, -1),  "MIDDLE"),
            # Linha de total
            ("BACKGROUND",    (0, -2),(-1, -2),  CINZA_FUNDO),
            ("LINEABOVE",     (0, -2),(-1, -2),  0.8, self.COR),
            # Linha de lucro
            ("BACKGROUND",    (0, -1),(-1, -1),  VERDE_BG),
            ("LINEABOVE",     (0, -1),(-1, -1),  0.6, VERDE_OK),
            ("LINEBELOW",     (0, -1),(-1, -1),  1.5, self.COR),
            # Grid
            ("GRID",          (0, 0), (-1, -1),  0.4, CINZA_BORDA),
        ]
        # Linhas alternadas
        for i in range(1, n - 2):
            if i % 2 == 0:
                estilo.append(("BACKGROUND", (0, i), (-1, i), CINZA_ALT))

        tab.setStyle(TableStyle(estilo))
        el.append(tab)
        el.append(Spacer(1, 0.35 * cm))
        return el

    def _secao_insights(self, insights: List[Insight]) -> list:
        el = []
        el.extend(self._titulo_secao("Analise dos Resultados"))
        el.append(Paragraph(
            "Analise dos principais pontos identificados nos numeros deste periodo:",
            self.s_corpo))

        mapa = {
            "positivo": (VERDE_BG,    VERDE_OK,    self.s_ins_tit_ok),
            "atencao":  (AMARELO_BG,  AMARELO_OK,  self.s_ins_tit_wa),
            "critico":  (VERMELHO_BG, VERMELHO_OK, self.s_ins_tit_cr),
        }

        for ins in insights:
            bg, borda, s_tit = mapa.get(ins.tipo, mapa["atencao"])
            card = Table(
                [[Paragraph(f"<b>{ins.titulo}</b>", s_tit)],
                 [Paragraph(ins.descricao, self.s_ins_desc)]],
                colWidths=[CONTENT_W - 1.2 * cm],
            )
            card.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), bg),
                ("LINEBEFORE",    (0, 0), (0, -1),  4, borda),
                ("TOPPADDING",    (0, 0), (-1, 0),  9),
                ("BOTTOMPADDING", (0, -1),(-1, -1), 9),
                ("TOPPADDING",    (0, 1), (-1, 1),  2),
                ("LEFTPADDING",   (0, 0), (-1, -1), 12),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
                ("GRID",          (0, 0), (-1, -1), 0.3, CINZA_BORDA),
            ]))
            el.append(KeepTogether(card))
            el.append(Spacer(1, 0.2 * cm))

        return el

    def _secao_recomendacoes(self, recs: List[Recommendation]) -> list:
        el = []
        el.extend(self._titulo_secao("Recomendacoes Estrategicas"))
        el.append(Paragraph(
            "Acoes recomendadas com base na analise dos resultados deste periodo:",
            self.s_corpo))

        prio_map = {
            "alta":  ("ALTA PRIORIDADE",  VERMELHO_OK),
            "media": ("MEDIA PRIORIDADE", AMARELO_OK),
            "baixa": ("BAIXA PRIORIDADE", VERDE_OK),
        }

        for i, rec in enumerate(recs, 1):
            label, cor = prio_map.get(rec.prioridade, prio_map["media"])
            s_prio = ParagraphStyle("P", fontName="Helvetica-Bold", fontSize=7,
                                    textColor=cor, alignment=TA_RIGHT, letterSpacing=0.3)
            card = Table([
                [Paragraph(f"<b>{i}. {rec.titulo}</b>", self.s_rec_tit),
                 Paragraph(label, s_prio)],
                [Paragraph(rec.descricao, self.s_rec_desc), ""],
            ], colWidths=[CONTENT_W * 0.68, CONTENT_W * 0.32])
            card.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), CINZA_FUNDO),
                ("LINEBEFORE",    (0, 0), (0, -1),  3, self.COR),
                ("LINEBELOW",     (0, 0), (-1, 0),  0.4, CINZA_BORDA),
                ("SPAN",          (0, 1), (1, 1)),
                ("VALIGN",        (0, 0), (-1, 0),  "MIDDLE"),
                ("TOPPADDING",    (0, 0), (-1, 0),  9),
                ("BOTTOMPADDING", (0, 0), (-1, 0),  9),
                ("TOPPADDING",    (0, 1), (-1, 1),  5),
                ("BOTTOMPADDING", (0, -1),(-1, -1), 9),
                ("LEFTPADDING",   (0, 0), (-1, -1), 12),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
                ("GRID",          (0, 0), (-1, -1), 0.3, CINZA_BORDA),
            ]))
            el.append(KeepTogether(card))
            el.append(Spacer(1, 0.18 * cm))

        return el

    def _rodape(self) -> list:
        el = []
        el.append(Spacer(1, 0.6 * cm))
        el.append(HRFlowable(width="100%", thickness=0.8,
                              color=CINZA_BORDA, spaceBefore=4, spaceAfter=8))
        el.append(Paragraph(
            f"Relatorio elaborado por <b>{self.config.company_name}</b> — "
            f"As analises e recomendacoes sao de carater orientativo e nao substituem "
            f"uma consultoria contabil especializada.",
            self.s_rodape,
        ))
        return el
