import streamlit as st
import pandas as pd
import plotly.express as px
from utils import get_col, aplicar_filtros

def mostrar_cursos():
    """Página de visualização de cursos"""
    df_c = aplicar_filtros(st.session_state.cursos_df)
    if df_c is not None:
        st.subheader("📊 Performance de Cursos")
        c_insc, c_conc = get_col(df_c, "inscritos"), get_col(df_c, "concluidos")
       
        col1, col2 = st.columns(2)
        if c_insc and c_conc:
            taxa = (df_c[c_conc].sum() / df_c[c_insc].sum() * 100)
            col1.metric("Taxa Conclusão Global", f"{taxa:.1f}%")
        col2.metric("Total de Registos", len(df_c))

        fig = px.bar(df_c.groupby("Curso", as_index=False).sum(numeric_only=True),
                     x="Curso", y=c_conc, title="Conclusões por Curso")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_c, use_container_width=True)
    else:
        st.info("Carregue ficheiros de Cursos na barra lateral.")