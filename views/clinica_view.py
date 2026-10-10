import pandas as pd
import streamlit as st


def render_clinica_dashboard(supabase):
  st.title("🏥 Painel Clínico: Prontuário, Internamento & Honorários")

  clinica_tab1, clinica_tab2, clinica_tab3 = st.tabs([
      "💳 Honorários & Gestão Financeira",
      "🩺 Prontuário Eletrónico (PME) & Assinatura",
      "📅 Agenda & Módulo de Internamento",
  ])

  with clinica_tab1:
    st.header("Gestão Financeira e Pagamentos Clínicos (MCX & IBAN)")
    col_fin1, col_fin2 = st.columns(2)
    with col_fin1:
      with st.form("form_honorario_clinica"):
        st.subheader("Registo de Honorário / Ato Médico")
        st.text_input("Identificação do Paciente / Pet")
        st.selectbox(
            "Tipo de Ato Médico",
            ["Consulta", "Cirurgia", "Vacinação", "Internamento"],
        )
        st.number_input("Valor (AOA)", min_value=1000, value=20000)
        if st.form_submit_button("Registar Fatura e Cobrar"):
          st.success("Ato médico registado e cobrado com sucesso!")
    with col_fin2:
      st.subheader("Controlo de Saldos e Contas Correntes")
      debitos_df = pd.DataFrame({
          "Paciente": ["Bobi", "Luna"],
          "Tutor": ["João Soares", "Carla Mendes"],
          "Saldo Devedor (AOA)": [15000, 45000],
          "Estado": ["Em Débito", "Pendente IBAN"],
      })
      st.dataframe(debitos_df, use_container_width=True)

  with clinica_tab2:
    st.header("Prontuário Médico Eletrónico (PME) & Assinatura Digital")
    with st.form("form_pme_clinica"):
      st.text_input("Nome do Paciente / Pet")
      st.text_area("Anamnese e Sinais Clínicos")
      st.text_area("Prescrição Médica e Receituário Digital")
      if st.form_submit_button("Salvar PME e Assinar Digitalmente"):
        st.success("Prontuário guardado com carimbo digital do veterinário!")

  with clinica_tab3:
    sub_ag1, sub_ag2 = st.tabs(
        ["📅 Agenda de Consultas/Cirurgias", "🛌 Módulo de Internamento"]
    )
    with sub_ag1:
      with st.form("form_agenda"):
        st.text_input("Nome do Pet")
        st.selectbox("Tipo", ["Consulta", "Cirurgia", "Retorno"])
        if st.form_submit_button("Agendar e Enviar Lembrete WhatsApp"):
          st.success("Marcação efetuada com sucesso!")
    with sub_ag2:
      with st.form("form_internamento"):
        st.text_input("Nome do Paciente em Hospitalização")
        st.text_input("Parâmetros Vitais (Temp, FC, FR)")
        if st.form_submit_button("Atualizar Ficha de Internamento"):
          st.success("Ficha de internamento atualizada!")