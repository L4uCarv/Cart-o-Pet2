"""Protocolos de vacinação e desparasitação e cálculo de idade."""
from datetime import date

# Dicionário integrado de informações e intervalos de vacinas
INFO_VACINAS = {
    "Polivalente V10": {
        "cat": "Vacina Polivalente",
        "doencas": ["Cinomose", "Parvovirose", "Coronavirose", "Hepatite Infecciosa", "Adenovirose Tipo 2", "Parainfluenza", "Leptospirose"],
        "intervalo_filhote": 21,
        "intervalo_adulto": 365,
    },
    "Polivalente V8": {
        "cat": "Vacina Polivalente",
        "doencas": ["Cinomose", "Parvovirose", "Coronavirose", "Hepatite Infecciosa", "Adenovirose Tipo 2", "Parainfluenza"],
        "intervalo_filhote": 21,
        "intervalo_adulto": 365,
    },
    "Vacina Antirrábica": {
        "cat": "Vacina Essencial",
        "doencas": ["Raiva Canina"],
        "intervalo_filhote": 365,
        "intervalo_adulto": 365,
    },
    "Vacina contra Tosse dos Canis (Gripe)": {
        "cat": "Vacina Complementar",
        "doencas": ["Bordetella bronchiseptica", "Parainfluenza"],
        "intervalo_filhote": 21,
        "intervalo_adulto": 365,
    },
    "Vacina contra Giardíase": {
        "cat": "Vacina Complementar",
        "doencas": ["Giardia duodenalis"],
        "intervalo_filhote": 21,
        "intervalo_adulto": 365,
    },
}

# Dicionário com categorias, sugestões rápidas e os dias corretos de efeito
# --- Espécies e vacinas felinas (ajusta ao protocolo do teu veterinário) ---
for _v in INFO_VACINAS.values():
  _v.setdefault("especies", ["Cão"])
INFO_VACINAS["Vacina Antirrábica"]["especies"] = ["Cão", "Gato"]
INFO_VACINAS["Vacina Antirrábica"]["doencas"] = ["Raiva"]
_FELINAS = {"cat": "Vacina Polivalente", "especies": ["Gato"], "intervalo_filhote": 21, "intervalo_adulto": 365}
_V3 = ["Panleucopenia felina", "Rinotraqueíte felina (herpesvírus)", "Calicivirose felina"]
INFO_VACINAS["Polivalente V3 (Tríplice)"] = {**_FELINAS, "doencas": _V3}
INFO_VACINAS["Polivalente V4 (Quádrupla)"] = {**_FELINAS, "doencas": _V3 + ["Clamidiose felina"]}
INFO_VACINAS["Polivalente V5 (Quíntupla)"] = {**_FELINAS, "doencas": _V3 + ["Clamidiose felina", "Leucemia felina (FeLV)"]}
INFO_VACINAS["Vacina contra Leucemia Felina (FeLV)"] = {
    **_FELINAS, "cat": "Vacina Opcional", "doencas": ["Leucemia felina (FeLV)"]}

# Listas para a janela de doenças (o utilizador marca as que a vacina protege)
DOENCAS_CAO = ["Cinomose", "Parvovirose", "Hepatite Infecciosa", "Adenovirose Tipo 2", "Parainfluenza", "Coronavirose",
               "Leptospirose", "Raiva", "Bordetella bronchiseptica", "Giardia duodenalis", "Leishmaniose"]
DOENCAS_GATO = ["Panleucopenia felina", "Rinotraqueíte felina (herpesvírus)", "Calicivirose felina", "Clamidiose felina",
                "Leucemia felina (FeLV)", "Raiva"]


def vacinas_para(especie: str) -> list:
  """Vacinas do catálogo aplicáveis à espécie (outras espécies: todas)."""
  if especie not in ("Cão", "Gato"):
    return list(INFO_VACINAS)
  return [nome for nome, v in INFO_VACINAS.items() if especie in v.get("especies", ["Cão"])]


def doencas_para(especie: str) -> list:
  return DOENCAS_GATO if especie == "Gato" else DOENCAS_CAO


