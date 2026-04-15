import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import get_col, aplicar_filtros

def mostrar_qualidade():
    """Página de Gestão de Qualidade"""
    st.header("🎯 Scorecard de Qualidade Pedagógica")  
    df_c_filt = aplicar_filtros(st.session_state.cursos_df)
    df_q_filt = aplicar_filtros(st.session_state.quest_df)

    # Inicializar objetivos no session_state se não existirem
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

    # Verificar se há dados
    has_cursos = df_c_filt is not None and not df_c_filt.empty
    has_quest = df_q_filt is not None and not df_q_filt.empty

    if has_cursos or has_quest:
        
        # ==================== CÁLCULO DOS KPIs ====================
        
        # --- KPI 1: Satisfação dos formandos (geral) ---
        if has_quest:
            media_sat = df_q_filt["Media"].mean()
            META_SAT = st.session_state.obj_satisfacao
        else:
            media_sat = 0
            META_SAT = st.session_state.obj_satisfacao
        
        # --- KPI 2: Taxa de Conclusão ---
        if has_cursos:
            c_insc = get_col(df_c_filt, "inscritos")
            c_conc = get_col(df_c_filt, "concluidos")
            t_conc = (df_c_filt[c_conc].sum() / df_c_filt[c_insc].sum() * 100) if c_insc and c_conc else 0
            META_CONC = st.session_state.obj_conclusao
        else:
            t_conc = 0
            META_CONC = st.session_state.obj_conclusao
        
        # --- KPI 3: Taxa de Aprovação ---
        if has_cursos:
            c_aval = get_col(df_c_filt, "avaliados")
            c_aprov = get_col(df_c_filt, "aprovados")
            t_aprov = (df_c_filt[c_aprov].sum() / df_c_filt[c_aval].sum() * 100) if c_aval and c_aprov else 0
            META_APROV = st.session_state.obj_aprovacao
        else:
            t_aprov = 0
            META_APROV = st.session_state.obj_aprovacao
        
        # --- KPI 4: Cumprimento do Plano Formativo ---
        if has_cursos:
            c_planeado = get_col(df_c_filt, "planeado")
            if c_planeado and c_conc:
                t_plano = (df_c_filt[c_conc].sum() / df_c_filt[c_planeado].sum() * 100)
            else:
                t_plano = None
            META_PLANO = st.session_state.obj_plano
        else:
            t_plano = None
            META_PLANO = st.session_state.obj_plano
        
        # --- KPI 5: Avaliação dos Formadores ---
        if has_quest:
            df_formador = df_q_filt[df_q_filt["Respondente"].str.contains("Formador", na=False)]
            if not df_formador.empty:
                media_formador = df_formador["Media"].mean()
            else:
                media_formador = None
            META_FORMADOR = st.session_state.obj_formador
        else:
            media_formador = None
            META_FORMADOR = st.session_state.obj_formador
        
        # CSS para tornar os KPIs clicáveis
        st.markdown("""
        <style>
        .kpi-card {
            background-color: white;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 10px;
            transition: all 0.2s ease;
        }
        .kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        .kpi-title {
            font-size: 14px;
            color: #666;
            margin-bottom: 5px;
        }
        .kpi-value {
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .kpi-meta {
            font-size: 12px;
            color: #888;
        }
        .obj-edit {
            font-size: 11px;
            color: #0066cc;
            cursor: pointer;
            text-decoration: underline;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # ==================== EXIBIÇÃO DOS KPIs ====================
        
        st.subheader("📊 KPIs Essenciais")
        
        # Linha 1: Satisfação, Conclusão, Aprovação
        col1, col2, col3 = st.columns(3)
        
        with col1:
            with st.container():
                delta_sat = media_sat - META_SAT
                delta_color = "▲" if delta_sat >= 0 else "▼"
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-title">🎓 Satisfação dos Formandos</div>
                    <div class="kpi-value">{media_sat:.2f} / 5</div>
                    <div class="kpi-meta">Objetivo: ≥ {META_SAT} | {delta_color} {abs(delta_sat):.2f}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("📊 Ver detalhes", key="btn_sat", use_container_width=True):
                    st.session_state.show_sat_popup = True
        
        with col2:
            with st.container():
                delta_conc = t_conc - META_CONC
                delta_color = "▲" if delta_conc >= 0 else "▼"
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-title">✅ Taxa de Conclusão</div>
                    <div class="kpi-value">{t_conc:.1f}%</div>
                    <div class="kpi-meta">Objetivo: ≥ {META_CONC}% | {delta_color} {abs(delta_conc):.1f}%</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("📊 Ver detalhes", key="btn_conc", use_container_width=True):
                    st.session_state.show_conc_popup = True
        
        with col3:
            with st.container():
                delta_aprov = t_aprov - META_APROV
                delta_color = "▲" if delta_aprov >= 0 else "▼"
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-title">📝 Taxa de Aprovação</div>
                    <div class="kpi-value">{t_aprov:.1f}%</div>
                    <div class="kpi-meta">Objetivo: ≥ {META_APROV}% | {delta_color} {abs(delta_aprov):.1f}%</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("📊 Ver detalhes", key="btn_aprov", use_container_width=True):
                    st.session_state.show_aprov_popup = True
        
        # Linha 2: Plano Formativo, Avaliação Formadores
        col4, col5, col6 = st.columns(3)
        
        with col4:
            with st.container():
                if t_plano is not None:
                    delta_plano = t_plano - META_PLANO
                    delta_color = "▲" if delta_plano >= 0 else "▼"
                    st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-title">📅 Cumprimento do Plano Formativo</div>
                        <div class="kpi-value">{t_plano:.1f}%</div>
                        <div class="kpi-meta">Objetivo: ≥ {META_PLANO}% | {delta_color} {abs(delta_plano):.1f}%</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-title">📅 Cumprimento do Plano Formativo</div>
                        <div class="kpi-value">N/D</div>
                        <div class="kpi-meta">⚠️ Adicione coluna "Planeado" ao CSV</div>
                    </div>
                    """, unsafe_allow_html=True)
                if st.button("📊 Ver detalhes", key="btn_plano", use_container_width=True):
                    st.session_state.show_plano_popup = True
        
        with col5:
            with st.container():
                if media_formador is not None:
                    delta_form = media_formador - META_FORMADOR
                    delta_color = "▲" if delta_form >= 0 else "▼"
                    st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-title">👨‍🏫 Avaliação dos Formadores</div>
                        <div class="kpi-value">{media_formador:.2f} / 5</div>
                        <div class="kpi-meta">Objetivo: ≥ {META_FORMADOR} | {delta_color} {abs(delta_form):.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-title">👨‍🏫 Avaliação dos Formadores</div>
                        <div class="kpi-value">N/D</div>
                        <div class="kpi-meta">⚠️ Sem dados de avaliação de formadores</div>
                    </div>
                    """, unsafe_allow_html=True)
                if st.button("📊 Ver detalhes", key="btn_formador", use_container_width=True):
                    st.session_state.show_formador_popup = True
        
        with col6:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">🔄 Taxa de Substituição de Formadores</div>
                <div class="kpi-value">Em breve</div>
                <div class="kpi-meta">⚠️ Necessita nova fonte de dados</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("⚠️ KPIs em Desenvolvimento")
        st.caption("Os KPIs abaixo necessitam de fontes de dados adicionais (Sistema de Incidentes, Helpdesk, etc.)")
        
        # Linha 3: KPIs futuros
        col7, col8, col9 = st.columns(3)
        
        with col7:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">🔧 Incidentes Operacionais</div>
                <div class="kpi-value">N/D</div>
                <div class="kpi-meta">📌 Necessita: Registos de incidentes</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">⏱️ Tempo Médio de Resolução</div>
                <div class="kpi-value">N/D</div>
                <div class="kpi-meta">📌 Necessita: Sistema de tickets</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col8:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">📢 Taxa de Reclamações</div>
                <div class="kpi-value">N/D</div>
                <div class="kpi-meta">📌 Necessita: Registo de reclamações</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">✅ Ações de Melhoria Implementadas</div>
                <div class="kpi-value">N/D</div>
                <div class="kpi-meta">📌 Necessita: Plano de ações</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col9:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">🔄 Recorrência de Problemas</div>
                <div class="kpi-value">N/D</div>
                <div class="kpi-meta">📌 Necessita: Histórico de incidentes</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">📋 Conformidade Documental</div>
                <div class="kpi-value">N/D</div>
                <div class="kpi-meta">📌 Necessita: Auditoria documental</div>
            </div>
            """, unsafe_allow_html=True)
        
        # ==================== POPUPS COM EDITOR DE OBJETIVO ====================
        
        # Preparar dados detalhados por curso para cada KPI disponível
        
        if has_cursos:
            # Taxa Conclusão por Curso
            df_conc_curso = df_c_filt.groupby("Curso").agg({
                c_insc: "sum",
                c_conc: "sum"
            }).reset_index()
            df_conc_curso["Taxa Conclusão (%)"] = (df_conc_curso[c_conc] / df_conc_curso[c_insc] * 100).round(1)
            df_conc_curso = df_conc_curso.rename(columns={c_insc: "Inscritos", c_conc: "Concluídos", "Curso": "Curso"})
            df_conc_curso = df_conc_curso[["Curso", "Inscritos", "Concluídos", "Taxa Conclusão (%)"]]
            
            # Taxa Aprovação por Curso
            df_aprov_curso = df_c_filt.groupby("Curso").agg({
                c_aval: "sum",
                c_aprov: "sum"
            }).reset_index()
            df_aprov_curso["Taxa Aprovação (%)"] = (df_aprov_curso[c_aprov] / df_aprov_curso[c_aval] * 100).round(1)
            df_aprov_curso = df_aprov_curso.rename(columns={c_aval: "Avaliados", c_aprov: "Aprovados", "Curso": "Curso"})
            df_aprov_curso = df_aprov_curso[["Curso", "Avaliados", "Aprovados", "Taxa Aprovação (%)"]]
            
            # Cumprimento Plano por Curso
            if t_plano is not None:
                df_plano_curso = df_c_filt.groupby("Curso").agg({
                    c_conc: "sum",
                    c_planeado: "sum"
                }).reset_index()
                df_plano_curso["Cumprimento Plano (%)"] = (df_plano_curso[c_conc] / df_plano_curso[c_planeado] * 100).round(1)
                df_plano_curso = df_plano_curso.rename(columns={c_conc: "Realizado", c_planeado: "Planeado", "Curso": "Curso"})
                df_plano_curso = df_plano_curso[["Curso", "Planeado", "Realizado", "Cumprimento Plano (%)"]]
        
        if has_quest:
            # Satisfação por Curso
            df_sat_curso = df_q_filt.groupby("Curso")["Media"].mean().reset_index()
            df_sat_curso["Média Satisfação"] = df_sat_curso["Media"].round(2)
            df_sat_curso = df_sat_curso[["Curso", "Média Satisfação"]]
            
            # Avaliação Formadores por Curso
            if media_formador is not None:
                df_formador_curso = df_formador.groupby("Curso")["Media"].mean().reset_index()
                df_formador_curso["Média Avaliação Formador"] = df_formador_curso["Media"].round(2)
                df_formador_curso = df_formador_curso[["Curso", "Média Avaliação Formador"]]
        
        # Popup Satisfação
        if st.session_state.get("show_sat_popup", False) and has_quest:
            with st.expander("📈 Detalhamento por Curso - Satisfação dos Formandos", expanded=True):
                
                # Editor de objetivo
                col_edit1, col_edit2 = st.columns([2, 1])
                with col_edit1:
                    novo_objetivo = st.number_input(
                        "✏️ Editar Objetivo do KPI",
                        min_value=1.0,
                        max_value=5.0,
                        value=st.session_state.obj_satisfacao,
                        step=0.1,
                        key="edit_obj_sat",
                        help="Altere o objetivo do KPI. O dashboard será atualizado automaticamente."
                    )
                    if novo_objetivo != st.session_state.obj_satisfacao:
                        st.session_state.obj_satisfacao = novo_objetivo
                        st.success(f"✅ Objetivo alterado para {novo_objetivo}")
                        st.rerun()
                
                with col_edit2:
                    st.metric("Valor Atual", f"{media_sat:.2f}")
                
                st.markdown("---")
                st.dataframe(
                    df_sat_curso.style.apply(
                        lambda x: ['background-color: #d4edda' if i == df_sat_curso["Média Satisfação"].idxmax() 
                                   else 'background-color: #f8d7da' if i == df_sat_curso["Média Satisfação"].idxmin() 
                                   else '' for i in range(len(df_sat_curso))],
                        axis=0
                    ).format({"Média Satisfação": "{:.2f}"}),
                    use_container_width=True,
                    hide_index=True
                )
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.caption(f"📊 Média Geral: {media_sat:.2f}")
                with col_b:
                    st.caption(f"⬆️ Melhor Curso: {df_sat_curso.loc[df_sat_curso['Média Satisfação'].idxmax(), 'Curso']} ({df_sat_curso['Média Satisfação'].max():.2f})")
                with col_c:
                    st.caption(f"⬇️ Pior Curso: {df_sat_curso.loc[df_sat_curso['Média Satisfação'].idxmin(), 'Curso']} ({df_sat_curso['Média Satisfação'].min():.2f})")
                if st.button("🔒 Fechar", key="close_sat"):
                    st.session_state.show_sat_popup = False
                    st.rerun()
        
        # Popup Conclusão
        if st.session_state.get("show_conc_popup", False) and has_cursos:
            with st.expander("📈 Detalhamento por Curso - Taxa de Conclusão", expanded=True):
                
                col_edit1, col_edit2 = st.columns([2, 1])
                with col_edit1:
                    novo_objetivo = st.number_input(
                        "✏️ Editar Objetivo do KPI",
                        min_value=0.0,
                        max_value=100.0,
                        value=st.session_state.obj_conclusao,
                        step=1.0,
                        key="edit_obj_conc",
                        help="Altere o objetivo do KPI. O dashboard será atualizado automaticamente."
                    )
                    if novo_objetivo != st.session_state.obj_conclusao:
                        st.session_state.obj_conclusao = novo_objetivo
                        st.success(f"✅ Objetivo alterado para {novo_objetivo}%")
                        st.rerun()
                
                with col_edit2:
                    st.metric("Valor Atual", f"{t_conc:.1f}%")
                
                st.markdown("---")
                st.dataframe(
                    df_conc_curso.style.apply(
                        lambda x: ['background-color: #d4edda' if i == df_conc_curso["Taxa Conclusão (%)"].idxmax() 
                                   else 'background-color: #f8d7da' if i == df_conc_curso["Taxa Conclusão (%)"].idxmin() 
                                   else '' for i in range(len(df_conc_curso))],
                        axis=0
                    ).format({"Taxa Conclusão (%)": "{:.1f}%"}),
                    use_container_width=True,
                    hide_index=True
                )
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.caption(f"📊 Média Geral: {t_conc:.1f}%")
                with col_b:
                    st.caption(f"⬆️ Melhor Curso: {df_conc_curso.loc[df_conc_curso['Taxa Conclusão (%)'].idxmax(), 'Curso']} ({df_conc_curso['Taxa Conclusão (%)'].max():.1f}%)")
                with col_c:
                    st.caption(f"⬇️ Pior Curso: {df_conc_curso.loc[df_conc_curso['Taxa Conclusão (%)'].idxmin(), 'Curso']} ({df_conc_curso['Taxa Conclusão (%)'].min():.1f}%)")
                if st.button("🔒 Fechar", key="close_conc"):
                    st.session_state.show_conc_popup = False
                    st.rerun()
        
        # Popup Aprovação
        if st.session_state.get("show_aprov_popup", False) and has_cursos:
            with st.expander("📈 Detalhamento por Curso - Taxa de Aprovação", expanded=True):
                
                col_edit1, col_edit2 = st.columns([2, 1])
                with col_edit1:
                    novo_objetivo = st.number_input(
                        "✏️ Editar Objetivo do KPI",
                        min_value=0.0,
                        max_value=100.0,
                        value=st.session_state.obj_aprovacao,
                        step=1.0,
                        key="edit_obj_aprov",
                        help="Altere o objetivo do KPI. O dashboard será atualizado automaticamente."
                    )
                    if novo_objetivo != st.session_state.obj_aprovacao:
                        st.session_state.obj_aprovacao = novo_objetivo
                        st.success(f"✅ Objetivo alterado para {novo_objetivo}%")
                        st.rerun()
                
                with col_edit2:
                    st.metric("Valor Atual", f"{t_aprov:.1f}%")
                
                st.markdown("---")
                st.dataframe(
                    df_aprov_curso.style.apply(
                        lambda x: ['background-color: #d4edda' if i == df_aprov_curso["Taxa Aprovação (%)"].idxmax() 
                                   else 'background-color: #f8d7da' if i == df_aprov_curso["Taxa Aprovação (%)"].idxmin() 
                                   else '' for i in range(len(df_aprov_curso))],
                        axis=0
                    ).format({"Taxa Aprovação (%)": "{:.1f}%"}),
                    use_container_width=True,
                    hide_index=True
                )
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.caption(f"📊 Média Geral: {t_aprov:.1f}%")
                with col_b:
                    st.caption(f"⬆️ Melhor Curso: {df_aprov_curso.loc[df_aprov_curso['Taxa Aprovação (%)'].idxmax(), 'Curso']} ({df_aprov_curso['Taxa Aprovação (%)'].max():.1f}%)")
                with col_c:
                    st.caption(f"⬇️ Pior Curso: {df_aprov_curso.loc[df_aprov_curso['Taxa Aprovação (%)'].idxmin(), 'Curso']} ({df_aprov_curso['Taxa Aprovação (%)'].min():.1f}%)")
                if st.button("🔒 Fechar", key="close_aprov"):
                    st.session_state.show_aprov_popup = False
                    st.rerun()
        
        # Popup Plano Formativo
        if st.session_state.get("show_plano_popup", False) and t_plano is not None:
            with st.expander("📈 Detalhamento por Curso - Cumprimento do Plano Formativo", expanded=True):
                
                col_edit1, col_edit2 = st.columns([2, 1])
                with col_edit1:
                    novo_objetivo = st.number_input(
                        "✏️ Editar Objetivo do KPI",
                        min_value=0.0,
                        max_value=100.0,
                        value=st.session_state.obj_plano,
                        step=1.0,
                        key="edit_obj_plano",
                        help="Altere o objetivo do KPI. O dashboard será atualizado automaticamente."
                    )
                    if novo_objetivo != st.session_state.obj_plano:
                        st.session_state.obj_plano = novo_objetivo
                        st.success(f"✅ Objetivo alterado para {novo_objetivo}%")
                        st.rerun()
                
                with col_edit2:
                    st.metric("Valor Atual", f"{t_plano:.1f}%")
                
                st.markdown("---")
                st.dataframe(
                    df_plano_curso.style.apply(
                        lambda x: ['background-color: #d4edda' if i == df_plano_curso["Cumprimento Plano (%)"].idxmax() 
                                   else 'background-color: #f8d7da' if i == df_plano_curso["Cumprimento Plano (%)"].idxmin() 
                                   else '' for i in range(len(df_plano_curso))],
                        axis=0
                    ).format({"Cumprimento Plano (%)": "{:.1f}%"}),
                    use_container_width=True,
                    hide_index=True
                )
                if st.button("🔒 Fechar", key="close_plano"):
                    st.session_state.show_plano_popup = False
                    st.rerun()
        
        # Popup Avaliação Formadores
        if st.session_state.get("show_formador_popup", False) and media_formador is not None:
            with st.expander("📈 Detalhamento por Curso - Avaliação dos Formadores", expanded=True):
                
                col_edit1, col_edit2 = st.columns([2, 1])
                with col_edit1:
                    novo_objetivo = st.number_input(
                        "✏️ Editar Objetivo do KPI",
                        min_value=1.0,
                        max_value=5.0,
                        value=st.session_state.obj_formador,
                        step=0.1,
                        key="edit_obj_formador",
                        help="Altere o objetivo do KPI. O dashboard será atualizado automaticamente."
                    )
                    if novo_objetivo != st.session_state.obj_formador:
                        st.session_state.obj_formador = novo_objetivo
                        st.success(f"✅ Objetivo alterado para {novo_objetivo}")
                        st.rerun()
                
                with col_edit2:
                    st.metric("Valor Atual", f"{media_formador:.2f}")
                
                st.markdown("---")
                st.dataframe(
                    df_formador_curso.style.apply(
                        lambda x: ['background-color: #d4edda' if i == df_formador_curso["Média Avaliação Formador"].idxmax() 
                                   else 'background-color: #f8d7da' if i == df_formador_curso["Média Avaliação Formador"].idxmin() 
                                   else '' for i in range(len(df_formador_curso))],
                        axis=0
                    ).format({"Média Avaliação Formador": "{:.2f}"}),
                    use_container_width=True,
                    hide_index=True
                )
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.caption(f"📊 Média Geral: {media_formador:.2f}")
                with col_b:
                    st.caption(f"⬆️ Melhor Curso: {df_formador_curso.loc[df_formador_curso['Média Avaliação Formador'].idxmax(), 'Curso']} ({df_formador_curso['Média Avaliação Formador'].max():.2f})")
                with col_c:
                    st.caption(f"⬇️ Pior Curso: {df_formador_curso.loc[df_formador_curso['Média Avaliação Formador'].idxmin(), 'Curso']} ({df_formador_curso['Média Avaliação Formador'].min():.2f})")
                if st.button("🔒 Fechar", key="close_formador"):
                    st.session_state.show_formador_popup = False
                    st.rerun()
        
        # ==================== VISUALIZAÇÕES EXISTENTES ====================
        ##OLa
        if has_quest:
            st.markdown("---")
            col_rad, col_bar = st.columns(2)

            with col_rad:
                st.subheader("Equilíbrio de Qualidade (Radar)")
                cat_stats = df_q_filt.groupby("Categoria")["Media"].mean().reset_index()
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(r=cat_stats["Media"], theta=cat_stats["Categoria"], fill='toself', name='Média'))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False)
                st.plotly_chart(fig_radar, use_container_width=True)

            with col_bar:
                st.subheader("Presencial vs. À Distância")
                mod_comp = df_q_filt.groupby(["Categoria", "Modalidade"])["Media"].mean().reset_index()
                fig_mod = px.bar(mod_comp, x="Categoria", y="Media", color="Modalidade", barmode="group", range_y=[0,5])
                st.plotly_chart(fig_mod, use_container_width=True)

            st.subheader("🔍 Identificação de Pontos Críticos (Heatmap)")
            pivot_heat = df_q_filt.pivot_table(index="Pergunta", columns="Modalidade", values="Media", aggfunc="mean").dropna()
           
            def color_rule(val):
                color = 'red' if val < 3.0 else 'orange' if val < 3.5 else 'green'
                return f'background-color: {color}; color: white'

            st.dataframe(pivot_heat.style.map(color_rule).format("{:.2f}"), use_container_width=True)
        
    else:
        st.warning("⚠️ Carregue ficheiros de Cursos e/ou Questionários na barra lateral para visualizar os KPIs.")
