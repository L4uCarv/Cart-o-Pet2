"""Rastreio das ninhadas do Canil: filhotes, falecimentos, adoções e saúde antes da adoção."""
from collections import Counter
from datetime import date

import pandas as pd
import streamlit as st

from services.supabase_client import erro
from utils.exportar import para_excel
from views import componentes as c

ESTADOS = {"vivo": "🟢 Vivo", "reservado": "🟡 Reservado", "adotado": "🏡 Adotado", "falecido": "⚫ Falecido"}


def _d(v):
  return date.fromisoformat(str(v)[:10]) if v else None


def _data(v) -> str:
  return c.fmt(v) if v else ""


def _sn(b) -> str:
  return "Sim" if b else "Não"


def tabela_filhotes(fs) -> pd.DataFrame:
  return pd.DataFrame([{
      "Filhote": f["identificacao"], "Sexo": f.get("sexo") or "", "Cor": f.get("cor") or "", "Estado": ESTADOS[f["estado"]],
      "Adotante / reservado por": f.get("adotante_nome") or "", "Contacto": f.get("adotante_contacto") or "",
      "E-mail": f.get("adotante_email") or "", "Data da adoção": _data(f.get("data_adocao")),
      "Vacinado antes da adoção": _sn(f["vacinado_antes"]), "Data da vacina": _data(f.get("vacina_data")), "Vacina": f.get("vacina_detalhe") or "",
      "Desparasitado antes da adoção": _sn(f["desparasitado_antes"]), "Data da desparasitação": _data(f.get("desparasitacao_data")),
      "Desparasitação": f.get("desparasitacao_detalhe") or "",
      "Falecido em": _data(f.get("data_obito")), "Causa": f.get("causa_obito") or ""} for f in fs])


def _resumo(n, fs) -> pd.DataFrame:
  total, cont = n["quantidade_filhotes"], Counter(f["estado"] for f in fs)
  adotados = [f for f in fs if f["estado"] == "adotado"]
  m = st.columns(6)
  m[0].metric("Nascidos", total)
  m[1].metric("Vivos", cont["vivo"])
  m[2].metric("Reservados", cont["reservado"])
  m[3].metric("Adotados", cont["adotado"])
  m[4].metric("Falecidos", cont["falecido"])
  m[5].metric("Por registar", max(0, total - len(fs)))
  v = sum(f["vacinado_antes"] for f in adotados)
  d = sum(f["desparasitado_antes"] for f in adotados)
  if adotados:
    k1, k2 = st.columns(2)
    k1.metric("Adotados vacinados antes da adoção", f"{v} de {len(adotados)}")
    k2.metric("Adotados desparasitados antes da adoção", f"{d} de {len(adotados)}")
    sem = [f["identificacao"] for f in adotados if not f["vacinado_antes"] or not f["desparasitado_antes"]]
    if sem:
      st.warning("Adotados sem vacina ou sem desparasitação registada antes da adoção: " + ", ".join(sem))
  if cont["falecido"] and total:
    st.caption(f"Mortalidade da ninhada: {cont['falecido']} de {total} ({cont['falecido'] / total * 100:.0f}%).")
  return pd.DataFrame([{"Ninhada": n["nome_ninhada"], "Nascimento": c.fmt(n["data_nascimento"]), "Nascidos": total, "Registados": len(fs),
                        "Vivos": cont["vivo"], "Reservados": cont["reservado"], "Adotados": cont["adotado"], "Falecidos": cont["falecido"],
                        "Adotados vacinados antes": v, "Adotados desparasitados antes": d}])


def _nova_ninhada(sb, user_id, animais):
  rot = {a["id"]: f"{a['nome']} ({a['especie']})" for a in animais}
  femeas = [a["id"] for a in animais if a.get("sexo") == "Fêmea"]
  machos = [a["id"] for a in animais if a.get("sexo") == "Macho"]
  k = c.chave("nin")
  nome = st.text_input("Identificação da ninhada (ex.: Ninhada Luna)", key=f"nn_{k}")
  a1, a2, a3 = st.columns(3)
  nasc = a1.date_input("Data de nascimento", value=date.today(), max_value=date.today(), key=f"nd_{k}")
  qtd = a2.number_input("Nº de filhotes nascidos", 1, 30, 4, key=f"nq_{k}")
  mae = a3.selectbox("Mãe (opcional)", [None] + femeas, format_func=lambda i: "—" if i is None else rot[i], key=f"nm_{k}")
  pai = st.selectbox("Pai (opcional)", [None] + machos, format_func=lambda i: "—" if i is None else rot[i], key=f"np_{k}")
  obs = st.text_area("Observações", key=f"no_{k}")
  if st.button("Guardar ninhada", type="primary", key=f"ng_{k}"):
    if not nome.strip():
      st.warning("Indica a identificação da ninhada.")
      return
    try:
      novo = sb.table("ninhadas").insert({
          "tutor_id": user_id, "nome_ninhada": nome.strip(), "data_nascimento": nasc.isoformat(), "quantidade_filhotes": int(qtd),
          "observacoes": obs.strip() or None, "mae_id": mae, "pai_id": pai}).execute().data[0]
      st.session_state["ninhada_sel"] = novo["id"]
      c.aviso("Ninhada guardada. Regista agora os filhotes.")
      c.novo_formulario()
      st.rerun()
    except Exception as e:
      st.error(erro(e))


