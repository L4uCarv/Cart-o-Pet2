from datetime import date

import pandas as pd
import streamlit as st

from services.supabase_client import erro
from views import componentes as c


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
    dos_membros = (
        sb.table("animais").select("*").neq("tutor_id", user_id)
        .is_("arquivado_em", "null").order("nome").execute().data
    )
    c.painel_animal(sb, dos_membros, user_id, dono=False)

  with aba4:
    with st.form("form_ninhada", clear_on_submit=True):
      nome = st.text_input("Identificação da ninhada (ex.: Ninhada Luna)")
      nasc = st.date_input("Data de nascimento", value=date.today(), max_value=date.today())
      qtd = st.number_input("Número de filhotes", 1, 20, 4)
      obs = st.text_area("Observações")
      if st.form_submit_button("Guardar ninhada"):
        try:
          sb.table("ninhadas").insert({
              "tutor_id": user_id, "nome_ninhada": nome.strip(),
              "data_nascimento": nasc.isoformat(), "quantidade_filhotes": int(qtd),
              "observacoes": obs.strip() or None,
          }).execute()
          st.success("Ninhada guardada.")
        except Exception as e:
          st.error(erro(e))
    ninhadas = sb.table("ninhadas").select("nome_ninhada, data_nascimento, quantidade_filhotes").eq("tutor_id", user_id).order("data_nascimento", desc=True).execute().data
    if ninhadas:
      st.dataframe(pd.DataFrame(ninhadas), use_container_width=True, hide_index=True)

  with aba5:
    c.pagamentos(sb, user_id)

  with aba6:
    c.relatorios_pets(sb, c.meus_animais(sb, user_id), st.session_state["user_nome"])
