import streamlit as st


def render_auth_sidebar(supabase):
  st.sidebar.title("🐾 CartãoPet V2")

  if "utilizador" not in st.session_state:
    st.session_state["utilizador"] = None
  if "papel" not in st.session_state:
    st.session_state["papel"] = None
  if "user_id" not in st.session_state:
    st.session_state["user_id"] = None
  if "mfa_validado" not in st.session_state:
    st.session_state["mfa_validado"] = False

  if st.session_state["utilizador"] is None:
    st.sidebar.subheader("🔒 Autenticação de Sistema")
    modo_auth = st.sidebar.radio("Modo", ["Entrar (Login)", "Registar Conta"])

    with st.sidebar.form("form_auth"):
      email_input = st.text_input("Email")
      senha_input = st.text_input("Senha", type="password")

      papel_escolhido = "tutor"
      nome_input = ""
      if modo_auth == "Registar Conta":
        nome_input = st.text_input("Nome Completo")
        papel_escolhido = st.selectbox(
            "Perfil de Acesso",
            [
                "tutor",
                "criador",
                "clinica",
                "super_admin",
                "financeiro",
                "moderador",
            ],
        )

      btn_submeter = st.form_submit_button(
          "Aceder" if modo_auth == "Entrar (Login)" else "Registar"
      )

      if btn_submeter:
        try:
          if modo_auth == "Registar Conta":
            res = supabase.auth.sign_up(
                {"email": email_input, "password": senha_input}
            )
            if res.user:
              supabase.table("perfis").insert({
                  "id": res.user.id,
                  "nome": nome_input,
                  "email": email_input,
                  "papel": papel_escolhido,
              }).execute()
              st.success("Conta criada com sucesso! Podes efetuar login.")
          else:
            res = supabase.auth.sign_in_with_password(
                {"email": email_input, "password": senha_input}
            )
            if res.user:
              perfil_res = (
                  supabase.table("perfis")
                  .select("*")
                  .eq("id", res.user.id)
                  .execute()
              )
              if perfil_res.data:
                dados = perfil_res.data[0]
                st.session_state["utilizador"] = dados["email"]
                st.session_state["papel"] = dados["papel"]
                st.session_state["user_id"] = dados["id"]
                if dados["papel"] in ["super_admin", "financeiro", "moderador"]:
                  st.session_state["mfa_validado"] = False
                else:
                  st.session_state["mfa_validado"] = True
                st.rerun()
        except Exception as e:
          st.error(f"Erro na autenticação: {e}")

  else:
    st.sidebar.success(f"Sessão: **{st.session_state['utilizador']}**")
    st.sidebar.info(f"Perfil RBAC: **{st.session_state['papel'].upper()}**")

    if (
        st.session_state["papel"] in ["super_admin", "financeiro", "moderador"]
        and not st.session_state["mfa_validado"]
    ):
      st.sidebar.warning("⚠️ Verificação MFA Obrigatória")
      codigo_mfa = st.sidebar.text_input(
          "Insira o código MFA (Teste: 123456)", type="password"
      )
      if st.sidebar.button("Validar MFA"):
        if codigo_mfa == "123456":
          st.session_state["mfa_validado"] = True
          st.success("MFA validado com sucesso!")
          st.rerun()
        else:
          st.error("Código MFA inválido.")

    if st.sidebar.button("🚪 Terminar Sessão"):
      supabase.auth.sign_out()
      st.session_state.clear()
      st.rerun()