import io
from datetime import date, timedelta
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


def gerar_grafico_peso_pet(pesos_historico):
  fig, ax = plt.subplots(figsize=(6, 3))
  if pesos_historico:
    datas = [p["data"] for p in pesos_historico]
    valores = [p["peso"] for p in pesos_historico]
    ax.plot(
        datas, valores, marker="o", color="#4F46E5", linewidth=2, markersize=6
    )
  else:
    ax.plot(["Registo Inicial"], [5.0], marker="o", color="#4F46E5")
  ax.set_ylabel("Peso (kg)")
  ax.set_title("Evolução do Peso e Crescimento do Pet")
  ax.grid(True, linestyle="--", alpha=0.6)

  img_buffer = io.BytesIO()
  plt.savefig(img_buffer, format="png", bbox_inches="tight")
  img_buffer.seek(0)
  plt.close(fig)
  return img_buffer


def calcular_idade_pet(data_nascimento):
  hoje = date.today()
  if data_nascimento > hoje:
    return "Data inválida", 0.0

  anos = hoje.year - data_nascimento.year
  meses = hoje.month - data_nascimento.month
  dias = hoje.day - data_nascimento.day

  if dias < 0:
    meses -= 1
  if meses < 0:
    anos -= 1
    meses += 12

  total_meses = anos * 12 + meses
  idade_anos_decimal = round(total_meses / 12, 1)

  if total_meses < 1:
    return "Menos de 1 mês", idade_anos_decimal
  elif total_meses < 12:
    return f"{total_meses} meses", idade_anos_decimal
  elif anos == 1:
    return f"1 ano e {meses} meses" if meses > 0 else "1 ano", idade_anos_decimal
  else:
    return f"{anos} anos e {meses} meses" if meses > 0 else f"{anos} anos", idade_anos_decimal


def render_tutor_dashboard(supabase):
  st.title("🐾 CartãoPet V2: Painel do Tutor e Saúde Animal")

  user_id = st.session_state.get("user_id")
  if not user_id:
    st.error(
        "Sessão inválida ou expirada. Por favor, termine sessão e volte a"
        " entrar."
    )
    return

  tutor_tab1, tutor_tab2, tutor_tab3 = st.tabs([
      "🐶 Gestão de Saúde & Vacinação",
      "🌸 Controlo Especializado (Fêmeas & Ninhadas)",
      "💳 Pagamentos & Transações",
  ])

  with tutor_tab1:
    st.header("Carteira Digital Centralizada & Crescimento")
    col_reg, col_list = st.columns(2)

    with col_reg:
      st.subheader("Registar Novo Animal")
      
      # Inicializar chaves no session_state para permitir limpeza correta
      if "reg_nome_pet" not in st.session_state:
        st.session_state["reg_nome_pet"] = ""
      if "reg_esp_pet" not in st.session_state:
        st.session_state["reg_esp_pet"] = "Cão"
      if "reg_raca_pet" not in st.session_state:
        st.session_state["reg_raca_pet"] = ""
      if "reg_sexo_pet" not in st.session_state:
        st.session_state["reg_sexo_pet"] = "Macho"
      if "reg_data_nasc" not in st.session_state:
        st.session_state["reg_data_nasc"] = date.today()
      if "reg_peso_pet" not in st.session_state:
        st.session_state["reg_peso_pet"] = 0.0

      nome_pet = st.text_input("Nome do Animal", key="reg_nome_pet")
      especie_pet = st.selectbox("Espécie", ["Cão", "Gato", "Outro"], key="reg_esp_pet")
      raca_pet = st.text_input("Raça", key="reg_raca_pet")
      sexo_pet = st.selectbox("Sexo", ["Macho", "Fêmea"], key="reg_sexo_pet")

      data_nasc_pet = st.date_input(
          "Data de Nascimento do Pet",
          max_value=date.today(),
          key="reg_data_nasc"
      )
      
      descricao_idade, idade_decimal = calcular_idade_pet(data_nasc_pet)
      st.info(f"📅 Idade calculada automaticamente: **{descricao_idade}**")

      peso_atual = st.number_input("Peso Atual (kg)", min_value=0.0, max_value=100.0, key="reg_peso_pet")

      if st.button("Salvar Pet na Carteira", type="primary"):
        if not nome_pet:
          st.warning("Por favor, insira o nome do animal.")
        else:
          try:
            supabase.table("animais").insert({
                "tutor_id": user_id,
                "nome": nome_pet,
                "especie": especie_pet,
                "raca": raca_pet,
                "sexo": sexo_pet,
                "idade_
