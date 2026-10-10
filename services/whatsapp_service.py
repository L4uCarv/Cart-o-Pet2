import os
import requests
import streamlit as st


def enviar_whatsapp(telemovel: str, mensagem: str) -> bool:
  """Envia uma mensagem de texto via API de WhatsApp real configurada nas Secrets."""
  api_url = st.secrets.get("WHATSAPP_API_URL", "")
  api_token = st.secrets.get("WHATSAPP_API_TOKEN", "")

  if not api_url or not api_token:
    # Fallback de segurança se as chaves não estiverem definidas
    print(
        f"[SIMULAÇÃO WHATSAPP] Para {telemovel}: {mensagem}"
    )  # Visível nos logs do servidor
    return True

  headers = {
      "Content-Type": "application/json",
      "Authorization": f"Bearer {api_token}",
  }

  payload = {
      "phone": telemovel,
      "message": mensagem,
  }

  try:
    response = requests.post(api_url, json=payload, headers=headers, timeout=10)
    return response.status_code in [200, 201]
  except Exception as e:
    print(f"Erro ao enviar WhatsApp: {e}")
    return false