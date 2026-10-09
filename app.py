import io
import os
from datetime import date, datetime, timedelta
import matplotlib.pyplot as plt
from fpdf import FPDF
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# Configuração da Página
st.set_page_config(
    page_title="CartãoPet V2 - Gestão Veterinária",
    page_icon="🐾",
    layout="wide",
)


# Carregar CSS Externo
def load_css(file_name):
  if os.path.exists(file_name):
    with open(file_name) as f:
      st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


load_css("assets/style.css")

# Inicialização do Supabase (utilizando secrets do Streamlit Cloud)
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "SUA_URL_SUPABASE")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "SUA_CHAVE_SUPABASE")


@st.cache_resource
def init_supabase() -> Client:
  return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase = init_supabase()

# --- AUTENTICAÇÃO SIMULADA / GESTÃO DE PERFIS ---
st.sidebar.title("🐾 CartãoPet V2")
papel_utilizador = st.sidebar.selectbox(
    "Nível de Acesso (Perfil)", ["Tutor", "Criador", "Clínica", "Admin"]
)
utilizador_atual = st.sidebar.text_input(
    "Utilizador / Email", "joao.tutor@email.com"
)

st.sidebar.markdown("---")
st.sidebar.info(
    f"Sessão ativa como: **{papel_utilizador.upper()}**\n\nPainel seguro"
    " integrado com Supabase."
)


# --- GERAÇÃO DE RELATÓRIO PDF COM MATPLOTLIB ---
def gerar_grafico_estatisticas():
  fig, ax = plt.subplots(figsize=(6, 3))
  categorias = ["Vacinas em Dia", "A Vencer", "Atrasadas"]
  valores = [5, 2, 1]
  cores = ["#10B981", "#F59E0B", "#EF4444"]

  ax.bar(categorias, valores, color=cores)
  ax.set_ylabel("Quantidade")
  ax.set_title("Estado Geral do Histórico de Saúde")

  img_buffer = io.BytesIO()
  plt.savefig(img_buffer, format="png", bbox_inches="tight")
  img_buffer.seek(0)
  plt.close(fig)
  return img_buffer


def gerar_pdf_pet(nome_pet, especie, raca):
  pdf = FPDF()
  pdf.add_page()
  pdf.set_font("helvetica", "B", 16)
  pdf.cell(0, 10, f"Cartão de Vacina Oficial - {nome_pet}", ln=True, align="C")

  pdf.set_font("helvetica", "", 12)
  pdf.ln(5)
  pdf.cell(0, 8, f"Espécie: {especie} | Raça: {raca}", ln=True)
  pdf.cell(
      0,
      8,
      f"Emitido em: {datetime.now().strftime('%d/%m/%Y')} via CartãoPet V2",
      ln=True,
  )
  pdf.ln(10)

  # Adicionar Gráfico Matplotlib ao PDF
  img_buf = gerar_grafico_estatisticas()
  temp_img_path = "temp_grafico.png"
  with open(temp_img_path, "wb") as f:
    f.write(img_buf.getbuffer())

  pdf.image(temp_img_path, x=30, w=150)
  if os.path.exists(temp_img_path):
    os.remove(temp_img_path)

  pdf.ln(10)
  pdf.set_font("helvetica", "I", 10)
  pdf.cell(
      0, 10, "Documento gerado eletronicamente com segurança Supabase.", align="C"
  )

  return pdf.output()


# --- INTERFACE PRINCIPAL ---
st.title("🛡️ CartãoPet V2: Gestão Inteligente de Saúde Animal")

aba1, aba2, aba3, aba4 = st.tabs(
    ["🐶 Os Meus Animais", "💉 Planos e Vacinas", "📅 Calendário", "📊 Relatórios"]
)

with aba1:
  st.header("Gestão de Animais de Estimação")
  col1, col2 = st.columns(2)

  with col1:
    with st.form("form_registo_pet"):
      st.subheader("Registar Novo Animal")
      nome_pet = st.text_input("Nome do Animal")
      especie_pet = st.selectbox("Espécie", ["Cão", "Gato", "Outro"])
      raca_pet = st.text_input("Raça")
      idade_pet = st.number_input(
          "Idade (Anos)", min_value=0, max_value=30, value=1
      )
      peso_pet = st.number_input(
          "Peso (kg)", min_value=0.1, max_value=100.0, value=5.0
      )

      submitted = st.form_submit_button("Salvar Animal")
      if submitted:
        st.success(
            f"Animal {nome_pet} registado com sucesso para o papel"
            f" {papel_utilizador}!"
        )
        # Código para inserir no Supabase:
        # supabase.table("animais").insert({"nome": nome_pet, "especie": especie_pet, ...}).execute()

  with col2:
    st.subheader("Lista Rápida (Simulação Supabase)")
    # Exemplo de listagem tabular
    dados_exemplo = pd.DataFrame({
        "Nome": ["Bobi", "Luna"],
        "Espécie": ["Cão", "Gato"],
        "Raça": ["Bichon Frisé", "SRD"],
        "Próxima Vacina": ["15/11/2026", "20/11/2026"],
    })
    st.dataframe(dados_exemplo, use_container_width=True)

with aba2:
  st.header("Controlo de Vacinas e Desparasitação")
  if papel_utilizador in ["Clínica", "Admin", "Criador"]:
    with st.form("form_vacina"):
      pet_selecionado = st.selectbox("Selecionar Animal", ["Bobi", "Luna"])
      tipo_registo = st.selectbox(
          "Tipo", ["Vacina (Ex: Raiva, Nobivac)", "Desparasitação (Ex: Drontal)"]
      )
      nome_produto = st.text_input("Nome do Produto / Lote")
      data_aplicacao = st.date_input(
          "Data da Aplicação", value=date.today()
      )
      proxima_dose = st.date_input(
          "Próxima Dose Recomendada", value=date.today() + timedelta(days=365)
      )

      btn_registo = st.form_submit_button("Adicionar Registo Clínico")
      if btn_registo:
        st.success(
            f"Registo de {tipo_registo} para {pet_selecionado} guardado na base"
            " de dados!"
        )
  else:
    st.warning(
        "A tua conta ('Tutor') tem permissão de leitura. Contacta uma clínica"
        " autorizada para submeter novos registos clínicos."
    )

with aba3:
  st.header("📅 Calendario de Próximas Doses")
  st.markdown(
      "Aqui podes visualizar de forma imediata quando será a próxima"
      " intervenção de saúde do teu animal:"
  )

  # Alertas visuais dinâmicos
  st.warning("⚠️ **Bobi**: Vacina Polivalente vence daqui a 15 dias (24/10/2026)")
  st.info(
      "ℹ️ **Luna**: Desparasitação interna agendada para o dia 05/11/2026"
  )

with aba4:
  st.header("📊 Relatórios e Exportação em PDF")
  st.markdown(
      "Gera relatórios oficiais certificados com gráficos analíticos embutidos"
      " para exportação."
  )

  pet_pdf = st.selectbox("Escolher Animal para Relatório", ["Bobi", "Luna"])

  if st.button("📄 Gerar e Descarregar PDF do Cartão"):
    pdf_bytes = gerar_pdf_pet(pet_pdf, "Cão", "Bichon Frisé")
    st.download_button(
        label="📥 Descarregar PDF Oficial",
        data=pdf_bytes,
        file_name=f"Cartao_Vacina_{pet_pdf}.pdf",
        mime="application/pdf",
    )