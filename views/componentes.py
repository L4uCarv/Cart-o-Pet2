"""Componentes partilhados pelos painéis Tutor, Canil e Veterinário."""
import io
import uuid
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import qrcode
import streamlit as st

from services.supabase_client import erro
from utils import iban as iban_util
from utils import cio as cio_util
from utils import relatorios_pets as rp
from utils.exportar import para_excel
from utils.recibo_pdf import gerar_recibo_pdf
from utils.relatorios_pets_pdf import gerar_historico_pdf, gerar_resumo_pdf
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
  """Data dd/mm/aaaa; devolve — para vazio, None ou NaN (o pandas 3 usa NaN em colunas de texto)."""
  if d is None or d == "" or pd.isna(d):
    return "—"
  return date.fromisoformat(str(d)[:10]).strftime("%d/%m/%Y")


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


PORTES = {"pequeno": "Pequeno (até 10 kg)", "medio": "Médio (10 a 25 kg)", "grande": "Grande (mais de 25 kg)"}


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
  porte = None
  if especie == "Cão":
    porte = st.selectbox("Porte (define a idade do 1.º cio nas cadelas)", list(PORTES), index=1,
                         format_func=PORTES.get, key=f"porte_{k}")
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
          "data_nascimento": nasc.isoformat(), "microchip": chip.strip() or None, "porte": porte,
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

  st.markdown("**🏷️ Vinheta (obrigatória)**")
  vinheta = st.file_uploader("Carregar imagem da vinheta", type=["jpg", "jpeg", "png", "webp"], key=f"fic_{k}")

  if st.button("Guardar registo", type="primary", key=f"gravar_{k}"):
    if not produto.strip():
      st.warning("Indica o produto aplicado.")
    elif vinheta is None:
      st.warning("A imagem da vinheta é obrigatória.")
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


# ---------- cio: previsão (cadelas) e estimativa (gatas) ----------
def _datas_cio(sb, ids):
  por = {}
  if not ids:
    return por
  for x in sb.table("cios_animal").select("animal_id, data_inicio").in_("animal_id", ids).execute().data:
    por.setdefault(x["animal_id"], []).append(date.fromisoformat(x["data_inicio"]))
  return por


def _situacao_cio(r) -> str:
  if r["estado"] == "janela":
    return "na janela agora"
  if r["estado"] == "ultrapassado":
    return "ultrapassado: regista o cio, se já houve"
  return f"a partir de {fmt(r['inicio'].isoformat())}" if r["inicio"] else ""


def previsoes_cio(sb, animais):
  """Quadro com a previsão (cadelas) e a estimativa (gatas) de todas as fêmeas, mais avisos de proximidade."""
  fem = [a for a in animais if a.get("sexo") == "Fêmea" and a["especie"] in ("Cão", "Gato") and not a.get("esterilizado")]
  if not fem:
    return
  por = _datas_cio(sb, [a["id"] for a in fem])
  linhas, alertas = [], []
  for a in fem:
    r = cio_util.prever(a, por.get(a["id"], []))
    rotulo = "Estimativa" if a["especie"] == "Gato" else "Previsão"
    if not r["aplicavel"]:
      linhas.append({"Animal": a["nome"], "Tipo": rotulo, "Quando": "—", "Janela": "", "Confiança": "", "Situação": r["texto"]})
      continue
    linhas.append({"Animal": a["nome"], "Tipo": rotulo, "Quando": fmt(r["central"].isoformat()),
                   "Janela": f"{fmt(r['inicio'].isoformat())} a {fmt(r['fim'].isoformat())}",
                   "Confiança": r["confianca"], "Situação": _situacao_cio(r)})
    if r["alerta"]:
      alertas.append(f"🌸 **{a['nome']}** ({rotulo.lower()}): "
                     + ("está na janela do cio agora." if r["estado"] == "janela"
                        else f"cio possível a partir de {fmt(r['inicio'].isoformat())}."))
  with st.expander("🌸 Cio: previsões (cadelas) e estimativas (gatas)", expanded=bool(alertas)):
    for al in alertas:
      st.warning(al)
    st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)
    st.caption("Cadelas: **previsão** calculada com o histórico do próprio animal. Gatas: apenas uma **estimativa** orientativa. "
               "Regista os cios na ficha de cada animal para melhorar os resultados.")


