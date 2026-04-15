import streamlit as st

# Importar módulos
from config import setup_page_config, initialize_session_state
from auth import verificar_autenticacao, mostrar_logout
from components.filters import sidebar_uploaders
from pages.cursos import mostrar_cursos
from pages.questionarios import mostrar_questionarios
from pages.qualidade import mostrar_qualidade
from pages.comparador import mostrar_comparador

# Configuração inicial
setup_page_config()
initialize_session_state()

# Verificar autenticação
if not verificar_autenticacao():
    st.stop()

# Mostrar logout e sidebar
mostrar_logout()
sidebar_uploaders()

# Navegação
pagina = st.radio("📌 Navegação", ["📚 Cursos", "📋 Questionários", "🎯 Gestão de Qualidade", "⚔️ Comparador Versus"], horizontal=True)

# Router para as páginas
if pagina == "📚 Cursos":
    mostrar_cursos()
elif pagina == "📋 Questionários":
    mostrar_questionarios()
elif pagina == "🎯 Gestão de Qualidade":
    mostrar_qualidade()
elif pagina == "⚔️ Comparador Versus":
    mostrar_comparador()