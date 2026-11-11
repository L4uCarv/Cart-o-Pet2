"""Componentes partilhados pelos painéis Tutor, Canil e Veterinário."""
import io
import uuid
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import qrcode
import streamlit as st

from services.supabase_client import erro
from utils import iban as iban_util
from utils.protocolos import INFO_DESPARASITACAO, INFO_VACINAS, calcular_idade_pet

EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "application/pdf": "pdf"}


# ---------- utilitários ----------
def aviso(msg: str):
  """Mensagem que sobrevive ao st.rerun() (mostrada no topo pela app)."""
  st.session_state["flash"] = msg


def novo_formulario():
  st.session_state["form_n"] = st.session_state.get("form_n", 0) + 1


def chave(*partes) -> str:
  return "_".join(str(p) for p in (*partes, st.session_state.get("form_n", 0)))


def fmt(d) -> str:
  return date.fromisoformat(str(d)[:10]).strftime("%d/%m/%Y") if d else "—"


def estado_reforco(proxima) -> str:
  if not proxima:
    return "sem reforço marcado"
  dias = (date.fromisoformat(str(proxima)) - date.today()).days
  if dias < 0:
    return f"🔴 atrasado há {-dias} dias"
  if dias <= 30:
    return f"🟠 reforço em {dias} dias"
  return f"🟢 próximo reforço {fmt(proxima)}"


def enviar_ficheiro(sb, bucket: str, pasta: str, ficheiro) -> str:
  caminho = f"{pasta}/{uuid.uuid4().hex}.{EXT.get(ficheiro.type, 'jpg')}"
  sb.storage.from_(bucket).upload(
      path=caminho,
      file=ficheiro.getvalue(),
      file_options={"content-type": ficheiro.type or "image/jpeg"},
  )
  return caminho


def url_assinada(sb, bucket: str, caminho: str):
  try:
    r = sb.storage.from_(bucket).create_signed_url(caminho, 3600)
    return r.get("signedURL") or r.get("signedUrl")
  except Exception:
    return None


# ---------- animais ----------
def meus_animais(sb, user_id):
  return (
      sb.table("animais").select("*").eq("tutor_id", user_id)
      .is_("arquivado_em", "null").order("nome").execute().data
  )


def registar_animal(sb, user_id):
  k = chave("novo")
  nome = st.text_input("Nome do animal", key=f"nome_{k}")
  c1, c2 = st.columns(2)
  especie = c1.selectbox("Espécie", ["Cão", "Gato", "Outro"], key=f"esp_{k}")
  raca = c2.text_input("Raça", key=f"raca_{k}")
  sexo = c1.selectbox("Sexo", ["Macho", "Fêmea"], key=f"sexo_{k}")
  nasc = c2.date_input("Data de nascimento", value=date.today(), max_value=date.today(), key=f"nasc_{k}")
  st.caption(f"📅 Idade: {calcular_idade_pet(nasc)[0]}")
  chip = st.text_input("Microchip (opcional)", key=f"chip_{k}")
  peso = st.number_input("Peso atual (kg)", 0.0, 100.0, 0.0, step=0.1, key=f"peso_{k}")
  if st.button("Guardar animal", type="primary", key=f"gravar_{k}"):
    if not nome.strip():
      st.warning("Indica o nome do animal.")
      return
    try:
      novo = sb.table("animais").insert({
          "tutor_id": user_id, "nome": nome.strip(), "especie": especie,
          "raca": raca.strip() or None, "sexo": sexo,
          "data_nascimento": nasc.isoformat(), "microchip": chip.strip() or None,
      }).execute().data[0]
      if peso > 0:
        sb.table("pesos_animal").insert({"animal_id": novo["id"], "peso_kg": peso}).execute()
      aviso(f"Animal **{nome.strip()}** registado.")
      novo_formulario()
      st.rerun()
    except Exception as e:
      st.error(erro(e))  # inclui a mensagem de limite de animais


