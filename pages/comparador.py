import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import get_col

def mostrar_comparador():
    """Página de Comparador entre Centros"""
    st.header("⚔️ Comparador entre Centros")
    
    df_c = st.session_state.cursos_df
    df_q = st.session_state.quest_df   
    # Verificar quais dados estão disponíveis
    has_cursos = df_c is not None and not df_c.empty
    has_quest = df_q is not None and not df_q.empty
    
    if has_cursos or has_quest:
        
        # Obter lista de centros disponíveis
        centros_disponiveis = set()
        if has_cursos:
            centros_disponiveis.update(df_c["Centro"].unique())
        if has_quest:
            centros_disponiveis.update(df_q["Centro"].unique())
        
        centros_disponiveis = sorted(list(centros_disponiveis))
        
        # Seletor de centros
        selecionados = st.multiselect(
            "🏢 Selecione os centros para comparar:", 
            centros_disponiveis, 
            default=centros_disponiveis[:3] if len(centros_disponiveis) >= 3 else centros_disponiveis,
            help="Compare até 5 centros simultaneamente"
        )
        
        if len(selecionados) > 5:
            st.warning("⚠️ Por favor, selecione no máximo 5 centros para uma visualização clara.")
            selecionados = selecionados[:5]
        
        if len(selecionados) >= 2:
            
            # Filtrar dados pelos centros selecionados
            df_c_comp = df_c[df_c["Centro"].isin(selecionados)] if has_cursos else None
            df_q_comp = df_q[df_q["Centro"].isin(selecionados)] if has_quest else None
            
            # ==================== KPIs RESUMIDOS POR CENTRO ====================
            st.subheader("📊 Comparação Rápida de KPIs por Centro")
            
            # Preparar dados para tabela de KPIs
            kpi_data = []
            
            for centro in selecionados:
                centro_kpi = {"Centro": centro}
                
                # Dados de Cursos
                if has_cursos:
                    df_c_centro = df_c_comp[df_c_comp["Centro"] == centro]
                    
                    c_insc = get_col(df_c_centro, "inscritos")
                    c_conc = get_col(df_c_centro, "concluidos")
                    c_aval = get_col(df_c_centro, "avaliados")
                    c_aprov = get_col(df_c_centro, "aprovados")
                    c_planeado = get_col(df_c_centro, "planeado")
                    
                    # Taxa Conclusão
                    if c_insc and c_conc:
                        total_insc = df_c_centro[c_insc].sum()
                        total_conc = df_c_centro[c_conc].sum()
                        centro_kpi["Taxa Conclusão (%)"] = (total_conc / total_insc * 100) if total_insc > 0 else 0
                        centro_kpi["Total Inscritos"] = total_insc
                        centro_kpi["Total Concluídos"] = total_conc
                    else:
                        centro_kpi["Taxa Conclusão (%)"] = None
                    
                    # Taxa Aprovação
                    if c_aval and c_aprov:
                        total_aval = df_c_centro[c_aval].sum()
                        total_aprov = df_c_centro[c_aprov].sum()
                        centro_kpi["Taxa Aprovação (%)"] = (total_aprov / total_aval * 100) if total_aval > 0 else 0
                    else:
                        centro_kpi["Taxa Aprovação (%)"] = None
                    
                    # Cumprimento Plano
                    if c_planeado and c_conc:
                        total_planeado = df_c_centro[c_planeado].sum()
                        total_realizado = df_c_centro[c_conc].sum()
                        centro_kpi["Cumprimento Plano (%)"] = (total_realizado / total_planeado * 100) if total_planeado > 0 else None
                    else:
                        centro_kpi["Cumprimento Plano (%)"] = None
                    
                    # Total de Cursos
                    centro_kpi["Nº Cursos"] = df_c_centro["Curso"].nunique()
                
                # Dados de Questionários
                if has_quest:
                    df_q_centro = df_q_comp[df_q_comp["Centro"] == centro]
                    
                    if not df_q_centro.empty:
                        # Satisfação Geral
                        centro_kpi["Satisfação Média"] = df_q_centro["Media"].mean()
                        
                        # Satisfação por Respondente
                        df_formandos = df_q_centro[df_q_centro["Respondente"] == "Formando"]
                        centro_kpi["Satisfação Formandos"] = df_formandos["Media"].mean() if not df_formandos.empty else None
                        
                        df_formadores = df_q_centro[df_q_centro["Respondente"] == "Formador/Tutor"]
                        centro_kpi["Avaliação Formadores"] = df_formadores["Media"].mean() if not df_formadores.empty else None
                        
                        # Total de Respostas
                        centro_kpi["Nº Respostas"] = len(df_q_centro)
                    else:
                        centro_kpi["Satisfação Média"] = None
                        centro_kpi["Nº Respostas"] = 0
                
                kpi_data.append(centro_kpi)
            
            # Exibir tabela de KPIs (sem background_gradient para evitar erro)
            df_kpi = pd.DataFrame(kpi_data)
            
            # Formatar e exibir - sem gradient para evitar matplotlib
            st.dataframe(
                df_kpi.style.format({
                    "Taxa Conclusão (%)": "{:.1f}%",
                    "Taxa Aprovação (%)": "{:.1f}%", 
                    "Cumprimento Plano (%)": "{:.1f}%",
                    "Satisfação Média": "{:.2f}",
                    "Satisfação Formandos": "{:.2f}",
                    "Avaliação Formadores": "{:.2f}"
                }),
                use_container_width=True,
                hide_index=True
            )
            
            st.markdown("---")
            
            # ==================== GRÁFICOS DE COMPARAÇÃO ====================
            st.subheader("📈 Visualizações Comparativas")
            
            # Linha 1: Gráficos de Barras para KPIs principais
            col_bar1, col_bar2 = st.columns(2)
            
            with col_bar1:
                if has_cursos:
                    # Gráfico: Taxa de Conclusão por Centro
                    df_conc_chart = df_kpi[["Centro", "Taxa Conclusão (%)"]].dropna()
                    if not df_conc_chart.empty:
                        fig_conc = px.bar(
                            df_conc_chart, 
                            x="Centro", 
                            y="Taxa Conclusão (%)",
                            title="📊 Taxa de Conclusão por Centro",
                            text="Taxa Conclusão (%)",
                            color="Taxa Conclusão (%)",
                            color_continuous_scale="RdYlGn",
                            range_color=[0, 100]
                        )
                        fig_conc.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                        fig_conc.add_hline(y=85, line_dash="dash", line_color="green", annotation_text="Meta 85%")
                        st.plotly_chart(fig_conc, use_container_width=True)
            
            with col_bar2:
                if has_cursos:
                    # Gráfico: Taxa de Aprovação por Centro
                    df_aprov_chart = df_kpi[["Centro", "Taxa Aprovação (%)"]].dropna()
                    if not df_aprov_chart.empty:
                        fig_aprov = px.bar(
                            df_aprov_chart, 
                            x="Centro", 
                            y="Taxa Aprovação (%)",
                            title="📝 Taxa de Aprovação por Centro",
                            text="Taxa Aprovação (%)",
                            color="Taxa Aprovação (%)",
                            color_continuous_scale="RdYlGn",
                            range_color=[0, 100]
                        )
                        fig_aprov.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                        fig_aprov.add_hline(y=80, line_dash="dash", line_color="green", annotation_text="Meta 80%")
                        st.plotly_chart(fig_aprov, use_container_width=True)
            
            # Linha 2: Satisfação e Avaliação
            col_sat1, col_sat2 = st.columns(2)
            
            with col_sat1:
                if has_quest:
                    # Gráfico: Satisfação Média por Centro
                    df_sat_chart = df_kpi[["Centro", "Satisfação Média"]].dropna()
                    if not df_sat_chart.empty:
                        fig_sat = px.bar(
                            df_sat_chart, 
                            x="Centro", 
                            y="Satisfação Média",
                            title="⭐ Satisfação Média por Centro",
                            text="Satisfação Média",
                            color="Satisfação Média",
                            color_continuous_scale="RdYlGn",
                            range_color=[1, 5]
                        )
                        fig_sat.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                        fig_sat.add_hline(y=4.2, line_dash="dash", line_color="green", annotation_text="Meta 4.2")
                        st.plotly_chart(fig_sat, use_container_width=True)
            
            with col_sat2:
                if has_quest:
                    # Gráfico: Avaliação Formadores por Centro
                    df_form_chart = df_kpi[["Centro", "Avaliação Formadores"]].dropna()
                    if not df_form_chart.empty:
                        fig_form = px.bar(
                            df_form_chart, 
                            x="Centro", 
                            y="Avaliação Formadores",
                            title="👨‍🏫 Avaliação dos Formadores por Centro",
                            text="Avaliação Formadores",
                            color="Avaliação Formadores",
                            color_continuous_scale="RdYlGn",
                            range_color=[1, 5]
                        )
                        fig_form.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                        fig_form.add_hline(y=4.3, line_dash="dash", line_color="green", annotation_text="Meta 4.3")
                        st.plotly_chart(fig_form, use_container_width=True)
            
            st.markdown("---")
            
            # ==================== RADAR COMPARATIVO ====================
            if has_quest:
                st.subheader("🕸️ Radar Comparativo por Categoria")
                
                # Preparar dados para radar
                df_radar = df_q_comp.groupby(["Centro", "Categoria"])["Media"].mean().reset_index()
                
                fig_radar_comp = go.Figure()
                cores = px.colors.qualitative.Set2
                
                for i, centro in enumerate(selecionados):
                    df_centro = df_radar[df_radar["Centro"] == centro]
                    if not df_centro.empty:
                        fig_radar_comp.add_trace(go.Scatterpolar(
                            r=df_centro["Media"],
                            theta=df_centro["Categoria"],
                            fill='toself',
                            name=f"{centro}",
                            line_color=cores[i % len(cores)],
                            opacity=0.7
                        ))
                
                fig_radar_comp.update_layout(
                    polar=dict(
                        radialaxis=dict(visible=True, range=[0, 5], tickvals=[1,2,3,4,5])
                    ),
                    showlegend=True,
                    height=550,
                    legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5),
                    title="Comparação da Qualidade por Categoria (1-5)"
                )
                st.plotly_chart(fig_radar_comp, use_container_width=True)
            
            st.markdown("---")
            
            # ==================== GRÁFICOS DE VOLUME ====================
            col_vol1, col_vol2 = st.columns(2)
            
            with col_vol1:
                if has_cursos:
                    # Gráfico: Total de Inscritos vs Concluídos
                    df_volume = df_kpi[["Centro", "Total Inscritos", "Total Concluídos"]].dropna()
                    if not df_volume.empty:
                        fig_volume = go.Figure()
                        fig_volume.add_trace(go.Bar(
                            x=df_volume["Centro"],
                            y=df_volume["Total Inscritos"],
                            name="Inscritos",
                            marker_color='steelblue'
                        ))
                        fig_volume.add_trace(go.Bar(
                            x=df_volume["Centro"],
                            y=df_volume["Total Concluídos"],
                            name="Concluídos",
                            marker_color='lightgreen'
                        ))
                        fig_volume.update_layout(
                            title="📚 Volume de Formandos por Centro",
                            barmode='group',
                            yaxis_title="Número de Formandos"
                        )
                        st.plotly_chart(fig_volume, use_container_width=True)
            
            with col_vol2:
                if has_quest:
                    # Gráfico: Número de Respostas por Centro
                    df_respostas = df_kpi[["Centro", "Nº Respostas"]].dropna()
                    if not df_respostas.empty:
                        fig_resp = px.pie(
                            df_respostas,
                            values="Nº Respostas",
                            names="Centro",
                            title="📋 Distribuição de Respostas por Centro",
                            hole=0.4,
                            color_discrete_sequence=px.colors.qualitative.Set2
                        )
                        fig_resp.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig_resp, use_container_width=True)
            
            st.markdown("---")
            
            # ==================== HEATMAP DE SATISFAÇÃO ====================
            if has_quest:
                st.subheader("🔥 Heatmap de Satisfação: Centro vs Categoria")
                
                # Criar matriz Centro x Categoria
                heatmap_data = df_q_comp.groupby(["Centro", "Categoria"])["Media"].mean().unstack(fill_value=0)
                
                fig_heatmap = px.imshow(
                    heatmap_data,
                    text_auto='.2f',
                    aspect="auto",
                    color_continuous_scale="RdYlGn",
                    range_color=[1, 5],
                    title="Média de Satisfação por Centro e Categoria"
                )
                fig_heatmap.update_layout(height=400)
                st.plotly_chart(fig_heatmap, use_container_width=True)
            
            st.markdown("---")
            
            # ==================== TABELAS DETALHADAS ====================
            with st.expander("📑 Ver Dados Detalhados por Centro"):
                
                tab1, tab2, tab3 = st.tabs(["📊 Cursos", "📋 Satisfação por Categoria", "🔍 Perguntas"])
                
                with tab1:
                    if has_cursos:
                        # Resumo de cursos por centro
                        if c_insc and c_conc and c_aval and c_aprov:
                            df_cursos_resumo = df_c_comp.groupby(["Centro", "Curso"]).agg({
                                c_insc: "sum",
                                c_conc: "sum",
                                c_aval: "sum",
                                c_aprov: "sum"
                            }).reset_index()
                            st.dataframe(df_cursos_resumo, use_container_width=True)
                        else:
                            st.dataframe(df_c_comp, use_container_width=True)
                    else:
                        st.info("Sem dados de cursos disponíveis")
                
                with tab2:
                    if has_quest:
                        # Tabela pivot Centro x Categoria
                        pivot_cat = df_q_comp.pivot_table(
                            index="Centro", 
                            columns="Categoria", 
                            values="Media", 
                            aggfunc="mean"
                        ).round(2)
                        st.dataframe(pivot_cat, use_container_width=True)
                    else:
                        st.info("Sem dados de questionários disponíveis")
                
                with tab3:
                    if has_quest:
                        # Tabela detalhada por pergunta
                        pivot_perg = df_q_comp.pivot_table(
                            index="Pergunta", 
                            columns="Centro", 
                            values="Media", 
                            aggfunc="mean"
                        ).round(2)
                        st.dataframe(pivot_perg, use_container_width=True)
                    else:
                        st.info("Sem dados de questionários disponíveis")
            
            # ==================== COMPARATIVO PRESENCIAL VS DISTÂNCIA ====================
            if has_quest:
                st.markdown("---")
                st.subheader("📊 Comparativo: Presencial vs À Distância por Centro")
                
                # Preparar dados
                mod_comparison = df_q_comp.groupby(["Centro", "Modalidade"])["Media"].mean().reset_index()
                
                fig_mod_comp = px.bar(
                    mod_comparison,
                    x="Centro",
                    y="Media",
                    color="Modalidade",
                    barmode="group",
                    title="Satisfação Média: Presencial vs À Distância",
                    text="Media",
                    color_discrete_sequence=["#2E86AB", "#A23B72"],
                    range_y=[0, 5]
                )
                fig_mod_comp.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                st.plotly_chart(fig_mod_comp, use_container_width=True)
        
        elif len(selecionados) == 1:
            st.info(f"👆 Selecione pelo menos mais um centro para comparar com **{selecionados[0]}**.")
        else:
            st.info("👆 Selecione pelo menos 2 centros no menu acima para iniciar a comparação.")
            
    else:
        st.info("📂 Carregue ficheiros de Cursos e/ou Questionários na barra lateral para ativar o comparador.")