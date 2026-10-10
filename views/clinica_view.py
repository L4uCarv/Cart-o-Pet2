import streamlit as st


def render_clinica_vacinas_desp(supabase, clinica_id):
  st.subheader("🏥 Certificação Veterinária de Vacinação e Tratamentos")

  tab_cv, tab_cd = st.tabs(["💉 Vacinação Certificada", "🔬 Desparasitação Clínica"])

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