# ---------- vacinas e desparasitações (vinheta obrigatória) ----------
def formulario_registo(sb, animal, tipo: str, clinico: bool = False):
  k = chave(tipo, animal["id"])
  if tipo == "vacina":
    produto = st.selectbox("Vacina", list(INFO_VACINAS), key=f"prod_{k}")
    info = INFO_VACINAS[produto]
    fase = st.radio("Fase do animal", ["Filhote", "Adulto"], horizontal=True, key=f"fase_{k}")
    dias = info["intervalo_filhote"] if fase == "Filhote" else info["intervalo_adulto"]
    espectro = ", ".join(info["doencas"])
  else:
    categoria = st.selectbox("Categoria", list(INFO_DESPARASITACAO), key=f"cat_{k}")
    dados = INFO_DESPARASITACAO[categoria]
    st.caption("💡 Sugestões: " + ", ".join(dados["produtos_sugeridos"]))
    produto = st.text_input("Produto aplicado", key=f"prod_{k}")
    dias, espectro = dados["dias"], dados["cat"]

  c1, c2 = st.columns(2)
  data = c1.date_input("Data de aplicação", value=date.today(), max_value=date.today(), key=f"data_{k}")
  proxima = c2.date_input("Próximo reforço", value=data + timedelta(days=dias), min_value=data, key=f"prox_{k}_{data}")
  c3, c4 = st.columns(2)
  lote = c3.text_input("Lote (da vinheta)", key=f"lote_{k}")
  validade = c4.date_input("Validade do lote", value=None, key=f"val_{k}")
  fabricante = st.text_input("Fabricante (opcional)", key=f"fab_{k}")
  extra = {}
  if clinico:
    c5, c6, c7 = st.columns(3)
    via = c5.selectbox("Via", ["Subcutânea", "Intramuscular", "Intranasal", "Oral", "Tópica"], key=f"via_{k}")
    peso = c6.number_input("Peso (kg)", 0.0, 100.0, 0.0, step=0.1, key=f"pc_{k}")
    temp = c7.number_input("Temp. (°C)", 0.0, 43.0, 0.0, step=0.1, key=f"tc_{k}")
    extra = {"via_administracao": via, "peso_clinico": peso or None, "temperatura_clinica": temp or None}

  st.markdown("**📸 Vinheta (obrigatória)**")
  foto = st.camera_input("Tirar foto da vinheta", key=f"cam_{k}")
  ficheiro = st.file_uploader("ou carregar ficheiro", type=["jpg", "jpeg", "png", "webp"], key=f"fic_{k}")
  vinheta = foto or ficheiro

  if st.button("Guardar registo", type="primary", key=f"gravar_{k}"):
    if not produto.strip():
      st.warning("Indica o produto aplicado.")
    elif vinheta is None:
      st.warning("A foto da vinheta é obrigatória.")
    elif validade and validade < data:
      st.warning("O lote já estava fora de validade na data de aplicação.")
    else:
      try:
        caminho = enviar_ficheiro(sb, "vinhetas", animal["id"], vinheta)
        sb.table("registos_medicos_v2").insert({
            "animal_id": animal["id"], "perfil_utilizador": "tutor",  # o servidor corrige
            "tipo": tipo, "nome_produto": produto.strip(),
            "data_aplicacao": data.isoformat(), "proxima_dose": proxima.isoformat(),
            "comprovativo_url": caminho, "numero_lote": lote.strip() or None,
            "data_validade": validade.isoformat() if validade else None,
            "fabricante": fabricante.strip() or None, "espectro_finalidade": espectro,
            **extra,
        }).execute()
        aviso("Registo guardado com a vinheta.")
        novo_formulario()
        st.rerun()
      except Exception as e:
        st.error(erro(e))


