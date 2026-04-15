import streamlit as st
import pandas as pd
from utils import aplicar_filtros
from components.filters import checklist_com_select_all

def mostrar_questionarios():
    """Página de visualização de questionários"""
    df_q = aplicar_filtros(st.session_state.quest_df) 
    
    if df_q is not None:
        st.subheader("📋 Base de Dados de Satisfação")
        
        # Linha 1 de filtros
        col1, col2, col3 = st.columns(3)

        with col1:
            all_mods = sorted(df_q["Modalidade"].unique())
            sel_mod = checklist_com_select_all(all_mods, "Filtrar Modalidade", "mods")

        with col2:
            all_resps = sorted(df_q["Respondente"].unique())
            sel_resp = checklist_com_select_all(all_resps, "Filtrar Respondentes", "resps")
            
        # Filtragem intermédia
        df_temp = df_q[(df_q["Modalidade"].isin(sel_mod)) & (df_q["Respondente"].isin(sel_resp))]

        with col3:
            all_cursos = sorted(df_temp["Curso"].unique())
            sel_cursos = checklist_com_select_all(all_cursos, "Filtrar Cursos", "cursos")

        # Linha 2 de filtros
        col4, col5 = st.columns(2)

        df_temp = df_temp[df_temp["Curso"].isin(sel_cursos)]

        with col4:
            all_cats = sorted(df_temp["Categoria"].unique())
            sel_cat = checklist_com_select_all(all_cats, "Filtrar Categorias", "cats")

        with col5:
            lista_pergs_filtrada = sorted(df_temp[df_temp["Categoria"].isin(sel_cat)]["Pergunta"].unique())
            sel_perg = checklist_com_select_all(lista_pergs_filtrada, "Filtrar Perguntas", "pergs")

        # Filtragem final
        df_display = df_temp[
            (df_temp["Categoria"].isin(sel_cat)) & 
            (df_temp["Pergunta"].isin(sel_perg))
        ]

        # Exibição
        if not df_display.empty:
            st.write(f"Exibindo **{len(df_display)}** registos.")
            st.dataframe(df_display, use_container_width=True)
        else:
            st.warning("Selecione os itens nos filtros acima para visualizar os dados.")
    else:
        st.info("Carregue ficheiros de Questionários na barra lateral para ativar os filtros.")