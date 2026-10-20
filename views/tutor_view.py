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


def calcular_idade_pet(data_nascimento):
  hoje = date.today()
  if data_nascimento > hoje:
    return "Data inválida", 0.0

  anos = hoje.year - data_nascimento.year
  meses = hoje.month - data_nascimento.month
  dias = hoje.day - data_nascimento.day

  if dias < 0:
    meses -= 1
  if meses < 0:
    anos -= 1
    meses += 12

  total_meses = anos * 12 + meses
  idade_anos_decimal = round(total_meses / 12, 1)

  if total_meses < 1:
    return "Menos de 1 mês", idade_anos_decimal
  elif total_meses < 12:
    return f"{total_meses} meses", idade_anos_decimal
  elif anos == 1:
    return f"1 ano e {meses} meses" if meses > 0 else "1 ano", idade_anos_decimal
  else:
    return f"{anos} anos e {meses} meses" if meses > 0 else f"{anos} anos", idade_anos_decimal


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
      st.subheader("Registar Novo Animal")

      nome_pet = st.text_input("Nome do Animal", key="reg_nome_pet")
      especie_pet = st.selectbox("Espécie", ["Cão", "Gato", "Outro"], key="reg_esp_pet")
      raca_pet = st.text_input("Raça", key="reg_raca_pet")
      sexo_pet = st.selectbox("Sexo", ["Macho", "Fêmea"], key="reg_sexo_pet")

      data_nasc_pet = st.date_input(
          "Data de Nascimento do Pet",
          value=date.today(),
          max_value=date.today(),
          key="reg_data_nasc"
      )
      
      descricao_idade, idade_decimal = calcular_idade_pet(data_nasc_pet)
      st.info(f"📅 Idade calculada automaticamente: **{descricao_idade}**")

      peso_atual = st.number_input("Peso Atual (kg)", min_value=0.0, max_value=100.0, value=0.0, key="reg_peso_pet")

      if st.button("Salvar Pet na Carteira", type="primary"):
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
                "idade_anos": idade_decimal,
                "peso": peso_atual,
            }).execute()
            st.success(f"Animal **{nome_pet}** registado com sucesso na base de dados!")
            
            # Remover as chaves da sessão para redefinir os campos no próximo rerun
            for k in ["reg_nome_pet", "reg_esp_pet", "reg_raca_pet", "reg_sexo_pet", "reg_data_nasc", "reg_peso_pet"]:
              if k in st.session_state:
                del st.session_state[k]
            
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

    # --- SEÇÃO UNIFICADA DE VACINAS E DESPARASITAÇÕES NA ABA 1 ---
    st.markdown("---")
    st.header("💉 Gestão de Vacinas & Desparasitações")

    try:
      animais_res_geral = (
          supabase.table("animais")
          .select("id, nome")
          .eq("tutor_id", user_id)
          .execute()
      )
      animais_lista = animais_res_geral.data
    except Exception:
      animais_lista = []

    sub_v, sub_d = st.tabs(["🛡️ Registar & Consultar Vacinas", "💊 Registar & Consultar Desparasitações"])

    with sub_v:
      with st.form("form_tutor_vacina_aba1"):
        st.markdown("**Registar Nova Vacina**")
        if not animais_lista:
          st.warning("Regista primeiro um animal na tua carteira para adicionar vacinas.")
          st.form_submit_button("Guardar", disabled=True)
          pet_sel_id = None
        else:
          pet_opcoes = {a["nome"]: a["id"] for a in animais_lista}
          pet_sel = st.selectbox("Selecionar Pet", list(pet_opcoes.keys()))
          pet_sel_id = pet_opcoes[pet_sel]

          nome_vacina = st.text_input("Nome da Vacina / Doenças Cobertas (Ex: V8, V10, Raiva)")
          data_aplicacao = st.date_input("Data de Aplicação")
          proxima_dose = st.date_input("Data do Próximo Reforço")

          if st.form_submit_button("Registar Vacina"):
            try:
              supabase.table("registos_medicos_v2").insert({
                  "animal_id": pet_sel_id,
                  "perfil_utilizador": "tutor",
                  "tipo": "vacina",
                  "nome_produto": nome_vacina,
                  "data_aplicacao": str(data_aplicacao),
                  "proxima_dose": str(proxima_dose),
              }).execute()
              st.success("Vacina registada com sucesso na caderneta digital!")
              st.rerun()
            except Exception as e:
              st.error(f"Erro ao registar vacina: {e}")

      st.markdown("---")
      st.subheader("📋 Histórico de Vacinas")
      if animais_lista:
        pet_cons_v = st.selectbox("Selecionar Pet para Consultar Vacinas", list(pet_opcoes.keys()), key="cons_v_aba1")
        id_cons_v = pet_opcoes[pet_cons_v]
        try:
          res_v = (
              supabase.table("registos_medicos_v2")
              .select("*")
              .eq("animal_id", id_cons_v)
              .eq("tipo", "vacina")
              .execute()
          )
          if res_v.data:
            df_v = pd.DataFrame(res_v.data)
            st.dataframe(df_v[["nome_produto", "data_aplicacao", "proxima_dose", "perfil_utilizador"]], use_container_width=True)
          else:
            st.info("Ainda não existem vacinas registadas para este pet.")
        except Exception as e:
          st.warning(f"A carregar registos... ({e})")
      else:
        st.info("Sem animais para consultar.")

    with sub_d:
      with st.form("form_tutor_desp_aba1"):
        st.markdown("**Registar Desparasitação (Interna ou Externa)**")
        if not animais_lista:
          st.warning("Regista primeiro um animal.")
          st.form_submit_button("Guardar", disabled=True)
          pet_sel_d_id = None
        else:
          pet_opcoes_d = {a["nome"]: a["id"] for a in animais_lista}
          pet_sel_d = st.selectbox("Selecionar Pet", list(pet_opcoes_d.keys()), key="pet_d_aba1")
          pet_sel_d_id = pet_opcoes_d[pet_sel_d]

          tipo_desp = st.selectbox("Tipo de Desparasitação", ["Interna (Comprimido/Xarope)", "Externa (Pipeta/Coleira)"])
          nome_produto = st.text_input("Nome do Produto (Ex: Drontal, NexGard)")
          data_aplicacao_d = st.date_input("Data de Aplicação", key="d_app_aba1")
          proxima_dose_d = st.date_input("Próxima Dose Recomendada", key="d_prox_aba1")

          if st.form_submit_button("Registar Desparasitação"):
            try:
              supabase.table("registos_medicos_v2").insert({
                  "animal_id": pet_sel_d_id,
                  "perfil_utilizador": "tutor",
                  "tipo": "desparasitacao",
                  "nome_produto": f"{tipo_desp} - {nome_produto}",
                  "data_aplicacao": str(data_aplicacao_d),
                  "proxima_dose": str(proxima_dose_d),
              }).execute()
              st.success("Desparasitação registada com sucesso!")
              st.rerun()
            except Exception as e:
              st.error(f"Erro ao registar desparasitação: {e}")

      st.markdown("---")
      st.subheader("📋 Histórico de Desparasitações")
      if animais_lista:
        pet_cons_d = st.selectbox("Selecionar Pet para Consultar Desparasitações", list(pet_opcoes.keys()), key="cons_d_aba1")
        id_cons_d = pet_opcoes[pet_cons_d]
        try:
          res_d = (
              supabase.table("registos_medicos_v2")
              .select("*")
              .eq("animal_id", id_cons_d)
              .eq("tipo", "desparasitacao")
              .execute()
          )
          if res_d.data:
