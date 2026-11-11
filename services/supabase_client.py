import streamlit as st
from supabase import Client, create_client


def cliente() -> Client:
  """Devolve o cliente Supabase DESTA sessão.

  Importante: nunca usar st.cache_resource para o cliente. Essa cache é
  partilhada por todos os utilizadores e o token de um utilizador passaria
  a ser usado nos pedidos dos outros.
  """
  if "sb" not in st.session_state:
    url = st.secrets.get("SUPABASE_URL", "")
    chave = st.secrets.get("SUPABASE_KEY", "")  # chave anon/publishable
    if not url or not chave:
      st.error("Faltam SUPABASE_URL e SUPABASE_KEY nos Secrets do Streamlit.")
      st.stop()
    st.session_state["sb"] = create_client(url, chave)
  return st.session_state["sb"]


def erro(e: Exception) -> str:
  """Texto legível de um erro da API (ex.: limite de animais atingido)."""
  return getattr(e, "message", None) or str(e)
