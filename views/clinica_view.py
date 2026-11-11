import streamlit as st

from services.supabase_client import erro
from views import componentes as c


def render_clinica_dashboard(sb):
  user_id = st.session_state["user_id"]
  parceiro = sb.table("parceiros").select("*").eq("perfil_id", user_id).execute().data
  if not parceiro or parceiro[0]["estado_credenciamento"] != "ativo":
    st.warning("O teu credenciamento ainda não está ativo. Aguarda a aprovação da administração.")
    return
  st.title("🏥 Painel do Veterinário")
  st.caption(f"Cédula / OMV: {parceiro[0]['numero_ordem']}")

  aba1, aba2 = st.tabs(["🔎 Abrir ficha por código", "👥 Os meus pacientes"])

  with aba1:
    st.caption("Pede ao tutor o código ou o QR do animal (válido 10 minutos).")
    codigo = st.text_input("Código do animal", key="cod_vet")
    if st.button("Abrir ficha", type="primary", key="cod_btn"):
      try:
        sb.rpc("resgatar_codigo_acesso", {"p_codigo": codigo}).execute()
        c.aviso("Acesso concedido por 30 dias. O animal já está na tua lista de pacientes.")
        st.rerun()
      except Exception as e:
        st.error(erro(e))

  with aba2:
    pacientes = sb.rpc("meus_pacientes").execute().data or []
    if not pacientes:
      st.info("Ainda não tens pacientes com acesso ativo.")
      return
    p = st.selectbox(
        "Paciente", pacientes,
        format_func=lambda x: f"{x['animal_nome']} ({x['especie']}) · tutor {x['tutor_nome']}", key="pac_sel")
    st.caption(f"Tutor: {p['tutor_nome']} · {p['tutor_email']} · acesso até {c.fmt(p['acesso_expira_em'])}")
    animal = sb.table("animais").select("*").eq("id", p["animal_id"]).execute().data[0]

    abas = st.tabs(["📋 Histórico", "💉 Vacina", "💊 Desparasitação", "🩺 Nova consulta", "⚖️ Peso"])
    with abas[0]:
      c.historico(sb, animal)
    with abas[1]:
      c.formulario_registo(sb, animal, "vacina", clinico=True)
    with abas[2]:
      c.formulario_registo(sb, animal, "desparasitacao", clinico=True)
    with abas[3]:
      k = c.chave("consulta", animal["id"])
      anamnese = st.text_area("Anamnese e sinais clínicos", key=f"an_{k}")
      exames = st.text_area("Exames complementares", key=f"ex_{k}")
      receita = st.text_area("Prescrição", key=f"rx_{k}")
      if st.button("Guardar consulta e assinar", type="primary", key=f"gc_{k}"):
        if not anamnese.strip():
          st.warning("A anamnese é obrigatória.")
        else:
          try:
            sb.table("prontuario_medico").insert({
                "animal_id": animal["id"], "veterinario_id": user_id,
                "anamnese": anamnese.strip(), "exames_complementares": exames.strip() or None,
                "prescricao_medicamentosa": receita.strip() or None,
                "carimbo_digital": "auto",  # o servidor aplica o carimbo OMV
            }).execute()
            c.aviso("Consulta guardada com o teu carimbo digital.")
            c.novo_formulario()
            st.rerun()
          except Exception as e:
            st.error(erro(e))
    with abas[4]:
      c.secao_peso(sb, animal)
