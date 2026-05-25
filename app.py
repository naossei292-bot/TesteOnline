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

# ============================================
# 🔒 SISTEMA DE AUTENTICAÇÃO (MULTI-PASSWORD)
# ============================================

def verificar_autenticacao():
    """Verifica a password e define o role (nível de acesso) na sessão."""
    if st.session_state.get("autenticado", False):
        return True
    
    st.title("🔒 Acesso Restrito")
    st.markdown("### Esta aplicação é privada")
    st.markdown("Introduza a sua palavra-passe para continuar.")
    
    password_input = st.text_input("Palavra-passe:", type="password", key="login_password")
    
    if st.button("🔓 Entrar", use_container_width=True):
        # Tenta obter as passwords dos secrets (recomendado)
        try:
            passwords_config = st.secrets["passwords"]
        except (KeyError, AttributeError):
            # Fallback APENAS PARA TESTES LOCAIS - NÃO USAR EM PRODUÇÃO
            st.warning("⚠️ Usando passwords hardcoded (apenas desenvolvimento).")
            passwords_config = {
                "admin": "admin123",
                "gestor_balancos": "balancos123",
                "gestor_qualidade": "qualidade123",
                "gestor_questionarios": "questionarios123"
            }
        
        # Verifica qual password corresponde
        role_encontrado = None
        for role, pwd_correta in passwords_config.items():
            if hmac.compare_digest(password_input, pwd_correta):
                role_encontrado = role
                break
        
        if role_encontrado:
            st.session_state["autenticado"] = True
            st.session_state["role"] = role_encontrado
            st.rerun()
        else:
            st.error("❌ Palavra-passe incorreta!")
            return False
    
    return False

# Se não autenticado, mostra apenas o formulário de login (sem sidebar)
if not verificar_autenticacao():
    st.stop()

# ============================================
# DEFINIÇÃO DE PERMISSÕES (páginas por role)
# ============================================
PERMISSOES = {
    "admin": [
        "🏠 Página Inicial",
        "📚 Balanços e Relatórios",
        "📋 Questionários",
        "🎯 Gestão de Qualidade",
        "📚 Cursos",
        "📊 Dashboard - Ações",
        "📊 Dashboard - Questionários"
    ],
    "gestor_balancos": [
        "🏠 Página Inicial",
        "📚 Balanços e Relatórios",
    ],
    "gestor_qualidade": [
        "🏠 Página Inicial",
        "📋 Questionários",
        "📚 Cursos",
        "🎯 Gestão de Qualidade",
        "📊 Dashboard - Ações",
    ],
    "gestor_questionarios": [
        "🏠 Página Inicial",
        "📋 Questionários",
        "📊 Dashboard - Questionários"
    ]
}

# Obtém o role do utilizador logado
role = st.session_state.get("role", "")
paginas_autorizadas = PERMISSOES.get(role, [])

# 🔥 CORREÇÃO PARA O STREAMLIT CLOUD 🔥
if not paginas_autorizadas:
    # Se o role não for encontrado ou estiver vazio, define permissões padrão
    if role == "admin":
        paginas_autorizadas = ["🏠 Página Inicial", "📚 Balanços e Relatórios", "📋 Questionários", "🎯 Gestão de Qualidade", "📚 Cursos", "📊 Dashboard - Ações", "📊 Dashboard - Questionários"]
    elif role == "gestor_balancos":
        paginas_autorizadas = ["🏠 Página Inicial", "📚 Balanços e Relatórios"]
    elif role == "gestor_qualidade":
        paginas_autorizadas = ["🏠 Página Inicial", "📋 Questionários", "📚 Cursos", "🎯 Gestão de Qualidade", "📊 Dashboard - Ações"]
    elif role == "gestor_questionarios":
        paginas_autorizadas = ["🏠 Página Inicial", "📋 Questionários", "📊 Dashboard - Questionários"]
    else:
        # Fallback para qualquer role desconhecido ou vazio
        paginas_autorizadas = ["🏠 Página Inicial"]
        # Opcional: mostrar aviso apenas em desenvolvimento
        # st.toast(f"⚠️ Role '{role}' a usar permissões padrão", icon="⚠️")

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
    # VERIFICAÇÃO DE SEGURANÇA DUPLA - Evita IndexError
    if not paginas_autorizadas:
        # Último recurso: define página inicial manualmente
        st.session_state.pagina = "🏠 Página Inicial"
    else:
        # Define página inicial se disponível, senão usa a primeira página da lista
        if "🏠 Página Inicial" in paginas_autorizadas:
            st.session_state.pagina = "🏠 Página Inicial"
        else:
            st.session_state.pagina = paginas_autorizadas[0]

