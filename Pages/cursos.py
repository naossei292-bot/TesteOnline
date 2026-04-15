import streamlit as st
import pandas as pd
import plotly.express as px
from utils.data_utils import get_col, aplicar_filtros

def mostrar_cursos():
    """Função principal da página de cursos"""
    st.header("📚 Análise de Cursos")
    
    df_c = aplicar_filtros(st.session_state.cursos_df)
    
    if df_c is not None and not df_c.empty:
        st.subheader("📊 Performance de Cursos")
        
        c_insc, c_conc = get_col(df_c, "inscritos"), get_col(df_c, "concluidos")
       
        col1, col2 = st.columns(2)
        
        if c_insc and c_conc:
            taxa = (df_c[c_conc].sum() / df_c[c_insc].sum() * 100)
            col1.metric("📈 Taxa Conclusão Global", f"{taxa:.1f}%")
        
        col2.metric("📊 Total de Registos", len(df_c))
    
        # Gráfico de conclusões por curso
        if c_conc:
            df_grouped = df_c.groupby("Curso", as_index=False).sum(numeric_only=True)
            fig = px.bar(
                df_grouped,
                x="Curso", 
                y=c_conc, 
                title="Conclusões por Curso",
                color=c_conc,
                color_continuous_scale="Viridis"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Tabela de dados
        st.subheader("📋 Dados Detalhados")
        st.dataframe(df_c, use_container_width=True)
        
    else:
        st.info("📂 Carregue ficheiros de Cursos na barra lateral para visualizar os dados.")

# Para compatibilidade com execução direta
if __name__ == "__main__":
    mostrar_cursos()