INFO_DESPARASITACAO = {
    "Desparasitação Interna (Comprimido / Xarope)": {
        "cat": "Interna",
        "produtos_sugeridos": ["Drontal Plus", "Milbemax", "Canex", "Endogard", "Vetmax Plus"],
        "dias": 90,  # 3 meses
    },
    "Desparasitação Externa (Pipeta / Coleira / Spray)": {
        "cat": "Externa",
        "produtos_sugeridos": ["Bravecto", "Simparica", "Frontline", "Seresto"],
        "dias": 30,  # 1 mês
    },
    "Antipulgas (Comprimidos)": {
        "cat": "Externa",
        "produtos_sugeridos": ["NexGard", "Simparica"],
        "dias": 30,  # 1 mês
    },
}


# --- Desparasitação por espécie (sugestões; confirma sempre com o veterinário) ---
_INT, _EXT, _PULG = list(INFO_DESPARASITACAO)
PRODUTOS_DESPARASITACAO = {
    "Cão": {
        _INT: ["Drontal Plus", "Milbemax", "Canex", "Endogard", "Vetmax Plus"],
        _EXT: ["Bravecto", "Simparica", "Frontline", "Seresto"],
        _PULG: ["NexGard", "Simparica"],
    },
    "Gato": {
        _INT: ["Drontal (gatos)", "Milbemax (gatos)", "Profender (spot-on)"],
        _EXT: ["Bravecto (spot-on gatos)", "Frontline (gatos)", "Seresto (coleira gatos)", "Revolution (selamectina)"],
        _PULG: ["Capstar (nitenpiram)"],
    },
}
PARASITAS_CAO = ["Vermes redondos (Toxocara, Toxascaris)", "Ancilóstomos", "Tricurídeos (Trichuris)", "Ténias (Dipylidium, Taenia)",
                 "Giardia", "Dirofilariose (Dirofilaria immitis)", "Pulgas", "Carraças", "Ácaros (sarna)", "Piolhos"]
PARASITAS_GATO = ["Vermes redondos (Toxocara cati)", "Ancilóstomos", "Ténias (Dipylidium, Taenia)", "Giardia",
                  "Vermes pulmonares (Aelurostrongylus)", "Pulgas", "Carraças", "Ácaros do ouvido (Otodectes)",
                  "Sarna (Notoedres)", "Piolhos"]
# parasitas habitualmente cobertos por cada categoria (pré-marcados na janela)
_HAB_CAO = {_INT: PARASITAS_CAO[:4], _EXT: ["Pulgas", "Carraças"], _PULG: ["Pulgas"]}
_HAB_GATO = {_INT: PARASITAS_GATO[:3], _EXT: ["Pulgas", "Carraças"], _PULG: ["Pulgas"]}


def _esp(especie: str) -> str:
  return "Gato" if especie == "Gato" else "Cão"


def produtos_para(categoria: str, especie: str) -> list:
  return PRODUTOS_DESPARASITACAO[_esp(especie)].get(categoria, [])


def parasitas_para(especie: str) -> list:
  return PARASITAS_GATO if especie == "Gato" else PARASITAS_CAO


def parasitas_habituais(categoria: str, especie: str) -> list:
  return (_HAB_GATO if especie == "Gato" else _HAB_CAO).get(categoria, [])


def calcular_idade_pet(data_nascimento):
  hoje = date.today()
  if data_nascimento > hoje:
    return "Data inválida", 0.0

  anos = hoje.year - data_nascimento.year
  meses = hoje.month - data_nascimento.month
  dias = hoje.day - data_nascimento.day

  if dias < 0:
    meses -= 1
  if meses < 0:
    anos -= 1
    meses += 12

  total_meses = anos * 12 + meses
  idade_anos_decimal = round(total_meses / 12, 1)

  if total_meses < 1:
    return "Menos de 1 mês", idade_anos_decimal
  elif total_meses < 12:
    return (f"{total_meses} mês" if total_meses == 1 else f"{total_meses} meses"), idade_anos_decimal
  else:
    txt_anos = "1 ano" if anos == 1 else f"{anos} anos"
    txt_meses = "1 mês" if meses == 1 else f"{meses} meses"
    return (f"{txt_anos} e {txt_meses}" if meses > 0 else txt_anos), idade_anos_decimal
