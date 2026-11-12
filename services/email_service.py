import smtplib
import ssl
from email.message import EmailMessage


def configurado(cfg: dict) -> bool:
  return all(cfg.get(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"))


def enviar(cfg: dict, para: str, assunto: str, corpo: str, anexo: bytes, nome_anexo: str):
  """Envia um e-mail com anexo PDF. Devolve (ok, mensagem)."""
  try:
    msg = EmailMessage()
    msg["From"] = cfg.get("SMTP_FROM") or cfg["SMTP_USER"]
    msg["To"] = para
    msg["Subject"] = assunto
    msg.set_content(corpo)
    msg.add_attachment(anexo, maintype="application", subtype="pdf", filename=nome_anexo)
    porta = int(cfg.get("SMTP_PORT") or 465)
    if porta == 465:
      with smtplib.SMTP_SSL(cfg["SMTP_HOST"], porta, context=ssl.create_default_context(), timeout=20) as s:
        s.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
        s.send_message(msg)
    else:
      with smtplib.SMTP(cfg["SMTP_HOST"], porta, timeout=20) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
        s.send_message(msg)
    return True, "enviado"
  except Exception as e:
    return False, str(e)
