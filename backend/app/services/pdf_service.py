"""
Geração de relatórios em PDF usando reportlab.
"""
import io
from datetime import datetime
from typing import List, Dict, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable, KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Paleta de cores
PRIMARY = colors.HexColor("#1877F2")   # Azul Meta
SECONDARY = colors.HexColor("#0A2540")
SUCCESS = colors.HexColor("#00B37A")
DANGER = colors.HexColor("#E53935")
LIGHT_GRAY = colors.HexColor("#F5F7FA")
BORDER = colors.HexColor("#E1E8ED")


def generate_campaign_report(
    campaigns: List[Dict],
    period: str,
    account_name: str = "Todas as Contas",
    summary: Dict = None,
) -> bytes:
    """
    Gera PDF de relatório de campanhas.
    Retorna bytes do PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=2 * cm,
        bottomMargin=1.5 * cm,
        title=f"Relatório de Campanhas — {period}",
    )

    styles = getSampleStyleSheet()

    # Estilos customizados
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=SECONDARY,
        spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "CustomSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#6B7280"),
        spaceAfter=20,
    )
    label_style = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#9CA3AF"),
        fontName="Helvetica",
    )
    metric_style = ParagraphStyle(
        "Metric",
        parent=styles["Normal"],
        fontSize=16,
        textColor=SECONDARY,
        fontName="Helvetica-Bold",
    )
    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=SECONDARY,
        spaceBefore=16,
        spaceAfter=8,
        fontName="Helvetica-Bold",
    )

    story = []

    # === CABEÇALHO ===
    story.append(Paragraph("Gestor de Tráfego Pago", title_style))
    story.append(Paragraph(f"Relatório de Campanhas — {period} | {account_name}", subtitle_style))
    story.append(Paragraph(f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}", label_style))
    story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY, spaceAfter=16))

    # === CARDS DE RESUMO ===
    if summary:
        story.append(Paragraph("Resumo do Período", section_style))
        summary_data = [
            [
                _metric_cell("💰 Investimento Total", f"R$ {summary.get('total_spend', 0):,.2f}", label_style, metric_style),
                _metric_cell("👁️ Impressões", f"{summary.get('total_impressions', 0):,}", label_style, metric_style),
                _metric_cell("🖱️ Cliques", f"{summary.get('total_clicks', 0):,}", label_style, metric_style),
                _metric_cell("🎯 Conversões", f"{summary.get('total_conversions', 0):,}", label_style, metric_style),
                _metric_cell("📈 ROAS Médio", f"{summary.get('average_roas', 0):.2f}x", label_style, metric_style),
                _metric_cell("💡 CPC Médio", f"R$ {summary.get('average_cpc', 0):.2f}", label_style, metric_style),
            ]
        ]
        summary_table = Table(
            summary_data,
            colWidths=[4.5 * cm] * 6,
        )
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
            ("BOX", (0, 0), (-1, -1), 1, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 16))

    # === TABELA DE CAMPANHAS ===
    story.append(Paragraph("Detalhamento por Campanha", section_style))

    if not campaigns:
        story.append(Paragraph("Nenhuma campanha encontrada no período.", styles["Normal"]))
    else:
        headers = [
            "Campanha", "Status", "Impressões", "Cliques",
            "Investimento", "CPM", "CPC", "CTR", "Conversões", "ROAS"
        ]

        table_data = [headers]
        for c in campaigns:
            status_text = "✅ Ativa" if c.get("status") == "ACTIVE" else "⏸️ Pausada"
            table_data.append([
                _truncate(c.get("campaign_name", ""), 30),
                status_text,
                f"{c.get('impressions', 0):,}",
                f"{c.get('clicks', 0):,}",
                f"R$ {c.get('spend', 0):,.2f}",
                f"R$ {c.get('cpm', 0):.2f}",
                f"R$ {c.get('cpc', 0):.2f}",
                f"{c.get('ctr', 0):.2f}%",
                f"{c.get('conversions', 0):,}",
                f"{c.get('roas', 0):.2f}x",
            ])

        col_widths = [6 * cm, 2.2 * cm, 2.5 * cm, 2 * cm, 2.8 * cm, 2.2 * cm, 2.2 * cm, 1.8 * cm, 2.5 * cm, 2 * cm]
        camp_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        camp_table.setStyle(TableStyle([
            # Cabeçalho
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            # Linhas de dados
            ("FONTSIZE", (0, 1), (-1, -1), 7.5),
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 1), (1, -1), "LEFT"),
            ("TOPPADDING", (0, 1), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            # Zebra
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            # Bordas
            ("BOX", (0, 0), (-1, -1), 1, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))

        # Colorir ROAS alto em verde
        for row_idx, c in enumerate(campaigns, start=1):
            roas = c.get("roas", 0)
            if roas >= 2.0:
                camp_table.setStyle(TableStyle([
                    ("TEXTCOLOR", (9, row_idx), (9, row_idx), SUCCESS),
                    ("FONTNAME", (9, row_idx), (9, row_idx), "Helvetica-Bold"),
                ]))
            elif roas > 0 and roas < 1.0:
                camp_table.setStyle(TableStyle([
                    ("TEXTCOLOR", (9, row_idx), (9, row_idx), DANGER),
                ]))

        story.append(camp_table)

    # === RODAPÉ ===
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER))
    story.append(Spacer(1, 6))
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontSize=7, textColor=colors.HexColor("#9CA3AF"), alignment=TA_CENTER
    )
    story.append(Paragraph(
        "Relatório gerado automaticamente pela Plataforma Gestor de Tráfego Pago | "
        f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        footer_style,
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def _metric_cell(label: str, value: str, label_style, value_style):
    """Cria um 'card' de métrica para a tabela de resumo."""
    from reportlab.platypus import KeepInFrame
    return [
        Paragraph(label, label_style),
        Spacer(1, 4),
        Paragraph(value, value_style),
    ]


def _truncate(text: str, max_len: int) -> str:
    if len(text) > max_len:
        return text[:max_len - 3] + "..."
    return text
