import streamlit as st

def setup_page_config():
    """Configuração inicial da página"""
    st.set_page_config(page_title="Dashboard KPI & Qualidade", layout="wide")
    st.markdown("<style>[data-testid='stMetricValue'] { font-size: 25px; }</style>", unsafe_allow_html=True)

def initialize_session_state():
    """Inicializa todas as variáveis de sessão"""
    if 'cursos_df' not in st.session_state:
        st.session_state.cursos_df = None
    if 'quest_df' not in st.session_state:
        st.session_state.quest_df = None
    if 'filtro_centro' not in st.session_state:
        st.session_state.filtro_centro = []
    
    # Objetivos dos KPIs
    if 'obj_satisfacao' not in st.session_state:
        st.session_state.obj_satisfacao = 4.2
    if 'obj_conclusao' not in st.session_state:
        st.session_state.obj_conclusao = 85.0
    if 'obj_aprovacao' not in st.session_state:
        st.session_state.obj_aprovacao = 80.0
    if 'obj_plano' not in st.session_state:
        st.session_state.obj_plano = 95.0
    if 'obj_formador' not in st.session_state:
        st.session_state.obj_formador = 4.3