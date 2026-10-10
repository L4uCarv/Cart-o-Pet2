import streamlit as st


def render_criador_vacinas_desp(supabase, criador_id):
  st.subheader("🏡 Gestão de Lote em Escala & Protocolo Neonatal (Canil)")

  tab_cn1, tab_cn2 = st.tabs([
      "💉 Vacinação Neonatal em Lote",
      "🍼 Protocolo Neonatal & Inventário",
  ])

  with tab_cn1:
    with st.form("form_criador_lote"):
      st.markdown("**Registo Simultâneo para Toda a Ninhada**")
      ident_ninhada = st.text_input(
          "Identificação da Ninhada (Ex: Ninhada Luna - Bichon Frisé)"
      )
      prefixo = st.text_input("Prefixo do Canil", value="Canil Von Haus")
      qtd_filhotes = st.number_input(
          "Número de Filhotes a Vacinar em Lote", 1, 20, 5
      )
      nome_vacina_lote = st.text_input(
          "Vacina Aplicada (Ex: 1ª Dose Puppy / V8)"
      )
      lote_vacina_lote = st.text_input("Número de Lote do Imunizante (Lote Único)")
      data_lote = st.date_input("Data de Aplicação do Lote")

      if st.form_submit_button("Aplicar Vacinação em Lote à Ninhada"):
        st.success(
            f"Vacinação em lote registada com sucesso para {qtd_filhotes}"
            f" filhotes da ninhada **{ident_ninhada}** ({prefixo})!"
        )

  with tab_cn2:
    with st.form("form_criador_protocolo"):
      st.markdown("**Cronograma e Controlo de Stock do Canil**")
      st.info(
          "🗓️ **Cronograma Padrão de Desparasitação Neonatal:**\n- 2ª Semana:"
          " Desparasitação Interna Preventiva (Xarope)\n- 4ª Semana:"
          " Desparasitação e 1ª Dose de Vacina\n- 6ª e 8ª Semanas: Reforços"
          " sucessivos e microchip."
      )
      st.markdown("---")
      st.subheader("Gestão de Stock de Xaropes e Comprimidos no Canil")
      col1, col2 = st.columns(2)
      with col1:
        st.metric("Stock de Xarope Neonatal", "3 frascos", "-1 usado hoje")
      with col2:
        st.metric("Stock de Comprimidos Drontal Puppy", "12 unidades", "Em dia")

      if st.form_submit_button("Atualizar Inventário do Canil"):
        st.success("Inventário de produtos veterinários atualizado com sucesso!")
