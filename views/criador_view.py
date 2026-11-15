import re
import unicodedata

import pandas as pd
import streamlit as st

from services.supabase_client import erro
from views import componentes as c
from views.ninhadas import render_ninhadas


def _norm(texto) -> str:
  t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
  return t.lower().strip()


def _alnum(texto) -> str:
  return re.sub(r"[^a-z0-9]", "", _norm(texto))


def render_criador_dashboard(sb):
  user_id = st.session_state["user_id"]
  st.title("🧬 Painel do Canil")

  aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs([
      "🐕 Os meus animais", "👥 Membros do canil", "🏡 Animais dos membros",
      "🍼 Ninhadas", "💳 Pagamentos", "📄 Relatórios",
  ])

  with aba1:
    c.caixa_transferencias(sb, user_id, st.session_state["user_email"])
    animais = c.meus_animais(sb, user_id)
    with st.expander("➕ Registar novo animal", expanded=not animais):
      c.registar_animal(sb, user_id)
    c.previsoes_cio(sb, animais)
    c.painel_animal(sb, animais, user_id)

  with aba2:
    st.caption("Até 4 membros, cada um com até 10 animais. O membro tem de aceitar o convite.")
    email = st.text_input("E-mail da conta do membro", key="conv_email")
    if st.button("Convidar membro", key="conv_btn"):
      try:
        sb.rpc("convidar_membro_canil", {"p_email": email}).execute()
        c.aviso("Convite enviado.")
        st.rerun()
      except Exception as e:
        st.error(erro(e))
    membros = sb.rpc("listar_membros_canil").execute().data or []
    if membros:
      df = pd.DataFrame(membros).rename(columns={"nome": "Nome", "email": "E-mail", "aceite": "Aceitou", "n_animais": "Animais"})
      st.dataframe(df[["Nome", "E-mail", "Aceitou", "Animais"]], use_container_width=True, hide_index=True)
      remover = st.selectbox("Remover membro", membros, format_func=lambda m: m["nome"], key="rem_sel")
      if st.button("Remover", key="rem_btn"):
        sb.table("membros_canil").delete().eq("membro_id", remover["membro_id"]).execute()
        c.aviso("Membro removido.")
        st.rerun()

  with aba3:
    st.caption("Consulta (só leitura) dos animais dos membros que aceitaram o convite.")
    membros_dados = sb.rpc("listar_membros_canil").execute().data or []
    nomes = {m["membro_id"]: m["nome"] for m in membros_dados}
    dos_membros = (
        sb.table("animais").select("*").neq("tutor_id", user_id)
        .is_("arquivado_em", "null").order("nome").execute().data
    )
    busca = st.text_input("🔎 Pesquisar por nome do animal ou microchip", key="busca_membros")
    q, qc = _norm(busca), _alnum(busca)
    filtrados = [a for a in dos_membros if not q or q in _norm(a["nome"]) or (qc and qc in _alnum(a.get("microchip")))]
    if dos_membros:
      st.caption(f"{len(filtrados)} de {len(dos_membros)} animais")
    if dos_membros and not filtrados:
      st.info("Nenhum animal corresponde à pesquisa.")
    if filtrados:
      st.dataframe(pd.DataFrame([{
          "Animal": a["nome"], "Espécie": a["especie"], "Raça": a.get("raca") or "", "Sexo": a.get("sexo") or "",
          "Microchip": a.get("microchip") or "", "Membro": nomes.get(a["tutor_id"], "")} for a in filtrados]),
          use_container_width=True, hide_index=True)
    c.previsoes_cio(sb, filtrados, nomes_donos=nomes)
    c.painel_animal(sb, filtrados, user_id, dono=False, nomes_donos=nomes)

  with aba4:
    render_ninhadas(sb, user_id)

  with aba5:
    c.pagamentos(sb, user_id)

  with aba6:
    c.relatorios_pets(sb, c.meus_animais(sb, user_id), st.session_state["user_nome"])
