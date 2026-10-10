import streamlit as st


def render_tutor_vacinas_desp(supabase, user_id):
  st.subheader("🐶 Gestão Doméstica de Vacinas e Desparasitações")

  tab_v, tab_d = st.tabs(["🛡️ Vacinas", "💊 Desparasitação"])

  with tab_v:
    with st.form("form_tutor_vacina"):
      st.markdown("**Registar Nova Vacina**")
      # Buscar animais do tutor
      animais_res = (
          supabase.table("animais")
          .select("id, nome")
          .eq("tutor_id", user_id)
          .execute()
      )
      animais = animais_res.data
      if not animais:
        st.warning(
            "Regista primeiro um animal na tua carteira para adicionar"
            " vacinas."
        )
        st.form_submit_button("Guardar", disabled=True)
        return

      pet_opcoes = {a["nome"]: a["id"] for a in animais}
      pet_sel = st.selectbox("Selecionar Pet", list(pet_opcoes.keys()))

      nome_vacina = st.text_input(
          "Nome da Vacina / Doenças Cobertas (Ex: V8, V10, Raiva)"
      )
      data_aplicacao = st.date_input("Data de Aplicação")
      proxima_dose = st.date_input(
          "Data do Próximo Reforço (Vencimento para Alertas)"
      )
      comprovativo = st.file_uploader(
          "Fotografia do Talão / Autocolante na Caderneta",
          type=["jpg", "png", "pdf"],
      )

      if st.form_submit_button("Registar Vacina"):
        try:
          supabase.table("registos_medicos_v2").insert({
              "animal_id": pet_opcoes[pet_sel],
              "perfil_utilizador": "tutor",
              "tipo": "vacina",
              "nome_produto": nome_vacina,
              "data_aplicacao": str(data_aplicacao),
              "proxima_dose": str(proxima_dose),
          }).execute()
          st.success("Vacina registada com sucesso na caderneta digital!")
        except Exception as e:
          st.error(f"Erro ao registar vacina: {e}")

  with tab_d:
    with st.form("form_tutor_desp"):
      st.markdown("**Registar Desparasitação (Interna ou Externa)**")
      pet_sel_d = st.selectbox(
          "Selecionar Pet", list(pet_opcoes.keys()), key="pet_d"
      )
      tipo_desp = st.selectbox(
          "Tipo de Desparasitação",
          ["Interna (Comprimido/Xarope)", "Externa (Pipeta/Coleira)"],
      )
      nome_produto = st.text_input(
          "Nome do Produto (Ex: Drontal, NexGard, Bravecto)"
      )
      data_aplicacao_d = st.date_input("Data de Aplicação", key="d_app")
      proxima_dose_d = st.date_input("Próxima Dose Recomendada", key="d_prox")

      if st.form_submit_button("Registar Desparasitação"):
        try:
          supabase.table("registos_medicos_v2").insert({
              "animal_id": pet_opcoes[pet_sel_d],
              "perfil_utilizador": "tutor",
              "tipo": "desparasitacao",
              "nome_produto": f"{tipo_desp} - {nome_produto}",
              "data_aplicacao": str(data_aplicacao_d),
              "proxima_dose": str(proxima_dose_d),
          }).execute()
          st.success("Desparasitação registada com sucesso!")
        except Exception as e:
          st.error(f"Erro ao registar desparasitação: {e}")
