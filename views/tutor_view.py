import io
from datetime import date, timedelta
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# Dicionário integrado de informações e intervalos de vacinas
INFO_VACINAS = {
    "Polivalente V10": {
        "cat": "Vacina Polivalente",
        "doencas": ["Cinomose", "Parvovirose", "Coronavirose", "Hepatite Infecciosa", "Adenovirose Tipo 2", "Parainfluenza", "Leptospirose"],
        "intervalo_filhote": 21,
        "intervalo_adulto": 365,
    },
    "Polivalente V8": {
        "cat": "Vacina Polivalente",
        "doencas": ["Cinomose", "Parvovirose", "Coronavirose", "Hepatite Infecciosa", "Adenovirose Tipo 2", "Parainfluenza"],
        "intervalo_filhote": 21,
        "intervalo_adulto": 365,
    },
    "Vacina Antirrábica": {
        "cat": "Vacina Essencial",
        "doencas": ["Raiva Canina"],
        "intervalo_filhote": 365,
        "intervalo_adulto": 365,
    },
    "Vacina contra Tosse dos Canis (Gripe)": {
        "cat": "Vacina Complementar",
        "doencas": ["Bordetella bronchiseptica", "Parainfluenza"],
        "intervalo_filhote": 21,
        "intervalo_adulto": 365,
    },
    "Vacina contra Giardíase": {
        "cat": "Vacina Complementar",
        "doencas": ["Giardia duodenalis"],
        "intervalo_filhote": 21,
        "intervalo_adulto": 365,
    },
}

