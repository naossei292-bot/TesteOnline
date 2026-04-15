import streamlit as st

def checklist_com_select_all(lista_itens, titulo, chave_unica):
    """Componente de checklist com botões Selecionar Tudo e Limpar Tudo"""
    with st.popover(titulo, use_container_width=True):
        c_btn1, c_btn2 = st.columns(2)
        
        # Botão Selecionar Tudo
        if c_btn1.button("Selecionar Tudo", key=f"all_btn_{chave_unica}"):
            for item in lista_itens:
                st.session_state[f"chk_{chave_unica}_{item}"] = True
            st.rerun()

        # Botão Limpar Tudo
        if c_btn2.button("Limpar Tudo", key=f"none_btn_{chave_unica}"):
            for item in lista_itens:
                st.session_state[f"chk_{chave_unica}_{item}"] = False
            st.rerun()

        selecionados = []
        for item in lista_itens:
            chave_item = f"chk_{chave_unica}_{item}"
            
            # Se o item ainda não estiver no estado, começa como True
            if chave_item not in st.session_state:
                st.session_state[chave_item] = True
            
            # O checkbox lê e escreve diretamente na chave do session_state
            if st.checkbox(str(item), key=chave_item):
                selecionados.append(item)
        return selecionados

def sidebar_uploaders():
    """Barra lateral com uploaders de ficheiros"""
    st.sidebar.title("📁 Gestão de Dados")
    
    with st.sidebar.expander("📚 Dados de Cursos (Moodle)", expanded=True):
        files_cursos = st.file_uploader("Upload CSV Cursos", type=["csv"], accept_multiple_files=True)
        if files_cursos:
            dfs = [pd.read_csv(f).rename(columns=lambda x: x.strip()) for f in files_cursos]
            st.session_state.cursos_df = pd.concat(dfs, ignore_index=True)
    
    with st.sidebar.expander("📋 Dados de Questionários", expanded=True):
        files_quest = st.file_uploader("Upload XLSX Questionários", type=["xlsx"], accept_multiple_files=True)
        if files_quest:
            dfs_q = [processar_questionarios_excel(f) for f in files_quest]
            st.session_state.quest_df = pd.concat(dfs_q, ignore_index=True)
    
    # Filtros Globais
    st.sidebar.markdown("---")
    lista_centros = set()
    if st.session_state.cursos_df is not None:
        lista_centros.update(st.session_state.cursos_df["Centro"].unique())
    if st.session_state.quest_df is not None:
        lista_centros.update(st.session_state.quest_df["Centro"].unique())
    
    st.session_state.filtro_centro = st.sidebar.multiselect(
        "Filtrar por Centro", sorted(list(lista_centros)), default=st.session_state.filtro_centro
    )