def _registar_filhotes(sb, n, fs):
  total, nid = n["quantidade_filhotes"], n["id"]
  existentes = {f["identificacao"] for f in fs}
  em_falta = [f"Filhote {i}" for i in range(1, total + 1) if f"Filhote {i}" not in existentes][: max(0, total - len(fs))]
  if em_falta and st.button(f"Criar os {len(em_falta)} filhotes em falta ({em_falta[0]}...)", key=f"fh_todos_{nid}"):
    try:
      sb.table("filhotes").insert([{"ninhada_id": nid, "identificacao": x} for x in em_falta]).execute()
      c.aviso("Filhotes criados. Agora podes indicar o sexo, a cor e o estado de cada um.")
      st.rerun()
    except Exception as e:
      st.error(erro(e))
  if len(fs) >= total:
    st.caption("Já registaste todos os filhotes desta ninhada.")
    return
  k = c.chave("fhn", nid)
  b1, b2, b3 = st.columns(3)
  ident = b1.text_input("Identificação (nome, coleira...)", key=f"fi_{k}")
  sexo = b2.selectbox("Sexo", ["", "Macho", "Fêmea"], key=f"fs_{k}")
  cor = b3.text_input("Cor", key=f"fc_{k}")
  if st.button("Adicionar filhote", key=f"fa_{k}"):
    if not ident.strip():
      st.warning("Indica a identificação do filhote.")
      return
    try:
      sb.table("filhotes").insert({"ninhada_id": nid, "identificacao": ident.strip(), "sexo": sexo or None, "cor": cor.strip() or None}).execute()
      c.aviso("Filhote registado.")
      c.novo_formulario()
      st.rerun()
    except Exception as e:
      st.error("Já existe um filhote com essa identificação." if "duplicate" in erro(e).lower() else erro(e))


def _editar_filhote(sb, n, f):
  k = c.chave("fh", f["id"])
  nasc = _d(n["data_nascimento"])
  aba_estado, aba_saude, aba_apagar = st.tabs(["📌 Estado e adoção", "💉 Saúde antes da adoção", "🗑️ Apagar"])

  with aba_estado:
    estado = st.selectbox("Estado", list(ESTADOS), index=list(ESTADOS).index(f["estado"]), format_func=ESTADOS.get, key=f"est_{k}")
    upd = {"estado": estado}
    if estado == "falecido":
      d1, d2 = st.columns(2)
      upd["data_obito"] = d1.date_input("Data do falecimento", value=_d(f.get("data_obito")) or date.today(), min_value=nasc,
                                        max_value=date.today(), key=f"dob_{k}").isoformat()
      upd["causa_obito"] = d2.text_input("Causa (opcional)", value=f.get("causa_obito") or "", key=f"cob_{k}").strip() or None
    if estado in ("adotado", "reservado"):
      upd["adotante_nome"] = st.text_input("Nome de quem adotou" if estado == "adotado" else "Reservado por",
                                           value=f.get("adotante_nome") or "", key=f"an_{k}").strip() or None
      e1, e2 = st.columns(2)
      upd["adotante_contacto"] = e1.text_input("Contacto (telefone)", value=f.get("adotante_contacto") or "", key=f"ac_{k}").strip() or None
      upd["adotante_email"] = e2.text_input("E-mail", value=f.get("adotante_email") or "", key=f"ae_{k}").strip() or None
      if estado == "adotado":
        upd["data_adocao"] = st.date_input("Data da adoção", value=_d(f.get("data_adocao")) or date.today(), min_value=nasc,
                                           max_value=date.today(), key=f"da_{k}").isoformat()
    if st.button("Guardar estado", type="primary", key=f"ges_{k}"):
      try:
        sb.table("filhotes").update(upd).eq("id", f["id"]).execute()
        c.aviso(f"{f['identificacao']}: estado guardado.")
        c.novo_formulario()
        st.rerun()
      except Exception as e:
        st.error(erro(e))

  with aba_saude:
    st.caption("Indica o que o filhote recebeu **antes de ir para o novo dono**. A data da vacina e da desparasitação tem de ser anterior à adoção.")
    vac = st.checkbox("Recebeu vacina antes da adoção", value=f["vacinado_antes"], key=f"vac_{k}")
    dvac, tvac = None, None
    if vac:
      v1, v2 = st.columns(2)
      dvac = v1.date_input("Data da vacina (ou da última)", value=_d(f.get("vacina_data")), min_value=nasc, max_value=date.today(), key=f"dv_{k}")
      tvac = v2.text_input("Vacina(s) (ex.: V10, 1.ª dose)", value=f.get("vacina_detalhe") or "", key=f"tv_{k}")
    desp = st.checkbox("Foi desparasitado antes da adoção", value=f["desparasitado_antes"], key=f"desp_{k}")
    ddesp, tdesp = None, None
    if desp:
      p1, p2 = st.columns(2)
      ddesp = p1.date_input("Data da desparasitação (ou da última)", value=_d(f.get("desparasitacao_data")), min_value=nasc,
                            max_value=date.today(), key=f"dd_{k}")
      tdesp = p2.text_input("Produto", value=f.get("desparasitacao_detalhe") or "", key=f"td_{k}")
    if st.button("Guardar saúde", type="primary", key=f"gsa_{k}"):
      try:
        sb.table("filhotes").update({
            "vacinado_antes": vac, "vacina_data": dvac.isoformat() if vac and dvac else None, "vacina_detalhe": (tvac or "").strip() or None,
            "desparasitado_antes": desp, "desparasitacao_data": ddesp.isoformat() if desp and ddesp else None,
            "desparasitacao_detalhe": (tdesp or "").strip() or None}).eq("id", f["id"]).execute()
        c.aviso(f"{f['identificacao']}: saúde guardada.")
        c.novo_formulario()
        st.rerun()
      except Exception as e:
        st.error(erro(e))

  with aba_apagar:
    st.caption("Apaga o registo deste filhote (por exemplo, se foi criado por engano). Não é possível desfazer.")
    ok = st.checkbox("Confirmo que quero apagar este filhote", key=f"delok_{k}")
    if st.button("Apagar filhote", disabled=not ok, key=f"del_{k}"):
      sb.table("filhotes").delete().eq("id", f["id"]).execute()
      c.aviso("Filhote apagado.")
      st.rerun()