def secao_cio(sb, animal):
  aid, cadela = animal["id"], animal["especie"] == "Cão"
  if cadela:
    st.info("🔮 **Previsão.** Nas cadelas o ciclo é regular, por isso a data é calculada a partir do histórico do próprio animal "
            "e fica mais precisa a cada cio registado.")
  else:
    st.warning("📍 **Estimativa.** Nas gatas o cio depende de muitos fatores (luz do dia, estação, acasalamento). "
               "O resultado é apenas uma estimativa orientativa, não uma previsão.")

  c1, c2 = st.columns(2)
  porte = animal.get("porte")
  if cadela:
    opcoes = list(PORTES)
    porte_novo = c1.selectbox("Porte", opcoes, index=opcoes.index(porte) if porte in opcoes else None, placeholder="Escolhe o porte",
                              format_func=PORTES.get, key=f"porte_{aid}")
  else:
    porte_novo = None
  esteril_novo = c2.checkbox("Esterilizada (castrada)", value=bool(animal.get("esterilizado")), key=f"esteril_{aid}")
  mudou = esteril_novo != bool(animal.get("esterilizado")) or (cadela and porte_novo != porte)
  if mudou and st.button("Guardar alterações", key=f"guardar_cio_{aid}"):
    try:
      upd = {"esterilizado": esteril_novo}
      if cadela:
        upd["porte"] = porte_novo
      sb.table("animais").update(upd).eq("id", aid).execute()
      aviso("Dados guardados.")
      st.rerun()
    except Exception as e:
      st.error(erro(e))

  cios = sb.table("cios_animal").select("*").eq("animal_id", aid).order("data_inicio").execute().data
  r = cio_util.prever(animal, [date.fromisoformat(x["data_inicio"]) for x in cios])
  st.subheader("Previsão do próximo cio" if cadela else "Estimativa do próximo cio")
  if not r["aplicavel"]:
    st.info(r["texto"])
  else:
    m1, m2, m3 = st.columns(3)
    m1.metric("Data central" if cadela else "Data aproximada", fmt(r["central"].isoformat()))
    m2.metric("Janela", f"{r['inicio'].strftime('%d/%m')} a {r['fim'].strftime('%d/%m/%Y')}")
    m3.metric("Confiança", r["confianca"])
    (st.warning if r["alerta"] else st.success)(r["texto"])
    for nota in r["notas"]:
      st.caption("• " + nota)
  st.caption("Não serve para escolher o melhor momento para acasalar: isso exige acompanhamento veterinário. "
             "Sinais como sangramento, vulva inchada ou mudança de comportamento valem mais do que qualquer previsão.")

  st.markdown("**Registar um cio**")
  k = chave("cio", aid)
  d1, d2 = st.columns([1, 2])
  data = d1.date_input("Data de início", value=date.today(), max_value=date.today(), key=f"cdata_{k}")
  obs = d2.text_input("Observações (opcional)", key=f"cobs_{k}")
  if st.button("Registar cio", type="primary", key=f"cbtn_{k}"):
    try:
      sb.table("cios_animal").insert({"animal_id": aid, "data_inicio": data.isoformat(), "observacoes": obs.strip() or None}).execute()
      aviso("Cio registado. A previsão foi atualizada.")
      novo_formulario()
      st.rerun()
    except Exception as e:
      st.error("Já existe um cio registado nessa data." if "duplicate" in erro(e).lower() else erro(e))

  if cios:
    st.markdown("**Cios registados**")
    anterior = None
    for x in reversed(cios):
      d = date.fromisoformat(x["data_inicio"])
      a1, a2, a3 = st.columns([2, 3, 1])
      a1.write(fmt(x["data_inicio"]))
      a2.caption((x.get("observacoes") or "") )
      if a3.button("Apagar", key=f"capagar_{x['id']}"):
        sb.table("cios_animal").delete().eq("id", x["id"]).execute()
        aviso("Registo apagado.")
        st.rerun()
    if len(cios) >= 2:
      ds = [date.fromisoformat(x["data_inicio"]) for x in cios]
      st.caption("Intervalos entre cios (dias): " + ", ".join(str((b - a).days) for a, b in zip(ds, ds[1:])))


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
  tem_cio = animal.get("sexo") == "Fêmea" and animal["especie"] in ("Cão", "Gato")
  nomes = ["📋 Histórico", "💉 Vacina", "💊 Desparasitação", "⚖️ Peso"] + (["🌸 Cio"] if tem_cio else []) + ["🩺 Veterinário", "🏡 Transferir"]
  abas = dict(zip(nomes, st.tabs(nomes)))
  with abas["📋 Histórico"]:
    historico(sb, animal)
  with abas["💉 Vacina"]:
    formulario_registo(sb, animal, "vacina")
  with abas["💊 Desparasitação"]:
    formulario_registo(sb, animal, "desparasitacao")
  with abas["⚖️ Peso"]:
    secao_peso(sb, animal)
  if tem_cio:
    with abas["🌸 Cio"]:
      secao_cio(sb, animal)
  with abas["🩺 Veterinário"]:
    secao_acesso_vet(sb, animal)
  with abas["🏡 Transferir"]:
    secao_transferir(sb, animal, user_id)


