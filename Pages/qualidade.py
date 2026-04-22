import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import unicodedata
import re

# ------------------------------------------------------------
# Funções auxiliares (caso não existam em utils.data_utils)
# ------------------------------------------------------------
def get_col(df, pattern):
    """Retorna a primeira coluna cujo nome contenha o pattern (case-insensitive)."""
    pattern = pattern.lower()
    for col in df.columns:
        if pattern in col.lower():
            return col
    return None

def aplicar_filtros(df):
    """Aplica os filtros globais da sidebar (centro, datas, etc.) se existirem."""
    if df is None or df.empty:
        return df
    # Filtro por centro (se existir no session_state)
    if hasattr(st.session_state, 'filtro_centro') and st.session_state.filtro_centro:
        if 'Centro' in df.columns:
            df = df[df['Centro'].isin(st.session_state.filtro_centro)]
    # Outros filtros podem ser adicionados aqui (datas, etc.)
    return df

# ------------------------------------------------------------
# Página principal de Qualidade
# ------------------------------------------------------------
def mostrar_qualidade():
    st.header("🎯 Scorecard de Qualidade Pedagógica")

    # ----- Dados dos Cursos (da página "Análise de Formações") -----
    df_cursos_raw = st.session_state.get("acoes_editaveis", None)
    if df_cursos_raw is not None and not df_cursos_raw.empty:
        if "Apagar" in df_cursos_raw.columns:
            df_cursos_raw = df_cursos_raw.drop(columns=["Apagar"])
        # Conversões de tipo
        for col in ["Inscritos", "Aptos", "Inaptos", "Desistentes", "Devedores",
                    "Taxa de satisfação Final", "Avaliação formador",
                    "Valor total a receber", "Valor Total Recebido"]:
            if col in df_cursos_raw.columns:
                df_cursos_raw[col] = pd.to_numeric(df_cursos_raw[col], errors="coerce")
        for col in ["Data Inicial", "Data Final"]:
            if col in df_cursos_raw.columns:
                df_cursos_raw[col] = pd.to_datetime(df_cursos_raw[col], errors="coerce", dayfirst=True)
    else:
        df_cursos_raw = None

    # ----- Dados dos Questionários (se existirem) -----
    df_quest_raw = st.session_state.get("quest_editaveis", None)

    # Aplicar filtros (centro, datas, etc.)
    df_cursos = aplicar_filtros(df_cursos_raw) if df_cursos_raw is not None else None
    df_quest = aplicar_filtros(df_quest_raw) if df_quest_raw is not None else None

    has_cursos = df_cursos is not None and not df_cursos.empty
    has_quest = df_quest is not None and not df_quest.empty

    # Inicializar objectivos (metas) no session_state
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
    if 'obj_substituicao' not in st.session_state:
        st.session_state.obj_substituicao = 10.0
    if 'obj_multiformador' not in st.session_state:
        st.session_state.obj_multiformador = 20.0
    if 'obj_reclamacao_curso' not in st.session_state:
        st.session_state.obj_reclamacao_curso = 5.0
    if 'obj_tmrp' not in st.session_state:
        st.session_state.obj_tmrp = 48.0
    if 'obj_acoes_implementadas' not in st.session_state:
        st.session_state.obj_acoes_implementadas = 80.0
    if 'obj_recorrencia' not in st.session_state:
        st.session_state.obj_recorrencia = 10.0
    if 'obj_conformidade' not in st.session_state:
        st.session_state.obj_conformidade = 100.0

    # Expander para editar as metas
    with st.expander("⚙️ Definir Objetivos (Metas) dos KPIs", expanded=False):
        st.markdown("Ajuste os valores desejados para cada indicador:")
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.obj_satisfacao = st.number_input(
                "🎓 Satisfação dos Formandos (máx 5)", min_value=0.0, max_value=5.0, step=0.1,
                value=st.session_state.obj_satisfacao, key="edit_sat"
            )
            st.session_state.obj_conclusao = st.number_input(
                "✅ Taxa de Conclusão (%)", min_value=0.0, max_value=100.0, step=1.0,
                value=st.session_state.obj_conclusao, key="edit_conc"
            )
            st.session_state.obj_aprovacao = st.number_input(
                "📝 Taxa de Aprovação (%)", min_value=0.0, max_value=100.0, step=1.0,
                value=st.session_state.obj_aprovacao, key="edit_aprov"
            )
            st.session_state.obj_plano = st.number_input(
                "📅 Cumprimento do Plano (%)", min_value=0.0, max_value=100.0, step=1.0,
                value=st.session_state.obj_plano, key="edit_plano"
            )
            st.session_state.obj_formador = st.number_input(
                "👨‍🏫 Avaliação dos Formadores (máx 5)", min_value=0.0, max_value=5.0, step=0.1,
                value=st.session_state.obj_formador, key="edit_form"
            )
        with col2:
            st.session_state.obj_substituicao = st.number_input(
                "🔄 Taxa de Substituição de Formadores (%) - máximo", min_value=0.0, max_value=100.0, step=1.0,
                value=st.session_state.obj_substituicao, key="edit_subst"
            )
            st.session_state.obj_multiformador = st.number_input(
                "👥 Ações com mais de um Formador (%) - mínimo", min_value=0.0, max_value=100.0, step=1.0,
                value=st.session_state.obj_multiformador, key="edit_mult"
            )
            st.session_state.obj_reclamacao_curso = st.number_input(
                "📢 Taxa de Reclamações por Curso (%) - máximo", min_value=0.0, max_value=100.0, step=0.5,
                value=st.session_state.obj_reclamacao_curso, key="edit_recl"
            )
            st.session_state.obj_tmrp = st.number_input(
                "⏱️ TMRP (horas) - máximo", min_value=0.0, max_value=200.0, step=1.0,
                value=st.session_state.obj_tmrp, key="edit_tmrp"
            )
            st.session_state.obj_acoes_implementadas = st.number_input(
                "✅ Ações de Melhoria Implementadas (%) - mínimo", min_value=0.0, max_value=100.0, step=1.0,
                value=st.session_state.obj_acoes_implementadas, key="edit_acoes"
            )
            st.session_state.obj_recorrencia = st.number_input(
                "⚠️ Recorrência de Problemas (%) - máximo", min_value=0.0, max_value=100.0, step=1.0,
                value=st.session_state.obj_recorrencia, key="edit_rec"
            )
            st.session_state.obj_conformidade = st.number_input(
                "📄 Conformidade Documental (%) - mínimo", min_value=0.0, max_value=100.0, step=1.0,
                value=st.session_state.obj_conformidade, key="edit_conf"
            )
        st.info("💡 As alterações são aplicadas imediatamente. Os objetivos são guardados durante a sessão.")

    # ------------------------------------------------------------
    # Cálculo dos KPIs principais (com as novas fórmulas)
    # ------------------------------------------------------------
    if has_cursos:
        total_inscritos = df_cursos["Inscritos"].sum() if "Inscritos" in df_cursos.columns else 0
        total_aptos = df_cursos["Aptos"].sum() if "Aptos" in df_cursos.columns else 0
        total_inaptos = df_cursos["Inaptos"].sum() if "Inaptos" in df_cursos.columns else 0
        
        # Taxa de Conclusão = ((Aptos + Inaptos) / Inscritos) * 100
        total_aptos_inaptos = total_aptos + total_inaptos
        taxa_conclusao = (total_aptos_inaptos / total_inscritos * 100) if total_inscritos > 0 else 0

        # Taxa de Aprovação = (Aptos / (Aptos + Inaptos)) * 100
        taxa_aprovacao = (total_aptos / total_aptos_inaptos * 100) if total_aptos_inaptos > 0 else 0

        # Cumprimento do Plano = (Finalizados / Previstas) * 100
        if "Status" in df_cursos.columns:
            status_norm = df_cursos["Status"].astype(str).str.strip().str.lower()
            total_finalizadas = (status_norm == "finalizado").sum()
            total_previstas = (status_norm == "prevista").sum()
            cumprimento_plano = (total_finalizadas / total_previstas * 100) if total_previstas > 0 else 0
        else:
            cumprimento_plano = None

        # Satisfação dos formandos (média da Taxa de satisfação Final)
        if "Taxa de satisfação Final" in df_cursos.columns:
            media_satisfacao_cursos = df_cursos["Taxa de satisfação Final"].mean()
        else:
            media_satisfacao_cursos = None

        # Avaliação dos formadores
        if "Avaliação formador" in df_cursos.columns:
            media_avaliacao_formador = df_cursos["Avaliação formador"].mean()
        else:
            media_avaliacao_formador = None
    else:
        total_inscritos = total_aptos = total_inaptos = 0
        taxa_conclusao = taxa_aprovacao = 0
        cumprimento_plano = None
        media_satisfacao_cursos = None
        media_avaliacao_formador = None

    # Se existirem questionários, usar a média da coluna "Média" (prioridade para satisfação)
    if has_quest and "Média" in df_quest.columns:
        media_satisfacao = df_quest["Média"].mean()
        if "Respondente" in df_quest.columns:
            df_formador_quest = df_quest[df_quest["Respondente"].str.contains("Formador", na=False)]
            media_formador_quest = df_formador_quest["Média"].mean() if not df_formador_quest.empty else None
        else:
            media_formador_quest = None
    else:
        media_satisfacao = media_satisfacao_cursos
        media_formador_quest = media_avaliacao_formador

    satisfacao_valor = media_satisfacao if media_satisfacao is not None else 0
    avaliacao_formador_valor = media_formador_quest if media_formador_quest is not None else 0

    # ------------------------------------------------------------
    # CSS personalizado para os cards
    # ------------------------------------------------------------
    st.markdown("""
    <style>
    .kpi-card {
        background-color: var(--secondary-background-color);
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 10px;
        transition: all 0.2s ease;
        border: 1px solid var(--border-color);
        height: 100%;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    .kpi-title {
        font-size: 14px;
        color: var(--text-color);
        opacity: 0.7;
        margin-bottom: 5px;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 5px;
        color: var(--text-color);
    }
    .kpi-meta {
        font-size: 12px;
        color: var(--text-color);
        opacity: 0.6;
    }
    .detail-button {
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.subheader("📊 KPI's Essenciais")

    # Estado para controlar qual detalhe está aberto (None = nenhum)
    if 'detalhe_ativo' not in st.session_state:
        st.session_state.detalhe_ativo = None

    # Função para alternar o detalhe
    def set_detalhe(kpi):
        if st.session_state.detalhe_ativo == kpi:
            st.session_state.detalhe_ativo = None   # fecha se clicar no mesmo
        else:
            st.session_state.detalhe_ativo = kpi    # abre o novo, fechando o anterior

    # Layout em 5 colunas (3 + 2)
    col1, col2, col3 = st.columns(3)
    col4, col5 = st.columns(2)

    with col1:
        delta_sat = satisfacao_valor - st.session_state.obj_satisfacao
        delta_color = "▲" if delta_sat >= 0 else "▼"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">🎓 Satisfação dos Formandos</div>
            <div class="kpi-value">{satisfacao_valor:.2f} / 5</div>
            <div class="kpi-meta">Objetivo: ≥ {st.session_state.obj_satisfacao} | {delta_color} {abs(delta_sat):.2f}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔍 Ver detalhes", key="btn_sat", use_container_width=True):
            set_detalhe('sat')

    with col2:
        delta_conc = taxa_conclusao - st.session_state.obj_conclusao
        delta_color = "▲" if delta_conc >= 0 else "▼"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">✅ Taxa de Conclusão</div>
            <div class="kpi-value">{taxa_conclusao:.1f}%</div>
            <div class="kpi-meta">Objetivo: ≥ {st.session_state.obj_conclusao}% | {delta_color} {abs(delta_conc):.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔍 Ver detalhes", key="btn_conc", use_container_width=True):
            set_detalhe('conc')

    with col3:
        delta_aprov = taxa_aprovacao - st.session_state.obj_aprovacao
        delta_color = "▲" if delta_aprov >= 0 else "▼"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">📝 Taxa de Aprovação</div>
            <div class="kpi-value">{taxa_aprovacao:.1f}%</div>
            <div class="kpi-meta">Objetivo: ≥ {st.session_state.obj_aprovacao:.0f}% | {delta_color} {abs(delta_aprov):.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔍 Ver detalhes", key="btn_aprov", use_container_width=True):
            set_detalhe('aprov')
    with col4:
        if cumprimento_plano is not None:
            delta_plano = cumprimento_plano - st.session_state.obj_plano
            delta_color = "▲" if delta_plano >= 0 else "▼"
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">📅 Cumprimento do Plano</div>
                <div class="kpi-value">{cumprimento_plano:.1f}%</div>
                <div class="kpi-meta">Objetivo: ≥ {st.session_state.obj_plano}% | {delta_color} {abs(delta_plano):.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">📅 Cumprimento do Plano</div>
                <div class="kpi-value">N/D</div>
                <div class="kpi-meta">⚠️ Coluna "Status" sem 'Prevista'/'Finalizado'</div>
            </div>
            """, unsafe_allow_html=True)
        if st.button("🔍 Ver detalhes", key="btn_plano", use_container_width=True):
            set_detalhe('plano')

    with col5:
        if avaliacao_formador_valor > 0:
            delta_avf = avaliacao_formador_valor - st.session_state.obj_formador
            delta_color = "▲" if delta_avf >= 0 else "▼"
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">👨‍🏫 Avaliação dos Formadores</div>
                <div class="kpi-value">{avaliacao_formador_valor:.2f} / 5</div>
                <div class="kpi-meta">Objetivo: ≥ {st.session_state.obj_formador} | {delta_color} {abs(delta_avf):.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">👨‍🏫 Avaliação dos Formadores</div>
                <div class="kpi-value">N/D</div>
                <div class="kpi-meta">⚠️ Sem dados</div>
            </div>
            """, unsafe_allow_html=True)
        if st.button("🔍 Ver detalhes", key="btn_avf", use_container_width=True):
            set_detalhe('avf')

    # ---------- ÁREAS DE DETALHE (apenas uma aberta de cada vez) ----------
    # Satisfação
        # Satisfação
    if st.session_state.detalhe_ativo == 'sat':
        with st.expander("📊 Detalhe da Satisfação dos Formandos", expanded=True):
            st.markdown("**Dados que compõem este indicador:**")
            if has_quest and "Média" in df_quest.columns:
                df_sat = df_quest[['Ação', 'Centro', 'Categoria', 'Média', 'Respondente']].copy()
                # Garantir que a coluna Média é numérica
                df_sat['Média'] = pd.to_numeric(df_sat['Média'], errors='coerce')
                meta_sat = st.session_state.obj_satisfacao
                
                # Função para colorir a célula da coluna 'Média' se abaixo da meta
                def highlight_below_meta(val, meta):
                    if pd.notna(val) and val < meta:
                        return 'background-color: #fce8ea; border-left: 4px solid #dc3545;'
                    return ''
                
                # Aplicar estilo apenas na coluna 'Média'
                styled_sat = df_sat.style.map(
                    lambda x: highlight_below_meta(x, meta_sat),
                    subset=['Média']
                )
                st.dataframe(styled_sat, use_container_width=True)
                
                st.markdown("**Filtros:**")
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    centros = st.multiselect("Centro", options=sorted(df_sat['Centro'].unique()), key="sat_centro")
                with col_f2:
                    categorias = st.multiselect("Categoria", options=sorted(df_sat['Categoria'].unique()), key="sat_cat")
                df_filt = df_sat.copy()
                if centros:
                    df_filt = df_filt[df_filt['Centro'].isin(centros)]
                if categorias:
                    df_filt = df_filt[df_filt['Categoria'].isin(categorias)]
                # Reaplicar estilo no DataFrame filtrado
                styled_filt = df_filt.style.map(
                    lambda x: highlight_below_meta(x, meta_sat),
                    subset=['Média']
                )
                st.dataframe(styled_filt, use_container_width=True)
                st.caption(f"Média global: {df_filt['Média'].mean():.2f} | Total de respostas: {len(df_filt)}")
            else:
                st.info("Dados de satisfação disponíveis apenas nos cursos (coluna 'Taxa de satisfação Final')")
                if has_cursos and "Taxa de satisfação Final" in df_cursos.columns:
                    df_sat_cursos = df_cursos[['Ação', 'Centro', 'Taxa de satisfação Final']].dropna()
                    df_sat_cursos['Taxa de satisfação Final'] = pd.to_numeric(df_sat_cursos['Taxa de satisfação Final'], errors='coerce')
                    meta_sat = st.session_state.obj_satisfacao
                    
                    def highlight_below_meta_sat(val):
                        if pd.notna(val) and val < meta_sat:
                            return 'background-color: #fce8ea; border-left: 4px solid #dc3545;'
                        return ''
                    
                    styled_cursos = df_sat_cursos.style.map(
                        highlight_below_meta_sat,
                        subset=['Taxa de satisfação Final']
                    )
                    st.dataframe(styled_cursos, use_container_width=True)
    # Taxa de Conclusão
    if st.session_state.detalhe_ativo == 'conc':
        with st.expander("📊 Detalhe da Taxa de Conclusão", expanded=True):
            if has_cursos and all(c in df_cursos.columns for c in ['Ação', 'Centro', 'Inscritos', 'Aptos', 'Inaptos']):
                df_conc = df_cursos[['Ação', 'Centro', 'Inscritos', 'Aptos', 'Inaptos']].copy()
                df_conc['Concluíram'] = df_conc['Aptos'] + df_conc['Inaptos']
                df_conc['Taxa_Conclusão_%'] = (df_conc['Concluíram'] / df_conc['Inscritos'] * 100).round(1)
                meta_conc = st.session_state.obj_conclusao
                
                # Destacar linhas onde a taxa de conclusão < meta
                def highlight_row(row):
                    if pd.notna(row['Taxa_Conclusão_%']) and row['Taxa_Conclusão_%'] < meta_conc:
                        return ['background-color: #fce8ea; border-left: 4px solid #dc3545;'] * len(row)
                    else:
                        return [''] * len(row)
                
                styled_conc = df_conc.style.apply(highlight_row, axis=1)
                st.dataframe(styled_conc, use_container_width=True)
                
                st.markdown("**Filtros:**")
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    centros = st.multiselect("Centro", options=sorted(df_conc['Centro'].unique()), key="conc_centro")
                with col_f2:
                    acoes = st.multiselect("Ação", options=sorted(df_conc['Ação'].unique()), key="conc_acao")
                df_filt = df_conc.copy()
                if centros:
                    df_filt = df_filt[df_filt['Centro'].isin(centros)]
                if acoes:
                    df_filt = df_filt[df_filt['Ação'].isin(acoes)]
                styled_filt = df_filt.style.apply(highlight_row, axis=1)
                st.dataframe(styled_filt, use_container_width=True)
                st.caption(f"Taxa global: {taxa_conclusao:.1f}% | Total cursos: {len(df_filt)}")
            else:
                st.warning("Dados insuficientes para calcular conclusão por curso.")

    # Taxa de Aprovação
    if st.session_state.detalhe_ativo == 'aprov':
        with st.expander("📊 Detalhe da Taxa de Aprovação", expanded=True):
            if has_cursos and all(c in df_cursos.columns for c in ['Ação', 'Centro', 'Aptos', 'Inaptos']):
                df_aprov = df_cursos[['Ação', 'Centro', 'Aptos', 'Inaptos']].copy()
                df_aprov['Avaliados'] = df_aprov['Aptos'] + df_aprov['Inaptos']
                df_aprov['Taxa_Aprovação_%'] = (df_aprov['Aptos'] / df_aprov['Avaliados'] * 100).round(1)
                meta_aprov = st.session_state.obj_aprovacao
                
                def highlight_row(row):
                    if pd.notna(row['Taxa_Aprovação_%']) and row['Taxa_Aprovação_%'] < meta_aprov:
                        return ['background-color: #fce8ea; border-left: 4px solid #dc3545;'] * len(row)
                    return [''] * len(row)
                
                styled_aprov = df_aprov.style.apply(highlight_row, axis=1)
                st.dataframe(styled_aprov, use_container_width=True)
                
                st.markdown("**Filtros:**")
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    centros = st.multiselect("Centro", options=sorted(df_aprov['Centro'].unique()), key="aprov_centro")
                with col_f2:
                    acoes = st.multiselect("Ação", options=sorted(df_aprov['Ação'].unique()), key="aprov_acao")
                df_filt = df_aprov.copy()
                if centros:
                    df_filt = df_filt[df_filt['Centro'].isin(centros)]
                if acoes:
                    df_filt = df_filt[df_filt['Ação'].isin(acoes)]
                styled_filt = df_filt.style.apply(highlight_row, axis=1)
                st.dataframe(styled_filt, use_container_width=True)
                st.caption(f"Taxa global: {taxa_aprovacao:.1f}% | Total cursos com avaliação: {len(df_filt)}")
            else:
                st.warning("Dados insuficientes para calcular aprovação por curso.")

    # Cumprimento do Plano
    if st.session_state.detalhe_ativo == 'plano':
        with st.expander("📊 Detalhe do Cumprimento do Plano", expanded=True):
            if has_cursos and "Status" in df_cursos.columns:
                df_plano = df_cursos[['Ação', 'Centro', 'Status']].copy()
                st.dataframe(df_plano, use_container_width=True)
                st.markdown("**Filtros:**")
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    centros = st.multiselect("Centro", options=sorted(df_plano['Centro'].unique()), key="plano_centro")
                with col_f2:
                    status_opts = st.multiselect("Status", options=sorted(df_plano['Status'].unique()), key="plano_status")
                df_filt = df_plano.copy()
                if centros:
                    df_filt = df_filt[df_filt['Centro'].isin(centros)]
                if status_opts:
                    df_filt = df_filt[df_filt['Status'].isin(status_opts)]
                st.dataframe(df_filt, use_container_width=True)
                finalizadas = (df_filt['Status'].str.lower() == 'finalizado').sum()
                previstas = (df_filt['Status'].str.lower() == 'prevista').sum()
                taxa_local = (finalizadas / previstas * 100) if previstas > 0 else 0
                st.caption(f"Taxa de cumprimento: {taxa_local:.1f}% | Finalizadas: {finalizadas} | Previstas: {previstas}")
            else:
                st.info("Coluna 'Status' não disponível nos cursos.")

    # Avaliação dos Formadores
    if st.session_state.detalhe_ativo == 'avf':
        with st.expander("📊 Detalhe da Avaliação dos Formadores", expanded=True):
            if has_quest and "Média" in df_quest.columns and "Respondente" in df_quest.columns:
                df_avf = df_quest[df_quest['Respondente'].str.contains("Formador", na=False)][['Ação', 'Centro', 'Categoria', 'Média']].copy()
                if not df_avf.empty:
                    df_avf['Média'] = pd.to_numeric(df_avf['Média'], errors='coerce')
                    meta_avf = st.session_state.obj_formador
                    
                    def highlight_below(val):
                        if pd.notna(val) and val < meta_avf:
                            return 'background-color: #fce8ea; border-left: 4px solid #dc3545;'
                        return ''
                    
                    styled_avf = df_avf.style.map(highlight_below, subset=['Média'])
                    st.dataframe(styled_avf, use_container_width=True)
                    
                    st.markdown("**Filtros:**")
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        centros = st.multiselect("Centro", options=sorted(df_avf['Centro'].unique()), key="avf_centro")
                    with col_f2:
                        categorias = st.multiselect("Categoria", options=sorted(df_avf['Categoria'].unique()), key="avf_cat")
                    df_filt = df_avf.copy()
                    if centros:
                        df_filt = df_filt[df_filt['Centro'].isin(centros)]
                    if categorias:
                        df_filt = df_filt[df_filt['Categoria'].isin(categorias)]
                    styled_filt = df_filt.style.map(highlight_below, subset=['Média'])
                    st.dataframe(styled_filt, use_container_width=True)
                    st.caption(f"Média global: {df_filt['Média'].mean():.2f} | Total respostas: {len(df_filt)}")
                else:
                    st.info("Nenhuma avaliação de formador encontrada nos questionários.")
            elif has_cursos and "Avaliação formador" in df_cursos.columns:
                df_avf_cursos = df_cursos[['Ação', 'Centro', 'Avaliação formador']].dropna()
                df_avf_cursos['Avaliação formador'] = pd.to_numeric(df_avf_cursos['Avaliação formador'], errors='coerce')
                meta_avf = st.session_state.obj_formador
                
                def highlight_below(val):
                    if pd.notna(val) and val < meta_avf:
                        return 'background-color: #fce8ea; border-left: 4px solid #dc3545;'
                    return ''
                
                styled_cursos = df_avf_cursos.style.map(highlight_below, subset=['Avaliação formador'])
                st.dataframe(styled_cursos, use_container_width=True)
                st.caption(f"Média: {df_avf_cursos['Avaliação formador'].mean():.2f}")
            else:
                st.warning("Sem dados de avaliação de formadores.")

    st.markdown("---")
    # ------------------------------------------------------------
    # KPI 4 – Ações com mais de um formador
    # ------------------------------------------------------------
    if has_cursos and "Formador" in df_cursos.columns:
        def contar_formadores(valor):
            if pd.isna(valor):
                return 0
            valor_str = str(valor)
            # Separadores comuns
            for sep in [',', ';', '/', ' e ']:
                if sep in valor_str:
                    return len([n.strip() for n in re.split(r'[,;/]| e ', valor_str) if n.strip()])
            return 1 if valor_str.strip() else 0

        df_cursos['num_formadores'] = df_cursos['Formador'].apply(contar_formadores)
        total_acoes = len(df_cursos)
        acoes_multiformador = (df_cursos['num_formadores'] > 1).sum()
        perc_multiformador = (acoes_multiformador / total_acoes * 100) if total_acoes > 0 else 0
        meta_multiformador = st.session_state.obj_multiformador
        delta_multiformador = perc_multiformador - meta_multiformador
        delta_color = "▲" if delta_multiformador >= 0 else "▼"

        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">👥 Ações com mais de um Formador</div>
            <div class="kpi-value">{acoes_multiformador} / {total_acoes}</div>
            <div class="kpi-meta">{perc_multiformador:.1f}% das ações | Meta: ≥ {meta_multiformador}% | {delta_color} {abs(delta_multiformador):.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Carregue um ficheiro de cursos com a coluna 'Formador' para ver ações com múltiplos formadores.")

    # ------------------------------------------------------------
    # KPI 5 – Taxa de Substituição de Formadores (com edição)
    # ------------------------------------------------------------
    st.markdown("---")
    st.subheader("👥 Substituição de Formadores")

    if has_cursos and "Formador" in df_cursos.columns and "Ação" in df_cursos.columns:
        def normalizar_string(texto):
            if pd.isna(texto):
                return ""
            texto = str(texto).strip().lower()
            texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
            return texto

        # Guardar snapshot original na primeira execução
        if "formadores_originais" not in st.session_state:
            originais = df_cursos[["Ação", "Formador"]].copy()
            originais["Formador_Norm"] = originais["Formador"].apply(normalizar_string)
            st.session_state.formadores_originais = originais
            st.session_state.formadores_originais_exibicao = df_cursos[["Ação", "Formador"]].copy()

        # Preparar DataFrame para edição
        df_edit_formadores = df_cursos[["Ação", "Formador"]].copy()
        df_edit_formadores.columns = ["ID Ação", "Formador Atual"]
        original_map = st.session_state.formadores_originais_exibicao.set_index("Ação")["Formador"].to_dict()
        df_edit_formadores["Formador Original"] = df_edit_formadores["ID Ação"].map(original_map)
        df_edit_formadores = df_edit_formadores[["ID Ação", "Formador Original", "Formador Atual"]]

        st.info("✏️ Edite o campo 'Formador Atual' para simular uma substituição. O KPI será atualizado automaticamente.")

        edited_formadores = st.data_editor(
            df_edit_formadores,
            use_container_width=True,
            column_config={
                "ID Ação": st.column_config.TextColumn("ID Ação", disabled=True),
                "Formador Original": st.column_config.TextColumn("Formador Original", disabled=True),
                "Formador Atual": st.column_config.TextColumn("Formador Atual"),
            },
            key="formadores_editor"
        )

        col_btn1, col_btn2 = st.columns([1, 5])
        with col_btn1:
            if st.button("💾 Guardar alterações de formadores", key="save_formadores"):
                for idx, row in edited_formadores.iterrows():
                    acao = row["ID Ação"]
                    novo_formador = row["Formador Atual"]
                    mask = df_cursos["Ação"] == acao
                    if mask.any():
                        df_cursos.loc[mask, "Formador"] = novo_formador
                st.session_state.acoes_editaveis = df_cursos
                st.success("✅ Formadores atualizados! A página vai recarregar.")
                st.rerun()

        # Calcular substituições usando normalização
        original_norm_map = st.session_state.formadores_originais.set_index("Ação")["Formador_Norm"].to_dict()
        substituicoes = 0
        total = len(edited_formadores)
        for idx, row in edited_formadores.iterrows():
            acao = row["ID Ação"]
            atual = row["Formador Atual"]
            atual_norm = normalizar_string(atual)
            original_norm = original_norm_map.get(acao, "")
            if atual_norm != original_norm:
                substituicoes += 1

        taxa_substituicao = (substituicoes / total * 100) if total > 0 else 0
        meta_subst = st.session_state.obj_substituicao
        delta_subst = taxa_substituicao - meta_subst
        delta_str = f"▲ {delta_subst:.1f}%" if delta_subst > 0 else f"▼ {abs(delta_subst):.1f}%"

        col_kpi1, col_kpi2 = st.columns(2)
        with col_kpi1:
            st.metric(
                label="🔄 Taxa de Substituição de Formadores",
                value=f"{taxa_substituicao:.1f}%",
                delta=delta_str,
                help=f"Percentagem de cursos onde o formador atual é diferente do original. Objetivo: ≤ {meta_subst}%"
            )
        with col_kpi2:
            st.metric(
                label="📊 Cursos com substituição",
                value=f"{substituicoes} / {total}",
                help="Número de cursos onde o formador foi trocado"
            )

        if st.button("🔄 Redefinir formadores originais (basear nos atuais)"):
            novos_originais = df_cursos[["Ação", "Formador"]].copy()
            novos_originais["Formador_Norm"] = novos_originais["Formador"].apply(normalizar_string)
            st.session_state.formadores_originais = novos_originais
            st.session_state.formadores_originais_exibicao = df_cursos[["Ação", "Formador"]].copy()
            st.success("Base de comparação redefinida. A taxa de substituição voltará a 0%.")
            st.rerun()
    else:
        st.info("Carregue um ficheiro de cursos com as colunas 'Ação' e 'Formador' para calcular a taxa de substituição.")

    # ------------------------------------------------------------
    # KPI 6 e 7 – Incidentes Operacionais e TMRP
    # ------------------------------------------------------------
    st.markdown("---")
    st.subheader("⚠️ Incidentes Operacionais e Resolução")

    if "incidentes_df" not in st.session_state:
        st.session_state.incidentes_df = None
    if "incidentes_filename" not in st.session_state:
        st.session_state.incidentes_filename = None

    if st.session_state.incidentes_df is not None:
        st.success(f"📁 Ficheiro carregado: **{st.session_state.incidentes_filename}**")
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("🔄 Carregar novo ficheiro", key="reset_incidentes"):
                st.session_state.incidentes_df = None
                st.session_state.incidentes_filename = None
                st.rerun()
        df_inc = st.session_state.incidentes_df.copy()
    else:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            modo_carga_inc = st.radio("Modo:", ["Substituir", "Adicionar"], horizontal=True, key="modo_carga_inc")
        with c2:
            incidente_file = st.file_uploader(
                "Carregar ficheiro de Incidentes (Excel)",
                type=["xlsx", "xls"], key="incidentes_upload"
            )
        with c3:
            try:
                with open("assets/Incidentes.xlsx", "rb") as f:
                    conteudo_inc = f.read()
                st.download_button(
                    label="📥 Exemplo Incidentes (Excel)",
                    data=conteudo_inc,
                    file_name="Incidentes.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except FileNotFoundError:
                st.error("⚠️ Ficheiro de exemplo não encontrado: assets/Incidentes.xlsx")
        if incidente_file is not None:
            try:
                df_inc = pd.read_excel(incidente_file)
                df_inc.columns = df_inc.columns.str.strip()
                # Validar colunas obrigatórias
                required = ['Ação', 'Centro', 'Descrição', 'Status', 'Data_Abertura']
                missing = [c for c in required if c not in df_inc.columns]
                if missing:
                    st.error(f"Colunas obrigatórias em falta: {missing}")
                    df_inc = None
                else:
                    st.session_state.incidentes_df = df_inc.copy()
                    st.session_state.incidentes_filename = incidente_file.name
                    st.rerun()
            except Exception as e:
                st.error(f"Erro ao processar ficheiro: {e}")
                df_inc = None
        else:
            df_inc = None

    if df_inc is not None:
        try:
            # Converter datas
            df_inc['Data_Abertura'] = pd.to_datetime(df_inc['Data_Abertura'], errors='coerce')
            if 'Data_Resolução' in df_inc.columns:
                df_inc['Data_Resolução'] = pd.to_datetime(df_inc['Data_Resolução'], errors='coerce')
            else:
                df_inc['Data_Resolução'] = pd.NaT

            # Normalizar Status (mapeamento para categorias padrão)
            status_map = {
                'aberto': 'Aberto',
                'em resolução': 'Em resolução',
                'resolvido': 'Resolvido',
                'aprovado': 'Resolvido',   # se existir "Aprovado", trata como resolvido
                '': 'Aberto',
                None: 'Aberto'
            }
            df_inc['Status'] = df_inc['Status'].astype(str).str.lower().map(status_map).fillna('Desconhecido')

            # Calcular TMRP em horas (apenas para resolvidos com ambas as datas)
            mask_resolvido = (df_inc['Status'] == 'Resolvido') & df_inc['Data_Abertura'].notna() & df_inc['Data_Resolução'].notna()
            df_inc['TMRP_horas'] = None
            df_inc.loc[mask_resolvido, 'TMRP_horas'] = (
                (df_inc.loc[mask_resolvido, 'Data_Resolução'] - df_inc.loc[mask_resolvido, 'Data_Abertura'])
                .dt.total_seconds() / 3600
            )

            # Aplicar filtro de centro (global)
            if hasattr(st.session_state, 'filtro_centro') and st.session_state.filtro_centro and 'Centro' in df_inc.columns:
                df_inc = df_inc[df_inc['Centro'].isin(st.session_state.filtro_centro)]

            if not df_inc.empty:
                # ---------- KPI 6: Nº Incidentes e tendência mensal ----------
                total_incidentes = len(df_inc)
                st.metric("📌 Nº Total de Incidentes Operacionais", total_incidentes)

                # Gráfico de evolução mensal (Data_Abertura)
                if not df_inc['Data_Abertura'].isna().all():
                    df_inc['AnoMes'] = df_inc['Data_Abertura'].dt.to_period('M')
                    incidentes_mensal = df_inc.groupby('AnoMes').size().reset_index(name='Quantidade')
                    incidentes_mensal['AnoMes'] = incidentes_mensal['AnoMes'].astype(str)
                    fig_mensal = px.line(
                        incidentes_mensal, x='AnoMes', y='Quantidade', markers=True,
                        title="Evolução Mensal do Número de Incidentes (abertura)",
                        labels={'AnoMes': 'Mês', 'Quantidade': 'Nº Incidentes'}
                    )
                    st.plotly_chart(fig_mensal, use_container_width=True)
                else:
                    st.info("Sem datas de abertura válidas para evolução mensal.")

                # ---------- KPI 7: TMRP ----------
                df_resolvidos = df_inc[df_inc['Status'] == 'Resolvido']
                tmrp_medio = df_resolvidos['TMRP_horas'].mean() if not df_resolvidos.empty else None
                meta_tmrp = st.session_state.obj_tmrp
                if tmrp_medio is not None:
                    delta_tmrp = tmrp_medio - meta_tmrp
                    delta_str = f"▲ {delta_tmrp:.0f}h" if delta_tmrp > 0 else f"▼ {abs(delta_tmrp):.0f}h"
                    st.metric(
                        label="⏱️ Tempo Médio de Resolução (TMRP)",
                        value=f"{tmrp_medio:.1f} h",
                        delta=delta_str,
                        help="Média do tempo entre abertura e resolução (apenas incidentes resolvidos). Objetivo: ≤ 48h"
                    )
                else:
                    st.metric(label="⏱️ Tempo Médio de Resolução (TMRP)", value="Sem incidentes resolvidos")

                # ---------- Análise por Status ----------
                st.subheader("📊 Distribuição por Estado")
                status_counts = df_inc['Status'].value_counts().reindex(['Aberto', 'Em resolução', 'Resolvido'], fill_value=0)
                col_s1, col_s2, col_s3 = st.columns(3)
                with col_s1:
                    st.metric("🟡 Aberto", status_counts.get('Aberto', 0))
                with col_s2:
                    st.metric("🟠 Em resolução", status_counts.get('Em resolução', 0))
                with col_s3:
                    st.metric("🟢 Resolvido", status_counts.get('Resolvido', 0))

                # Gráfico de barras dos estados
                fig_status = px.bar(
                    x=status_counts.index, y=status_counts.values,
                    labels={'x': 'Estado', 'y': 'Nº Incidentes'},
                    title="Incidentes por Estado", text_auto=True,
                    color=status_counts.index,
                    color_discrete_map={'Aberto':'orange', 'Em resolução':'gold', 'Resolvido':'green'}
                )
                st.plotly_chart(fig_status, use_container_width=True)

                # ---------- Análise por Centro (TMRP e contagem) ----------
                if 'Centro' in df_inc.columns:
                    st.subheader("🏢 Desempenho por Centro")
                    # Contagem por centro e estado
                    centro_status = df_inc.groupby(['Centro', 'Status']).size().unstack(fill_value=0)
                    # Garantir que as colunas de estado existem
                    for estado in ['Aberto', 'Em resolução', 'Resolvido']:
                        if estado not in centro_status.columns:
                            centro_status[estado] = 0

                    # Contagem de resolvidos dentro e fora da meta (<=48h e >48h)
                    df_resolvidos_centro = df_resolvidos.copy()
                    if not df_resolvidos_centro.empty:
                        df_resolvidos_centro['Dentro_meta'] = df_resolvidos_centro['TMRP_horas'] <= 48
                        dentro_meta = df_resolvidos_centro[df_resolvidos_centro['Dentro_meta']].groupby('Centro').size()
                        fora_meta = df_resolvidos_centro[~df_resolvidos_centro['Dentro_meta']].groupby('Centro').size()
                    else:
                        dentro_meta = pd.Series(dtype=int)
                        fora_meta = pd.Series(dtype=int)

                    # TMRP médio por centro (apenas resolvidos)
                    tmrp_centro = df_resolvidos.groupby('Centro')['TMRP_horas'].mean().round(1)

                    # Construir DataFrame de resumo
                    centros = centro_status.index
                    centro_resumo = pd.DataFrame(index=centros)
                    centro_resumo['Aberto'] = centro_status['Aberto']
                    centro_resumo['Em resolução'] = centro_status['Em resolução']
                    centro_resumo['Resolvido'] = centro_status['Resolvido']
                    centro_resumo['Resolvidos dentro da meta (≤48h)'] = dentro_meta.reindex(centros, fill_value=0)
                    centro_resumo['Resolvidos fora da meta (>48h)'] = fora_meta.reindex(centros, fill_value=0)
                    centro_resumo['TMRP médio (h)'] = tmrp_centro.reindex(centros)

                    # Ordenar por centro
                    centro_resumo = centro_resumo.sort_index()
                    st.dataframe(centro_resumo, use_container_width=True)

                # ---------- Tabela detalhada com datas e tempos (com filtros) ----------
                st.subheader("📋 Lista detalhada de Incidentes")
                
                # Preparar DataFrame para exibição
                df_display = df_inc.copy()
                df_display['Tempo (horas)'] = df_display['TMRP_horas'].apply(lambda x: f"{x:.1f} h" if pd.notna(x) else "-")
                df_display['Data Abertura'] = df_display['Data_Abertura'].dt.strftime('%d/%m/%Y')
                df_display['Data Resolução'] = df_display['Data_Resolução'].dt.strftime('%d/%m/%Y')
                cols_show = ['Ação', 'Centro', 'Descrição', 'Status', 'Data Abertura', 'Data Resolução', 'Tempo (horas)']
                df_filtravel = df_display[cols_show].copy()
                
                # Criar filtros na sidebar da tabela (usando colunas)
                st.markdown("**Filtros:**")
                col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                
                with col_f1:
                    acoes = st.multiselect("Ação", options=sorted(df_filtravel['Ação'].unique()), key="filt_acao")
                with col_f2:
                    centros = st.multiselect("Centro", options=sorted(df_filtravel['Centro'].unique()), key="filt_centro")
                with col_f3:
                    estados = st.multiselect("Estado", options=sorted(df_filtravel['Status'].unique()), key="filt_status")
                with col_f4:
                    busca_desc = st.text_input("🔍 Buscar na Descrição", placeholder="Palavra-chave", key="filt_desc")
                
                # Aplicar filtros
                df_filtrado = df_filtravel.copy()
                if acoes:
                    df_filtrado = df_filtrado[df_filtrado['Ação'].isin(acoes)]
                if centros:
                    df_filtrado = df_filtrado[df_filtrado['Centro'].isin(centros)]
                if estados:
                    df_filtrado = df_filtrado[df_filtrado['Status'].isin(estados)]
                if busca_desc:
                    df_filtrado = df_filtrado[df_filtrado['Descrição'].str.contains(busca_desc, case=False, na=False)]
                
                st.dataframe(df_filtrado, use_container_width=True, height=400)
                
                # Mostrar contagem de registos após filtros
                st.caption(f"📌 Mostrando {len(df_filtrado)} de {len(df_filtravel)} incidentes.")
                # ---------- Expansor: Incidentes com TMRP acima da meta ----------
                with st.expander("⚠️ Incidentes resolvidos com TMRP > 48h (fora da meta)"):
                    if not df_resolvidos.empty:
                        fora_meta = df_resolvidos[df_resolvidos['TMRP_horas'] > meta_tmrp]
                        if not fora_meta.empty:
                            st.dataframe(fora_meta[['Ação', 'Centro', 'Descrição', 'Data_Abertura', 'Data_Resolução', 'TMRP_horas']],
                                         use_container_width=True)
                        else:
                            st.success("✅ Nenhum incidente resolvido ultrapassou as 48h.")
                    else:
                        st.info("Sem incidentes resolvidos para análise.")

            else:
                st.info("Nenhum incidente após aplicação dos filtros.")
        except Exception as e:
            st.error(f"Erro ao processar incidentes: {e}")
    else:
        st.info("⬆️ Carregue um ficheiro Excel com os dados de incidentes (colunas: Ação, Centro, Descrição, Status, Data_Abertura, Data_Resolução opcional) para visualizar os KPIs 6 e 7.")
    
    # ------------------------------------------------------------
    # KPI 8 – Taxa de Reclamações
    # ------------------------------------------------------------
   
    st.markdown("---")
    st.subheader("📢 Taxa de Reclamações")

    if "reclamacoes_df" not in st.session_state:
        st.session_state.reclamacoes_df = None
    if "reclamacoes_filename" not in st.session_state:
        st.session_state.reclamacoes_filename = None

    if st.session_state.reclamacoes_df is not None:
        st.success(f"📁 Ficheiro de reclamações carregado: **{st.session_state.reclamacoes_filename}**")
        col_reset1, _ = st.columns([1, 5])
        with col_reset1:
            if st.button("🔄 Trocar ficheiro de reclamações", key="reset_recl"):
                st.session_state.reclamacoes_df = None
                st.session_state.reclamacoes_filename = None
                st.rerun()
        df_recl = st.session_state.reclamacoes_df.copy()
    else:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            modo_carga_recl = st.radio("Modo:", ["Substituir", "Adicionar"], horizontal=True, key="modo_carga_recl")
        with c2:
            recl_file = st.file_uploader("Carregar ficheiro de Reclamações (Excel)", type=["xlsx", "xls"], key="reclamacoes_upload")
        with c3:
            try:
                with open("assets/reclamacoes.xlsx", "rb") as f:
                    conteudo_recl = f.read()
                st.download_button(label="📥 Exemplo Reclamações (Excel)", data=conteudo_recl,
                                file_name="reclamacoes.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True)
            except FileNotFoundError:
                st.error("⚠️ Ficheiro de exemplo não encontrado: assets/reclamacoes.xlsx")
        if recl_file is not None:
            try:
                df_recl = pd.read_excel(recl_file)
                df_recl.columns = df_recl.columns.str.strip()
                st.session_state.reclamacoes_df = df_recl.copy()
                st.session_state.reclamacoes_filename = recl_file.name
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao processar reclamações: {e}")
                df_recl = None
        else:
            df_recl = None

    if df_recl is not None and has_cursos:
        # Aplicar filtro de centro
        if hasattr(st.session_state, 'filtro_centro') and st.session_state.filtro_centro and 'Centro' in df_recl.columns:
            df_recl = df_recl[df_recl['Centro'].isin(st.session_state.filtro_centro)]

        # ---------- PRÉ-PROCESSAMENTO DOS DADOS ----------
        # 1. Limpeza da coluna 'Valor Devolvido'
        if 'Valor Devolvido' in df_recl.columns:
            df_recl['Valor Devolvido'] = (
                df_recl['Valor Devolvido']
                .astype(str)
                .str.replace('€', '', regex=False)
                .str.replace(',', '.', regex=False)
                .str.strip()
            )
            df_recl['Valor Devolvido'] = pd.to_numeric(df_recl['Valor Devolvido'], errors='coerce').fillna(0)
        else:
            df_recl['Valor Devolvido'] = 0

        # 2. Garantir coluna de identificação do curso (Ação)
        if 'Ação' not in df_recl.columns:
            if 'Curso' in df_recl.columns:
                df_recl.rename(columns={'Curso': 'Ação'}, inplace=True)
            else:
                st.error("O ficheiro de reclamações deve conter uma coluna 'Ação' (ou 'Curso') para identificar a formação.")
                df_recl = None

        if df_recl is not None:
            # ---------- CÁLCULO DAS MÉTRICAS ----------
            total_reclamacoes = len(df_recl)

            # Número de cursos realizados (com base no ficheiro de cursos)
            if 'Ação' in df_cursos.columns:
                total_cursos_realizados = df_cursos['Ação'].nunique()
            else:
                total_cursos_realizados = 0
                st.warning("O ficheiro de cursos não contém a coluna 'Ação' para contar os cursos realizados.")

            # Taxa de reclamações por curso (KPI principal)
            if total_cursos_realizados > 0:
                taxa_reclamacoes_curso = (total_reclamacoes / total_cursos_realizados) * 100
            else:
                taxa_reclamacoes_curso = 0

            # Taxa de reclamações aceites
            if 'Status' in df_recl.columns:
                aceites = (df_recl['Status'].astype(str).str.lower() == 'aceite').sum()
                taxa_aceites = (aceites / total_reclamacoes * 100) if total_reclamacoes > 0 else 0
            else:
                taxa_aceites = None

            # Total de valor devolvido
            total_devolvido = df_recl['Valor Devolvido'].sum()

            # ---------- EXIBIÇÃO DOS KPIs ----------
            col_recl1, col_recl2, col_recl3 = st.columns(3)

            with col_recl1:
                meta_reclamacao = st.session_state.obj_reclamacao_curso
                delta_recl = taxa_reclamacoes_curso - meta_reclamacao
                delta_color = "▲" if delta_recl > 0 else "▼"
                st.metric(
                    label="📊 Taxa de Reclamações por Curso",
                    value=f"{taxa_reclamacoes_curso:.1f}%",
                    delta=f"{delta_color} {abs(delta_recl):.1f}%",
                    help=f"Objetivo: ≤ {meta_reclamacao}%  |  {total_reclamacoes} reclamações em {total_cursos_realizados} cursos"
                )

            with col_recl2:
                if taxa_aceites is not None:
                    st.metric(label="✅ Reclamações Aceites", value=f"{taxa_aceites:.1f}%")
                else:
                    st.metric(label="✅ Reclamações Aceites", value="N/D")

            with col_recl3:
                st.metric(label="💰 Total Devolvido", value=f"{total_devolvido:,.2f} €".replace(',', ' '))

            # (Opcional) Tabela de apoio com contagem de reclamações por curso
            if 'Ação' in df_recl.columns:
                recl_por_curso = df_recl.groupby('Ação').size().reset_index(name='Reclamações')
                with st.expander("📋 Reclamações por Curso (detalhe)"):
                    st.dataframe(recl_por_curso, use_container_width=True)

            # ---------- LISTA COMPLETA DE RECLAMAÇÕES COM FILTROS ----------
            with st.expander("📋 Lista completa de Reclamações", expanded=False):
                # Preparar DataFrame para exibição (remover colunas técnicas se necessário)
                df_lista = df_recl.copy()
                
                # Garantir que colunas existem para filtros
                cols_disponiveis = df_lista.columns.tolist()
                
                # Criar filtros dinâmicos baseados nas colunas disponíveis
                st.markdown("**🔍 Filtrar reclamações:**")
                col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                
                # Filtro por Ação (se existir)
                if 'Ação' in cols_disponiveis:
                    with col_f1:
                        acao_filter = st.multiselect("Ação", options=sorted(df_lista['Ação'].dropna().unique()), key="recl_acao")
                else:
                    acao_filter = []
                
                # Filtro por Centro (se existir)
                if 'Centro' in cols_disponiveis:
                    with col_f2:
                        centro_filter = st.multiselect("Centro", options=sorted(df_lista['Centro'].dropna().unique()), key="recl_centro")
                else:
                    centro_filter = []
                
                # Filtro por Status (se existir)
                if 'Status' in cols_disponiveis:
                    with col_f3:
                        status_filter = st.multiselect("Status", options=sorted(df_lista['Status'].dropna().unique()), key="recl_status")
                else:
                    status_filter = []
                
                # Busca textual em todas as colunas de texto (ex: Motivo, Descrição, etc.)
                with col_f4:
                    texto_busca = st.text_input("🔍 Buscar texto", placeholder="Palavra-chave", key="recl_busca")
                
                # Aplicar filtros
                df_filtrado = df_lista.copy()
                if acao_filter:
                    df_filtrado = df_filtrado[df_filtrado['Ação'].isin(acao_filter)]
                if centro_filter:
                    df_filtrado = df_filtrado[df_filtrado['Centro'].isin(centro_filter)]
                if status_filter:
                    df_filtrado = df_filtrado[df_filtrado['Status'].isin(status_filter)]
                if texto_busca:
                    # Procurar em todas as colunas de texto (object)
                    mask = pd.Series([False] * len(df_filtrado))
                    for col in df_filtrado.select_dtypes(include=['object']).columns:
                        mask |= df_filtrado[col].astype(str).str.contains(texto_busca, case=False, na=False)
                    df_filtrado = df_filtrado[mask]
                
                # Exibir tabela com contagem
                st.dataframe(df_filtrado, use_container_width=True)
                st.caption(f"📌 Mostrando {len(df_filtrado)} de {len(df_lista)} reclamações.")

    else:
        if not has_cursos:
            st.warning("Carregue o ficheiro de Cursos (com a coluna 'Ação') para calcular a taxa de reclamações por curso.")
        else:
            st.info("⬆️ Carregue um ficheiro Excel com os dados de reclamações para visualizar os KPIs.")
    # ------------------------------------------------------------
    # KPI 9 – Ações de Melhoria Implementadas e Recorrência
    # ------------------------------------------------------------
    st.markdown("---")
    st.subheader("🔧 Ações de Melhoria e Recorrência")

    if "acoes_df" not in st.session_state:
        st.session_state.acoes_df = None
    if "acoes_filename" not in st.session_state:
        st.session_state.acoes_filename = None

    if st.session_state.acoes_df is not None:
        st.success(f"📁 Ficheiro de Ações de Melhoria carregado: **{st.session_state.acoes_filename}**")
        col_reset, _ = st.columns([1, 5])
        with col_reset:
            if st.button("🔄 Trocar ficheiro de ações", key="reset_acoes"):
                st.session_state.acoes_df = None
                st.session_state.acoes_filename = None
                st.rerun()
        df_acoes = st.session_state.acoes_df.copy()
    else:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            modo_carga_acoes = st.radio("Modo:", ["Substituir", "Adicionar"], horizontal=True, key="modo_carga_acoes")
        with c2:
            acoes_file = st.file_uploader("Carregar ficheiro de Ações de Melhoria (Excel)", type=["xlsx", "xls"], key="acoes_upload")
        with c3:
            try:
                with open("assets/acoes_melhoria.xlsx", "rb") as f:
                    conteudo_acoes = f.read()
                st.download_button(label="📥 Exemplo Ações de Melhoria (Excel)", data=conteudo_acoes,
                                   file_name="acoes_melhoria.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)
            except FileNotFoundError:
                st.error("⚠️ Ficheiro de exemplo não encontrado: assets/acoes_melhoria.xlsx")
        if acoes_file is not None:
            try:
                df_acoes = pd.read_excel(acoes_file)
                df_acoes.columns = df_acoes.columns.str.strip()
                st.session_state.acoes_df = df_acoes.copy()
                st.session_state.acoes_filename = acoes_file.name
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao processar ficheiro de ações: {e}")
                df_acoes = None
        else:
            df_acoes = None

    if df_acoes is not None:
        if hasattr(st.session_state, 'filtro_centro') and st.session_state.filtro_centro and 'Centro' in df_acoes.columns:
            df_acoes = df_acoes[df_acoes['Centro'].isin(st.session_state.filtro_centro)]

        if not df_acoes.empty:
            total_acoes_melhoria = len(df_acoes)
            # Verificar implementação
            if 'Implementada' in df_acoes.columns:
                if df_acoes['Implementada'].dtype == 'object':
                    implementadas = (df_acoes['Implementada'].str.lower() == 'sim').sum()
                else:
                    implementadas = (df_acoes['Implementada'] == 1).sum()
            else:
                implementadas = 0

            if 'Problema_Recorreu' in df_acoes.columns:
                if df_acoes['Problema_Recorreu'].dtype == 'object':
                    recorrencias = (df_acoes['Problema_Recorreu'].str.lower() == 'sim').sum()
                else:
                    recorrencias = (df_acoes['Problema_Recorreu'] == 1).sum()
            else:
                recorrencias = 0

            perc_implementadas = (implementadas / total_acoes_melhoria) * 100 if total_acoes_melhoria > 0 else 0
            perc_recorrencia = (recorrencias / total_acoes_melhoria) * 100 if total_acoes_melhoria > 0 else 0
            meta_implementadas = st.session_state.obj_acoes_implementadas
            meta_recorrencia = st.session_state.obj_recorrencia

            col_acoes1, col_acoes2 = st.columns(2)
            with col_acoes1:
                delta_imp = perc_implementadas - meta_implementadas
                delta_imp_str = f"▲ {delta_imp:.1f}%" if delta_imp >= 0 else f"▼ {abs(delta_imp):.1f}%"
                st.metric(label="✅ Ações de Melhoria Implementadas", value=f"{perc_implementadas:.1f}%",
                          delta=delta_imp_str, help=f"Objetivo: ≥ {meta_implementadas}%")
            with col_acoes2:
                delta_rec = perc_recorrencia - meta_recorrencia
                delta_rec_str = f"▲ {delta_rec:.1f}%" if delta_rec > 0 else f"▼ {abs(delta_rec):.1f}%"
                st.metric(label="⚠️ Recorrência de Problemas", value=f"{perc_recorrencia:.1f}%",
                          delta=delta_rec_str, help=f"Objetivo: ≤ {meta_recorrencia}%")

            if 'Data_Implementacao' in df_acoes.columns:
                df_acoes['Data_Implementacao'] = pd.to_datetime(df_acoes['Data_Implementacao'], errors='coerce')
                df_acoes['Mes'] = df_acoes['Data_Implementacao'].dt.to_period('M').astype(str)
                acoes_por_mes = df_acoes.groupby('Mes').size().reset_index(name='Quantidade')
                if not acoes_por_mes.empty:
                    fig_acoes = px.bar(acoes_por_mes, x='Mes', y='Quantidade', title="Ações de Melhoria por Mês")
                    st.plotly_chart(fig_acoes, use_container_width=True)

            with st.expander("📋 Lista de Ações de Melhoria"):
                st.dataframe(df_acoes, use_container_width=True)
        else:
            st.info("Nenhuma ação de melhoria após aplicação dos filtros.")
    else:
        st.info("⬆️ Carregue um ficheiro Excel com as Ações de Melhoria para visualizar o KPI 9.")

    # ------------------------------------------------------------
    # KPI 10 – Conformidade Documental (DGERT/PSP)
    # ------------------------------------------------------------
    st.markdown("---")
    st.subheader("📄 Conformidade Documental (DGERT/PSP)")

    if "conformidade_df" not in st.session_state:
        st.session_state.conformidade_df = None
    if "conformidade_filename" not in st.session_state:
        st.session_state.conformidade_filename = None

    def is_conforme(valor):
        if pd.isna(valor):
            return False
        valor_str = str(valor).lower()
        valor_str = unicodedata.normalize('NFKD', valor_str).encode('ASCII', 'ignore').decode('ASCII')
        return valor_str in ['sim', 's', '1', 'true']

    if st.session_state.conformidade_df is not None:
        st.success(f"📁 Ficheiro de Conformidade Documental carregado: **{st.session_state.conformidade_filename}**")
        col_reset, _ = st.columns([1, 5])
        with col_reset:
            if st.button("🔄 Trocar ficheiro de conformidade", key="reset_conf"):
                st.session_state.conformidade_df = None
                st.session_state.conformidade_filename = None
                st.rerun()
        df_conf = st.session_state.conformidade_df.copy()
    else:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            modo_carga_conf = st.radio("Modo:", ["Substituir", "Adicionar"], horizontal=True, key="modo_carga_conf")
        with c2:
            conf_file = st.file_uploader("Carregar ficheiro de Conformidade Documental (Excel)", type=["xlsx", "xls"], key="conformidade_upload")
        with c3:
            try:
                with open("assets/conformidade_documental.xlsx", "rb") as f:
                    conteudo_conf = f.read()
                st.download_button(label="📥 Exemplo Conformidade (Excel)", data=conteudo_conf,
                                   file_name="conformidade_documental.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)
            except FileNotFoundError:
                st.error("⚠️ Ficheiro de exemplo não encontrado: assets/conformidade_documental.xlsx")
        if conf_file is not None:
            try:
                df_conf = pd.read_excel(conf_file)
                df_conf.columns = df_conf.columns.str.strip()
                st.session_state.conformidade_df = df_conf.copy()
                st.session_state.conformidade_filename = conf_file.name
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao processar ficheiro de conformidade: {e}")
                df_conf = None
        else:
            df_conf = None

    if df_conf is not None:
        if hasattr(st.session_state, 'filtro_centro') and st.session_state.filtro_centro and 'Centro' in df_conf.columns:
            df_conf = df_conf[df_conf['Centro'].isin(st.session_state.filtro_centro)]

        if not df_conf.empty:
            total_docs = len(df_conf)
            conformes = df_conf['Conforme'].apply(is_conforme).sum()
            taxa_conformidade = (conformes / total_docs) * 100 if total_docs > 0 else 0
            meta_conformidade = st.session_state.obj_conformidade
            delta_conf = taxa_conformidade - meta_conformidade
            delta_conf_str = f"▲ {delta_conf:.1f}%" if delta_conf >= 0 else f"▼ {abs(delta_conf):.1f}%"

            st.metric(label="📑 Taxa de Conformidade Documental", value=f"{taxa_conformidade:.1f}%",
                      delta=delta_conf_str, help="Objetivo: 100% (crítico para DGERT/PSP)")

            if taxa_conformidade < 100:
                nao_conformes = df_conf[~df_conf['Conforme'].apply(is_conforme)]
                st.warning(f"⚠️ Atenção: {len(nao_conformes)} documento(s) não conforme(s). Ação corretiva necessária.")
                with st.expander("📋 Documentos não conformes"):
                    st.dataframe(nao_conformes, use_container_width=True)
            else:
                st.success("✅ Todos os documentos estão em conformidade. Parabéns!")

            if 'Curso' in df_conf.columns:
                conf_por_curso = df_conf.groupby('Curso').apply(
                    lambda g: (g['Conforme'].apply(is_conforme).sum() / len(g)) * 100
                ).reset_index(name='Taxa_Conformidade_%')
                fig_conf = px.bar(conf_por_curso, x='Curso', y='Taxa_Conformidade_%',
                                  title="Conformidade Documental por Curso", range_y=[0, 100])
                fig_conf.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="Meta 100%")
                st.plotly_chart(fig_conf, use_container_width=True)

            with st.expander("📋 Lista completa de documentos"):
                st.dataframe(df_conf, use_container_width=True)
        else:
            st.info("Nenhum dado de conformidade após aplicação dos filtros.")
    else:
        st.info("⬆️ Carregue um ficheiro Excel com os dados de Conformidade Documental para visualizar o KPI 10.")

    # ------------------------------------------------------------
    # Visualizações adicionais (se existirem questionários)
    # ------------------------------------------------------------
    if has_quest:
        st.markdown("---")
        col_rad, col_bar = st.columns(2)

        with col_rad:
            st.subheader("Equilíbrio de Qualidade (Radar)")
            if "Categoria" in df_quest.columns and "Média" in df_quest.columns:
                cat_stats = df_quest.groupby("Categoria")["Média"].mean().reset_index()
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(r=cat_stats["Média"], theta=cat_stats["Categoria"],
                                                    fill='toself', name='Média'))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False)
                st.plotly_chart(fig_radar, use_container_width=True)
            else:
                st.info("Colunas 'Categoria' e/ou 'Média' não encontradas nos questionários.")

        with col_bar:
            st.subheader("Presencial vs. À Distância")
            if "Categoria" in df_quest.columns and "Modalidade" in df_quest.columns and "Média" in df_quest.columns:
                mod_comp = df_quest.groupby(["Categoria", "Modalidade"])["Média"].mean().reset_index()
                fig_mod = px.bar(mod_comp, x="Categoria", y="Média", color="Modalidade", barmode="group", range_y=[0, 5])
                st.plotly_chart(fig_mod, use_container_width=True)
            else:
                st.info("Colunas necessárias (Categoria, Modalidade, Média) não encontradas.")

    else:
        if not has_cursos:
            st.warning("⚠️ Carregue ficheiros de Cursos e/ou Questionários na barra lateral para visualizar os KPIs.")

if __name__ == "__main__":
    mostrar_qualidade()