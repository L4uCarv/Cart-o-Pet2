import pandas as pd
import streamlit as st

from services.supabase_client import erro
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


def render_admin_dashboard(sb, papel):
  st.title("🛠️ Painel de Administração")
  if papel == "financeiro":
    (aba,) = st.tabs(["💳 Pagamentos"])
    with aba:
      pagamentos(sb)
    return
  abas = st.tabs(["📊 Visão geral", "🏥 Credenciamentos", "💳 Pagamentos", "👥 Utilizadores", "🧾 Auditoria"])
  for aba, funcao in zip(abas, [visao_geral, credenciamentos, pagamentos, utilizadores, auditoria]):
    with aba:
      funcao(sb)
