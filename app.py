import streamlit as st
import pandas as pd
import hmac
from utils.data_utils import processar_questionarios_excel, get_col

# --------------------------
# CONFIGURAÇÃO DA PÁGINA
# --------------------------
st.set_page_config(page_title="Dashboard KPI & Qualidade", layout="wide")

st.markdown("<style>[data-testid='stMetricValue'] { font-size: 25px; }</style>", unsafe_allow_html=True)

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
st.sidebar.markdown("### 📌 Navegação")

if st.sidebar.button("📚 Cursos", use_container_width=True, key="nav_cursos"):
    st.session_state.pagina = "📚 Cursos"
    st.rerun()

if st.sidebar.button("📋 Questionários", use_container_width=True, key="nav_quest"):
    st.session_state.pagina = "📋 Questionários"
    st.rerun()

if st.sidebar.button("🎯 Gestão de Qualidade", use_container_width=True, key="nav_qualidade"):
    st.session_state.pagina = "🎯 Gestão de Qualidade"
    st.rerun()

if st.sidebar.button("⚔️ Comparador Versus", use_container_width=True, key="nav_comparador"):
    st.session_state.pagina = "⚔️ Comparador Versus"
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("💡 Dica: Carregue os ficheiros nas secções acima")

# Uploads
with st.sidebar.expander("📚 Dados de Cursos (Moodle)", expanded=True):
    files_cursos = st.file_uploader("Upload CSV Cursos", type=["csv"], accept_multiple_files=True)
    if files_cursos:
        dfs = [pd.read_csv(f).rename(columns=lambda x: x.strip()) for f in files_cursos]
        st.session_state.cursos_df = pd.concat(dfs, ignore_index=True)
        st.sidebar.success(f"✅ {len(files_cursos)} ficheiro(s) carregado(s)")

with st.sidebar.expander("📋 Dados de Questionários", expanded=True):
    files_quest = st.file_uploader("Upload XLSX Questionários", type=["xlsx"], accept_multiple_files=True)
    if files_quest:
        dfs_q = [processar_questionarios_excel(f) for f in files_quest]
        st.session_state.quest_df = pd.concat(dfs_q, ignore_index=True)
        st.sidebar.success(f"✅ {len(files_quest)} ficheiro(s) carregado(s)")

# Filtro global por Centro
st.sidebar.markdown("---")
lista_centros = set()
if st.session_state.cursos_df is not None:
    lista_centros.update(st.session_state.cursos_df["Centro"].unique())
if st.session_state.quest_df is not None:
    lista_centros.update(st.session_state.quest_df["Centro"].unique())

st.session_state.filtro_centro = st.sidebar.multiselect(
    "Filtrar por Centro", 
    sorted(list(lista_centros)), 
    default=st.session_state.filtro_centro
)

# Botão de logout (agora na sidebar, mais intuitivo)
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair", use_container_width=True, help="Terminar sessão"):
    st.session_state.clear()
    st.rerun()

# ============================================
# CONTEÚDO PRINCIPAL (BASEADO NA SELEÇÃO)
# ============================================

if st.session_state.pagina == "📚 Cursos":
    from Pages.cursos import mostrar_cursos
    mostrar_cursos()

elif st.session_state.pagina == "📋 Questionários":
    from Pages.questionarios import mostrar_questionarios
    mostrar_questionarios()

elif st.session_state.pagina == "🎯 Gestão de Qualidade":
    from Pages.qualidade import mostrar_qualidade
    mostrar_qualidade()

elif st.session_state.pagina == "⚔️ Comparador Versus":
    from Pages.comparador import mostrar_comparador
    mostrar_comparador()