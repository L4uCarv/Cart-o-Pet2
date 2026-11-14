"""Conciliação de pagamentos com o extrato do banco (Excel/CSV).

Funções puras (sem Streamlit nem Supabase) para poderem ser testadas.
Os resultados são SUGESTÕES: quem aprova é sempre o administrador.
"""
import hashlib
import io
import math
import re
import unicodedata
from datetime import timedelta

import pandas as pd


# ---------- leitura do ficheiro ----------
def folhas(conteudo: bytes, nome: str) -> list:
  if nome.lower().endswith((".xlsx", ".xls")):
    return pd.ExcelFile(io.BytesIO(conteudo)).sheet_names
  return []


def ler_bruto(conteudo: bytes, nome: str, folha=None) -> pd.DataFrame:
  """Lê o ficheiro SEM cabeçalho, para o utilizador indicar em que linha ele está."""
  if nome.lower().endswith((".xlsx", ".xls")):
    return pd.read_excel(io.BytesIO(conteudo), sheet_name=folha or 0, header=None, dtype=object)
  for enc in ("utf-8-sig", "latin-1"):
    try:
      return pd.read_csv(io.BytesIO(conteudo), sep=None, engine="python", header=None, dtype=object, encoding=enc)
    except UnicodeDecodeError:
      continue
  raise ValueError("Não foi possível ler o CSV (codificação desconhecida).")


def aplicar_cabecalho(bruto: pd.DataFrame, linha: int) -> pd.DataFrame:
  """linha = nº da linha (1 = primeira) onde estão os nomes das colunas."""
  cab = [str(x).strip() if str(x) != "nan" else f"coluna {i + 1}" for i, x in enumerate(bruto.iloc[linha - 1])]
  vistos, finais = {}, []
  for n in cab:  # nomes repetidos recebem sufixo
    vistos[n] = vistos.get(n, 0) + 1
    finais.append(n if vistos[n] == 1 else f"{n} ({vistos[n]})")
  df = bruto.iloc[linha:].copy()
  df.columns = finais
  return df.dropna(how="all").reset_index(drop=True)


# ---------- conversões ----------
def numero(x):
  """Converte '12 000,00', '12.000,50', '12,000.50', '(1 500,00)' em float. None se não for número."""
  if x is None or (isinstance(x, float) and math.isnan(x)):
    return None
  if isinstance(x, (int, float)):
    return float(x)
  s = str(x).strip()
  if not s or s.lower() == "nan":
    return None
  neg = s.startswith("-") or s.endswith("-") or (s.startswith("(") and s.endswith(")"))
  s = re.sub(r"[^\d,.]", "", s)
  if not s:
    return None
  if "," in s and "." in s:
    dec = "," if s.rfind(",") > s.rfind(".") else "."
    s = s.replace("." if dec == "," else ",", "").replace(dec, ".")
  elif "," in s:
    p = s.split(",")
    s = p[0] + "." + p[1] if len(p) == 2 and len(p[1]) in (1, 2) else s.replace(",", "")
  elif "." in s:
    p = s.split(".")
    s = s.replace(".", "") if len(p) > 2 or (len(p) == 2 and len(p[1]) == 3) else s
  try:
    v = float(s)
  except ValueError:
    return None
  return -v if neg else v


def norm(txt) -> str:
  t = unicodedata.normalize("NFKD", str(txt or "")).encode("ascii", "ignore").decode()
  return re.sub(r"[^A-Z0-9]", "", t.upper())


def preparar_creditos(df: pd.DataFrame, col_data: str, cols_desc: list, col_valor: str) -> pd.DataFrame:
  """Devolve só os créditos (valor > 0) com colunas: data, descricao, valor, hash."""
  out = pd.DataFrame({
      "data": pd.to_datetime(df[col_data], dayfirst=True, errors="coerce"),
      "descricao": df[cols_desc].fillna("").astype(str).agg(" ".join, axis=1).str.strip() if cols_desc else "",
      "valor": df[col_valor].map(numero),
  })
  out = out.dropna(subset=["data", "valor"])
  out = out[out["valor"] > 0].reset_index(drop=True)
  out["data"] = out["data"].dt.normalize()
  # impressão digital estável; linhas idênticas recebem um contador (1.ª, 2.ª, ...)
  base = out["data"].dt.strftime("%Y-%m-%d") + "|" + out["valor"].map(lambda v: f"{v:.2f}") + "|" + out["descricao"].map(norm)
  seq = base.groupby(base).cumcount()
  out["hash"] = [hashlib.sha256(f"{b}|{n}".encode()).hexdigest() for b, n in zip(base, seq)]
  return out


# ---------- comparação ----------
def comparar(pendentes: list, creditos: pd.DataFrame, usados: set, antes: int = 10, depois: int = 2, tolerancia: float = 0.0) -> list:
  """pendentes: dicts com id, data, valor, referencia. Devolve um resultado por pagamento.

  Estados: Encontrado (valor + data + referência), Possível (valor + data, sem referência),
           Já usado (só há créditos que já aprovaram outro pagamento), Não encontrado.
  """
  resultados = {}
  atribuidos = set()

  def candidatos(p):
    dp = pd.Timestamp(p["data"]).tz_localize(None).normalize() if pd.Timestamp(p["data"]).tzinfo else pd.Timestamp(p["data"]).normalize()
    m = ((creditos["valor"] - float(p["valor"])).abs() <= tolerancia + 0.005) \
        & (creditos["data"] >= dp - timedelta(days=antes)) & (creditos["data"] <= dp + timedelta(days=depois))
    c = creditos[m].copy()
    c["_dist"] = (c["data"] - dp).abs()
    return c.sort_values("_dist")

  ordenados = sorted(pendentes, key=lambda p: str(p["data"]))
  cand = {p["id"]: candidatos(p) for p in ordenados}

  def livres(c):
    return c[~c["hash"].isin(usados) & ~c["hash"].isin(atribuidos)]

  def montar(p, estado, c=None, n=0):
    r = {"id": p["id"], "estado": estado, "candidatos": n}
    if c is not None:
      r.update({"hash": c["hash"], "data_credito": c["data"].date(), "valor_credito": float(c["valor"]), "descricao_credito": c["descricao"]})
    return r

  # 1.ª passagem: valor + data + referência
  for p in ordenados:
    ref = norm(p.get("referencia"))
    if len(ref) < 4:
      continue
    l = livres(cand[p["id"]])
    l = l[l["descricao"].map(norm).str.contains(ref, regex=False)]
    if len(l):
      c = l.iloc[0]
      atribuidos.add(c["hash"])
      resultados[p["id"]] = montar(p, "Encontrado", c, len(l))
  # 2.ª passagem: só valor + data
  for p in ordenados:
    if p["id"] in resultados:
      continue
    l = livres(cand[p["id"]])
    if len(l):
      c = l.iloc[0]
      atribuidos.add(c["hash"])
      resultados[p["id"]] = montar(p, "Possível", c, len(l))
    elif len(cand[p["id"]]) and cand[p["id"]]["hash"].isin(usados).all():
      resultados[p["id"]] = montar(p, "Já usado")
    else:
      resultados[p["id"]] = montar(p, "Não encontrado")
  return [resultados[p["id"]] for p in ordenados]
