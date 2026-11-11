import pandas as pd
import streamlit as st

from services.supabase_client import erro
from utils import iban as iban_util
from views import componentes as c

PAPEIS = ["tutor", "criador", "clinica", "financeiro", "moderador", "super_admin"]
NOMES_PAPEL = {"tutor": "Tutor", "criador": "Canil", "clinica": "Veterinário",
               "financeiro": "Financeiro", "moderador": "Moderador", "super_admin": "Super admin"}


def auditar(sb, acao: str, detalhes: str = ""):
  """Regista a ação do administrador no audit_logs."""
  try:
    sb.table("audit_logs").insert({"admin_id": st.session_state["user_id"], "acao": acao, "detalhes": detalhes}).execute()
  except Exception:
    pass  # a auditoria nunca deve bloquear a ação


def serie(lista, nome):
  if not lista:
    return pd.DataFrame({nome: []})
  df = pd.DataFrame(lista).rename(columns={"n": nome}).set_index("mes")
  return df[[nome]].astype(float)


def fmt_aoa(v) -> str:
  return f"{float(v):,.0f} AOA".replace(",", " ")


def visao_geral(sb):
  try:
    k = sb.rpc("admin_kpis").execute().data
  except Exception as e:
    st.error(erro(e))
    return
  c0, c1 = st.columns([4, 1])
  c0.subheader("Visão geral da plataforma")
  if c1.button("🔄 Atualizar", key="adm_refresh"):
    st.rerun()

  if k["pedidos_pendentes"] or k["pagamentos_pendentes"]:
    st.warning(f"⚠️ {k['pedidos_pendentes']} pedido(s) de credenciamento e "
               f"{k['pagamentos_pendentes']} pagamento(s) à espera de validação.")

  total_users = sum(k["utilizadores"].values())
  validados = (k["registos_validados"] / k["registos"] * 100) if k["registos"] else 0
  a = st.columns(4)
  a[0].metric("Utilizadores", total_users, f"+{k['novos_utilizadores_30d']} em 30 dias")
  a[1].metric("Animais ativos", k["animais"])
  a[2].metric("Registos de saúde", k["registos"], f"+{k['registos_30d']} em 30 dias")
  a[3].metric("Consultas", k["consultas"])
  b = st.columns(4)
  b[0].metric("Reforços em atraso", k["reforcos_atrasados"])
  b[1].metric("Reforços nos próximos 30 dias", k["reforcos_30d"])
  b[2].metric("Registos validados por veterinário", f"{validados:.0f}%")
  b[3].metric("Acessos de veterinário ativos", k["acessos_vet_ativos"])
  d = st.columns(4)
  d[0].metric("Veterinários ativos", k["veterinarios_ativos"])
  d[1].metric("Canis ativos", k["canis_ativos"])
  d[2].metric("Receita aprovada", fmt_aoa(k["receita_aprovada"]), f"{fmt_aoa(k['receita_30d'])} em 30 dias")
  d[3].metric("Transferências pendentes", k["transferencias_pendentes"])

  st.markdown("---")
  g1, g2 = st.columns(2)
  with g1:
    st.markdown("**Registos de saúde por mês**")
    st.bar_chart(serie(k["serie_registos"], "Registos"))
    st.markdown("**Utilizadores por perfil**")
    perfis = pd.DataFrame({"Utilizadores": {NOMES_PAPEL.get(p, p): n for p, n in k["utilizadores"].items()}})
    st.bar_chart(perfis)
  with g2:
    st.markdown("**Novos utilizadores por mês**")
    st.bar_chart(serie(k["serie_utilizadores"], "Novos utilizadores"))
    st.markdown("**Animais por espécie**")
    if k["especies"]:
      st.bar_chart(pd.DataFrame({"Animais": k["especies"]}))
    else:
      st.caption("Sem animais.")
  st.markdown("**Receita aprovada por mês (AOA)**")
  st.bar_chart(serie(k["serie_receita"], "Receita"))


