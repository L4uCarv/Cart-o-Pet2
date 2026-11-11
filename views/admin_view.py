import pandas as pd
import streamlit as st

from services.supabase_client import erro
from views import componentes as c


def render_admin_dashboard(sb, papel):
  st.title("🛠️ Administração")
  nomes = ["💳 Pagamentos"] if papel == "financeiro" else ["🏥 Credenciamentos", "💳 Pagamentos"]
  abas = st.tabs(nomes)

  if papel != "financeiro":
    with abas[0]:
      pend = sb.table("parceiros").select("*").eq("estado_credenciamento", "pendente").execute().data
      if not pend:
        st.info("Sem pedidos pendentes.")
      perfis = {}
      if pend:
        ids = [p["perfil_id"] for p in pend]
        perfis = {x["id"]: x for x in sb.table("perfis").select("id, nome, email").in_("id", ids).execute().data}
      for p in pend:
        quem = perfis.get(p["perfil_id"], {})
        with st.container(border=True):
          st.markdown(f"**{quem.get('nome', '?')}** · {quem.get('email', '')}")
          st.caption(f"Pede conta: {'Canil' if p['papel_solicitado'] == 'criador' else 'Veterinário'} · nº {p['numero_ordem']}")
          c1, c2 = st.columns(2)
          if c1.button("Aprovar", type="primary", key=f"ap_{p['id']}"):
            try:
              sb.table("perfis").update({"papel": p["papel_solicitado"]}).eq("id", p["perfil_id"]).execute()
              sb.table("parceiros").update({"estado_credenciamento": "ativo"}).eq("id", p["id"]).execute()
              c.aviso("Conta aprovada.")
              st.rerun()
            except Exception as e:
              st.error(erro(e))
          if c2.button("Recusar", key=f"rj_{p['id']}"):
            sb.table("parceiros").update({"estado_credenciamento": "suspenso"}).eq("id", p["id"]).execute()
            c.aviso("Pedido recusado.")
            st.rerun()

  with abas[-1]:
    pend = sb.table("transacoes_pagamentos").select("*").eq("estado", "Pendente").order("criado_at").execute().data
    if not pend:
      st.info("Sem pagamentos pendentes.")
    for t in pend:
      with st.container(border=True):
        st.markdown(f"**{t['valor']} AOA** · {t['metodo']} · {t['referencia']}")
        url = c.url_assinada(sb, "comprovativos", t["comprovativo_url"]) if t.get("comprovativo_url") else None
        if url:
          st.link_button("Ver comprovativo", url)
        c1, c2 = st.columns(2)
        if c1.button("Aprovar", type="primary", key=f"pa_{t['id']}"):
          sb.table("transacoes_pagamentos").update({"estado": "Aprovado"}).eq("id", t["id"]).execute()
          c.aviso("Pagamento aprovado.")
          st.rerun()
        if c2.button("Rejeitar", key=f"pr_{t['id']}"):
          sb.table("transacoes_pagamentos").update({"estado": "Rejeitado"}).eq("id", t["id"]).execute()
          c.aviso("Pagamento rejeitado.")
          st.rerun()