MAX_VINHETAS_PDF = 40


def relatorios_pets(sb, animais, tutor_nome):
  """Relatórios do tutor: resumo atual de todos os animais e histórico detalhado de cada um."""
  if not animais:
    st.info("Regista pelo menos um animal para gerar relatórios.")
    return
  tipo = st.radio("Tipo de relatório", ["📌 Resumo atual (dados mais recentes)", "📚 Histórico detalhado"], key="rp_tipo")
  detalhado = tipo.startswith("📚")
  com_fotos = False
  if detalhado:
    escolhidos = st.multiselect("Animais", animais, default=animais, format_func=lambda a: a["nome"], key="rp_animais")
    com_fotos = st.checkbox(f"Incluir as fotos das vinhetas no PDF (até {MAX_VINHETAS_PDF}; demora mais)", key="rp_fotos")
  else:
    escolhidos = animais
    st.caption("Um quadro por animal, com os dados do cadastro, o último peso, a última consulta e a situação atual de cada vacina e desparasitação.")
  if not escolhidos:
    st.info("Escolhe pelo menos um animal.")
    return

  ids = [a["id"] for a in escolhidos]
  regs = sb.table("registos_medicos_v2").select("*").in_("animal_id", ids).order("data_aplicacao", desc=True).execute().data
  cons = sb.table("prontuario_medico").select("*").in_("animal_id", ids).order("criado_at", desc=True).execute().data
  pesos = sb.table("pesos_animal").select("*").in_("animal_id", ids).order("medido_em", desc=True).execute().data

  if detalhado:
    folhas = rp.historico_dfs(escolhidos, regs, cons, pesos)
    nome_base = "historico_detalhado"
    abas = st.tabs(list(folhas))
    for aba, df in zip(abas, folhas.values()):
      with aba:
        st.dataframe(df, use_container_width=True, hide_index=True) if len(df) else st.caption("Sem registos.")
  else:
    resumo, situacao = rp.resumo_dfs(escolhidos, regs, cons, pesos)
    folhas = {"Resumo": resumo, "Situação das vacinas": situacao}
    nome_base = "resumo_animais"
    st.dataframe(resumo, use_container_width=True, hide_index=True)
    if len(situacao):
      st.markdown("**Situação de cada vacina e desparasitação**")
      st.dataframe(situacao, use_container_width=True, hide_index=True)

  hoje = date.today().isoformat()
  b1, b2 = st.columns(2)
  b1.download_button("⬇️ Excel", para_excel({k: v for k, v in folhas.items() if len(v)} or {"Vazio": pd.DataFrame()}),
                     file_name=f"{nome_base}_{hoje}.xlsx", key="rp_xlsx",
                     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
  assinatura = (detalhado, tuple(ids), com_fotos)
  if b2.button("📄 Gerar PDF", type="primary", key="rp_gerar"):
    with st.spinner("A gerar o PDF..."):
      try:
        if detalhado:
          imagens = {}
          if com_fotos:
            for r in [r for r in rp.ativos(regs) if r.get("comprovativo_url")][:MAX_VINHETAS_PDF]:
              try:
                imagens[r["comprovativo_url"]] = sb.storage.from_("vinhetas").download(r["comprovativo_url"])
              except Exception:
                pass
          pdf = gerar_historico_pdf(tutor_nome, escolhidos, regs, cons, pesos, imagens)
        else:
          pdf = gerar_resumo_pdf(tutor_nome, escolhidos, regs, cons, pesos)
        st.session_state["rp_pdf"] = (assinatura, pdf, f"{nome_base}_{hoje}.pdf")
      except Exception as e:
        st.error(erro(e))
  guardado = st.session_state.get("rp_pdf")
  if guardado and guardado[0] == assinatura:
    st.download_button("⬇️ Descarregar o PDF", guardado[1], file_name=guardado[2], mime="application/pdf", key="rp_pdf_dl")


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


def fmt_aoa(v) -> str:
  return f"{float(v):,.0f} AOA".replace(",", " ")


def empresa() -> dict:
  return {"nome": st.secrets.get("EMPRESA_NOME", "CartãoPet"),
          "nif": st.secrets.get("EMPRESA_NIF", ""), "morada": st.secrets.get("EMPRESA_MORADA", "")}


def estado_subscricao(sb, user_id):
  d = sb.table("perfis").select("subscricao_valida_ate").eq("id", user_id).execute().data
  return d[0]["subscricao_valida_ate"] if d else None


def mostrar_metodo_compacto(sb, m, bancos):
  """Versão pequena de um método de pagamento, para mostrar vários lado a lado."""
  if m["tipo"] == "IBAN":
    url = logo_banco(sb, bancos.get(m.get("banco_codigo") or ""))
    valor = iban_util.formatar(m["iban"])
  else:
    url, valor = None, m["telemovel"]
  c1, c2 = st.columns([1, 4])
  if url:
    c1.image(url, width=24)
  else:
    c1.markdown("🏦")
  c2.caption(f"**{m.get('banco_nome') or 'Multicaixa Express'}**  \n{m['titular']}")
  st.code(valor, language=None, wrap_lines=True)


def pagamentos(sb, user_id):
  ate = estado_subscricao(sb, user_id)
  if ate and date.fromisoformat(ate) >= date.today():
    st.success(f"✅ Subscrição ativa até **{fmt(ate)}**. Um novo pagamento prolonga a partir dessa data.")
  elif ate:
    st.warning(f"A tua subscrição terminou em {fmt(ate)}.")
  else:
    st.info("Ainda não tens subscrição ativa.")

  metodos = sb.table("metodos_pagamento").select("*").eq("ativo", True).order("criado_at").execute().data
  planos = sb.table("planos").select("*").eq("ativo", True).order("meses").execute().data
  bancos = bancos_por_codigo(sb) if metodos else {}
  if not metodos or not planos:
    st.info("A administração ainda não configurou os planos e os métodos de pagamento.")
  else:
    st.markdown("**1. Escolhe o tempo de subscrição**")
    k = chave("pag")
    plano = st.selectbox("Plano", planos, key=f"pl_{k}", format_func=lambda p: f"{p['nome']} · {fmt_aoa(p['preco'])}")
    st.metric("Valor a pagar", fmt_aoa(plano["preco"]), f"{plano['meses']} mês/meses de acesso", delta_color="off")
    st.markdown("**2. Faz o pagamento para um destes**")
    colunas = st.columns(min(len(metodos), 3))  # lado a lado (máx. 3 por linha)
    for i, m in enumerate(metodos):
      with colunas[i % len(colunas)]:
        with st.container(border=True):
          mostrar_metodo_compacto(sb, m, bancos)
    st.markdown("**3. Envia o comprovativo**")
    escolha = st.selectbox(
        "Paguei para", metodos, key=f"met_{k}",
        format_func=lambda m: f"{m.get('banco_nome') or m['tipo']} · "
                              + (iban_util.formatar(m["iban"])[-9:] if m["tipo"] == "IBAN" else m["telemovel"]))
    ref = st.text_input("Referência / descrição da transferência", key=f"ref_{k}")
    comp = st.file_uploader("Comprovativo", type=["jpg", "jpeg", "png", "pdf"], key=f"comp_{k}")
    if st.button("Submeter pagamento", type="primary", key=f"sub_{k}"):
      if not ref.strip() or comp is None:
        st.warning("Preenche a referência e anexa o comprovativo.")
      else:
        try:
          caminho = enviar_ficheiro(sb, "comprovativos", user_id, comp)
          sb.table("transacoes_pagamentos").insert({
              "utilizador_id": user_id, "metodo": escolha["tipo"], "metodo_pagamento_id": escolha["id"],
              "plano_id": plano["id"], "referencia": ref.strip(), "valor": plano["preco"],
              "estado": "Pendente", "comprovativo_url": caminho,
          }).execute()
          aviso("Pagamento submetido. Assim que for confirmado, a subscrição é atualizada e recebes o recibo.")
          novo_formulario()
          st.rerun()
        except Exception as e:
          st.error(erro(e))

  hist = sb.table("transacoes_pagamentos").select("criado_at, metodo, referencia, valor, meses, estado").eq("utilizador_id", user_id).order("criado_at", desc=True).execute().data
  if hist:
    st.markdown("**Os meus pagamentos**")
    df = pd.DataFrame(hist)
    df["criado_at"] = pd.to_datetime(df["criado_at"]).dt.strftime("%d/%m/%Y")
    st.dataframe(df.rename(columns={"criado_at": "Data", "metodo": "Método", "referencia": "Referência", "valor": "Valor", "meses": "Meses", "estado": "Estado"}),
                 use_container_width=True, hide_index=True)
  recibos = sb.table("recibos").select("*").eq("utilizador_id", user_id).order("emitido_em", desc=True).execute().data
  if recibos:
    st.markdown("**🧾 Os meus recibos**")
    for r in recibos:
      c1, c2 = st.columns([4, 1])
      c1.write(f"{r['numero']} · {fmt_aoa(r['valor'])} · válido até {fmt(r['valido_ate'])}")
      c2.download_button("PDF", gerar_recibo_pdf(r, empresa()), file_name=f"{r['numero']}.pdf", mime="application/pdf", key=f"rec_{r['id']}")