def historico(sb, animal):
  """Linha do tempo do animal: vacinas, desparasitações e consultas."""
  aid = animal["id"]
  regs = sb.table("registos_medicos_v2").select("*").eq("animal_id", aid).order("data_aplicacao", desc=True).execute().data
  consultas = sb.table("prontuario_medico").select("*").eq("animal_id", aid).order("criado_at", desc=True).execute().data
  substituidos = {r["substitui_id"] for r in regs if r.get("substitui_id")}
  eventos = [(r["data_aplicacao"], "registo", r) for r in regs if r["id"] not in substituidos]
  eventos += [(c["criado_at"][:10], "consulta", c) for c in consultas]
  eventos.sort(key=lambda e: e[0], reverse=True)

  filtro = st.radio("Mostrar", ["Tudo", "Vacinas", "Desparasitações", "Consultas"], horizontal=True, key=f"filtro_{aid}")
  mostrados = 0
  for data, kind, r in eventos:
    if filtro == "Vacinas" and not (kind == "registo" and r["tipo"] == "vacina"):
      continue
    if filtro == "Desparasitações" and not (kind == "registo" and r["tipo"] == "desparasitacao"):
      continue
    if filtro == "Consultas" and kind != "consulta":
      continue
    mostrados += 1
    with st.container(border=True):
      if kind == "consulta":
        st.markdown(f"**🩺 Consulta** · {fmt(data)}")
        st.write(r["anamnese"])
        if r.get("prescricao_medicamentosa"):
          st.caption(f"Prescrição: {r['prescricao_medicamentosa']}")
        st.caption(f"✅ {r['carimbo_digital']}")
      else:
        icone = "💉" if r["tipo"] == "vacina" else "💊"
        st.markdown(f"**{icone} {r['nome_produto']}** · {fmt(data)}")
        st.caption(estado_reforco(r.get("proxima_dose")))
        detalhes = [x for x in [f"lote {r['numero_lote']}" if r.get("numero_lote") else "",
                                f"validade {fmt(r['data_validade'])}" if r.get("data_validade") else "",
                                r.get("fabricante") or ""] if x]
        if detalhes:
          st.caption(" · ".join(detalhes))
        if r.get("validado_por"):
          st.caption(f"✅ Validado por veterinário ({r.get('carimbo_digital_omv') or 'OMV'})")
        else:
          st.caption("Registo do tutor / canil (não validado)")
        with st.expander("Ver vinheta"):
          url = url_assinada(sb, "vinhetas", r["comprovativo_url"])
          st.image(url) if url else st.caption("Vinheta indisponível.")
  if not mostrados:
    st.info("Sem registos para mostrar.")


# ---------- peso ----------
def secao_peso(sb, animal, pode_registar: bool = True):
  aid = animal["id"]
  pesos = sb.table("pesos_animal").select("peso_kg, medido_em").eq("animal_id", aid).order("medido_em").execute().data
  if len(pesos) >= 2:
    df = pd.DataFrame(pesos)
    df["medido_em"] = pd.to_datetime(df["medido_em"])
    st.line_chart(df.set_index("medido_em")["peso_kg"])
  elif pesos:
    st.metric("Último peso", f"{pesos[0]['peso_kg']} kg")
  else:
    st.info("Ainda sem pesos registados.")
  if pode_registar:
    kg = st.number_input("Novo peso (kg)", 0.0, 100.0, 0.0, step=0.1, key=chave("kg", aid))
    if st.button("Registar peso", key=chave("btnkg", aid)):
      if kg <= 0:
        st.warning("Indica um peso válido.")
      else:
        try:
          sb.table("pesos_animal").insert({"animal_id": aid, "peso_kg": kg}).execute()
          aviso("Peso registado.")
          novo_formulario()
          st.rerun()
        except Exception as e:
          st.error(erro(e))


# ---------- acesso do veterinário (QR) ----------
def secao_acesso_vet(sb, animal):
  aid = animal["id"]
  st.caption("Gera um código temporário (10 minutos, uso único). O veterinário usa-o para abrir esta ficha durante 30 dias.")
  if st.button("Gerar código e QR", key=f"qr_{aid}"):
    try:
      st.session_state[f"codigo_{aid}"] = sb.rpc("gerar_codigo_acesso", {"p_animal": aid}).execute().data
    except Exception as e:
      st.error(erro(e))
  codigo = st.session_state.get(f"codigo_{aid}")
  if codigo:
    st.code(codigo)
    buf = io.BytesIO()
    qrcode.make(codigo).save(buf, format="PNG")
    st.image(buf.getvalue(), width=200)
  st.markdown("**Veterinários com acesso**")
  agora = pd.Timestamp.now(tz="UTC")
  acessos = sb.rpc("acessos_do_animal", {"p_animal": aid}).execute().data or []
  ativos = [a for a in acessos if not a["revogado_em"] and pd.Timestamp(a["expira_em"]) > agora]
  if not ativos:
    st.caption("Nenhum acesso ativo.")
  for a in ativos:
    c1, c2 = st.columns([3, 1])
    c1.write(f"{a['veterinario_nome']} · até {fmt(a['expira_em'])}")
    if c2.button("Revogar", key=f"rev_{a['acesso_id']}"):
      sb.table("acessos_veterinario").update({"revogado_em": datetime.now(timezone.utc).isoformat()}).eq("id", a["acesso_id"]).execute()
      aviso("Acesso revogado.")
      st.rerun()


