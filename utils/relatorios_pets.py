"""Dados dos relatórios de animais (resumo atual e histórico detalhado). Funções puras."""
from datetime import date

import pandas as pd

from utils.protocolos import calcular_idade_pet


def fmt_d(d) -> str:
  if d is None or d == "" or (not isinstance(d, str) and pd.isna(d)):
    return ""
  return date.fromisoformat(str(d)[:10]).strftime("%d/%m/%Y")


def estado_reforco(prox) -> str:
  if not prox:
    return "Sem reforço marcado"
  dias = (date.fromisoformat(str(prox)[:10]) - date.today()).days
  if dias < 0:
    return f"Atrasado há {-dias} dias"
  if dias <= 30:
    return f"A vencer em {dias} dias"
  return "Em dia"


def idade_txt(a) -> str:
  return calcular_idade_pet(date.fromisoformat(a["data_nascimento"]))[0] if a.get("data_nascimento") else ""


def do_animal(lista, aid):
  return [x for x in lista if x["animal_id"] == aid]


def ativos(registos):
  """Ignora os registos que foram corrigidos por um registo posterior."""
  subst = {r["substitui_id"] for r in registos if r.get("substitui_id")}
  return [r for r in registos if r["id"] not in subst]


def validacao_txt(r) -> str:
  if r.get("validado_por"):
    return f"Veterinário ({r.get('carimbo_digital_omv') or 'OMV'})"
  return "Tutor/Canil (não validado)"


def situacao_vacinal(registos_animal):
  """Último registo de cada produto (o mais recente de cada vacina/desparasitação)."""
  ultimo = {}
  for r in sorted(ativos(registos_animal), key=lambda r: r["data_aplicacao"]):
    ultimo[(r["tipo"], r["nome_produto"])] = r
  return sorted(ultimo.values(), key=lambda r: (r["tipo"], r["nome_produto"]))


def _mais_recente(regs, tipo):
  l = [r for r in regs if r["tipo"] == tipo]
  return max(l, key=lambda r: r["data_aplicacao"]) if l else None


def resumo_dfs(animais, registos, consultas, pesos):
  """Devolve (resumo por animal, situação por produto) com os dados mais recentes."""
  linhas, sit = [], []
  for a in animais:
    regs = ativos(do_animal(registos, a["id"]))
    ps = sorted(do_animal(pesos, a["id"]), key=lambda p: p["medido_em"])
    cs = do_animal(consultas, a["id"])
    vac, desp = _mais_recente(regs, "vacina"), _mais_recente(regs, "desparasitacao")
    sv = situacao_vacinal(regs)
    estados = [estado_reforco(r.get("proxima_dose")) for r in sv]
    linhas.append({
        "Nome": a["nome"], "Espécie": a["especie"], "Raça": a.get("raca") or "", "Sexo": a.get("sexo") or "",
        "Nascimento": fmt_d(a.get("data_nascimento")), "Idade": idade_txt(a), "Microchip": a.get("microchip") or "",
        "Último peso (kg)": float(ps[-1]["peso_kg"]) if ps else None, "Data do peso": fmt_d(ps[-1]["medido_em"]) if ps else "",
        "Última vacina": vac["nome_produto"] if vac else "", "Data da vacina": fmt_d(vac["data_aplicacao"]) if vac else "",
        "Última desparasitação": desp["nome_produto"] if desp else "", "Data da desparasitação": fmt_d(desp["data_aplicacao"]) if desp else "",
        "Última consulta": fmt_d(max(c["criado_at"] for c in cs)) if cs else "",
        "Reforços em atraso": sum(e.startswith("Atrasado") for e in estados),
        "Reforços a vencer (30 dias)": sum(e.startswith("A vencer") for e in estados),
        "Total de registos": len(regs) + len(cs),
    })
    for r in sv:
      sit.append({"Animal": a["nome"], "Tipo": "Vacina" if r["tipo"] == "vacina" else "Desparasitação", "Produto": r["nome_produto"],
                  "Última aplicação": fmt_d(r["data_aplicacao"]), "Próximo reforço": fmt_d(r.get("proxima_dose")),
                  "Estado": estado_reforco(r.get("proxima_dose")), "Lote": r.get("numero_lote") or "", "Validação": validacao_txt(r)})
  return pd.DataFrame(linhas), pd.DataFrame(sit)


def historico_dfs(animais, registos, consultas, pesos):
  nomes = {a["id"]: a["nome"] for a in animais}
  vac = []
  for r in sorted(ativos(registos), key=lambda r: r["data_aplicacao"], reverse=True):
    vac.append({"Animal": nomes.get(r["animal_id"], ""), "Data": fmt_d(r["data_aplicacao"]),
                "Tipo": "Vacina" if r["tipo"] == "vacina" else "Desparasitação", "Produto": r["nome_produto"],
                "Próximo reforço": fmt_d(r.get("proxima_dose")), "Lote": r.get("numero_lote") or "",
                "Validade do lote": fmt_d(r.get("data_validade")), "Fabricante": r.get("fabricante") or "",
                "Via": r.get("via_administracao") or "", "Peso (kg)": r.get("peso_clinico"), "Temperatura (°C)": r.get("temperatura_clinica"),
                "Validação": validacao_txt(r)})
  con = [{"Animal": nomes.get(c["animal_id"], ""), "Data": fmt_d(c["criado_at"]), "Anamnese": c.get("anamnese") or "",
          "Exames": c.get("exames_complementares") or "", "Prescrição": c.get("prescricao_medicamentosa") or "",
          "Carimbo": c.get("carimbo_digital") or ""}
         for c in sorted(consultas, key=lambda c: c["criado_at"], reverse=True)]
  pes = [{"Animal": nomes.get(p["animal_id"], ""), "Data": fmt_d(p["medido_em"]), "Peso (kg)": float(p["peso_kg"])}
         for p in sorted(pesos, key=lambda p: p["medido_em"], reverse=True)]
  return {"Vacinas e desparasitações": pd.DataFrame(vac), "Consultas": pd.DataFrame(con), "Pesos": pd.DataFrame(pes)}
