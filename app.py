import streamlit as st
from supabase import create_client
import os

# Configuração da página
st.set_page_config(
    page_title="CartãoPet V2 - Plataforma de Gestão Veterinária",
    page_icon="🐾",
    layout="wide"
)

# Inicializar cliente Supabase usando os secrets do Streamlit
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Inicializar variáveis de sessão
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "user_papel" not in st.session_state:
    st.session_state.user_papel = None

# Barra Lateral para Autenticação
st.sidebar.image("https://img.icons8.com/color/96/pet-commands-train.png", width=80)
st.sidebar.title("CartãoPet V2")

if not st.session_state.user_id:
    st.sidebar.subheader("🔒 Autenticação de Sistema")
    modo = st.sidebar.radio("Modo", ["Entrar (Login)", "Registar Conta"])

    if modo == "Entrar (Login)":
        with st.sidebar.form("form_login"):
            email = st.text_input("Email")
            senha = st.text_input("Senha", type="password")
            submitted_login = st.form_submit_button("Aceder")

            if submitted_login:
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                    user = res.user
                    
                    if user:
                        st.session_state.user_id = user.id
                        st.session_state.user_email = user.email
                        
                        # Buscar o papel do utilizador na tabela public.perfis
                        perfil_res = supabase.table("perfis").select("papel").eq("id", user.id).execute()
                        if perfil_res.data:
                            st.session_state.user_papel = perfil_res.data[0]["papel"]
                        else:
                            st.session_state.user_papel = "tutor" # Papel por defeito
                            
                        st.success("Sessão iniciada com sucesso!")
                        st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Erro no login: {e}")

    else: # Registar Conta
        with st.sidebar.form("form_registo"):
            nome = st.text_input("Nome Completo")
            email = st.text_input("Email de Registo")
            senha = st.text_input("Senha (mín. 6 caracteres)", type="password")
            papel_escolhido = st.selectbox(
                "Perfil de Utilizador", 
                ["tutor", "criador", "clinica"],
                format_func=lambda x: {"tutor": "Tutor / Dono de Pet", "criador": "Criador / Canil", "clinica": "Clínica Veterinária"}[x]
            )
            submitted_registo = st.form_submit_button("Criar Conta & Entrar")

            if submitted_registo:
                if not nome or not email or not senha:
                    st.sidebar.warning("Por favor, preencha todos os campos.")
                else:
                    try:
                        # 1. Registar o utilizador no sistema de Auth do Supabase
                        res = supabase.auth.sign_up({"email": email, "password": senha})
                        user = res.user
                        
                        if user:
                            # 2. Criar automaticamente o registo correspondente na tabela publica perfis
                            supabase.table("perfis").insert({
                                "id": user.id,
                                "nome": nome,
                                "email": email,
                                "papel": papel_escolhido
                            }).execute()

                            # 3. INICIAÇÃO AUTOMÁTICA DA SESSÃO
                            st.session_state.user_id = user.id
                            st.session_state.user_email = user.email
                            st.session_state.user_papel = papel_escolhido
                            
                            st.sidebar.success("Conta criada e sessão iniciada com sucesso!")
                            st.rerun()
                    except Exception as e:
                        st.sidebar.error(f"Erro na autenticação: {e}")

else:
    # Se já estiver autenticado, mostra botão de Terminar Sessão na barra lateral
    st.sidebar.info(f"Conectado como:\n**{st.session_state.user_email}**\n*(Perfil: {st.session_state.user_papel.upper()})*")
    if st.sidebar.button("Terminar Sessão", type="primary"):
        supabase.auth.sign_out()
        st.session_state.user_id = None
        st.session_state.user_email = None
        st.session_state.user_papel = None
        st.rerun()

# Router Principal com base no Perfil do Utilizador
if not st.session_state.user_id:
    st.title("🐾 CartãoPet V2: Plataforma de Gestão Veterinária")
    st.info("👈 Efetue login ou registe uma nova conta na barra lateral para aceder aos recursos do sistema.")
else:
    papel = st.session_state.user_papel
    
    if papel == "tutor":
        try:
            from views.tutor_view import render_tutor_dashboard
            render_tutor_dashboard(supabase)
        except ImportError as e:
            st.error(f"Erro ao carregar o painel do tutor: {e}")
            
    elif papel == "clinica":
        try:
            from views.clinica_view import render_clinica_dashboard
            render_clinica_dashboard(supabase)
        except ImportError as e:
            st.error(f"Erro ao carregar o painel da clínica: {e}")
            
    elif papel == "criador":
        try:
            from views.criador_view import render_criador_dashboard
            render_criador_dashboard(supabase)
        except ImportError as e:
            st.error(f"Erro ao carregar o painel do criador: {e}")
            
    else:
        st.warning(f"Perfil desconhecido ou não configurado: {papel}")
