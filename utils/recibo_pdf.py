"""Geração do recibo em PDF (reportlab). Só usa caracteres Latin-1."""
import io

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def _aoa(v) -> str:
  return f"{float(v):,.2f}".replace(",", " ").replace(".", ",") + " AOA"


def _data(d) -> str:
  return pd.Timestamp(d).strftime("%d/%m/%Y")


def gerar_recibo_pdf(r: dict, empresa: dict) -> bytes:
  buf = io.BytesIO()
  c = canvas.Canvas(buf, pagesize=A4)
  w, h = A4
  m = 20 * mm
  azul = colors.HexColor("#4F46E5")

  c.setFillColor(azul)
  c.rect(0, h - 32 * mm, w, 32 * mm, stroke=0, fill=1)
  c.setFillColor(colors.white)
  c.setFont("Helvetica-Bold", 20)
  c.drawString(m, h - 17 * mm, empresa.get("nome") or "CartãoPet")
  c.setFont("Helvetica", 9)
  linhas_emp = [x for x in [f"NIF: {empresa['nif']}" if empresa.get("nif") else "", empresa.get("morada") or ""] if x]
  for i, t in enumerate(linhas_emp):
    c.drawString(m, h - (23 + 5 * i) * mm, t)
  c.setFont("Helvetica-Bold", 16)
  c.drawRightString(w - m, h - 17 * mm, "RECIBO")
  c.setFont("Helvetica", 10)
  c.drawRightString(w - m, h - 24 * mm, f"Nº {r['numero']}")

  c.setFillColor(colors.black)
  y = h - 48 * mm
  def par(rotulo, valor, y):
    c.setFont("Helvetica", 9); c.setFillColor(colors.grey); c.drawString(m, y, rotulo)
    c.setFont("Helvetica-Bold", 11); c.setFillColor(colors.black); c.drawString(m + 42 * mm, y, str(valor))
  par("Data de emissão", _data(r["emitido_em"]), y); y -= 8 * mm
  par("Cliente", r["cliente_nome"], y); y -= 8 * mm
  par("E-mail", r["cliente_email"], y); y -= 8 * mm
  forma = r.get("metodo") or ""
  if r.get("banco_nome"):
    forma += f" - {r['banco_nome']}"
  par("Forma de pagamento", forma or "-", y); y -= 14 * mm

  c.setFillColor(colors.HexColor("#F3F4F6"))
  c.rect(m, y - 2 * mm, w - 2 * m, 9 * mm, stroke=0, fill=1)
  c.setFillColor(colors.black)
  c.setFont("Helvetica-Bold", 10)
  c.drawString(m + 3 * mm, y + 1 * mm, "Descrição")
  c.drawRightString(w - m - 3 * mm, y + 1 * mm, "Valor")
  y -= 10 * mm
  c.setFont("Helvetica", 11)
  c.drawString(m + 3 * mm, y, r["descricao"])
  c.drawRightString(w - m - 3 * mm, y, _aoa(r["valor"]))
  y -= 7 * mm
  c.setFont("Helvetica", 9); c.setFillColor(colors.grey)
  c.drawString(m + 3 * mm, y, f"Período de validade: {_data(r['valido_de'])} a {_data(r['valido_ate'])} ({r['meses']} mês/meses)")
  y -= 6 * mm
  c.setStrokeColor(colors.lightgrey); c.line(m, y, w - m, y)
  y -= 10 * mm
  c.setFillColor(colors.black); c.setFont("Helvetica-Bold", 13)
  c.drawRightString(w - m, y, f"Total pago: {_aoa(r['valor'])}")

  c.setFont("Helvetica", 8); c.setFillColor(colors.grey)
  c.drawString(m, 22 * mm, "Documento emitido automaticamente pelo CartãoPet após confirmação do pagamento.")
  c.drawString(m, 17.5 * mm, "Comprovativo interno; não substitui fatura ou recibo fiscal certificado, quando aplicavel.")
  c.showPage()
  c.save()
  return buf.getvalue()