# ---------- transferência de titularidade ----------
def secao_transferir(sb, animal, user_id):
  aid = animal["id"]
  pend = sb.table("transferencias_titularidade").select("*").eq("animal_id", aid).eq("estado", "pendente").execute().data
  if pend:
    t = pend[0]
    st.info(f"Transferência pendente para **{t['para_email']}** (expira em {fmt(t['expira_em'])}).")
    if st.button("Cancelar transferência", key=f"canc_{t['id']}"):
      sb.table("transferencias_titularidade").update({"estado": "cancelada"}).eq("id", t["id"]).execute()
      aviso("Transferência cancelada.")
      st.rerun()
    return
  st.caption("O novo tutor recebe a ficha completa, com histórico e vinhetas, e o acesso dos veterinários é revogado.")
  email = st.text_input("E-mail do novo tutor", key=chave("tmail", aid))
  if st.button("Iniciar transferência", key=chave("tbtn", aid)):
    if "@" not in email:
      st.warning("Indica um e-mail válido.")
    else:
      try:
        sb.table("transferencias_titularidade").insert({
            "animal_id": aid, "de_tutor_id": user_id,
            "para_email": email.strip().lower(), "animal_nome": animal["nome"],
        }).execute()
        aviso("Transferência iniciada. O destinatário tem de aceitar.")
        novo_formulario()
        st.rerun()
      except Exception as e:
        st.error(erro(e))


def caixa_transferencias(sb, user_id, email):
  recebidas = (
      sb.table("transferencias_titularidade").select("*").eq("estado", "pendente")
      .ilike("para_email", email).neq("de_tutor_id", user_id).execute().data
  )
  for t in recebidas:
    with st.container(border=True):
      st.markdown(f"🏡 Recebeste a transferência do animal **{t.get('animal_nome') or ''}**")
      c1, c2 = st.columns(2)
      if c1.button("Aceitar", type="primary", key=f"acc_{t['id']}"):
        try:
          sb.rpc("aceitar_transferencia", {"p_id": t["id"]}).execute()
          aviso("Animal transferido para a tua conta.")
          st.rerun()
        except Exception as e:
          st.error(erro(e))
      if c2.button("Recusar", key=f"rec_{t['id']}"):
        sb.rpc("recusar_transferencia", {"p_id": t["id"]}).execute()
        aviso("Transferência recusada.")
        st.rerun()


def caixa_convites(sb):
  for c in sb.rpc("meus_convites").execute().data or []:
    with st.container(border=True):
      if c["aceite"]:
        st.caption(f"Fazes parte do canil **{c['canil_nome']}** (até 10 animais).")
      else:
        st.markdown(f"🐕 O canil **{c['canil_nome']}** convidou-te como membro.")
        if st.button("Aceitar convite", key=f"conv_{c['canil_id']}"):
          sb.rpc("aceitar_convite_canil", {"p_canil": c["canil_id"]}).execute()
          aviso("Convite aceite.")
          st.rerun()


# ---------- painel de um animal ----------
def painel_animal(sb, animais, user_id, dono: bool = True):
  if not animais:
    st.info("Ainda não há animais para mostrar.")
    return
  animal = st.selectbox("Animal", animais, format_func=lambda a: f"{a['nome']} ({a['especie']})", key=chave("sel", dono))
  idade = calcular_idade_pet(date.fromisoformat(animal["data_nascimento"]))[0] if animal.get("data_nascimento") else "idade desconhecida"
  st.caption(f"{animal.get('raca') or animal['especie']} · {animal.get('sexo') or ''} · {idade}"
             + (f" · microchip {animal['microchip']}" if animal.get("microchip") else ""))
  if not dono:
    historico(sb, animal)
    return
  abas = st.tabs(["📋 Histórico", "💉 Vacina", "💊 Desparasitação", "⚖️ Peso", "🩺 Veterinário", "🏡 Transferir"])
  with abas[0]:
    historico(sb, animal)
  with abas[1]:
    formulario_registo(sb, animal, "vacina")
  with abas[2]:
    formulario_registo(sb, animal, "desparasitacao")
  with abas[3]:
    secao_peso(sb, animal)
  with abas[4]:
    secao_acesso_vet(sb, animal)
  with abas[5]:
    secao_transferir(sb, animal, user_id)


