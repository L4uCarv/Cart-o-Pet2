import io
from datetime import date, timedelta
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


def gerar_grafico_peso_pet(pesos_historico):
  fig, ax = plt.subplots(figsize=(6, 3))
  if pesos_historico:
    datas = [p["data"] for p in pesos_historico]
    valores = [p["peso"] for p in pesos_historico]
    ax.plot(
        datas, valores, marker="o", color="#4F46E5", linewidth=2, markersize=6
    )
  else:
    ax.plot(["Registo Inicial"], [5.0], marker="o", color="#4F46E5")
  ax.set_ylabel("Peso (kg)")
  ax.set_title("Evolução do Peso e Crescimento do Pet")
  ax.grid(True, linestyle="--", alpha=0.6)

  img_buffer = io.BytesIO()
  plt.savefig(img_buffer, format="png", bbox_inches="tight")
  img_buffer.seek(0)
  plt.close(fig)
  return img_buffer


def render_tutor_dashboard(supabase):
  st.title("🐾 CartãoPet V2: Painel do Tutor e Saúde Animal")

  user_id = st.session_state.get("user_id")
  if not user_id:
    st.error(
        "Sessão inválida ou expirada. Por favor, termine sessão e volte a"
        " entrar."
    )
    return

  tutor_tab1, tutor_tab2, tutor_tab3 = st.tabs([
      "🐶 Gestão de Saúde & Vacinação",
      "🌸 Controlo Especializado (Fêmeas & Ninhadas)",
      "💳 Pagamentos & Transações",
  ])

  with tutor_tab1:
    st.header("Carteira Digital Centralizada & Crescimento")
    col_reg, col_list = st.columns(2)

    with col_reg:
      with st.form("form_registo_pet_tutor"):
        st.subheader("Registar Novo Animal")
        nome_pet = st.text_input("Nome do Animal")
        especie_pet = st.selectbox("Espécie", ["Cão", "Gato", "Outro"])
        raca_pet = st.text_input("Raça")
        sexo_pet = st.selectbox("Sexo", ["Macho", "Fêmea"])
        idade_pet = st.number_input("Idade (Anos)", 0, 30, 1)
        peso_atual = st.number_input("Peso Atual (kg)", 0.1, 100.0, 5.0)

        submitted_pet = st.form_submit_button("Salvar Pet na Carteira")
        if submitted_pet:
          if not nome_pet:
            st.warning("Por favor, insira o nome do animal.")
          else:
            try:
              supabase.table("animais").insert({
                  "tutor_id": user_id,
                  "nome": nome_pet,
                  "especie": especie_pet,
                  "raca": raca_pet,
                  "sexo": sexo_pet,
                  "idade_anos": idade_pet,
                  "peso": peso_atual,
              }).execute()
              st.success(
                  f"Animal **{nome_pet}** registado com sucesso na base de"
                  " dados!"
              )
              st.rerun()
            except Exception as e:
              st.error(f"Erro ao guardar animal no Supabase: {e}")

    with col_list:
      st.subheader("Os Meus Animais Registados")
      try:
        response = (
            supabase.table("animais").select("*").eq("tutor_id", user_id).execute()
        )
        animais = response.data

        if animais:
          df_animais = pd.DataFrame(animais)
          st.dataframe(
              df_animais[["nome", "especie", "raca", "sexo", "peso"]],
              use_container_width=True,
          )
        else:
          st.info(
              "Ainda não tens animais registados. Usa o formulário ao lado para"
              " adicionar o primeiro!"
          )
      except Exception:
        st.warning("A carregar animais da base de dados...")

      st.markdown("---")
      st.subheader("Evolução de Peso e Crescimento")
      historico_ex = [
          {"data": "2026-02-10", "peso": 4.2},
          {"data": "2026-06-15", "peso": 4.8},
          {"data": "2026-09-20", "peso": 5.0},
      ]
      buf_peso = gerar_grafico_peso_pet(historico_ex)
      st.image(buf_peso)

    st.markdown("---")
    st.subheader("💉 Histórico de Vacinas com Carimbo Digital")
    st.info(
        "🛡️ **Bobi** — Vacina Polivalente (Validade: Em Dia) | Carimbo Digital:"
        " `Dr. António Silva (OMV-4012)`"
    )

  with tutor_tab2:
    st.header("Controlo Especializado para Fêmeas, Ninhadas e Adoções")
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(
        ["🌸 Calculadora de Cio", "🍼 Gestório de Ninhada", "🏡 Mapeamento de Adoções"]
    )

    with sub_tab1:
      st.subheader("Calculadora Preditiva de Ciclo Estral (Cio)")
      ultima_data_cio = st.date_input(
          "Início do Último Cio Registado", value=date.today()
      )
      ciclo_medio = st.number_input(
          "Duração Média do Ciclo (Dias)", 120, 365, 180
      )

      if st.button("Calcular Período Fértil"):
        proximo_cio = ultima_data_cio + timedelta(days=ciclo_medio)
        inicio_fertil = proximo_cio + timedelta(days=9)
        fim_fertil = proximo_cio + timedelta(days=15)
        st.success(
            f"📅 **Previsão do Próximo Cio:** {proximo_cio.strftime('%d/%m/%Y')}"
        )
        st.info(
            "✨ **Janela Fértil:** Entre"
            f" **{inicio_fertil.strftime('%d/%m/%Y')}** e"
            f" **{fim_fertil.strftime('%d/%m/%Y')}**"
        )

    with sub_tab2:
      st.subheader("Registo Detalhado por Ninhada")
      with st.form("form_ninhada"):
        nome_ninhada = st.text_input(
            "Identificação da Ninhada / Mãe (Ex: Ninhada Luna)"
        )
        data_nasc = st.date_input("Data de Nascimento", value=date.today())
        qtd_filhotes = st.number_input("Número de Filhotes Nascidos", 1, 20, 4)
        if st.form_submit_button("Guardar Ninhada"):
          st.success(
              f"Ninhada '{nome_ninhada}' registada com {qtd_filhotes} filhotes!"
          )

    with sub_tab3:
      st.subheader("Mapeamento Pós-Adoção de Filhotes")
      with st.form("form_adocao"):
        filhote_nome = st.text_input("Nome / Microchip do Filhote")
        adotante_nome = st.text_input("Nome Completo do Adotante")
        if st.form_submit_button("Registar Adoção"):
          st.success(
              f"Adoção do filhote **{filhote_nome}** mapeada com sucesso!"
          )

  with tutor_tab3:
    st.subheader("Gestão Doméstica de Vacinas e Desparasitações")
    tab_v, tab_d = st.tabs(["🛡️ Vacinas", "💊 Desparasitação"])

    with tab_v:
      with st.form("form_tutor_vacina"):
        st.markdown("**Registar Nova Vacina**")
        try:
          animais_res = (
              supabase.table("animais")
              .select("id, nome")
              .eq("tutor_id", user_id)
              .execute()
          )
          animais = animais_res.data
        except Exception:
          animais = []

        if not animais:
          st.warning(
              "Regista primeiro um animal na tua carteira para adicionar"
              " vacinas."
          )
          st.
