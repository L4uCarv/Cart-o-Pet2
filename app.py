import os
import streamlit as st
from services.supabase_client import supabase

# Importação das vistas modulares
from views.admin_view import render_admin_dashboard
from views.auth_view import render_auth_sidebar
from views.clinica_view import render_clinica_dashboard
from views.criador_view import render_criador_dashboard
from views.tutor_view import render_tutor_dashboard

# Configuração da Página
st.set_page_config(
    page_title="CartãoPet V2 - Plataforma Veterinária Integrada",
    page_icon="🐾",
    layout="wide",
)


# Carregar CSS Externo
def load_css(file_name):
  if os.path.exists(file_name):
    with open(file_name) as f:
      st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


load_css("assets/style.css")

# --- GESTÃO DE SESSÃO ---
if "utilizador" not in st.session_state:
  st.session_state["utilizador"] = None
if "papel" not in st.session_state:
  st.session_state["papel"] = None
if "user_id" not in st.session_state:
  st.session_state["user_id"] = None
if "mfa_validado" not in st.session_state:
  st.session_state["mfa_validado"] = False

# --- BARRA LATERAL (AUTENTICAÇÃO) ---
render_auth_sidebar(supabase)

# --- ROUTER PRINCIPAL ---
if st.session_state["utilizador"] is None:
  st.title("🛡️ CartãoPet V2: Plataforma de Gestão Veterinária")
  st.info(
      "👈 Efetue login ou registe uma nova conta na barra lateral para aceder"
      " aos recursos do sistema."
  )

elif (
    st.session_state["papel"] in ["super_admin", "financeiro", "moderador"]
    and not st.session_state["mfa_validado"]
):
  st.warning(
      "🔒 Acesso restrito. Conclua a validação de Autenticação Multifator (MFA)"
      " na barra lateral para continuar."
  )

else:
  papel = st.session_state["papel"]

  # Direcionamento por Papel (RBAC)
  if papel in ["super_admin", "financeiro", "moderador"]:
    render_admin_dashboard(supabase, papel)
  elif papel == "criador":
    render_criador_dashboard(supabase)
  elif papel == "clinica":
    render_clinica_dashboard(supabase)
  else:
    render_tutor_dashboard(supabase)