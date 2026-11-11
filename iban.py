"""Utilitários de IBAN (ISO 13616). A base de dados volta a validar tudo."""
import re


def normalizar(iban: str) -> str:
  return re.sub(r"\s", "", iban or "").upper()


def formatar(iban: str) -> str:
  s = normalizar(iban)
  return " ".join(s[i:i + 4] for i in range(0, len(s), 4))


def valido(iban: str) -> bool:
  s = normalizar(iban)
  if not re.fullmatch(r"[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}", s):
    return False
  if s.startswith("AO") and not re.fullmatch(r"AO[0-9]{23}", s):
    return False
  rearranjado = s[4:] + s[:4]
  numero = "".join(str(int(ch, 36)) for ch in rearranjado)  # A=10 ... Z=35
  return int(numero) % 97 == 1


def codigo_banco(iban: str):
  """Código de 4 dígitos do banco num IBAN angolano (posições 5-8)."""
  s = normalizar(iban)
  return s[4:8] if s.startswith("AO") and len(s) >= 8 else None
