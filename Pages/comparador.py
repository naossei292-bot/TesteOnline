import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.data_utils import get_col

# NÃO chame st.set_page_config aqui (já está no app.py)
# st.set_page_config(page_title="Comparador entre Centros", layout="wide")

def mostrar_comparador():
    """Função principal da página de comparador"""
    st.header("⚔️ Comparador entre Centros")

    df_c = st.session_state.cursos_df
    df_q = st.session_state.quest_df

    has_cursos = df_c is not None and not df_c.empty
    has_quest = df_q is not None and not df_q.empty

    if has_cursos or has_quest:
        
        # Obter centros disponíveis
        centros_disponiveis = set()
        if has_cursos:
            centros_disponiveis.update(df_c["Centro"].unique())
        if has_quest:
            centros_disponiveis.update(df_q["Centro"].unique())
        
        centros_disponiveis = sorted(list(centros_disponiveis))
        
        selecionados = st.multiselect(
            "🏢 Selecione os centros para comparar:", 
            centros_disponiveis, 
            default=centros_disponiveis[:3] if len(centros_disponiveis) >= 3 else centros_disponiveis,
            help="Compare até 5 centros simultaneamente"
        )
        
        if len(selecionados) > 5:
            st.warning("⚠️ Selecione no máximo 5 centros para uma visualização clara.")
            selecionados = selecionados[:5]
        
        if len(selecionados) >= 2:
            
            # Filtrar dados
            df_c_comp = df_c[df_c["Centro"].isin(selecionados)] if has_cursos else None
            df_q_comp = df_q[df_q["Centro"].isin(selecionados)] if has_quest else None
            
            # Preparar KPIs por centro
            kpi_data = []
            for centro in selecionados:
                centro_kpi = {"Centro": centro}
                
                if has_cursos:
                    df_c_centro = df_c_comp[df_c_comp["Centro"] == centro]
                    c_insc = get_col(df_c_centro, "inscritos")
                    c_conc = get_col(df_c_centro, "concluidos")
                    c_aval = get_col(df_c_centro, "avaliados")
                    c_aprov = get_col(df_c_centro, "aprovados")
                    c_planeado = get_col(df_c_centro, "planeado")
                    
                    if c_insc and c_conc:
                        total_insc = df_c_centro[c_insc].sum()
                        total_conc = df_c_centro[c_conc].sum()
                        centro_kpi["Taxa Conclusão (%)"] = (total_conc / total_insc * 100) if total_insc > 0 else 0
                        centro_kpi["Total Inscritos"] = total_insc
                        centro_kpi["Total Concluídos"] = total_conc
                    else:
                        centro_kpi["Taxa Conclusão (%)"] = None
                    
                    if c_aval and c_aprov:
                        total_aval = df_c_centro[c_aval].sum()
                        total_aprov = df_c_centro[c_aprov].sum()
                        centro_kpi["Taxa Aprovação (%)"] = (total_aprov / total_aval * 100) if total_aval > 0 else 0
                    else:
                        centro_kpi["Taxa Aprovação (%)"] = None
                    
                    centro_kpi["Nº Cursos"] = df_c_centro["Curso"].nunique()
                
                if has_quest:
                    df_q_centro = df_q_comp[df_q_comp["Centro"] == centro]
                    if not df_q_centro.empty:
                        centro_kpi["Satisfação Média"] = df_q_centro["Media"].mean()
                        centro_kpi["Nº Respostas"] = len(df_q_centro)
                    else:
                        centro_kpi["Satisfação Média"] = None
                        centro_kpi["Nº Respostas"] = 0
                
                kpi_data.append(centro_kpi)
            
            df_kpi = pd.DataFrame(kpi_data)
            
            # Tabela comparativa
            st.subheader("📊 Comparação Rápida de KPIs")
            st.dataframe(
                df_kpi.style.format({
                    "Taxa Conclusão (%)": "{:.1f}%",
                    "Taxa Aprovação (%)": "{:.1f}%", 
                    "Satisfação Média": "{:.2f}"
                }),
                use_container_width=True,
                hide_index=True
            )
            
            st.markdown("---")
            
            # Gráficos comparativos
            st.subheader("📈 Visualizações Comparativas")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if has_cursos and "Taxa Conclusão (%)" in df_kpi.columns:
                    df_conc = df_kpi[["Centro", "Taxa Conclusão (%)"]].dropna()
                    if not df_conc.empty:
                        fig = px.bar(df_conc, x="Centro", y="Taxa Conclusão (%)", 
                                    title="Taxa de Conclusão", text="Taxa Conclusão (%)",
                                    color="Taxa Conclusão (%)", color_continuous_scale="RdYlGn")
                        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                        st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                if has_quest and "Satisfação Média" in df_kpi.columns:
                    df_sat = df_kpi[["Centro", "Satisfação Média"]].dropna()
                    if not df_sat.empty:
                        fig = px.bar(df_sat, x="Centro", y="Satisfação Média", 
                                    title="Satisfação Média", text="Satisfação Média",
                                    color="Satisfação Média", color_continuous_scale="RdYlGn")
                        fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                        st.plotly_chart(fig, use_container_width=True)
            
            # Radar comparativo
            if has_quest:
                st.markdown("---")
                st.subheader("🕸️ Radar Comparativo por Categoria")
                
                df_radar = df_q_comp.groupby(["Centro", "Categoria"])["Media"].mean().reset_index()
                
                fig_radar = go.Figure()
                cores = px.colors.qualitative.Set2
                
                for i, centro in enumerate(selecionados):
                    df_centro = df_radar[df_radar["Centro"] == centro]
                    if not df_centro.empty:
                        fig_radar.add_trace(go.Scatterpolar(
                            r=df_centro["Media"],
                            theta=df_centro["Categoria"],
                            fill='toself',
                            name=centro,
                            line_color=cores[i % len(cores)],
                            opacity=0.7
                        ))
                
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
                    showlegend=True,
                    height=500
                )
                st.plotly_chart(fig_radar, use_container_width=True)
        
        elif len(selecionados) == 1:
            st.info(f"👆 Selecione pelo menos mais um centro para comparar com **{selecionados[0]}**.")
        else:
            st.info("👆 Selecione pelo menos 2 centros para iniciar a comparação.")
    else:
        st.info("📂 Carregue ficheiros de Cursos e/ou Questionários na barra lateral.")

if __name__ == "__main__":
    mostrar_comparador()