# Dicionário com categorias, sugestões rápidas e os dias corretos de efeito
INFO_DESPARASITACAO = {
    "Desparasitação Interna ( Xarope)": {
        "cat": "Interna",
        "produtos_sugeridos": ["Drontal Plus", "Milbemax", "Canex", "Endogard", "Vetmax Plus"],
        "dias": 90,  # 3 meses
    },
    "Desparasitação Externa (Pipeta / Coleira / Spray)": {
        "cat": "Externa",
        "produtos_sugeridos": [ "Bravecto", "Simparica", "Frontline", "Seresto"],
        "dias": 30,  # 1 mês 
    },
    "Antipulgas (Comprimidos)": {
        "cat": "Externa", 
        "Produtos_sugeridos": ["NexGard", "Simparica"],
        "dias": 30, # 1 mês
    },
    
}


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
          dados_tabela = []
          for a in animais:
            animal_id = a["id"]
            
            res_v = supabase.table("registos_medicos_v2").select("nome_produto, proxima_dose").eq("animal_id", animal_id).eq("tipo", "vacina").order("data_aplicacao", desc=True).limit(1).execute()
            status_vacina = "Pendente"
            if res_v.data:
              v_info = res_v.data[0]
              status_vacina = f"{v_info['nome_produto']} (Próx: {v_info['proxima_dose']})"

            res_d = supabase.table("registos_medicos_v2").select("nome_produto, proxima_dose").eq("animal_id", animal_id).eq("tipo", "desparasitacao").order("data_aplicacao", desc=True).limit(1).execute()
            status_desp = "Pendente"
            if res_d.data:
              d_info = res_d.data[0]
              status_desp = f"{d_info['nome_produto']} (Próx: {d_info['proxima_dose']})"

            dados_tabela.append({
                "Nome": a["nome"],
                "Espécie": a["especie"],
                "Raça": a["raca"],
                "Sexo": a["sexo"],
                "Peso (kg)": a["peso"],
                "Vacina": status_vacina,
                "Desparasitação": status_desp
            })

          df_animais = pd.DataFrame(dados_tabela)
          st.dataframe(df_animais, use_container_width=True)
        else:
          st.info(
              "Ainda não tens animais registados. Usa o formulário ao lado para"
              " adicionar o primeiro!"
          )
      except Exception as e:
        st.warning(f"A carregar animais da base de dados... ({e})")

      st.markdown("---")
      st.subheader("Evolução de Peso e Crescimento")
      historico_ex = [
          {"data": "2026-02-10", "peso": 4.2},
          {"data": "2026-06-15", "peso": 4.8},
          {"data": "2026-09-20", "peso": 5.0},
      ]
      buf_peso = gerar_grafico_peso_pet(historico_ex)
      st.image(buf_peso)

    # --- DUAS COLUNAS LADO A LADO PARA VACINAS E DESPARASITAÇÕES ---
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

    col_vacina, col_desp = st.columns(2)

    # 1. COLUNA DE VACINAS INTELIGENTE
    with col_vacina:
      st.subheader("🛡️ Consulta de Vacinas")
      
      with st.popover("➕ Registar Nova Vacina"):
        st.markdown("**Registar Vacina Inteligente**")
        if not animais_lista:
          st.warning("Regista primeiro um animal.")
        else:
          pet_opcoes = {a["nome"]: a["id"] for a in animais_lista}
          pet_sel = st.selectbox("Selecionar Pet", list(pet_opcoes.keys()), key="sel_pet_v")
          pet_sel_id = pet_opcoes[pet_sel]

          nome_vacina = st.selectbox("Tipo de Vacina", list(INFO_VACINAS.keys()), key="input_nome_v")
          
          detalhes_vacina = INFO_VACINAS[nome_vacina]
          
          doencas_selecionadas = st.multiselect(
              "Doenças Cobertas (Pode ajustar/adicionar)",
              options=["Cinomose", "Parvovirose", "Coronavirose", "Hepatite Infecciosa", "Adenovirose Tipo 2", "Parainfluenza", "Leptospirose", "Raiva Canina", "Bordetella bronchiseptica", "Giardia duodenalis"],
              default=detalhes_vacina['doencas'],
              key="multiselect_doencas_v"
          )

          peso_vacina = st.number_input("Peso no Momento (kg)", min_value=0.0, max_value=100.0, value=5.0, key="input_peso_v")
          idade_vacina = st.text_input("Idade no Momento (Ex: 4 meses)", key="input_idade_v")
          
          data_aplicacao = st.date_input("Data Aplicação", value=date.today(), key="input_data_v")
          
          fase_etaria = st.radio("Fase do Pet para Intervalo", ["Filhote", "Adulto"], horizontal=True, key="fase_etaria_v")
          
          dias_intervalo = detalhes_vacina["intervalo_filhote"] if fase_etaria == "Filhote" else detalhes_vacina["intervalo_adulto"]
          proxima_dose_calculada = data_aplicacao + timedelta(days=dias_intervalo)
          
          st.success(f"📅 **Próximo Reforço Calculado:** {proxima_dose_calculada.strftime('%d/%m/%Y')}")

          if st.button("Salvar Vacina", type="primary", key="btn_salvar_v"):
            try:
              doencas_str = ", ".join(doencas_selecionadas)
              supabase.table("registos_medicos_v2").insert({
                  "animal_id": pet_sel_id,
                  "perfil_utilizador": "tutor",
                  "tipo": "vacina",
                  "nome_produto": f"{nome_vacina} ({doencas_str})",
                  "peso_clinico": peso_vacina,
                  "fabricante": idade_vacina,
                  "data_aplicacao": str(data_aplicacao),
                  "proxima_dose": str(proxima_dose_calculada),
              }).execute()
              st.success("Vacina registada com sucesso!")
              st.rerun()
            except Exception as e:
              st.error(f"Erro: {e}")

      st.markdown("---")
      st.markdown("**📋 Histórico de Vacinas**")
      try:
        res_all_v = supabase.table("registos_medicos_v2").select("nome_produto, peso_clinico, fabricante, data_aplicacao, proxima_dose").eq("tipo", "vacina").execute()
        if res_all_v.data:
          df_all_v = pd.DataFrame(res_all_v.data)
          df_all_v = df_all_v.rename(columns={
              "nome_produto": "Vacina & Doenças",
              "peso_clinico": "Peso (kg)",
              "fabricante": "Idade",
              "data_aplicacao": "Aplicação",
              "proxima_dose": "Próxima Dose"
          })
          st.dataframe(df_all_v[["Vacina & Doenças", "Peso (kg)", "Idade", "Aplicação", "Próxima Dose"]], use_container_width=True)
        else:
          st.info("Sem registos de vacinas.")
      except Exception:
        st.info("A carregar...")

    # 2. COLUNA DE DESPARASITAÇÕES COM SUGESTÕES RÁPIDAS + ESCRITA LIVRE E DIAS INTELIGENTES (30 ou 90 DIAS)
    with col_desp:
      st.subheader("💊 Consulta de Desparasitações")
      
      with st.popover("➕ Registar Nova Desparasitação"):
        st.markdown("**Registar Desparasitação Inteligente**")
        if not animais_lista:
          st.warning("Regista primeiro um animal.")
        else:
          pet_opcoes_d = {a["nome"]: a["id"] for a in animais_lista}
          pet_sel_d = st.selectbox("Selecionar Pet", list(pet_opcoes_d.keys()), key="sel_pet_d")
          pet_sel_d_id = pet_opcoes_d[pet_sel_d]

          tipo_desp_chave = st.selectbox("Categoria", list(INFO_DESPARASITACAO.keys()), key="input_tipo_d")
          dados_cat = INFO_DESPARASITACAO[tipo_desp_chave]

          # Exibe ajuda visual com as sugestões rápidas para consulta do utilizador
          sugestoes_str = ", ".join(dados_cat["produtos_sugeridos"])
          st.caption(f"💡 *Sugestões populares:* {sugestoes_str}")

          # Campo de texto totalmente livre onde podes escrever qualquer nome (Ex: Simparica, Vetmax Plus, Drontal, etc.)
          nome_produto_livre = st.text_input("Nome do Produto / Comprimido / Xarope", placeholder="Escreva o nome do produto...", key="input_livre_prod_d")

          peso_desp = st.number_input("Peso no Momento (kg)", min_value=0.0, max_value=100.0, value=5.0, key="input_peso_d")
          idade_desp = st.text_input("Idade no Momento (Ex: 6 meses)", key="input_idade_d")

          data_aplicacao_d = st.date_input("Data Aplicação", value=date.today(), key="input_data_d")
          
          # Cálculo automático dos dias correto (30 dias para externo como NexGard / Simparica, 90 dias para interno)
          dias_intervalo_d = dados_cat["dias"]
          proxima_dose_calc_d = data_aplicacao_d + timedelta(days=dias_intervalo_d)
          
          st.success(f"📅 **Próxima Dose Calculada ({dias_intervalo_d} dias):** {proxima_dose_calc_d.strftime('%d/%m/%Y')}")

          if st.button("Salvar Desparasitação", type="primary", key="btn_salvar_d"):
            if not nome_produto_livre:
              st.warning("Por favor, escreva o nome do produto ou comprimido.")
            else:
              try:
                cat_curta = dados_cat["cat"]
                supabase.table("registos_medicos_v2").insert({
                    "animal_id": pet_sel_d_id,
                    "perfil_utilizador": "tutor",
                    "tipo": "desparasitacao",
                    "nome_produto": f"{nome_produto_livre} ({cat_curta})",
                    "peso_clinico": peso_desp,
                    "fabricante": idade_desp,
                    "data_aplicacao": str(data_aplicacao_d),
                    "proxima_dose": str(proxima_dose_calc_d),
                }).execute()
                st.success("Desparasitação registada com sucesso!")
                st.rerun()
              except Exception as e:
                st.error(f"Erro: {e}")

      st.markdown("---")
      st.markdown("**📋 Histórico de Desparasitações**")
      try:
        res_all_d = supabase.table("registos_medicos_v2").select("nome_produto, peso_clinico, fabricante, data_aplicacao, proxima_dose").eq("tipo", "desparasitacao").execute()
        if res_all_d.data:
          df_all_d = pd.DataFrame(res_all_d.data)
          df_all_d = df_all_d.rename(columns={
              "nome_produto": "Produto & Categoria",
              "peso_clinico": "Peso (kg)",
              "fabricante": "Idade",
              "data_aplicacao": "Aplicação",
              "proxima_dose": "Próxima Dose"
          })
          st.dataframe(df_all_d[["Produto & Categoria", "Peso (kg)", "Idade", "Aplicação", "Próxima Dose"]], use_container_width=True)
        else:
          st.info("Sem registos de desparasitações.")
      except Exception:
        st.info("A carregar...")

  with tutor_tab2:
    st.header("Controlo Especializado para Fêmeas, Ninhadas e Adoções")
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(
        ["🌸 Calculadora de Cio", "🍼 Gestório de Ninhada", "🏡 Mapeamento de Adoções"]
    )

    with sub_tab1:
      st.subheader("Calculadora Preditiva de Ciclo Estral (Cio)")
      ultima_data_cio = st.date_input("Início do Último Cio Registado", value=date.today(), key="cio_data")
      ciclo_medio = st.number_input("Duração Média do Ciclo (Dias)", 120, 365, 180, key="cio_dias")

      if st.button("Calcular Período Fértil", key="btn_cio"):
        proximo_cio = ultima_data_cio + timedelta(days=ciclo_medio)
        inicio_fertil = proximo_cio + timedelta(days=9)
        fim_fertil = proximo_cio + timedelta(days=15)
        st.success(f"📅 **Previsão do Próximo Cio:** {proximo_cio.strftime('%d/%m/%Y')}")
        st.info(f"✨ **Janela Fértil:** Entre **{inicio_fertil.strftime('%d/%m/%Y')}** e **{fim_fertil.strftime('%d/%m/%Y')}**")

    with sub_tab2:
      st.subheader("Registo Detalhado por Ninhada")
      with st.form("form_ninhada"):
        nome_ninhada = st.text_input("Identificação da Ninhada / Mãe (Ex: Ninhada Luna)")
        data_nasc = st.date_input("Data de Nascimento", value=date.today(), key="ninhada_data")
        qtd_filhotes = st.number_input("Número de Filhotes Nascidos", 1, 20, 4)
        if st.form_submit_button("Guardar Ninhada"):
          st.success(f"Ninhada '{nome_ninhada}' registada com {qtd_filhotes} filhotes!")

    with sub_tab3:
      st.subheader("Mapeamento Pós-Adoção de Filhotes")
      with st.form("form_adocao"):
        filhote_nome = st.text_input("Nome / Microchip do Filhote")
        adotante_nome = st.text_input("Nome Completo do Adotante")
        if st.form_submit_button("Registar Adoção"):
          st.success(f"Adoção do filhote **{filhote_nome}** mapeada com sucesso!")

  with tutor_tab3:
    st.subheader("💳 Gestão de Pagamentos & Transações")
    st.info("Consulte aqui o histórico de pagamentos de consultas, exames e transações efetuadas via Multicaixa / IBAN.")

    with st.form("form_pagamento_tutor"):
      st.markdown("**Registar Pagamento / Comprovativo**")
      st.text_input("Descrição do Serviço (Ex: Consulta Veterinária)")
      st.number_input("Valor Pago (AOA)", min_value=0.0, value=5000.0)
      st.file_uploader("Comprovativo de Pagamento (MCX / Talão)", type=["jpg", "png", "pdf"])
      if st.form_submit_button("Submeter Comprovativo"):
        st.success("Comprovativo de pagamento submetido com sucesso!")