# ---------- credenciamento e pagamentos ----------
def pedido_credenciamento(sb, user_id):
  atual = sb.table("parceiros").select("*").eq("perfil_id", user_id).execute().data
  if atual:
    p = atual[0]
    st.info(f"Pedido de conta **{'Canil' if p['papel_solicitado'] == 'criador' else 'Veterinário'}**: estado **{p['estado_credenciamento']}**. "
            "Quando for aprovado, termina a sessão e volta a entrar.")
    return
  st.caption("Contas Canil e Veterinário são aprovadas manualmente pela administração.")
  tipo = st.selectbox("Tipo de conta", ["criador", "clinica"], format_func=lambda x: "Canil / Criador" if x == "criador" else "Veterinário", key="ped_tipo")
  num = st.text_input("Nº da cédula profissional (OMV) ou da licença do canil", key="ped_num")
  if st.button("Pedir credenciamento", key="ped_btn"):
    if not num.strip():
      st.warning("Indica o número.")
      return
    try:
      sb.table("parceiros").insert({"perfil_id": user_id, "numero_ordem": num.strip(), "papel_solicitado": tipo, "estado_credenciamento": "pendente"}).execute()
      aviso("Pedido enviado.")
      st.rerun()
    except Exception as e:
      st.error(erro(e))


# ---------- métodos de pagamento e bancos ----------
def bancos_por_codigo(sb) -> dict:
  return {b["codigo"]: b for b in sb.table("bancos").select("*").execute().data}


def logo_banco(sb, banco):
  """Logótipo do banco: ficheiro carregado > ícone do site do banco > nada."""
  if not banco:
    return None
  if banco.get("logo_path"):
    return sb.storage.from_("logos-bancos").get_public_url(banco["logo_path"])
  if banco.get("dominio"):
    return f"https://www.google.com/s2/favicons?domain={banco['dominio']}&sz=128"
  return None


def linha_banco(sb, banco, titulo: str, legenda: str = ""):
  c1, c2 = st.columns([1, 8])
  url = logo_banco(sb, banco)
  if url:
    c1.image(url, width=40)
  else:
    c1.markdown("🏦")
  c2.markdown(f"**{titulo}**" + (f"  \n{legenda}" if legenda else ""))


def mostrar_metodo(sb, m, bancos):
  banco = bancos.get(m.get("banco_codigo") or "")
  if m["tipo"] == "IBAN":
    linha_banco(sb, banco, m.get("banco_nome") or "Banco", f"Titular: {m['titular']}")
    st.code(iban_util.formatar(m["iban"]), language=None)
  else:
    linha_banco(sb, None, "Multicaixa Express", f"Titular: {m['titular']}")
    st.code(m["telemovel"], language=None)


def pagamentos(sb, user_id):
  metodos = sb.table("metodos_pagamento").select("*").eq("ativo", True).order("criado_at").execute().data
  bancos = bancos_por_codigo(sb) if metodos else {}
  if not metodos:
    st.info("A administração ainda não configurou métodos de pagamento.")
  else:
    st.markdown("**Onde pagar**")
    for m in metodos:
      with st.container(border=True):
        mostrar_metodo(sb, m, bancos)
    k = chave("pag")
    escolha = st.selectbox(
        "Paguei para", metodos, key=f"met_{k}",
        format_func=lambda m: f"{m.get('banco_nome') or m['tipo']} · "
                              + (iban_util.formatar(m["iban"])[-9:] if m["tipo"] == "IBAN" else m["telemovel"]))
    valor = st.number_input("Valor (AOA)", min_value=0.0, value=5000.0, step=500.0, key=f"val_{k}")
    ref = st.text_input("Referência / descrição", key=f"ref_{k}")
    comp = st.file_uploader("Comprovativo", type=["jpg", "jpeg", "png", "pdf"], key=f"comp_{k}")
    if st.button("Submeter pagamento", type="primary", key=f"sub_{k}"):
      if not ref.strip() or comp is None or valor <= 0:
        st.warning("Preenche a referência, o valor e anexa o comprovativo.")
      else:
        try:
          caminho = enviar_ficheiro(sb, "comprovativos", user_id, comp)
          sb.table("transacoes_pagamentos").insert({
              "utilizador_id": user_id, "metodo": escolha["tipo"], "metodo_pagamento_id": escolha["id"],
              "referencia": ref.strip(), "valor": valor, "estado": "Pendente", "comprovativo_url": caminho,
          }).execute()
          aviso("Pagamento submetido para validação.")
          novo_formulario()
          st.rerun()
        except Exception as e:
          st.error(erro(e))
  hist = sb.table("transacoes_pagamentos").select("criado_at, metodo, referencia, valor, estado").eq("utilizador_id", user_id).order("criado_at", desc=True).execute().data
  if hist:
    st.dataframe(pd.DataFrame(hist), use_container_width=True, hide_index=True)
