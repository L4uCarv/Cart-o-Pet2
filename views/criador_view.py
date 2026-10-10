import pandas as pd
import streamlit as st


def render_criador_dashboard(supabase):
  st.title("🧬 Painel do Criador: Gestão Comercial & Plantel do Canil")

  criador_tab1, criador_tab2, criador_tab3 = st.tabs([
      "💰 Comercial, Sinais & Faturação",
      "🐕 Plantel, Pedigree & Neonatal",
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
        "💉 Vacinação Neonatal em Lote",
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
    st.header("Transferência de Titularidade & Contratos Pós-Venda")
    with st.form("form_transferencia_criador"):
      st.text_input("Identificação do Filhote / Microchip")
      st.text_input("Email do Novo Tutor no Sistema")
      if st.form_submit_button("Transferir Cartão Digital"):
        st.success("Cartão transferido para o novo tutor com sucesso!")