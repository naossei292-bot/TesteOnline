import streamlit as st
import pandas as pd
import hmac
import hashlib
import extra_streamlit_components as stx
from datetime import datetime, timedelta
from utils.data_utils import processar_questionarios_excel, get_col

# --------------------------
# CONFIGURAÇÃO DA PÁGINA
# --------------------------
st.set_page_config(page_title="Dashboard KPI & Qualidade", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        [data-testid="stSidebarNav"] { display: none; }
    </style>
""", unsafe_allow_html=True)
st.markdown("<style>[data-testid='stMetricValue'] { font-size: 25px; }</style>", unsafe_allow_html=True)

# ============================================
# 🍪 COOKIE CONTROLLER
# ============================================
cookie_manager = stx.CookieManager()

# ============================================
# 🔒 SISTEMA DE AUTENTICAÇÃO PERSISTENTE
# ============================================
COOKIE_NAME = "dashboard_auth"
COOKIE_DURATION_HORAS = 8

def gerar_token(role: str) -> str:
    """Gera um token HMAC assinado."""
    secret = str(st.secrets.get("cookie_secret", "fallback_secret"))
    timestamp = datetime.now().strftime("%Y%m%d%H")
    payload = f"{role}:{timestamp}"
    token = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return f"{role}:{token}"

def verificar_token(cookie_value: str):
    """Verifica se o token é válido. Retorna o role ou None."""
    try:
        partes = cookie_value.split(":")
        if len(partes) != 2:
            return None
        role, token_recebido = partes
        secret = str(st.secrets.get("cookie_secret", "fallback_secret"))
        for horas_atras in range(COOKIE_DURATION_HORAS + 1):
            timestamp = (datetime.now() - timedelta(hours=horas_atras)).strftime("%Y%m%d%H")
            payload = f"{role}:{timestamp}"
            token_esperado = hmac.new(
                secret.encode("utf-8"),
                payload.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()
            if hmac.compare_digest(token_recebido, token_esperado):
                return role
        return None
    except Exception:
        return None

def obter_passwords_config():
    """Obtém as passwords das secrets."""
    try:
        passwords_config = st.secrets["passwords"]
        resultado = {}
        for role, pwd in passwords_config.items():
            if isinstance(pwd, bytes):
                resultado[role] = pwd.decode("utf-8")
            else:
                resultado[role] = str(pwd)
        return resultado
    except (KeyError, AttributeError):
        st.error("🔐 Erro: Configuração de passwords não encontrada!")
        st.stop()
        return {}

def verificar_autenticacao():
    """Verifica autenticação via session_state ou cookie."""

    # Já autenticado nesta sessão
    if st.session_state.get("autenticado", False):
        return True

    # Tentar restaurar via cookie
    cookie_value = cookie_manager.get(cookie=COOKIE_NAME)
    if cookie_value:
        role = verificar_token(cookie_value)
        if role:
            st.session_state["autenticado"] = True
            st.session_state["role"] = role
            return True
        else:
            cookie_manager.delete(COOKIE_NAME)

    # 3️⃣ Formulário de login
    st.title("🔒 Acesso Restrito")
    st.markdown("### Esta aplicação é privada")
    st.markdown("Introduza a sua palavra-passe para continuar.")

    password_input = st.text_input("Palavra-passe:", type="password", key="login_password")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔓 Entrar", use_container_width=True, type="primary"):
            passwords_config = obter_passwords_config()
            role_encontrado = None

            for role, pwd_correta in passwords_config.items():
                # Comparação segura sem problemas de encoding
                if password_input == pwd_correta:
                    role_encontrado = role
                    break

            if role_encontrado:
                st.session_state["autenticado"] = True
                st.session_state["role"] = role_encontrado

                token = gerar_token(role_encontrado)
                expiry = datetime.now() + timedelta(hours=COOKIE_DURATION_HORAS)
                cookie_manager.set(COOKIE_NAME, token, expires_at=expiry)

                st.success(f"✅ Bem-vindo, {role_encontrado.replace('_', ' ').title()}!")
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

if st.sidebar.button("🚪 Sair", use_container_width=True, key="btn_logout"):
    cookie_manager.delete(COOKIE_NAME)  # ← apaga cookie
    for key in ['autenticado', 'role', 'sessao_guardada', 'login_time', 'last_activity']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# ============================================
# CONTEÚDO PRINCIPAL
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