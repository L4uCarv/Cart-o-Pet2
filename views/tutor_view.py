import base64
import calendar
import io
import os
import unicodedata
from datetime import date, datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image
from postgrest.exceptions import APIError
import streamlit as st
from supabase import create_client

st.set_page_config(
    page_title="Sistema Integrado de Saúde Pet",
    page_icon="🐾",
    layout="wide",
)

# ==============================================================================
# 1. LEITURA DE SEGREDOS & CLIENTE SUPABASE
# ==============================================================================
def obter_secret_ou_env(chave, fallback=None):
    if hasattr(st, "secrets"):
        try:
            valor = st.secrets.get(chave)
            if valor is not None:
                return valor
        except Exception:
            pass
    if isinstance(fallback, dict):
        return fallback.get(chave)
    return os.environ.get(chave, fallback)

SUPABASE_URL = obter_secret_ou_env("supabase", {}).get("url") if isinstance(obter_secret_ou_env("supabase", {}), dict) else obter_secret_ou_env("SUPABASE_URL")
SUPABASE_KEY = obter_secret_ou_env("supabase", {}).get("key") if isinstance(obter_secret_ou_env("supabase", {}), dict) else obter_secret_ou_env("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ Configuração ausente: defina SUPABASE_URL e SUPABASE_KEY (ou as chaves em secrets.toml).")
    st.stop()

@st.cache_resource
def get_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = get_supabase_client()
except Exception as exc:
    supabase = None
    st.error(f"⚠️ Não foi possível estabelecer a ligação ao Supabase. Detalhe: {exc}")
    st.stop()

PERFIS_VALIDOS = {"Tutor", "Criador", "Clinica", "ADMINISTRADOR"}

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