def credenciamentos(sb):
  pend = sb.table("parceiros").select("*").eq("estado_credenciamento", "pendente").execute().data
  if not pend:
    st.info("Sem pedidos pendentes.")
  perfis = {}
  if pend:
    ids = [p["perfil_id"] for p in pend]
    perfis = {x["id"]: x for x in sb.table("perfis").select("id, nome, email").in_("id", ids).execute().data}
  for p in pend:
    quem = perfis.get(p["perfil_id"], {})
    tipo = "Canil" if p["papel_solicitado"] == "criador" else "Veterinário"
    with st.container(border=True):
      st.markdown(f"**{quem.get('nome', '?')}** · {quem.get('email', '')}")
      st.caption(f"Pede conta: {tipo} · nº {p['numero_ordem']}")
      c1, c2 = st.columns(2)
      if c1.button("Aprovar", type="primary", key=f"ap_{p['id']}"):
        try:
          sb.table("perfis").update({"papel": p["papel_solicitado"]}).eq("id", p["perfil_id"]).execute()
          sb.table("parceiros").update({"estado_credenciamento": "ativo"}).eq("id", p["id"]).execute()
          auditar(sb, "CREDENCIAMENTO_APROVADO", f"{quem.get('email')} como {tipo}")
          c.aviso("Conta aprovada.")
          st.rerun()
        except Exception as e:
          st.error(erro(e))
      if c2.button("Recusar", key=f"rj_{p['id']}"):
        sb.table("parceiros").update({"estado_credenciamento": "suspenso"}).eq("id", p["id"]).execute()
        auditar(sb, "CREDENCIAMENTO_RECUSADO", f"{quem.get('email')} como {tipo}")
        c.aviso("Pedido recusado.")
        st.rerun()


def pagamentos(sb):
  pend = sb.table("transacoes_pagamentos").select("*").eq("estado", "Pendente").order("criado_at").execute().data
  if not pend:
    st.info("Sem pagamentos pendentes.")
  for t in pend:
    with st.container(border=True):
      st.markdown(f"**{fmt_aoa(t['valor'])}** · {t['metodo']} · {t['referencia']}")
      url = c.url_assinada(sb, "comprovativos", t["comprovativo_url"]) if t.get("comprovativo_url") else None
      if url:
        st.link_button("Ver comprovativo", url)
      c1, c2 = st.columns(2)
      if c1.button("Aprovar", type="primary", key=f"pa_{t['id']}"):
        sb.table("transacoes_pagamentos").update({"estado": "Aprovado"}).eq("id", t["id"]).execute()
        auditar(sb, "PAGAMENTO_APROVADO", f"{t['referencia']} · {t['valor']} AOA")
        c.aviso("Pagamento aprovado.")
        st.rerun()
      if c2.button("Rejeitar", key=f"pr_{t['id']}"):
        sb.table("transacoes_pagamentos").update({"estado": "Rejeitado"}).eq("id", t["id"]).execute()
        auditar(sb, "PAGAMENTO_REJEITADO", f"{t['referencia']} · {t['valor']} AOA")
        c.aviso("Pagamento rejeitado.")
        st.rerun()
  with st.expander("Histórico de pagamentos"):
    hist = sb.table("transacoes_pagamentos").select("criado_at, metodo, referencia, valor, estado").neq("estado", "Pendente").order("criado_at", desc=True).limit(100).execute().data
    if hist:
      st.dataframe(pd.DataFrame(hist), use_container_width=True, hide_index=True)
    else:
      st.caption("Ainda sem histórico.")


def utilizadores(sb):
  dados = sb.rpc("admin_utilizadores").execute().data or []
  if not dados:
    st.info("Sem utilizadores.")
    return
  df = pd.DataFrame(dados)
  f1, f2 = st.columns([1, 2])
  filtro = f1.selectbox("Perfil", ["Todos"] + PAPEIS, format_func=lambda p: p if p == "Todos" else NOMES_PAPEL[p], key="u_filtro")
  busca = f2.text_input("Pesquisar por nome ou e-mail", key="u_busca")
  if filtro != "Todos":
    df = df[df["papel"] == filtro]
  if busca:
    m = df["nome"].str.contains(busca, case=False, na=False) | df["email"].str.contains(busca, case=False, na=False)
    df = df[m]
  vis = df.rename(columns={"nome": "Nome", "email": "E-mail", "papel": "Perfil", "criado_at": "Criado em", "n_animais": "Animais"})
  vis["Perfil"] = vis["Perfil"].map(lambda p: NOMES_PAPEL.get(p, p))
  vis["Criado em"] = pd.to_datetime(vis["Criado em"]).dt.strftime("%d/%m/%Y")
  st.dataframe(vis[["Nome", "E-mail", "Perfil", "Animais", "Criado em"]], use_container_width=True, hide_index=True)

  st.markdown("**Alterar perfil de um utilizador**")
  st.caption("Para Canil e Veterinário, prefere aprovar o pedido em *Credenciamentos*: o veterinário só usa códigos de acesso com credenciamento ativo.")
  outros = [u for u in dados if u["id"] != st.session_state["user_id"]]
  alvo = st.selectbox("Utilizador", outros, format_func=lambda u: f"{u['nome']} · {u['email']}", key="u_alvo")
  novo = st.selectbox("Novo perfil", PAPEIS, format_func=lambda p: NOMES_PAPEL[p], key="u_novo")
  ok = st.checkbox("Confirmo a alteração", key="u_ok")
  if st.button("Alterar perfil", key="u_btn", disabled=not ok):
    try:
      sb.table("perfis").update({"papel": novo}).eq("id", alvo["id"]).execute()
      auditar(sb, "PAPEL_ALTERADO", f"{alvo['email']}: {alvo['papel']} → {novo}")
      c.aviso("Perfil alterado. O utilizador deve terminar sessão e voltar a entrar.")
      st.rerun()
    except Exception as e:
      st.error(erro(e))


