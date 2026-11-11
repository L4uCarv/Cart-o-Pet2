import streamlit as st

from views import componentes as c


def render_tutor_dashboard(sb):
  user_id, email = st.session_state["user_id"], st.session_state["user_email"]
  st.title("🐾 Os meus animais")

  c.caixa_convites(sb)
  c.caixa_transferencias(sb, user_id, email)
  animais = c.meus_animais(sb, user_id)

  aba1, aba2, aba3 = st.tabs(["🐶 Animais e saúde", "💳 Pagamentos", "🏥 Pedir conta Canil / Veterinário"])
  with aba1:
    with st.expander("➕ Registar novo animal", expanded=not animais):
      c.registar_animal(sb, user_id)
    c.painel_animal(sb, animais, user_id)
  with aba2:
    c.pagamentos(sb, user_id)
  with aba3:
    c.pedido_credenciamento(sb, user_id)