# ==============================================================================
# 2. ESTILIZAÇÃO CSS
# ==============================================================================
st.markdown(
    """
    <style>
    .stApp {
        background-color: #FAF8F5;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        color: #000000 !important;
    }
    .stApp p,
    .stApp label,
    .stApp [data-testid="stMarkdownContainer"],
    .stApp [data-testid="stWidgetLabel"],
    .stApp [data-baseweb="select"] * {
        color: #000000 !important;
    }
    div.stButton > button:first-child {
        background-color: #4E877C !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    div.stButton > button:first-child:hover {
        background-color: #3B6B62 !important;
        color: #FFFFFF !important;
    }
    div.stButton > button[kind="primary"] {
        background-color: #D47A5B !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #C06649 !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF;
        border: 1px solid #E2DBD0 !important;
        border-radius: 12px !important;
    }
    h1, h2, h3, h4 {
        color: #000000 !important;
        font-weight: 700 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# 3. FUNÇÕES AUXILIARES & CÁLCULOS
# ==============================================================================
def normalizar_texto(value):
    if value is None:
        return ""
    return unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii").strip().lower()

def normalizar_tipo_perfil(valor):
    if valor is None:
        return "Tutor"
    chave = normalizar_texto(valor).replace(" ", "").replace("_", "")
    mapa = {
        "admin": "ADMINISTRADOR",
        "administrador": "ADMINISTRADOR",
        "tutor": "Tutor",
        "criador": "Criador",
        "clinica": "Clinica",
        "clínica": "Clinica",
        "clinicaveterinaria": "Clinica",
        "veterinaria": "Clinica",
    }
    valor_normalizado = mapa.get(chave, str(valor).strip())
    if valor_normalizado not in PERFIS_VALIDOS:
        return "Tutor"
    return valor_normalizado

def validar_email(email):
    if not email or not isinstance(email, str):
        return False
    email = email.strip()
    return "@" in email and "." in email.split("@")[-1]

def validar_senha(senha, min_len=6):
    if not isinstance(senha, str):
        return False
    return len(senha.strip()) >= min_len

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)

def limpar_texto(value, default=""):
    if value is None:
        return default
    if not isinstance(value, str):
        value = str(value)
    valor_limpo = value.strip()
    return valor_limpo if valor_limpo else default

def preparar_sessao_autenticacao(usuario, sessao):
    if usuario is not None:
        st.session_state.usuario = usuario
    if sessao is not None:
        st.session_state.access_token = sessao.access_token
        st.session_state.refresh_token = sessao.refresh_token
        supabase.postgrest.auth(sessao.access_token)

def carregar_perfil_usuario(user_id):
    if not user_id:
        return {}
    try:
        perfil_res = supabase.table("tutores").select("*").eq("id", user_id).execute()
        if perfil_res.data:
            perfil = perfil_res.data[0]
            perfil["tipo_perfil"] = normalizar_tipo_perfil(perfil.get("tipo_perfil"))
            return perfil
    except APIError as exc:
        if "JWT expired" in str(exc) or "401" in str(exc):
            st.session_state.clear()
            st.warning("A sua sessão expirou. Por favor, inicie sessão novamente.")
            st.rerun()
    return {}

def guardar_sessao_apos_login(usuario, sessao):
    preparar_sessao_autenticacao(usuario, sessao)
    st.session_state.perfil = carregar_perfil_usuario(usuario.id if usuario else None)
    st.session_state.pop("cache_pets", None)

def encerrar_sessao():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    st.session_state.clear()
    st.rerun()

def mensagem_erro_api(exc, fallback="Não foi possível completar a operação no momento."):
    if exc is None:
        return fallback
    texto = str(exc).lower()
    if "jwt expired" in texto or "unauthorized" in texto or "401" in texto:
        return "A sessão expirou. Inicie sessão novamente."
    if "duplicate" in texto or "already exists" in texto:
        return "Já existe um registo com estes dados."
    if "not found" in texto or "404" in texto:
        return "O registo solicitado não foi encontrado."
    return fallback

def executar_consulta(segura, fallback=None, mensagem_padrao="Não foi possível completar a operação no momento."):
    try:
        return segura()
    except APIError as exc:
        st.warning(mensagem_erro_api(exc, mensagem_padrao))
        return fallback
    except Exception as exc:
        st.warning(mensagem_erro_api(exc, mensagem_padrao))
        return fallback

def garantir_autenticacao_ativa():
    refresh_token = st.session_state.get("refresh_token")
    if refresh_token:
        try:
            res = supabase.auth.refresh_session(refresh_token)
            if res and getattr(res, "session", None):
                st.session_state.access_token = res.session.access_token
                st.session_state.refresh_token = res.session.refresh_token
                supabase.postgrest.auth(res.session.access_token)
                return True
        except Exception:
            st.session_state.pop("refresh_token", None)
    access_token = st.session_state.get("access_token")
    if access_token:
        try:
            supabase.postgrest.auth(access_token)
            return True
        except Exception:
            st.session_state.pop("access_token", None)
    return False

def obter_meses_idade(data_nascimento_str):
    try:
        data_nasc = datetime.strptime(str(data_nascimento_str), "%Y-%m-%d").date()
        hoje = date.today()
        return (hoje.year - data_nasc.year) * 12 + (hoje.month - data_nasc.month)
    except Exception:
        return 0

def calcular_idade(data_nascimento_str):
    try:
        data_nasc = datetime.strptime(str(data_nascimento_str), "%Y-%m-%d").date()
        hoje = date.today()
        anos = hoje.year - data_nasc.year
        meses = hoje.month - data_nasc.month
        dias = hoje.day - data_nasc.day
        if dias < 0:
            meses -= 1
        if meses < 0:
            anos -= 1
            meses += 12
        total_meses = (anos * 12) + meses
        if total_meses < 1:
            return f"{(hoje - data_nasc).days} dia(s)"
        elif anos < 1:
            return f"{meses} mês(es)"
        else:
            return f"{anos} ano(s)" if meses == 0 else f"{anos} ano(s) e {meses} m."
    except Exception:
        return "Idade Não Informada"

def calcular_idade_humana_equivalente(meses_idade, peso=0.0):
    if meses_idade <= 1:
        return "1 ano"
    elif meses_idade <= 3:
        return "3 a 4 anos"
    elif meses_idade <= 6:
        return "8 a 10 anos (Infância)"
    elif meses_idade <= 12:
        return "14 a 16 anos (Adolescência)"
    elif meses_idade <= 24:
        return "22 a 24 anos (Jovem Adulto)"
    else:
        anos_cao = meses_idade / 12.0
        if peso > 45:
            mult = 7.5
        elif peso > 25:
            mult = 6.0
        elif peso > 10:
            mult = 5.0
        else:
            mult = 4.0
        idade_h = 24 + int((anos_cao - 2) * mult)
        return f"~{idade_h} anos humanos"

def calcular_previsao_primeiro_cio(data_nascimento_str):
    try:
        return datetime.strptime(str(data_nascimento_str), "%Y-%m-%d").date() + timedelta(days=180)
    except Exception:
        return date.today()

def calcular_data_parto(data_cruzamento):
    return data_cruzamento + timedelta(days=63)

def sugerir_proxima_vacina(nome_vacina, data_ap, meses_idade):
    info = INFO_VACINAS.get(nome_vacina)
    if not info:
        return data_ap + timedelta(days=21)
    if meses_idade < 4 and "Antirrábica" not in nome_vacina:
        return data_ap + timedelta(days=info["intervalo_filhote"])
    return data_ap + timedelta(days=info["intervalo_adulto"])

def sugerir_proxima_desparasitacao(tipo_tratamento, data_ap, meses_idade):
    if "Externa" in tipo_tratamento:
        return data_ap + timedelta(days=30)
    elif meses_idade < 6:
        return data_ap + timedelta(days=15)
    else:
        return data_ap + timedelta(days=90)

def carregar_imagem_base64(uploaded_file):
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        base64_str = base64.b64encode(bytes_data).decode()
        return f"data:{uploaded_file.type};base64,{base64_str}"
    return None

def carregar_lista_pets(user_id, tipo_perfil):
    if not user_id and tipo_perfil != "ADMINISTRADOR":
        return []

    def consulta():
        if tipo_perfil == "Clinica":
            return supabase.table("pets").select("*").execute().data or []
        return supabase.table("pets").select("*").eq("tutor_id", user_id).execute().data or []

    return executar_consulta(consulta, fallback=[], mensagem_padrao="Não foi possível carregar os pets neste momento.")

def obter_dados_pet(pet_id):
    garantir_autenticacao_ativa()
    try:
        if f"vacinas_{pet_id}" not in st.session_state:
            st.session_state[f"vacinas_{pet_id}"] = supabase.table("vacinas").select("*").eq("pet_id", pet_id).order("data_aplicacao", desc=True).execute().data or []
        if f"desps_{pet_id}" not in st.session_state:
            st.session_state[f"desps_{pet_id}"] = supabase.table("desparasitacoes").select("*").eq("pet_id", pet_id).order("data_aplicacao", desc=True).execute().data or []
        return st.session_state[f"vacinas_{pet_id}"], st.session_state[f"desps_{pet_id}"]
    except APIError as e:
        if "JWT expired" in str(e):
            st.session_state.clear()
            st.warning("Sessão expirada. Por favor, entre novamente.")
            st.rerun()
        return [], []

def invalidar_cache_pet(pet_id):
    st.session_state.pop(f"vacinas_{pet_id}", None)
    st.session_state.pop(f"desps_{pet_id}", None)
    st.session_state.pop(f"reps_{pet_id}", None)
    st.session_state.pop(f"ninhadas_{pet_id}", None)

# ==============================================================================
# 4. DIALOGS (JANELAS FLUTUANTES)
# ==============================================================================
@st.dialog("✏️ Editar Perfil do Pet")
def modal_editar_pet(pet_obj):
    st.markdown(f"Alterar dados cadastrais de **{pet_obj['nome']}**:")
    
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        e_nome = st.text_input("Nome Pet:", value=pet_obj["nome"], key="ed_pet_nome")
        e_raca = st.text_input("Raça:", value=pet_obj.get("raca", "SRD"), key="ed_pet_raca")
        dt_val = datetime.strptime(str(pet_obj["data_nascimento"]), "%Y-%m-%d").date() if pet_obj.get("data_nascimento") else date.today()
        e_nasc = st.date_input("Data de Nascimento:", value=dt_val, key="ed_pet_nasc")
    with col_e2:
        lista_sexos = ["Fêmea", "Macho"]
        idx_sexo = lista_sexos.index(pet_obj.get("sexo", "Fêmea")) if pet_obj.get("sexo") in lista_sexos else 0
        e_sexo = st.selectbox("Sexo:", lista_sexos, index=idx_sexo, key="ed_pet_sexo")
        
        lista_pelos = ["Curto", "Longo", "Ondulado", "Liso"]
        idx_pelo = lista_pelos.index(pet_obj.get("pelo", "Curto")) if pet_obj.get("pelo") in lista_pelos else 0
        e_pelo = st.selectbox("Tipo de Pêlo:", lista_pelos, index=idx_pelo, key="ed_pet_pelo")
        e_peso = st.number_input("Peso Atual (kg):", value=float(pet_obj.get("peso_atual", 0.0)), step=0.1, min_value=0.0, key="ed_pet_peso")

    e_foto = st.file_uploader("Alterar Foto (opcional):", type=["png", "jpg", "jpeg"], key="ed_pet_foto")

    if st.button("Salvar Alterações", type="primary", use_container_width=True, key="btn_save_ed_pet"):
        garantir_autenticacao_ativa()
        dados_up = {
            "nome": e_nome,
            "raca": e_raca,
            "data_nascimento": str(e_nasc),
            "sexo": e_sexo,
            "pelo": e_pelo,
            "peso_atual": e_peso,
        }
        if e_foto:
            dados_up["foto_url"] = carregar_imagem_base64(e_foto)

        supabase.table("pets").update(dados_up).eq("id", pet_obj["id"]).execute()
        st.session_state.pop("cache_pets", None)
        invalidar_cache_pet(pet_obj["id"])
        st.success("Perfil do pet atualizado com sucesso!")
        st.rerun()

@st.dialog("⚠️ Confirmar Exclusão")
def modal_eliminar_pet(pet_obj):
    st.error(f"Tem a certeza de que deseja eliminar o perfil de **{pet_obj['nome']}**?")
    st.caption("Esta ação apagará permanentemente todos os registros de vacinas, desparasitações e histórico reprodutivo deste animal.")
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if st.button("Sim, Eliminar", type="primary", use_container_width=True, key="btn_conf_del"):
            garantir_autenticacao_ativa()
            supabase.table("pets").delete().eq("id", pet_obj["id"]).execute()
            st.session_state.pop("cache_pets", None)
            invalidar_cache_pet(pet_obj["id"])
            if st.session_state.get("pet_selecionado_id") == pet_obj["id"]:
                st.session_state.pet_selecionado_id = None
            st.success("Perfil eliminado com sucesso!")
            st.rerun()
    with col_d2:
        if st.button("Cancelar", use_container_width=True, key="btn_canc_del"):
            st.rerun()

@st.dialog("📝 Lançar Nova Vacina")
def modal_editar_vacina(pet_obj):
    st.markdown(f"Registar nova aplicação para **{pet_obj['nome']}**:")
    v_escolha = st.selectbox("Escolha a vacina:", ["-- Selecione uma vacina --"] + list(INFO_VACINAS.keys()), index=0, key="m_v_sel_vazia")
    
    chk_selecionados = []
    if v_escolha != "-- Selecione uma vacina --":
        st.write("**Doenças Prevenidas:**")
        doencas = INFO_VACINAS[v_escolha]["doencas"]
        colunas_doencas = st.columns(min(3, len(doencas)))
        for indice, doenca in enumerate(doencas):
            with colunas_doencas[indice % len(colunas_doencas)]:
                if st.checkbox(doenca, value=True, key=f"m_chk_v_{doenca}"):
                    chk_selecionados.append(doenca)
                
    c1, c2 = st.columns(2)
    with c1:
        d_ap = st.date_input("Data da Aplicação", date.today(), key="m_v_ap_vazia")
        v_vinheta = st.text_input("Vinheta (L/Val)", key="m_v_vinheta")
    with c2:
        meses = obter_meses_idade(pet_obj["data_nascimento"])
        d_sug = sugerir_proxima_vacina(v_escolha, d_ap, meses) if v_escolha != "-- Selecione uma vacina --" else date.today() + timedelta(days=21)
        d_px = st.date_input("Data Prevista para a Próxima", d_sug, key="m_v_px_vazia")
        v_aplicador = st.text_input("Aplicador", key="m_v_aplicador")
        
    if st.button("Gravar", type="primary", use_container_width=True, key="btn_modal_save_v"):
        if v_escolha != "-- Selecione uma vacina --":
            garantir_autenticacao_ativa()
            try:
                supabase.table("vacinas").insert({
                    "pet_id": pet_obj["id"],
                    "tipo_registro": "Vacina",
                    "nome_vacina": v_escolha,
                    "dose_descricao": INFO_VACINAS[v_escolha]["cat"],
                    "doencas_protegidas": ", ".join(chk_selecionados),
                    "data_aplicacao": str(d_ap),
                    "proxima_dose": str(d_px),
                    "peso_kg": pet_obj.get("peso_atual", 0.0),
                    "vinheta": limpar_texto(v_vinheta) or None,
                    "aplicador": limpar_texto(v_aplicador) or None,
                }).execute()
            except APIError as exc:
                st.error(f"Não foi possível gravar a vacina: {mensagem_erro_api(exc)}")
            else:
                invalidar_cache_pet(pet_obj["id"])
                st.success("Vacina gravada com sucesso!")
                st.rerun()
        else:
            st.warning("Por favor, selecione a vacina antes de gravar.")

@st.dialog("📝 Lançar Desparasitante / Controlo Anti-Carraças")
def modal_editar_desparasitante(pet_obj):
    st.markdown(f"Registar novo controlo para **{pet_obj['nome']}**:")
    c1, c2 = st.columns(2)
    with c1:
        t_trat = st.selectbox("Tipo de Tratamento:", ["-- Selecione o tipo --", "Interna (Vermes)", "Externa (Carraças/Pulgas)", "Combinado"], index=0, key="m_d_tipo_vazio")
        n_prod = st.text_input("Produto:", value="", placeholder="Ex: Simparica, Drontal...", key="m_d_prod_vazio")
        d_vinheta = st.text_input("Vinheta (L/Val)", key="m_d_vinheta")
    with c2:
        f_farm = st.selectbox(
            "Forma Farmacêutica:", 
            ["-- Selecione a apresentação --", "Comprimido", "Líquido / Suspensão", "Pipeta (Spot-on)", "Pasta oral", "Coleira", "Injetável", "Outro"], 
            index=0, 
            key="m_d_farm_vazia"
        )
        p_reg = st.number_input("Peso Atual do Pet (kg):", value=0.0, step=0.1, min_value=0.0, key="m_d_peso_vazio")
        d_aplicador = st.text_input("Aplicador", key="m_d_aplicador")

    c_d1, c_d2 = st.columns(2)
    with c_d1:
        dt_ap = st.date_input("Data de Aplicação", date.today(), key="m_d_ap_vazia")
    with c_d2:
        meses = obter_meses_idade(pet_obj["data_nascimento"])
        tipo_real = t_trat if t_trat != "-- Selecione o tipo --" else "Interna"
        dt_sug = sugerir_proxima_desparasitacao(tipo_real, dt_ap, meses)
        dt_px = st.date_input("Próxima Dose", dt_sug, key="m_d_px_vazia")

    if st.button("Gravar", type="primary", use_container_width=True, key="btn_modal_save_d"):
        if t_trat != "-- Selecione o tipo --" and n_prod.strip() != "":
            garantir_autenticacao_ativa()
            supabase.table("desparasitacoes").insert({
                "pet_id": pet_obj["id"],
                "tipo": t_trat,
                "nome_produto": n_prod,
                "peso_kg": p_reg if p_reg > 0 else pet_obj.get("peso_atual", 0.0),
                "data_aplicacao": str(dt_ap),
                "proxima_dose": str(dt_px),
                "observacoes": f"Forma: {f_farm}",
                "vinheta": limpar_texto(d_vinheta) or None,
                "aplicador": limpar_texto(d_aplicador) or None,
            }).execute()

            if p_reg > 0:
                supabase.table("pets").update({"peso_atual": p_reg}).eq("id", pet_obj["id"]).execute()
                
            invalidar_cache_pet(pet_obj["id"])
            st.session_state.pop("cache_pets", None)
            st.success("Registo gravado com sucesso!")
            st.rerun()
        else:
            st.warning("Por favor, preencha o tipo de tratamento e o nome do produto.")

# ==============================================================================
# 5. SESSÃO & AUTENTICAÇÃO
# ==============================================================================
if "usuario" not in st.session_state:
    st.session_state.usuario = None
if "perfil" not in st.session_state:
    st.session_state.perfil = {}
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None
if "pet_selecionado_id" not in st.session_state:
    st.session_state.pet_selecionado_id = None
if "pagina_atual" not in st.session_state:
    st.session_state.pagina_atual = "Pág. Inicial"

if st.session_state.get("usuario") and not st.session_state.get("perfil"):
    st.session_state.perfil = carregar_perfil_usuario(st.session_state.usuario.id)

garantir_autenticacao_ativa()

if not st.session_state.usuario:
    st.title("🐾 Plataforma de Gestão e Saúde Pet")
    menu_auth = st.sidebar.radio("Acesso ao Sistema", ["Login", "Criar Conta"])

    if menu_auth == "Login":
        st.subheader("🔑 Iniciar Sessão")
        email_login = limpar_texto(st.text_input("E-mail")).lower()
        senha_login = st.text_input("Palavra-passe", type="password")

        if st.button("Entrar", type="primary", use_container_width=True):
            if not validar_email(email_login):
                st.warning("Introduza um e-mail válido.")
            elif not validar_senha(senha_login):
                st.warning("A palavra-passe deve ter pelo menos 6 caracteres.")
            else:
                try:
                    res = supabase.auth.sign_in_with_password({"email": email_login, "password": senha_login})
                    if res.user and res.session:
                        guardar_sessao_apos_login(res.user, res.session)
                        st.success("Login efetuado com sucesso!")
                        st.rerun()
                except Exception:
                    st.error("Credenciais inválidas. Verifique os dados inseridos.")

    elif menu_auth == "Criar Conta":
        st.subheader("📝 Registo de Novo Utilizador")
        tipo_conta = st.radio("Selecione o perfil:", ["Tutor", "Criador", "Clínica Veterinária"])

        nome = limpar_texto(st.text_input("Nome Completo"))
        email = limpar_texto(st.text_input("E-mail")).lower()
        senha = st.text_input("Palavra-passe", type="password")
        telefone = limpar_texto(st.text_input("Telefone"))
        endereco = limpar_texto(st.text_input("Endereço"))

        if st.button("Concluir Registo", type="primary"):
            if not nome or not telefone or not endereco or not validar_email(email) or not validar_senha(senha):
                st.warning("Preencha todos os campos obrigatórios corretamente.")
            else:
                try:
                    res = supabase.auth.sign_up({"email": email, "password": senha})
                    if res.user:
                        tipo_perfil_val = "Clinica" if tipo_conta == "Clínica Veterinária" else tipo_conta
                        perfil_dict = {
                            "id": res.user.id,
                            "nome": nome,
                            "email": email,
                            "telefone": telefone,
                            "endereco": endereco,
                            "tipo_perfil": normalizar_tipo_perfil(tipo_perfil_val),
                            "status": "ativo",
                            "data_pagamento": str(date.today()),
                        }
                        supabase.table("tutores").insert(perfil_dict).execute()
                        if res.session:
                            guardar_sessao_apos_login(res.user, res.session)
                        else:
                            st.session_state.usuario = res.user
                            st.session_state.perfil = perfil_dict
                        st.success("Conta criada com sucesso!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Erro ao cadastrar: {e}")

# ==============================================================================
# 6. PAINEL PRINCIPAL
# ==============================================================================
else:
    perfil = st.session_state.perfil or {}
    tipo_perfil = normalizar_tipo_perfil(perfil.get("tipo_perfil", "Tutor"))
    perfil["tipo_perfil"] = tipo_perfil
    user_id = st.session_state.usuario.id if st.session_state.get("usuario") else None

    if tipo_perfil in {"Tutor", "Criador", "Clinica"}:
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"], [data-testid="stHeader"] { display: none; }
            </style>
            """,
            unsafe_allow_html=True,
        )

    if "cache_pets" not in st.session_state or st.session_state.cache_pets is None:
        recarregar_dados_sessao(user_id, tipo_perfil)
    meus_pets = st.session_state.cache_pets

    if not st.session_state.pet_selecionado_id and meus_pets:
        st.session_state.pet_selecionado_id = meus_pets[0]["id"]

    col_nav1, col_nav2, col_nav3, col_exit = st.columns([1, 1.2, 1, 0.6])
    with col_nav1:
        if st.button("🏠 Pág. Inicial", use_container_width=True, type="primary" if st.session_state.pagina_atual == "Pág. Inicial" else "secondary"):
            st.session_state.pagina_atual = "Pág. Inicial"
            st.rerun()
    with col_nav2:
        if st.button("📝 Consultar e Editar", use_container_width=True, type="primary" if st.session_state.pagina_atual == "Consultar e Editar" else "secondary"):
            st.session_state.pagina_atual = "Consultar e Editar"
            st.rerun()
    with col_nav3:
        if st.button("🩺 Enfermidades", use_container_width=True, type="primary" if st.session_state.pagina_atual == "Pág. Efermidades" else "secondary"):
            st.session_state.pagina_atual = "Pág. Efermidades"
            st.rerun()
    with col_exit:
        if st.button("🚪 Sair", use_container_width=True):
            encerrar_sessao()

    st.divider()

    if st.session_state.pagina_atual == "Pág. Inicial":
        st.markdown("### 📋 Painel Geral de Pets")
        if meus_pets:
            for p in meus_pets:
                with st.container(border=True):
                    col_foto, col_info, col_links = st.columns([1, 1.8, 1.6])
                    with col_info:
                        st.markdown(f"**Nome:** {p['nome']}")
                        st.markdown(f"**Raça:** {p.get('raca', 'SRD')}")
                        st.markdown(f"**Idade:** {calcular_idade(p['data_nascimento'])}")
                        st.markdown(f"**Peso:** {p.get('peso_atual', 0.0)} kg")
                    with col_links:
                        if st.button("🔗 Consultar Detalhes", key=f"det_{p['id']}", use_container_width=True):
                            st.session_state.pet_selecionado_id = p["id"]
                            st.session_state.pagina_atual = "Consultar e Editar"
                            st.rerun()
        else:
            st.info("Nenhum pet cadastrado.")

    elif st.session_state.pagina_atual == "Consultar e Editar":
        st.markdown("### 📝 Consultar e Editar")
        if meus_pets:
            pet_dict = {p["nome"]: p["id"] for p in meus_pets}
            lista_ids = list(pet_dict.values())
            idx_atual = lista_ids.index(st.session_state.pet_selecionado_id) if st.session_state.pet_selecionado_id in lista_ids else 0

            pet_sel_nome = st.selectbox("Selecionar Pet:", list(pet_dict.keys()), index=idx_atual)
            pet_id = pet_dict[pet_sel_nome]
            st.session_state.pet_selecionado_id = pet_id
            pet = next(p for p in meus_pets if p["id"] == pet_id)

            vacs_pet, desps_pet = obter_dados_pet(pet["id"])
            ultima_vac = vacs_pet[0] if vacs_pet else None
            ultimo_desp = desps_pet[0] if desps_pet else None

            # --- TABELAS DE VACINAÇÃO E DESPARASITAÇÃO LADO A LADO ---
            col_vac, col_desp = st.columns(2, gap="medium")

            with col_vac:
                with st.container(border=True):
                    col_vt, col_vb = st.columns([2.2, 0.8])
                    with col_vt:
                        st.markdown("#### 🛡️ Registar & Consultar Vacinas")
                    with col_vb:
                        if st.button("➕ Novo", key="btn_open_modal_v", use_container_width=True):
                            modal_editar_vacina(pet)

                    if ultima_vac:
                        st.markdown(f"**Vacina:** `{ultima_vac['nome_vacina']}`")
                        st.info(f"🛡️ **Protege contra:** {ultima_vac.get('doencas_protegidas', 'N/I')}")
                        st.write(f"📅 **Aplicação:** {ultima_vac['data_aplicacao']} | 🔄 **Próxima:** {ultima_vac['proxima_dose']}")

                    st.divider()
                    st.markdown("##### 📋 Histórico de Vacinas")
                    if vacs_pet:
                        df_v = pd.DataFrame([{
                            "Vacina": v["nome_vacina"],
                            "Peso (kg)": v.get("peso_kg", pet.get("peso_atual", 0.0)),
                            "Idade": calcular_idade(pet["data_nascimento"]),
                            "Aplicação": v["data_aplicacao"],
                            "Próxima": v["proxima_dose"]
                        } for v in vacs_pet])
                        st.dataframe(df_v, use_container_width=True, hide_index=True)
                    else:
                        st.info("Sem histórico de vacinação.")

            with col_desp:
                with st.container(border=True):
                    col_dt_t, col_dt_b = st.columns([2.2, 0.8])
                    with col_dt_t:
                        st.markdown("#### 💊 Registar & Consultar Desparasitações")
                    with col_dt_b:
                        if st.button("➕ Novo", key="btn_open_modal_d", use_container_width=True):
                            modal_editar_desparasitante(pet)

                    if ultimo_desp:
                        st.markdown(f"**Produto:** `{ultimo_desp['nome_produto']}` ({ultimo_desp['tipo']})")
                        st.write(f"📅 **Aplicação:** {ultimo_desp['data_aplicacao']} | 🔄 **Próxima:** {ultimo_desp['proxima_dose']} | ⚖️ **Peso:** {ultimo_desp['peso_kg']} kg")

                    st.divider()
                    st.markdown("##### 📋 Histórico Parasitário")
                    if desps_pet:
                        df_d = pd.DataFrame([{
                            "Tipo": d["tipo"],
                            "Produto": d["nome_produto"],
                            "Peso": f"{d['peso_kg']} kg",
                            "Aplicação": d["data_aplicacao"],
                            "Próxima Dose": d["proxima_dose"]
                        } for d in desps_pet])
                        st.dataframe(df_d, use_container_width=True, hide_index=True)
                    else:
                        st.info("Sem histórico de desparasitação.")
        else:
            st.info("Cadastre um pet para consultar os detalhes.")

    elif st.session_state.pagina_atual == "Pág. Efermidades":
        st.markdown("### 🩺 Gestão de Enfermidades e Óbitos")
        st.info("Painel de controlo clínico secundário.")
