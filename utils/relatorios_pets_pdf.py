"""PDF dos relatórios de animais (reportlab/platypus)."""
import io
from datetime import date
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

from utils import relatorios_pets as rp

AZUL = colors.HexColor("#4F46E5")
CINZA = colors.HexColor("#F3F4F6")
_ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=_ss["Title"], fontName="Helvetica-Bold", fontSize=18, alignment=TA_LEFT, textColor=AZUL, spaceAfter=2)
H2 = ParagraphStyle("h2", parent=_ss["Heading2"], fontName="Helvetica-Bold", fontSize=12, spaceBefore=10, spaceAfter=4)
TXT = ParagraphStyle("txt", parent=_ss["BodyText"], fontName="Helvetica", fontSize=9, leading=12)
PEQ = ParagraphStyle("peq", parent=TXT, fontSize=8, leading=10, textColor=colors.HexColor("#555555"))
CEL = ParagraphStyle("cel", parent=TXT, fontSize=8, leading=10)


def _t(x) -> str:
  """Texto seguro para o PDF: escapa XML e troca o que a fonte padrão não suporta."""
  s = escape(str(x if x is not None else ""))
  return s.encode("latin-1", "replace").decode("latin-1")


def _tabela(cab, linhas, larguras):
  dados = [[Paragraph(f"<b>{_t(c)}</b>", CEL) for c in cab]] + [[Paragraph(_t(c), CEL) for c in l] for l in linhas]
  t = Table(dados, colWidths=larguras, repeatRows=1)
  t.setStyle(TableStyle([
      ("BACKGROUND", (0, 0), (-1, 0), CINZA), ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.grey),
      ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAFA")]),
      ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
      ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#DDDDDD"))]))
  return t


def _cabecalho(titulo, subtitulo):
  return [Paragraph(_t(titulo), H1), Paragraph(_t(subtitulo), PEQ), Spacer(1, 4 * mm)]


def _rodape(c, d):
  c.saveState(); c.setFont("Helvetica", 7.5); c.setFillColor(colors.grey)
  c.drawString(18 * mm, 10 * mm, "CartãoPet - relatório gerado automaticamente. Os registos 'Veterinário' foram validados por profissional credenciado.")
  c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Página {d.page}")
  c.restoreState()


def _doc(elementos):
  buf = io.BytesIO()
  SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                    title="Relatório CartãoPet").build(elementos, onFirstPage=_rodape, onLaterPages=_rodape)
  return buf.getvalue()


def _ficha(a, com_nome=True):
  linha = " · ".join(x for x in [a["especie"], a.get("raca") or "", a.get("sexo") or "", rp.idade_txt(a)] if x)
  chip = f"Microchip: {a['microchip']}" if a.get("microchip") else "Sem microchip registado"
  titulo = [Paragraph(f"<b>{_t(a['nome'])}</b>", ParagraphStyle("n", parent=H2, fontSize=14, spaceBefore=0))] if com_nome else []
  return titulo + [Paragraph(_t(linha), TXT), Paragraph(_t(chip + (f" · Nascimento: {rp.fmt_d(a['data_nascimento'])}" if a.get("data_nascimento") else "")), PEQ)]


def gerar_resumo_pdf(tutor_nome, animais, registos, consultas, pesos) -> bytes:
  el = _cabecalho("Resumo atual dos animais", f"Tutor: {tutor_nome} · Gerado em {date.today().strftime('%d/%m/%Y')}")
  if not animais:
    el.append(Paragraph("Sem animais registados.", TXT))
  for a in animais:
    regs = rp.ativos(rp.do_animal(registos, a["id"]))
    ps = sorted(rp.do_animal(pesos, a["id"]), key=lambda p: p["medido_em"])
    cs = rp.do_animal(consultas, a["id"])
    bloco = _ficha(a)
    peso = f"{ps[-1]['peso_kg']} kg (em {rp.fmt_d(ps[-1]['medido_em'])})" if ps else "sem registo"
    cons = rp.fmt_d(max(c["criado_at"] for c in cs)) if cs else "sem consultas"
    bloco.append(Paragraph(f"Último peso: <b>{_t(peso)}</b> · Última consulta: <b>{_t(cons)}</b>", TXT))
    bloco.append(Spacer(1, 2 * mm))
    sv = rp.situacao_vacinal(regs)
    if sv:
      linhas = [[("Vacina" if r["tipo"] == "vacina" else "Desparasitação"), r["nome_produto"], rp.fmt_d(r["data_aplicacao"]),
                 rp.fmt_d(r.get("proxima_dose")), rp.estado_reforco(r.get("proxima_dose")), rp.validacao_txt(r)] for r in sv]
      bloco.append(_tabela(["Tipo", "Produto", "Última", "Próximo reforço", "Estado", "Validação"], linhas,
                           [24 * mm, 46 * mm, 20 * mm, 24 * mm, 30 * mm, 30 * mm]))
    else:
      bloco.append(Paragraph("Sem vacinas ou desparasitações registadas.", PEQ))
    bloco.append(Spacer(1, 7 * mm))
    el.append(KeepTogether(bloco))
  return _doc(el)


def _imagem(dados: bytes, largura_mm=42):
  from PIL import Image as PILImage
  im = PILImage.open(io.BytesIO(dados)).convert("RGB")
  im.thumbnail((700, 700))
  buf = io.BytesIO(); im.save(buf, format="JPEG", quality=70); buf.seek(0)
  w, h = im.size
  return Image(buf, width=largura_mm * mm, height=largura_mm * mm * h / w)


def gerar_historico_pdf(tutor_nome, animais, registos, consultas, pesos, imagens=None) -> bytes:
  """imagens: {caminho_da_vinheta: bytes}. Se vazio, não inclui as vinhetas."""
  imagens = imagens or {}
  el = []
  for i, a in enumerate(animais):
    if i:
      el.append(PageBreak())
    el += _cabecalho(f"Histórico detalhado - {a['nome']}", f"Tutor: {tutor_nome} · Gerado em {date.today().strftime('%d/%m/%Y')}")
    el += _ficha(a, com_nome=False)
    regs = sorted(rp.ativos(rp.do_animal(registos, a["id"])), key=lambda r: r["data_aplicacao"], reverse=True)
    cs = sorted(rp.do_animal(consultas, a["id"]), key=lambda c: c["criado_at"], reverse=True)
    ps = sorted(rp.do_animal(pesos, a["id"]), key=lambda p: p["medido_em"], reverse=True)

    el.append(Paragraph("Vacinas e desparasitações", H2))
    if regs:
      linhas = [[rp.fmt_d(r["data_aplicacao"]), "Vacina" if r["tipo"] == "vacina" else "Desparasit.", r["nome_produto"],
                 (f"Lote {r['numero_lote']}" if r.get("numero_lote") else "") + (f" · val. {rp.fmt_d(r['data_validade'])}" if r.get("data_validade") else ""),
                 rp.fmt_d(r.get("proxima_dose")), rp.validacao_txt(r)] for r in regs]
      el.append(_tabela(["Data", "Tipo", "Produto", "Lote / validade", "Próx. reforço", "Validação"], linhas,
                        [20 * mm, 22 * mm, 40 * mm, 36 * mm, 22 * mm, 34 * mm]))
    else:
      el.append(Paragraph("Sem registos.", PEQ))

    fotos = [(r, imagens.get(r["comprovativo_url"])) for r in regs if imagens.get(r["comprovativo_url"])]
    if fotos:
      el.append(Paragraph("Vinhetas", H2))
      celulas = []
      for r, dados in fotos:
        try:
          celulas.append([_imagem(dados), Paragraph(_t(f"{rp.fmt_d(r['data_aplicacao'])} - {r['nome_produto']}"), PEQ)])
        except Exception:
          continue
      for k in range(0, len(celulas), 4):
        grupo = celulas[k:k + 4]
        linha_img = [c[0] for c in grupo] + [""] * (4 - len(grupo))
        linha_leg = [c[1] for c in grupo] + [""] * (4 - len(grupo))
        t = Table([linha_img, linha_leg], colWidths=[44 * mm] * 4)
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 1), (-1, 1), 6)]))
        el.append(KeepTogether(t))

    el.append(Paragraph("Consultas", H2))
    if cs:
      for c in cs:
        partes = [Paragraph(f"<b>{rp.fmt_d(c['criado_at'])}</b> · {_t(c.get('carimbo_digital') or '')}", TXT),
                  Paragraph(f"<b>Anamnese:</b> {_t(c.get('anamnese'))}", TXT)]
        if c.get("exames_complementares"):
          partes.append(Paragraph(f"<b>Exames:</b> {_t(c['exames_complementares'])}", TXT))
        if c.get("prescricao_medicamentosa"):
          partes.append(Paragraph(f"<b>Prescrição:</b> {_t(c['prescricao_medicamentosa'])}", TXT))
        partes.append(Spacer(1, 3 * mm))
        el.append(KeepTogether(partes))
    else:
      el.append(Paragraph("Sem consultas registadas.", PEQ))

    el.append(Paragraph("Evolução do peso", H2))
    if ps:
      el.append(_tabela(["Data", "Peso (kg)"], [[rp.fmt_d(p["medido_em"]), p["peso_kg"]] for p in ps], [30 * mm, 30 * mm]))
    else:
      el.append(Paragraph("Sem pesos registados.", PEQ))
  if not animais:
    el = _cabecalho("Histórico detalhado", f"Tutor: {tutor_nome}") + [Paragraph("Sem animais selecionados.", TXT)]
  return _doc(el)
