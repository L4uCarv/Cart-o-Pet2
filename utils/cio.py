"""Previsão (cadelas) e estimativa (gatas) do cio. Funções puras, sem Streamlit.

Cadelas: ciclos regulares -> PREVISÃO calculada a partir do histórico do próprio animal.
Gatas:   ciclo muito variável (luz, estação, acasalamento) -> apenas ESTIMATIVA orientativa.
Valores típicos de referência; não substituem o veterinário.
"""
import calendar
from datetime import date, timedelta
from statistics import pstdev

# 1.º cio das cadelas, em meses de idade, por porte
PRIMEIRO_CIO_CADELA = {"pequeno": (6, 10), "medio": (8, 12), "grande": (12, 24), None: (6, 24)}
PRIMEIRO_CIO_GATA = (5, 10)
INTERVALO_PADRAO_CADELA = 180   # dias (cerca de 6 meses)
RETORNO_GATA = (14, 21)         # dias, se não houver acasalamento
AVISO_DIAS = 30


def add_meses(d: date, n: int) -> date:
  m = d.month - 1 + n
  y, mo = d.year + m // 12, m % 12 + 1
  return date(y, mo, min(d.day, calendar.monthrange(y, mo)[1]))


def _f(d: date) -> str:
  return d.strftime("%d/%m/%Y")


def _resultado(tipo, **kw):
  base = {"tipo": tipo, "aplicavel": True, "fase": None, "inicio": None, "fim": None, "central": None,
          "confianca": "", "texto": "", "estado": "", "dias_ate": None, "alerta": False, "notas": []}
  base.update(kw)
  return base


def _estado_e_alerta(r, hoje):
  ini, fim, cen = r["inicio"], r["fim"], r["central"]
  if hoje < ini:
    r["estado"] = "futuro"
  elif hoje <= fim:
    r["estado"] = "janela"
  else:
    r["estado"] = "ultrapassado"
  r["dias_ate"] = (cen - hoje).days
  r["alerta"] = r["estado"] == "janela" or (r["estado"] == "futuro" and (ini - hoje).days <= AVISO_DIAS)
  return r


def prever(animal: dict, cios: list, hoje: date = None) -> dict:
  """animal: dict com especie, sexo, data_nascimento (ISO ou None), porte, esterilizado.
  cios: lista de datas (date) de início de cio já registadas."""
  hoje = hoje or date.today()
  especie = animal.get("especie")
  gata = especie == "Gato"
  tipo = "estimativa" if gata else "previsao"
  if especie not in ("Cão", "Gato"):
    return _resultado(tipo, aplicavel=False, texto="A previsão de cio está disponível para cadelas e gatas.")
  if animal.get("sexo") != "Fêmea":
    return _resultado(tipo, aplicavel=False, texto="Só se aplica a fêmeas.")
  if animal.get("esterilizado"):
    return _resultado(tipo, aplicavel=False, texto="Animal esterilizado: não tem cio.")

  cios = sorted(set(cios))
  nasc = date.fromisoformat(str(animal["data_nascimento"])[:10]) if animal.get("data_nascimento") else None

  # ---------- ainda sem cios registados: 1.º cio pela idade ----------
  if not cios:
    if nasc is None:
      return _resultado(tipo, aplicavel=False, texto="Indica a data de nascimento (ou regista um cio) para obter a "
                        + ("estimativa." if gata else "previsão."))
    lo, hi = PRIMEIRO_CIO_GATA if gata else PRIMEIRO_CIO_CADELA.get(animal.get("porte"), PRIMEIRO_CIO_CADELA[None])
    ini, fim = add_meses(nasc, lo), add_meses(nasc, hi)
    cen = ini + (fim - ini) // 2
    r = _resultado(tipo, fase="primeiro", inicio=ini, fim=fim, central=cen, confianca="orientativa" if gata else "baixa")
    if not gata and not animal.get("porte"):
      r["notas"].append("Define o porte para uma janela mais precisa (sem porte usa-se 6 a 24 meses).")
    if gata:
      r["notas"].append("Algumas raças têm o primeiro cio mais cedo (ex.: siamesa) e outras mais tarde (ex.: persa).")
    _estado_e_alerta(r, hoje)
    qual = "estimativa" if gata else "previsão"
    if r["estado"] == "futuro":
      r["texto"] = f"Primeiro cio: {qual} entre {_f(ini)} e {_f(fim)}, com base na idade."
    elif r["estado"] == "janela":
      r["texto"] = f"Está na idade típica do primeiro cio (entre {_f(ini)} e {_f(fim)}): pode acontecer a qualquer momento."
    else:
      r["texto"] = (f"Já passou a idade típica do primeiro cio (até {_f(fim)}). Se ainda não aconteceu, fala com o veterinário; "
                    "se já aconteceu, regista a data.")
    return r

  ultimo = cios[-1]

  # ---------- gatas: estimativa orientativa ----------
  if gata:
    ini, fim = ultimo + timedelta(days=RETORNO_GATA[0]), ultimo + timedelta(days=RETORNO_GATA[1])
    r = _resultado(tipo, fase="seguinte", inicio=ini, fim=fim, central=ini + (fim - ini) // 2, confianca="orientativa")
    r["notas"].append("Se não houver acasalamento, as gatas costumam voltar ao cio passadas 2 a 3 semanas, durante a época reprodutiva.")
    _estado_e_alerta(r, hoje)
    if r["estado"] == "ultrapassado":
      r["texto"] = (f"Último cio registado em {_f(ultimo)}. Já passaram mais de 3 semanas: pode já ter voltado ao cio ou estar "
                    "fora da época reprodutiva. Se houve novo cio, regista-o.")
    else:
      r["texto"] = f"Estimativa: novo cio possível entre {_f(ini)} e {_f(fim)} (a partir do último, em {_f(ultimo)})."
    return r

  # ---------- cadelas: previsão pelo histórico ----------
  intervalos = [(b - a).days for a, b in zip(cios, cios[1:])]
  usados = intervalos[-3:]
  if usados:
    media = round(sum(usados) / len(usados))
    margem = 30 if len(usados) == 1 else max(14, round(pstdev(usados)))
  else:
    media, margem = INTERVALO_PADRAO_CADELA, 45
  confianca = {0: "baixa", 1: "baixa", 2: "média"}.get(len(usados), "boa")
  central = ultimo + timedelta(days=media)
  r = _resultado(tipo, fase="seguinte", inicio=central - timedelta(days=margem), fim=central + timedelta(days=margem),
                 central=central, confianca=confianca)
  r.update({"intervalo": media, "n_intervalos": len(usados)})
  if not usados:
    r["notas"].append(f"Só há um cio registado: usa-se o intervalo habitual de cerca de {INTERVALO_PADRAO_CADELA} dias. "
                      "Os primeiros ciclos costumam ser irregulares; a previsão melhora a cada cio registado.")
  else:
    r["notas"].append(f"Calculado com o intervalo médio de {media} dias entre os últimos {len(usados)} ciclo(s) registado(s).")
  if media < 90 or media > 400:
    r["notas"].append("Os intervalos registados são muito irregulares: fala com o veterinário.")
  _estado_e_alerta(r, hoje)
  if r["estado"] == "ultrapassado":
    r["texto"] = (f"Previsão ultrapassada (era {_f(r['inicio'])} a {_f(r['fim'])}). Se já houve cio, regista a data; "
                  "se não houve, fala com o veterinário.")
  else:
    r["texto"] = f"Previsão: próximo cio por volta de {_f(central)} (entre {_f(r['inicio'])} e {_f(r['fim'])})."
  return r
