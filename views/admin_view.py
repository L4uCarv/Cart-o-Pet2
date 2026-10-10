from datetime import datetime
import pandas as pd
import streamlit as st


def render_admin_dashboard(supabase, papel):
  st.title(f"🛠️ Painel Administrativo ({papel.replace('_', ' ').title()})")
  admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs([
      "💳 Gestão de Pagamentos & MCX",
      "👥 Controlo de Acessos & Auditoria",
      "🏥 Clínicas & Parceiros",
      "🎧 Suporte & Disputas",
  ])

  with admin_tab1:
    st.header("Conciliação Bancária & Validação de Pagamentos")
    col1, col2 = st.columns(2)
    with col1:
      st.subheader("Fila de Auditoria de Pagamentos")
      dados_pendentes = pd.DataFrame({
          "ID_Transacao": ["TX-9841", "TX-9842"],
          "Telemovel_MCX": ["936342306", "934071334"],
          "Valor (AOA)": [15000, 25000],
          "Referencia": ["CARTAO-01", "CARTAO-02"],
          "Estado": ["Pendente", "Pendente"],
      })
      st.dataframe(dados_pendentes, use_container_width=True)
      tx_sel = st.selectbox(
          "Selecionar Transação", dados_pendentes["ID_Transacao"]
      )
      if st.button("✅ Aprovar Pagamento & Notificar WhatsApp"):
        st.success(f"Pagamento {tx_sel} aprovado com sucesso!")
      if st.button("❌ Rejeitar Pagamento"):
        st.error(f"Transação {tx_sel} rejeitada por inconformidade.")
    with col2:
      st.subheader("Conciliação por Lote (CSV / XLSX)")
      st.file_uploader("Carregar Extrato Bancário IBAN", type=["csv", "xlsx"])

  with admin_tab2:
    st.header("Matriz de Perfis (RBAC) & Audit Trail")
    logs_df = pd.DataFrame({
        "Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "Utilizador": [st.session_state["utilizador"]],
        "Ação": ["SESSÃO_ADMIN_AUDITADA"],
        "IP": ["192.168.1.55"],
    })
    st.dataframe(logs_df, use_container_width=True)

  with admin_tab3:
    st.header("Gestão de Clínicas e Veterinários Parceiros")
    clinicas_df = pd.DataFrame({
        "Clínica": ["VetCare Luanda", "PetSaúde Talatona"],
        "Diretor Clínico": ["Dr. António Silva", "Dra. Carla Mendes"],
        "Estado": ["Ativo", "Pendente"],
    })
    st.dataframe(clinicas_df, use_container_width=True)

  with admin_tab4:
    st.header("Módulo de Suporte & Disputas")
    st.info("ℹ️ Não existem disputas pendentes no momento.")