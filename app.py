from datetime import date
from pathlib import Path

import streamlit as st

from services.supabase_client import cliente, erro

st.set_page_config(page_title="CartãoPet", page_icon="🐾", layout="wide")

css = Path(__file__).parent / "assets" / "style.css"
if css.exists():
  st.markdown(f"<style>{css.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

sb = cliente()  # um cliente por sessão (ver services/supabase_client.py)
if "user_id" not in st.session_state:
  st.session_state["user_id"] = None

if "flash" in st.session_state:
  st.success(st.session_state.pop("flash"))


def carregar_perfil(user):
  dados = sb.table("perfis").select("nome, papel, subscricao_valida_ate").eq("id", user.id).execute().data
  if not dados:
    raise RuntimeError("Perfil não encontrado. Contacta a administração.")
  st.session_state.update(
      user_id=user.id, user_email=user.email,
      user_nome=dados[0]["nome"], papel=dados[0]["papel"],
      subscricao_ate=dados[0].get("subscricao_valida_ate"),
  )


st.sidebar.title("🐾 CartãoPet")

if not st.session_state["user_id"]:
  modo = st.sidebar.radio("Modo", ["Entrar", "Criar conta"])
  with st.sidebar.form("form_auth"):
    nome = st.text_input("Nome completo") if modo == "Criar conta" else ""
    email = st.text_input("E-mail")
    senha = st.text_input("Palavra-passe (mín. 8 caracteres)", type="password")
    ok = st.form_submit_button("Entrar" if modo == "Entrar" else "Criar conta")
  if ok:
    try:
      if modo == "Entrar":
        carregar_perfil(sb.auth.sign_in_with_password({"email": email.strip(), "password": senha}).user)
        st.rerun()
      else:
        if not nome.strip() or len(senha) < 8:
          st.sidebar.warning("Indica o nome e uma palavra-passe com 8 ou mais caracteres.")
        else:
          res = sb.auth.sign_up({
              "email": email.strip(), "password": senha,
              "options": {"data": {"nome": nome.strip()}},  # o servidor cria o perfil
          })
          if res.session:
            carregar_perfil(res.user)
            st.rerun()
          else:
            st.sidebar.success("Conta criada. Confirma o e-mail e depois entra.")
    except Exception as e:
      st.sidebar.error(erro(e))
  st.title("🐾 CartãoPet")
  st.info("Entra ou cria uma conta na barra lateral. Todas as contas começam como **Tutor**; "
          "as contas Canil e Veterinário pedem-se depois, dentro da app, e são aprovadas pela administração.")
  st.stop()

st.sidebar.info(f"**{st.session_state['user_nome']}**\n\n{st.session_state['user_email']}\n\nPerfil: **{st.session_state['papel'].upper()}**")
if st.session_state["papel"] in ("tutor", "criador", "clinica"):
  ate = st.session_state.get("subscricao_ate")
  if ate and date.fromisoformat(ate) >= date.today():
    st.sidebar.success(f"Subscrição ativa até {date.fromisoformat(ate).strftime('%d/%m/%Y')}")
  else:
    st.sidebar.warning("Sem subscrição ativa")
if st.sidebar.button("🔄 Atualizar perfil"):
  carregar_perfil(sb.auth.get_user().user)
  st.rerun()
if st.sidebar.button("Terminar sessão", type="primary"):
  try:
    sb.auth.sign_out()
  finally:
    st.session_state.clear()
    st.rerun()

papel = st.session_state["papel"]
if papel == "tutor":
  from views.tutor_view import render_tutor_dashboard
  render_tutor_dashboard(sb)
elif papel == "criador":
  from views.criador_view import render_criador_dashboard
  render_criador_dashboard(sb)
elif papel == "clinica":
  from views.clinica_view import render_clinica_dashboard
  render_clinica_dashboard(sb)
elif papel in ("super_admin", "financeiro"):
  from views.admin_view import render_admin_dashboard
  render_admin_dashboard(sb, papel)
else:
  st.warning(f"Perfil sem painel disponível: {papel}")
