import streamlit as st
import pandas as pd
import hmac
from utils.data_utils import processar_questionarios_excel, get_col

# --------------------------
# CONFIGURAÇÃO DA PÁGINA
# --------------------------
st.set_page_config(page_title="Dashboard KPI & Qualidade", layout="wide", initial_sidebar_state="collapsed")

# Esconder o menu lateral automático do Streamlit
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("<style>[data-testid='stMetricValue'] { font-size: 25px; }</style>", unsafe_allow_html=True)

# ... resto do código (autenticação, sidebar, etc.)
# ============================================
# 🔒 SISTEMA DE AUTENTICAÇÃO
# ============================================

def verificar_autenticacao():
    """Verifica se o utilizador está autenticado"""
    if st.session_state.get("autenticado", False):
        return True
    
    st.title("🔒 Acesso Restrito")
    st.markdown("### Esta aplicação é privada")
    st.markdown("Introduza a palavra-passe para continuar.")
    
    password_input = st.text_input("Palavra-passe:", type="password", key="login_password")
    
    if st.button("🔓 Entrar", use_container_width=True):
        try:
            password_correta = st.secrets["password"]
        except KeyError:
            st.error("⚠️ Erro de configuração: Password não definida nos Secrets")
            st.info("Contacte o administrador da aplicação.")
            return False
        
        if hmac.compare_digest(password_input, password_correta):
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("❌ Palavra-passe incorreta!")
            return False
    
    return False

# Se não autenticado, mostra apenas o formulário de login (sem sidebar)
if not verificar_autenticacao():
    st.stop()

# ============================================
# A PARTIR DAQUI, UTILIZADOR AUTENTICADO
# ============================================

# ============================================
# INICIALIZAÇÃO DO ESTADO
# ============================================
if 'cursos_df' not in st.session_state: 
    st.session_state.cursos_df = None
if 'quest_df' not in st.session_state: 
    st.session_state.quest_df = None
if 'filtro_centro' not in st.session_state: 
    st.session_state.filtro_centro = []
if 'pagina' not in st.session_state:
    st.session_state.pagina = "📚 Cursos"

# ============================================
# BARRA LATERAL (só aparece após login)
# ============================================

st.sidebar.title("📁 Gestão de Dados")
# Menu de navegação
st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 Navegação - Balanços e Relatórios")
if st.sidebar.button("Relatórios", use_container_width=True, key="nav_relatorios"):
    st.session_state.pagina = "📚 Balanços e Relatórios"   # sem "E Balanços"
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 Navegação - Questionários de avaliação")
if st.sidebar.button("📋 Questionários", use_container_width=True, key="nav_quest"):
    st.session_state.pagina = "📋 Questionários"
    st.rerun()


# Menu de navegação
st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 Navegação - Gestão de Qualidade")

if st.sidebar.button("📚 Cursos", use_container_width=True, key="nav_cursos"):
    st.session_state.pagina = "📚 Cursos"
    st.rerun()

if st.sidebar.button("🎯 Gestão de Qualidade", use_container_width=True, key="nav_qualidade"):
    st.session_state.pagina = "🎯 Gestão de Qualidade"
    st.rerun()

if st.sidebar.button("📊 Dashboard", use_container_width=True, key="nav_dashboard"):
    st.session_state.pagina = "📊 Dashboard"
    st.rerun()

if st.sidebar.button("⚔️ Comparador Versus -  EM DESENVOLVIMENTO", use_container_width=True, key="nav_comparador"):
    st.session_state.pagina = "⚔️ Comparador Versus"
    st.rerun()





# ============================================
# CONTEÚDO PRINCIPAL (BASEADO NA SELEÇÃO)
# ============================================

if st.session_state.pagina == "📚 Cursos":
    from Pages.cursos import mostrar_cursos
    mostrar_cursos()

elif st.session_state.pagina == "📚 Relatórios":
    from Pages.balancos_e_relatorios import mostrar_relatorios
    mostrar_relatorios()

elif st.session_state.pagina == "📋 Questionários":
    from Pages.questionarios import mostrar_questionarios
    mostrar_questionarios()

elif st.session_state.pagina == "🎯 Gestão de Qualidade":
    from Pages.qualidade import mostrar_qualidade
    mostrar_qualidade()

elif st.session_state.pagina == "⚔️ Comparador Versus":
    from Pages.comparador import mostrar_comparador
    mostrar_comparador()

elif st.session_state.pagina == "📊 Dashboard":
    from Pages.dashboardformacoes import mostrar_dashboard
    mostrar_dashboard()


    # Botão de logout (agora na sidebar, mais intuitivo)
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair", use_container_width=True, help="Terminar sessão"):
    st.session_state.clear()
    st.rerun()
st.sidebar.markdown("---")
