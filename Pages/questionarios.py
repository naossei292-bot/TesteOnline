import streamlit as st
import pandas as pd
from utils.data_utils import aplicar_filtros

st.set_page_config(page_title="Questionários", layout="wide")

st.header("📋 Base de Dados de Satisfação")

def checklist_com_select_all(lista_itens, titulo, chave_unica):
    """Componente de checklist com selecionar/limpar tudo"""
    with st.popover(titulo, use_container_width=True):
        c_btn1, c_btn2 = st.columns(2)
        
        if c_btn1.button("✅ Selecionar Tudo", key=f"all_btn_{chave_unica}"):
            for item in lista_itens:
                st.session_state[f"chk_{chave_unica}_{item}"] = True
            st.rerun()

        if c_btn2.button("❌ Limpar Tudo", key=f"none_btn_{chave_unica}"):
            for item in lista_itens:
                st.session_state[f"chk_{chave_unica}_{item}"] = False
            st.rerun()

        selecionados = []
        for item in lista_itens:
            chave_item = f"chk_{chave_unica}_{item}"
            
            if chave_item not in st.session_state:
                st.session_state[chave_item] = True
            
            if st.checkbox(str(item), key=chave_item):
                selecionados.append(item)
        return selecionados

df_q = aplicar_filtros(st.session_state.quest_df)

if df_q is not None and not df_q.empty:
    
    # Filtros
    col1, col2, col3 = st.columns(3)

    with col1:
        all_mods = sorted(df_q["Modalidade"].unique())
        sel_mod = checklist_com_select_all(all_mods, "🎯 Filtrar Modalidade", "mods")

    with col2:
        all_resps = sorted(df_q["Respondente"].unique())
        sel_resp = checklist_com_select_all(all_resps, "👥 Filtrar Respondentes", "resps")
        
    df_temp = df_q[(df_q["Modalidade"].isin(sel_mod)) & (df_q["Respondente"].isin(sel_resp))]

    with col3:
        all_cursos = sorted(df_temp["Curso"].unique())
        sel_cursos = checklist_com_select_all(all_cursos, "📚 Filtrar Cursos", "cursos")

    col4, col5 = st.columns(2)
    df_temp = df_temp[df_temp["Curso"].isin(sel_cursos)]

    with col4:
        all_cats = sorted(df_temp["Categoria"].unique())
        sel_cat = checklist_com_select_all(all_cats, "📂 Filtrar Categorias", "cats")

    with col5:
        lista_pergs_filtrada = sorted(df_temp[df_temp["Categoria"].isin(sel_cat)]["Pergunta"].unique())
        sel_perg = checklist_com_select_all(lista_pergs_filtrada, "❓ Filtrar Perguntas", "pergs")

    # Exibição dos dados
    df_display = df_temp[
        (df_temp["Categoria"].isin(sel_cat)) & 
        (df_temp["Pergunta"].isin(sel_perg))
    ]

    if not df_display.empty:
        st.success(f"✅ Exibindo **{len(df_display)}** registos")
        st.dataframe(df_display, use_container_width=True)
        
        # Estatísticas rápidas
        with st.expander("📊 Estatísticas Rápidas"):
            col_med1, col_med2, col_med3 = st.columns(3)
            with col_med1:
                st.metric("Média Geral", f"{df_display['Media'].mean():.2f}")
            with col_med2:
                st.metric("Mediana", f"{df_display['Media'].median():.2f}")
            with col_med3:
                st.metric("Desvio Padrão", f"{df_display['Media'].std():.2f}")
    else:
        st.warning("⚠️ Selecione os itens nos filtros acima para visualizar os dados.")
else:
    st.info("📂 Carregue ficheiros de Questionários na barra lateral para ativar os filtros.")