import pandas as pd
import streamlit as st


def render_clinica_dashboard(supabase):
  st.title("🏥 Painel Clínico: Prontuário, Internamento & Honorários")

  clinica_tab1, clinica_tab2, clinica_tab3, clinica_tab4 = st.tabs([
      "💳 Honorários & Gestão Financeira",
      "🩺 Prontuário Eletrónico (PME) & Assinatura",
      "💉 Certificação de Vacinas & Desparasitação",
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
    st.subheader("Certificação Veterinária de Vacinação e Tratamentos")
    tab_cv, tab_cd = st.tabs(["💉 Vacinação Certificada", "🔬 Desparasitação"])

    with tab_cv:
      with st.form("form_vet_vacina"):
        st.markdown("**Ato Médico: Aplicação e Registo de Vacina**")
        id_paciente = st.text_input(
            "ID Único do Animal ou Microchip / Nome do Paciente"
        )
        nome_comercial = st.text_input(
            "Nome Comercial e Fabricante (Ex: Vanguard Plus, Zoetis)"
        )
        lote = st.text_input("Número de Lote da Vacina")

        col1, col2 = st.columns(2)
        with col1:
          data_fab = st.date_input("Data de Fabricação")
        with col2:
          data_val = st.date_input("Data de Validade")

        via_adm = st.selectbox(
            "Via de Administração",
            ["Subcutânea", "Intramuscular", "Intranasal"],
        )

        col3, col4 = st.columns(2)
        with col3:
          peso_pet = st.number_input("Peso Atual do Pet (kg)", 0.1, 100.0, 10.0)
        with col4:
          temp_pet = st.number_input(
              "Temperatura Corporal (°C)", 35.0, 43.0, 38.5
          )

        carimbo_omv = st.text_input(
            "Carimbo Digital / OMV (Ex: Dr. António Silva - OMV 4012)",
            value="Dr. António Silva (OMV-4012)",
        )

        if st.form_submit_button("Certificar e Emitir Carimbo Digital"):
          st.success(
              f"Vacina {nome_comercial} (Lote: {lote}) certificada e assinada"
              f" digitalmente por {carimbo_omv}!"
          )

    with tab_cd:
      with st.form("form_vet_desp"):
        st.markdown("**Controlo de Endoparasitas e Ectoparasitas (Clínica)**")
        id_paciente_d = st.text_input(
            "ID Único do Animal / Microchip", key="id_d"
        )
        principio_ativo = st.text_input(
            "Princípio Ativo e Dosagem (Baseado no Peso)"
        )
        lote_produto = st.text_input("Número de Lote do Produto", key="lote_d")
        finalidade = st.selectbox(
            "Finalidade / Espectro",
            [
                "Endoparasitas (Lombrigas/Ténias)",
                "Ectoparasitas (Pulgas/Carraças)",
                "Leishmaniose (Prevenção Flebótomos)",
            ],
        )
        carimbo_omv_d = st.text_input(
            "Carimbo OMV", value="Dr. António Silva (OMV-4012)", key="omv_d"
        )

        if st.form_submit_button("Registar Tratamento Antiparasitário"):
          st.success(
              "Tratamento antiparasitário validado clinicamente e anexado ao"
              " histórico do paciente!"
          )

  with clinica_tab4:
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