# ============================================
# BARRA LATERAL CONDICIONAL (baseada no role)
# ============================================

st.sidebar.title("📁 Gestão de Dados")
st.sidebar.markdown("---")

# Mostrar informações do utilizador logado
st.sidebar.info(f"👤 **Utilizador:** {role.replace('_', ' ').title() if role else 'Utilizador'}", icon="ℹ️")

# --- Página Inicial (sempre visível para todos os roles autenticados) ---
st.sidebar.markdown("### 🏠 Navegação")
if st.sidebar.button("🏠 Página Inicial", use_container_width=True, key="nav_home"):
    st.session_state.pagina = "🏠 Página Inicial"
    st.rerun()

st.sidebar.markdown("---")

# --- Balanços e Relatórios (apenas para quem tem permissão) ---
if "📚 Balanços e Relatórios" in paginas_autorizadas:
    if st.sidebar.button("📚 Balanços e Relatórios", use_container_width=True, key="nav_relatorios"):
        st.session_state.pagina = "📚 Balanços e Relatórios"
        st.rerun()

# --- Questionários ---
if "📋 Questionários" in paginas_autorizadas:
    if st.sidebar.button("📋 Questionários", use_container_width=True, key="nav_questionarios"):
        st.session_state.pagina = "📋 Questionários"
        st.rerun()

if "📊 Dashboard - Questionários" in paginas_autorizadas:
    if st.sidebar.button("📊 Dashboard - Questionários", use_container_width=True, key="nav_dashboard_questionarios"):
        st.session_state.pagina = "📊 Dashboard - Questionários"
        st.rerun()

# --- Cursos (apenas para quem tem permissão) ---
if "📚 Cursos" in paginas_autorizadas:
    if st.sidebar.button("📚 Cursos", use_container_width=True, key="nav_cursos"):
        st.session_state.pagina = "📚 Cursos"
        st.rerun()
        
# --- Gestão de Qualidade ---
if "🎯 Gestão de Qualidade" in paginas_autorizadas:
    if st.sidebar.button("🎯 Gestão de Qualidade", use_container_width=True, key="nav_qualidade"):
        st.session_state.pagina = "🎯 Gestão de Qualidade"
        st.rerun()

if "📊 Dashboard - Ações" in paginas_autorizadas:
    if st.sidebar.button("📊 Dashboard - Ações", use_container_width=True, key="nav_dashboard_acoes"):
        st.session_state.pagina = "📊 Dashboard - Ações"
        st.rerun()

# Botão de logout (sempre visível)
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair", use_container_width=True, key="btn_logout", help="Terminar sessão"):
    st.session_state.clear()
    st.rerun()
st.sidebar.markdown("---")

# ============================================
# CONTEÚDO PRINCIPAL (BASEADO NA SELEÇÃO)
# ============================================

# Segurança extra: se a página atual não está autorizada, redefine para a página inicial
if paginas_autorizadas and st.session_state.pagina not in paginas_autorizadas:
    if "🏠 Página Inicial" in paginas_autorizadas:
        st.session_state.pagina = "🏠 Página Inicial"
    elif paginas_autorizadas:
        st.session_state.pagina = paginas_autorizadas[0]
    else:
        st.session_state.pagina = "🏠 Página Inicial"
    st.rerun()

# Navegação condicional
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