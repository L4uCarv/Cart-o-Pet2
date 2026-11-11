# 🐾 CartãoPet

Cartão de vacinas e rastreio de animais de estimação. Python + Streamlit + Supabase.

## Perfis
| Perfil | Regras |
|---|---|
| **Tutor** | Até 4 animais. Regista vacinas/desparasitações **com foto da vinheta**, vê o histórico, dá acesso temporário ao veterinário por código/QR e transfere animais. |
| **Canil** (`criador`) | Até 4 membros (convite com aceitação), cada um com até 10 animais. Vê os animais dos membros, gere ninhadas e transferências. |
| **Veterinário** (`clinica`) | Abre fichas por código, regista vacinas e consultas (ficam **validadas**, com carimbo OMV) e tem a lista dos seus pacientes. |
| **Admin** (`super_admin`, `financeiro`) | Aprova Canis/Veterinários e valida pagamentos. |

Contas novas são sempre Tutor. Canil e Veterinário pedem-se na app e são aprovados por um admin.
Um admin cria-se à mão: no Supabase, `update perfis set papel = 'super_admin' where email = '...'`.

## Segurança
Toda a segurança está na base de dados (RLS, triggers e funções no Supabase); a app não decide permissões.
Usa **só** a chave anon/publishable. O cliente Supabase é criado por sessão (nunca em cache partilhada).

## Executar
```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # preencher
streamlit run app.py
```
Publicação: Streamlit Community Cloud (Secrets em *Settings*) ou `docker compose up`.

## Não incluído nesta versão
Relatório PDF, MFA real para admins, alertas por WhatsApp (`services/whatsapp_service.py` existe, sem uso),
vacinação em lote por ninhada, agenda/internamento/honorários da clínica.