def render_ninhadas(sb, user_id):
  ninhadas = sb.table("ninhadas").select("*").eq("tutor_id", user_id).order("data_nascimento", desc=True).execute().data
  animais = c.meus_animais(sb, user_id)
  with st.expander("➕ Nova ninhada", expanded=not ninhadas):
    _nova_ninhada(sb, user_id, animais)
  if not ninhadas:
    return

  rot = {n["id"]: f"{n['nome_ninhada']} · {c.fmt(n['data_nascimento'])}" for n in ninhadas}
  if st.session_state.get("ninhada_sel") not in rot:
    st.session_state.pop("ninhada_sel", None)
  nid = st.selectbox("Ninhada", list(rot), format_func=rot.get, key="ninhada_sel")
  n = next(x for x in ninhadas if x["id"] == nid)
  nomes = {a["id"]: a["nome"] for a in animais}
  pais = " · ".join(x for x in [f"Mãe: {nomes[n['mae_id']]}" if n.get("mae_id") in nomes else "",
                                f"Pai: {nomes[n['pai_id']]}" if n.get("pai_id") in nomes else ""] if x)
  if pais:
    st.caption(pais)

  fs = sb.table("filhotes").select("*").eq("ninhada_id", nid).order("criado_at").execute().data
  resumo = _resumo(n, fs)
  st.markdown("**Rastreio dos filhotes**")
  if fs:
    tabela = tabela_filhotes(fs)
    st.dataframe(tabela, use_container_width=True, hide_index=True)
    st.download_button("⬇️ Exportar rastreio (Excel)", para_excel({"Resumo": resumo, "Filhotes": tabela}),
                       file_name=f"ninhada_{n['nome_ninhada'].lower().replace(' ', '_')}_{date.today().isoformat()}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"nin_xlsx_{nid}")
  else:
    st.info("Ainda não há filhotes registados nesta ninhada.")

  with st.expander("➕ Registar filhotes", expanded=not fs):
    _registar_filhotes(sb, n, fs)
  if fs:
    st.markdown("**Atualizar um filhote**")
    rf = {f["id"]: f"{f['identificacao']} · {ESTADOS[f['estado']]}" for f in fs}
    chave_f = f"filhote_sel_{nid}"
    if st.session_state.get(chave_f) not in rf:
      st.session_state.pop(chave_f, None)
    fid = st.selectbox("Filhote", list(rf), format_func=rf.get, key=chave_f)
    _editar_filhote(sb, n, next(x for x in fs if x["id"] == fid))
