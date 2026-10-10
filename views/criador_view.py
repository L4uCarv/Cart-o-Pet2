import pandas as pd
import streamlit as st


def render_criador_dashboard(supabase):
  st.title("🧬 Painel do Criador: Gestão Comercial & Plantel do Canil")

  criador_tab1, criador_tab2, criador_tab3, criador_tab4 = st.tabs([
      "💰 Comercial, Sinais & Faturação",
      "🐕 Plantel, Pedigree & Neonatal",
      "💉 Vacinação & Desparasitação em Lote",
      "🏡 Transferência & Contratos Pós-Venda",
  ])

  with criador_tab1:
    st.header("Gestão Comercial e Reservas (MCX & IBAN)")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
      with st.form("form_reserva_filhote"):
        st.subheader("Registo de Sinal de Reserva")
        st.text_input("Identificação da Ninhada / Filhote")
        st.number_input("Valor do Sinal (AOA)", 5000, 25000)
        if st.form_submit_button("Validar e Registar Sinal"):
          st.success("Sinal registado com sucesso!")
    with col_c2:
      st.subheader("Conciliação de Ninhada por Lote")
      st.file_uploader(
          "Extrato Bancário do Canil (.csv ou .xlsx)", type=["csv", "xlsx"]
      )

  with criador_tab2:
    st.header("Gestão de Plantel, Pedigree & Controlo Neonatal")
    sub_p1, sub_p2, sub_p3 = st.tabs([
        "🐾 Plantel de Reprodutores",
        "📜 Árvore Genealógica (Pedigree LOP)",
        "🗓️ Calendário Neonatal",
    ])
    with sub_p1:
      with st.form("form_plantel"):
        st.text_input("Nome do Cão / Matriz")
        st.text_input("Número de Registo Pedigree / LOP")
        if st.form_submit_button("Adicionar ao Plantel"):
          st.success("Reprodutor adicionado ao plantel!")
    with sub_p2:
      st.text_input("Nome do Filhote com Prefixo do Canil")
      if st.button("Gerar Certificado de Pedigree Provisório"):
        st.success("Certificado LOP gerado com sucesso!")
    with sub_p3:
      st.info(
          "🗓️ **Ninhada Atual:** 4ª semana (Desparasitação) e 6ª semana"
          " (Vacinação em lote) agendadas."
      )

  with criador_tab3:
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
        lote_vacina_lote = st.text_input(
            "Número de Lote do Imunizante (Lote Único)"
        )
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
          st.metric(
              "Stock de Comprimidos Drontal Puppy", "12 unidades", "Em dia"
          )

        if st.form_submit_button("Atualizar Inventário do Canil"):
          st.success("Inventário de produtos veterinários atualizado com sucesso!")

  with criador_tab4:
    st.header("Transferência de Titularidade & Contratos Pós-Venda")
    with st.form("form_transferencia_criador"):
      st.text_input("Identificação do Filhote / Microchip")
      st.text_input("Email do Novo Tutor no Sistema")
      if st.form_submit_button("Transferir Cartão Digital"):
        st.success("Cartão transferido para o novo tutor com sucesso!")
