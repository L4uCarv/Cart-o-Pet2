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
