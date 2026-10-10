import streamlit as st
from supabase import Client, create_client

SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")


@st.cache_resource
def get_supabase_client() -> Client:
  if not SUPABASE_URL or not SUPABASE_KEY:
    st.error(
        "As credenciais do Supabase não foram encontradas nas Secrets do"
        " Streamlit!"
    )
    st.stop()
  return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase = get_supabase_client()