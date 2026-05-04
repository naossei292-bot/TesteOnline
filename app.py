import streamlit as st
import pandas as pd
import hmac
from datetime import datetime, timedelta
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

# ============================================
# 🔒 SISTEMA DE AUTENTICAÇÃO SIMPLES
# ============================================

def obter_passwords_config():
    """Obtém as passwords das secrets."""
    try:
        passwords_config = st.secrets["passwords"]
        # Converte bytes para string se necessário
        passwords_config_str = {}
        for role, pwd in passwords_config.items():
            if isinstance(pwd, bytes):
                passwords_config_str[role] = pwd.decode('utf-8')
            else:
                passwords_config_str[role] = str(pwd)
        return passwords_config_str
    except (KeyError, AttributeError):
        st.error("🔐 Erro: Configuração de passwords não encontrada!")
        st.stop()
        return {}

def verificar_autenticacao():
    """Verifica a password e mantém sessão."""
    
    # Verificar se já está autenticado
    if st.session_state.get("autenticado", False):
        return True
    
    # Verificar se existe sessão guardada (apenas para o mesmo browser/aba)
    if "sessao_guardada" in st.session_state:
        return True
    
    # Mostrar formulário de login
    st.title("🔒 Acesso Restrito")
    st.markdown("### Esta aplicação é privada")
    st.markdown("Introduza a sua palavra-passe para continuar.")
    
    password_input = st.text_input("Palavra-passe:", type="password", key="login_password")
    
    if st.button("🔓 Entrar", use_container_width=True, type="primary"):
        passwords_config = obter_passwords_config()
        
        # Verifica qual password corresponde
        role_encontrado = None
        for role, pwd_correta in passwords_config.items():
            try:
                if hmac.compare_digest(password_input.encode('utf-8'), pwd_correta.encode('utf-8')):
                    role_encontrado = role
                    break
            except:
                if password_input == pwd_correta:
                    role_encontrado = role
                    break
        
        if role_encontrado:
            st.session_state["autenticado"] = True
            st.session_state["role"] = role_encontrado
            st.session_state["sessao_guardada"] = True
            st.session_state["login_time"] = datetime.now()
            st.rerun()
        else:
            st.error("❌ Palavra-passe incorreta!")
            return False
    
    return False

# ============================================
# EXECUTAR AUTENTICAÇÃO
# ============================================

if not verificar_autenticacao():
    st.stop()

# ============================================
# DEFINIÇÃO DE PERMISSÕES
# ============================================
PERMISSOES = {
    "admin": [
        "🏠 Página Inicial",
        "📚 Balanços e Relatórios",
        "📋 Questionários",
        "🎯 Gestão de Qualidade",
        "📚 Cursos",
        "⚔️ Comparador Versus",
        "📊 Dashboard - Ações",
        "📊 Dashboard - Questionários"
    ],
    "gestor_BALANÇOS": [
        "🏠 Página Inicial",
        "📚 Balanços e Relatórios",
    ],
    "gestor_qualidade": [
        "🏠 Página Inicial",
        "📚 Cursos",
        "🎯 Gestão de Qualidade",
        "📊 Dashboard - Ações",
        "⚔️ Comparador Versus"
    ],
    "gestor_questionarios": [
        "🏠 Página Inicial",
        "📋 Questionários",
        "📊 Dashboard - Questionários"
    ]
}

role = st.session_state.get("role", "")
paginas_autorizadas = PERMISSOES.get(role, [])

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
    st.session_state.pagina = "🏠 Página Inicial" if "🏠 Página Inicial" in paginas_autorizadas else paginas_autorizadas[0]

# ============================================
# BARRA LATERAL
# ============================================

st.sidebar.title("📁 Gestão de Dados")
st.sidebar.markdown("---")
st.sidebar.info(f"👤 **Utilizador:** {role.replace('_', ' ').title()}", icon="ℹ️")

st.sidebar.markdown("### 🏠 Navegação")
if st.sidebar.button("🏠 Página Inicial", use_container_width=True, key="nav_home"):
    st.session_state.pagina = "🏠 Página Inicial"
    st.rerun()

st.sidebar.markdown("---")

if "📚 Balanços e Relatórios" in paginas_autorizadas:
    if st.sidebar.button("📚 Balanços e Relatórios", use_container_width=True, key="nav_relatorios"):
        st.session_state.pagina = "📚 Balanços e Relatórios"
        st.rerun()

if "📋 Questionários" in paginas_autorizadas:
    if st.sidebar.button("📋 Questionários", use_container_width=True, key="nav_questionarios"):
        st.session_state.pagina = "📋 Questionários"
        st.rerun()

if "📊 Dashboard - Questionários" in paginas_autorizadas:
    if st.sidebar.button("📊 Dashboard - Questionários", use_container_width=True, key="nav_dashboard_questionarios"):
        st.session_state.pagina = "📊 Dashboard - Questionários"
        st.rerun()

if "📚 Cursos" in paginas_autorizadas:
    if st.sidebar.button("📚 Cursos", use_container_width=True, key="nav_cursos"):
        st.session_state.pagina = "📚 Cursos"
        st.rerun()
        
if "🎯 Gestão de Qualidade" in paginas_autorizadas:
    if st.sidebar.button("🎯 Gestão de Qualidade", use_container_width=True, key="nav_qualidade"):
        st.session_state.pagina = "🎯 Gestão de Qualidade"
        st.rerun()

if "📊 Dashboard - Ações" in paginas_autorizadas:
    if st.sidebar.button("📊 Dashboard - Ações", use_container_width=True, key="nav_dashboard_acoes"):
        st.session_state.pagina = "📊 Dashboard - Ações"
        st.rerun()

if "⚔️ Comparador Versus" in paginas_autorizadas:
    if st.sidebar.button("⚔️ Comparador Versus", use_container_width=True, key="nav_comparador"):
        st.session_state.pagina = "⚔️ Comparador Versus"
        st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair", use_container_width=True, key="btn_logout", help="Terminar sessão"):
    # Limpar apenas os dados de autenticação
    for key in ['autenticado', 'role', 'sessao_guardada', 'login_time']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()
st.sidebar.markdown("---")

# ============================================
# CONTEÚDO Principal
# ============================================

if st.session_state.pagina not in paginas_autorizadas and paginas_autorizadas:
    st.session_state.pagina = "🏠 Página Inicial" if "🏠 Página Inicial" in paginas_autorizadas else paginas_autorizadas[0]
    st.rerun()

if st.session_state.pagina == "🏠 Página Inicial":
    from Pages.welcome import mostrar_welcome
    mostrar_welcome()

elif st.session_state.pagina == "📚 Cursos":
    from Pages.cursos import mostrar_cursos
    mostrar_cursos()

elif st.session_state.pagina == "📚 Balanços e Relatórios":
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

elif st.session_state.pagina == "📊 Dashboard - Ações":
    from Pages.dashboardformacoes import mostrar_dashboard
    mostrar_dashboard()

elif st.session_state.pagina == "📊 Dashboard - Questionários":
    from Pages.dashboardquestionarios import mostrar_questionarios_dashboard
    mostrar_questionarios_dashboard()