def auditoria(sb):
  logs = sb.table("audit_logs").select("criado_at, admin_id, acao, detalhes").order("criado_at", desc=True).limit(200).execute().data
  if not logs:
    st.info("Ainda sem ações registadas.")
    return
  ids = list({x["admin_id"] for x in logs})
  nomes = {p["id"]: p["email"] for p in sb.table("perfis").select("id, email").in_("id", ids).execute().data}
  df = pd.DataFrame(logs)
  df["Administrador"] = df["admin_id"].map(lambda i: nomes.get(i, i))
  df["Quando"] = pd.to_datetime(df["criado_at"]).dt.strftime("%d/%m/%Y %H:%M")
  st.dataframe(df.rename(columns={"acao": "Ação", "detalhes": "Detalhes"})[["Quando", "Administrador", "Ação", "Detalhes"]],
               use_container_width=True, hide_index=True)


def metodos_pagamento(sb):
  bancos = c.bancos_por_codigo(sb)
  st.subheader("Novo método de pagamento")
  tipo = st.radio("Tipo", ["IBAN", "MCX"], format_func=lambda x: "IBAN (conta bancária)" if x == "IBAN" else "Multicaixa Express (telemóvel)",
                  horizontal=True, key=c.chave("mp_tipo"))
  titular = st.text_input("Titular da conta", key=c.chave("mp_tit"))
  dados, novo_banco, pronto = {"tipo": tipo, "titular": titular.strip()}, None, False

  if tipo == "IBAN":
    txt = st.text_input("IBAN", placeholder="AO06 0055 0000 9209 3133 1015 2", key=c.chave("mp_iban"))
    s = iban_util.normalizar(txt)
    if s:
      if not iban_util.valido(s):
        st.error("IBAN inválido: confirma os dígitos (o angolano tem 25 caracteres).")
      else:
        dados["iban"] = s
        codigo = iban_util.codigo_banco(s)
        banco = bancos.get(codigo) if codigo else None
        if banco:
          with st.container(border=True):
            c.linha_banco(sb, banco, f"✅ {banco['nome']}", f"Código {codigo} · {iban_util.formatar(s)}")
          pronto = True
        else:
          st.warning(f"O banco com código {codigo or 'estrangeiro'} ainda não está na lista. Indica-o uma vez e fica guardado para os próximos IBAN.")
          nome = st.text_input("Nome do banco", key=c.chave("mp_bnome"))
          dominio = st.text_input("Site do banco, para obter o logótipo (ex.: bancobic.ao)", key=c.chave("mp_bdom"))
          logo = st.file_uploader("ou carregar o logótipo (PNG/JPG, máx. 1 MB)", type=["png", "jpg", "jpeg", "webp"], key=c.chave("mp_blogo"))
          if dominio.strip():
            c.linha_banco(sb, {"dominio": dominio.strip()}, nome or "Pré-visualização")
          dados["banco_nome"] = nome.strip()
          if codigo:
            novo_banco = {"codigo": codigo, "nome": nome.strip(), "dominio": dominio.strip() or None, "_logo": logo}
          pronto = bool(nome.strip())
  else:
    dados["telemovel"] = st.text_input("Nº de telemóvel Multicaixa Express", key=c.chave("mp_tel"))
    pronto = bool(dados["telemovel"].strip())

  if st.button("Guardar método", type="primary", key=c.chave("mp_btn"), disabled=not (pronto and titular.strip())):
    try:
      if novo_banco:
        logo = novo_banco.pop("_logo")
        if logo is not None:
          novo_banco["logo_path"] = c.enviar_ficheiro(sb, "logos-bancos", novo_banco["codigo"], logo)
        sb.table("bancos").insert(novo_banco).execute()
      sb.table("metodos_pagamento").insert(dados).execute()
      auditar(sb, "METODO_PAGAMENTO_CRIADO", f"{tipo} · {titular.strip()}")
      c.aviso("Método de pagamento guardado.")
      c.novo_formulario()
      st.rerun()
    except Exception as e:
      st.error(erro(e))

  st.markdown("---")
  st.subheader("Métodos configurados")
  metodos = sb.table("metodos_pagamento").select("*").order("criado_at", desc=True).execute().data
  if not metodos:
    st.info("Ainda não há métodos.")
  for m in metodos:
    with st.container(border=True):
      c.mostrar_metodo(sb, m, bancos)
      st.caption(("🟢 Ativo" if m["ativo"] else "⚪ Desativado"))
      b1, b2 = st.columns(2)
      if b1.button("Desativar" if m["ativo"] else "Ativar", key=f"mpa_{m['id']}"):
        sb.table("metodos_pagamento").update({"ativo": not m["ativo"]}).eq("id", m["id"]).execute()
        auditar(sb, "METODO_PAGAMENTO_ALTERADO", f"{m['titular']} → {'desativado' if m['ativo'] else 'ativado'}")
        st.rerun()
      if b2.button("Apagar", key=f"mpd_{m['id']}"):
        try:
          sb.table("metodos_pagamento").delete().eq("id", m["id"]).execute()
          auditar(sb, "METODO_PAGAMENTO_APAGADO", m["titular"])
          st.rerun()
        except Exception:
          st.error("Este método já tem pagamentos associados. Desativa-o em vez de o apagar.")

  with st.expander("🏦 Bancos e logótipos"):
    st.markdown("**➕ Cadastrar novo banco**")
    st.caption("O código são os 4 dígitos que aparecem nas posições 5 a 8 de um IBAN angolano (ex.: AO06 **0055** ...).")
    n1, n2 = st.columns(2)
    n_cod = n1.text_input("Código do banco (4 dígitos)", max_chars=4, key=c.chave("nb_cod"))
    n_nome = n2.text_input("Nome do banco", key=c.chave("nb_nome"))
    n3, n4 = st.columns(2)
    n_sigla = n3.text_input("Sigla (opcional)", key=c.chave("nb_sigla"))
    n_dom = n4.text_input("Site (ex.: bancobic.ao)", key=c.chave("nb_dom"))
    n_logo = st.file_uploader("Logótipo (opcional, PNG/JPG, máx. 1 MB)", type=["png", "jpg", "jpeg", "webp"], key=c.chave("nb_logo"))
    if st.button("Guardar novo banco", key=c.chave("nb_btn")):
      if not (n_cod.isdigit() and len(n_cod) == 4) or not n_nome.strip():
        st.warning("Indica um código de 4 dígitos e o nome do banco.")
      elif n_cod in bancos:
        st.warning(f"O código {n_cod} já existe ({bancos[n_cod]['nome']}). Edita-o na lista abaixo.")
      else:
        try:
          novo = {"codigo": n_cod, "nome": n_nome.strip(), "sigla": n_sigla.strip() or None, "dominio": n_dom.strip() or None}
          if n_logo is not None:
            novo["logo_path"] = c.enviar_ficheiro(sb, "logos-bancos", n_cod, n_logo)
          sb.table("bancos").insert(novo).execute()
          auditar(sb, "BANCO_CRIADO", f"{n_cod} · {n_nome.strip()}")
          c.aviso("Banco cadastrado.")
          c.novo_formulario()
          st.rerun()
        except Exception as e:
          st.error(erro(e))
    st.markdown("---")
    st.markdown("**Bancos cadastrados**")
    if bancos:
      alvo = st.selectbox("Banco", list(bancos.values()), format_func=lambda b: f"{b['codigo']} · {b['nome']}", key="bk_sel")
      c.linha_banco(sb, alvo, alvo["nome"], f"Código {alvo['codigo']}" + (f" · {alvo['dominio']}" if alvo.get("dominio") else ""))
      dom = st.text_input("Site do banco (para o logótipo automático)", value=alvo.get("dominio") or "", key=f"bk_dom_{alvo['codigo']}")
      img = st.file_uploader("Carregar logótipo oficial (substitui o automático)", type=["png", "jpg", "jpeg", "webp"], key=f"bk_img_{alvo['codigo']}")
      if st.button("Guardar banco", key=f"bk_btn_{alvo['codigo']}"):
        try:
          upd = {"dominio": dom.strip() or None}
          if img is not None:
            upd["logo_path"] = c.enviar_ficheiro(sb, "logos-bancos", alvo["codigo"], img)
          sb.table("bancos").update(upd).eq("codigo", alvo["codigo"]).execute()
          c.aviso("Banco atualizado.")
          st.rerun()
        except Exception as e:
          st.error(erro(e))


def render_admin_dashboard(sb, papel):
  st.title("🛠️ Painel de Administração")
  if papel == "financeiro":
    abas = st.tabs(["💳 Pagamentos", "🏦 Métodos de pagamento"])
    funcoes = [pagamentos, metodos_pagamento]
  else:
    abas = st.tabs(["📊 Visão geral", "🏥 Credenciamentos", "💳 Pagamentos", "🏦 Métodos de pagamento", "👥 Utilizadores", "🧾 Auditoria"])
    funcoes = [visao_geral, credenciamentos, pagamentos, metodos_pagamento, utilizadores, auditoria]
  for aba, funcao in zip(abas, funcoes):
    with aba:
      funcao(sb)
