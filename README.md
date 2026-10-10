# 🐾 CartãoPet V2 - Gestão Veterinária Inteligente

> Sistema completo e seguro para cartões de vacina de animais de estimação, com perfis multi-nível, integração com base de dados cloud e relatórios analíticos em PDF.

## 🚀 Sobre o Projeto
O **CartãoPet V2** é uma aplicação web desenvolvida em **Python** com **Streamlit**, desenhada para simplificar o controlo de saúde animal (vacinas e desparasitações). Funciona como uma plataforma centralizada onde Tutores, Criadores, Clínicas e Administradores colaboram de forma segura.

## ✨ Funcionalidades Principais
* **Autenticação e Perfis Multi-Nível:** Permissões segmentadas para *Tutor*, *Criador*, *Clínica* e *Admin*.
* **Base de Dados Cloud:** Dados sincronizados em tempo real através do **Supabase**.
* **Relatórios PDF Avançados:** Geração de cartões e histórico médico em PDF utilizando `fpdf2` com gráficos analíticos gerados por `matplotlib`.
* **Calendário e Alertas:** Acompanhamento visual de datas de próximas doses de vacinação e desparasitação.
* **Pronto para Cloud:** Configurado para deploy rápido e gratuito no **Streamlit Cloud**.

## 🛠️ Tecnologias Utilizadas
* **Frontend & Lógica:** Python, Streamlit
* **Base de Dados & Auth:** Supabase (PostgreSQL)
* **Visualização de Dados:** Matplotlib, Pandas
* **Geração de Documentos:** FPDF2
* **Containerização:** Docker & Docker Compose

## 🗂️ Estrutura do Repositório
```text
cartaopet/
├── .streamlit/
│   └── config.toml
├── assets/
│   └── style.css
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── schema.sql
└── app.py