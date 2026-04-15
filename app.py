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
# MENU DE NAVEGAÇÃO
# ============================================
st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 Navegação")

# Botões de navegação na sidebar
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

# Verificar autenticação
if not verificar_autenticacao():
    st.stop()

# Botão de logout
col_logout1, col_logout2 = st.columns([6, 1])
with col_logout2:
    if st.button("🚪 Sair", help="Terminar sessão"):
        st.session_state.clear()
        st.rerun()

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
# BARRA LATERAL
# ============================================
st.sidebar.title("📁 Gestão de Dados")

with st.sidebar.expander("📚 Dados de Cursos (Moodle)", expanded=True):
    files_cursos = st.file_uploader("Upload CSV Cursos", type=["csv"], accept_multiple_files=True)
files_cursos = st.file_uploader("Upload CSV Cursos", type=["csv"], accept_multiple_files=True)

if files_cursos:
    # Guardar ficheiros em memória
    st.session_state["files_cursos"] = [(f.name, f.read()) for f in files_cursos]

    dfs = []
    for name, content in st.session_state["files_cursos"]:
        df = pd.read_csv(pd.io.common.BytesIO(content))
        df = df.rename(columns=lambda x: x.strip())
        dfs.append(df)

    st.session_state.cursos_df = pd.concat(dfs, ignore_index=True)
    st.sidebar.success(f"✅ {len(dfs)} ficheiro(s) carregado(s)")

# 🔁 Recarregar automaticamente após rerun
elif "files_cursos" in st.session_state:
    dfs = []
    for name, content in st.session_state["files_cursos"]:
        df = pd.read_csv(pd.io.common.BytesIO(content))
        df = df.rename(columns=lambda x: x.strip())
        dfs.append(df)

    st.session_state.cursos_df = pd.concat(dfs, ignore_index=True)
with st.sidebar.expander("📋 Dados de Questionários", expanded=True):
    files_quest = st.file_uploader("Upload XLSX Questionários", type=["xlsx"], accept_multiple_files=True)
files_quest = st.file_uploader("Upload XLSX Questionários", type=["xlsx"], accept_multiple_files=True)

if files_quest:
    st.session_state["files_quest"] = [(f.name, f.read()) for f in files_quest]

    dfs_q = []
    for name, content in st.session_state["files_quest"]:
        df = processar_questionarios_excel(pd.io.common.BytesIO(content))
        dfs_q.append(df)

    st.session_state.quest_df = pd.concat(dfs_q, ignore_index=True)
    st.sidebar.success(f"✅ {len(dfs_q)} ficheiro(s) carregado(s)")

elif "files_quest" in st.session_state:
    dfs_q = []
    for name, content in st.session_state["files_quest"]:
        df = processar_questionarios_excel(pd.io.common.BytesIO(content))
        dfs_q.append(df)

    st.session_state.quest_df = pd.concat(dfs_q, ignore_index=True)
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



# ============================================
# CONTEÚDO PRINCIPAL (BASEADO NA SELEÇÃO)
# ============================================

if st.session_state.pagina == "📚 Cursos":
    # Importar e executar a página de cursos
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