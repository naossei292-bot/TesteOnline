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
        st.session_state.obj_conclusao = 85.0      # % (Aptos+Inaptos)/Inscritos
    if 'obj_plano' not in st.session_state:
        st.session_state.obj_plano = 95.0          # % cumprimento do plano (Finalizados/Previstas)
    if 'obj_formador' not in st.session_state:
        st.session_state.obj_formador = 4.3
    if 'obj_substituicao' not in st.session_state:
        st.session_state.obj_substituicao = 10.0   # % máxima de substituição

    # ------------------------------------------------------------
    # Cálculo dos KPIs principais (com as novas fórmulas)
    # ------------------------------------------------------------
    if has_cursos:
        total_inscritos = df_cursos["Inscritos"].sum() if "Inscritos" in df_cursos.columns else 0
        total_aptos = df_cursos["Aptos"].sum() if "Aptos" in df_cursos.columns else 0
        total_inaptos = df_cursos["Inaptos"].sum() if "Inaptos" in df_cursos.columns else 0
        
        # NOVA FÓRMULA: Taxa de Conclusão = ((Aptos + Inaptos) / Inscritos) * 100
        total_aptos_inaptos = total_aptos + total_inaptos
        taxa_conclusao = (total_aptos_inaptos / total_inscritos * 100) if total_inscritos > 0 else 0

        # Cumprimento do Plano = (Finalizados / Previstas) * 100
        if "Status" in df_cursos.columns:
            # Normalizar status (case-insensitive, sem espaços)
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
        total_inscritos = total_aptos = total_inaptos = taxa_conclusao = 0
        cumprimento_plano = None
        media_satisfacao_cursos = None
        media_avaliacao_formador = None

    # Se existirem questionários, usar a média da coluna "Média" (prioridade)
    if has_quest and "Média" in df_quest.columns:
        media_satisfacao = df_quest["Média"].mean()
        # Avaliação específica para formadores (se houver categoria)
        if "Respondente" in df_quest.columns:
            df_formador_quest = df_quest[df_quest["Respondente"].str.contains("Formador", na=False)]
            media_formador_quest = df_formador_quest["Média"].mean() if not df_formador_quest.empty else None
        else:
            media_formador_quest = None
    else:
        media_satisfacao = media_satisfacao_cursos  # fallback para dados dos cursos
        media_formador_quest = media_avaliacao_formador

    # Definir valores finais a exibir
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
    </style>
    """, unsafe_allow_html=True)

    st.subheader("📊 KPIs Essenciais")

    # Exibição em 4 colunas (Satisfação, Taxa Conclusão, Cumprimento Plano, Avaliação Formadores)
    col1, col2, col3, col4 = st.columns(4)

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

    with col2:
        delta_conc = taxa_conclusao - st.session_state.obj_conclusao
        delta_color = "▲" if delta_conc >= 0 else "▼"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">✅ Taxa de Conclusão (Aptos+Inaptos)/Inscritos</div>
            <div class="kpi-value">{taxa_conclusao:.1f}%</div>
            <div class="kpi-meta">Objetivo: ≥ {st.session_state.obj_conclusao}% | {delta_color} {abs(delta_conc):.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        if cumprimento_plano is not None:
            delta_plano = cumprimento_plano - st.session_state.obj_plano
            delta_color = "▲" if delta_plano >= 0 else "▼"
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">📅 Cumprimento do Plano (Finalizados/Previstas)</div>
                <div class="kpi-value">{cumprimento_plano:.1f}%</div>
                <div class="kpi-meta">Objetivo: ≥ {st.session_state.obj_plano}% | {delta_color} {abs(delta_plano):.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">📅 Cumprimento do Plano</div>
                <div class="kpi-value">N/D</div>
                <div class="kpi-meta">⚠️ Coluna "Status" sem valores 'Prevista'/'Finalizado'</div>
            </div>
            """, unsafe_allow_html=True)

    with col4:
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
                <div class="kpi-meta">⚠️ Sem dados (coluna 'Avaliação formador')</div>
            </div>
            """, unsafe_allow_html=True)

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
        meta_multiformador = 20.0
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
            if 'Data' in df_inc.columns:
                df_inc['Data'] = pd.to_datetime(df_inc['Data'], errors='coerce')
            if 'Data_Abertura' in df_inc.columns:
                df_inc['Data_Abertura'] = pd.to_datetime(df_inc['Data_Abertura'], errors='coerce')
            if 'Data_Resolução' in df_inc.columns:
                df_inc['Data_Resolução'] = pd.to_datetime(df_inc['Data_Resolução'], errors='coerce')

            # Calcular TMRP em horas
            if 'TMRP' in df_inc.columns:
                df_inc['TMRP_horas'] = df_inc['TMRP'].astype(str).str.extract(r'(\d+(?:\.\d+)?)')[0]
                df_inc['TMRP_horas'] = pd.to_numeric(df_inc['TMRP_horas'], errors='coerce')
            else:
                if 'Data_Abertura' in df_inc and 'Data_Resolução' in df_inc:
                    df_inc['TMRP_horas'] = (df_inc['Data_Resolução'] - df_inc['Data_Abertura']).dt.total_seconds() / 3600
                else:
                    df_inc['TMRP_horas'] = None

            # Aplicar filtro de centro
            if hasattr(st.session_state, 'filtro_centro') and st.session_state.filtro_centro and 'Centro' in df_inc.columns:
                df_inc = df_inc[df_inc['Centro'].isin(st.session_state.filtro_centro)]

            if not df_inc.empty:
                total_incidentes = len(df_inc)
                tmrp_medio = df_inc['TMRP_horas'].mean() if df_inc['TMRP_horas'].notna().any() else None
                meta_tmrp = 48

                col_inc1, col_inc2 = st.columns(2)
                with col_inc1:
                    st.metric(label="📌 Nº Total de Incidentes Operacionais", value=f"{total_incidentes}")
                with col_inc2:
                    if tmrp_medio is not None:
                        delta_tmrp = tmrp_medio - meta_tmrp
                        delta_str = f"▲ {delta_tmrp:.0f}h" if delta_tmrp > 0 else f"▼ {abs(delta_tmrp):.0f}h"
                        st.metric(label="⏱️ Tempo Médio de Resolução (TMRP)", value=f"{tmrp_medio:.1f} h", delta=delta_str)
                    else:
                        st.metric(label="⏱️ Tempo Médio de Resolução (TMRP)", value="Dados insuficientes")

                # Evolução mensal
                if 'Data' in df_inc.columns:
                    df_inc['AnoMes'] = df_inc['Data'].dt.to_period('M')
                    incidentes_mensal = df_inc.groupby('AnoMes').size().reset_index(name='Quantidade')
                    incidentes_mensal['AnoMes'] = incidentes_mensal['AnoMes'].astype(str)
                    if not incidentes_mensal.empty:
                        fig_inc = px.line(incidentes_mensal, x='AnoMes', y='Quantidade', markers=True,
                                          title="Evolução Mensal do Número de Incidentes")
                        st.plotly_chart(fig_inc, use_container_width=True)

                with st.expander("📋 Detalhe dos Incidentes"):
                    st.dataframe(df_inc, use_container_width=True)
            else:
                st.info("Nenhum incidente após aplicação dos filtros.")
        except Exception as e:
            st.error(f"Erro ao processar incidentes: {e}")
    else:
        st.info("⬆️ Carregue um ficheiro Excel com os dados de incidentes para visualizar os KPIs 6 e 7.")

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

        total_reclamacoes = len(df_recl)
        total_formandos = total_inscritos  # já calculado anteriormente
        taxa_reclamacoes = (total_reclamacoes / total_formandos * 100) if total_formandos > 0 else 0
        meta_reclamacao = 5.0
        delta_recl = taxa_reclamacoes - meta_reclamacao
        delta_color = "▲" if delta_recl > 0 else "▼"

        col_recl1, col_recl2 = st.columns(2)
        with col_recl1:
            st.metric(label="📋 Nº Total de Reclamações", value=f"{total_reclamacoes}")
        with col_recl2:
            st.metric(label="📊 Taxa de Reclamações por Formando", value=f"{taxa_reclamacoes:.2f}%",
                      delta=f"{delta_color} {abs(delta_recl):.2f}%", help="Objetivo: ≤ 5%")

        if 'Curso' in df_recl.columns:
            recl_por_curso = df_recl.groupby('Curso').size().reset_index(name='Reclamações')
            fig_recl = px.bar(recl_por_curso, x='Curso', y='Reclamações', title="Reclamações por Curso")
            st.plotly_chart(fig_recl, use_container_width=True)

        with st.expander("📋 Lista de Reclamações"):
            st.dataframe(df_recl, use_container_width=True)
    else:
        if not has_cursos:
            st.warning("Carregue o ficheiro de Cursos para calcular a taxa de reclamações.")
        else:
            st.info("⬆️ Carregue um ficheiro Excel com os dados de reclamações para visualizar o KPI 8.")

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
            meta_implementadas = 80.0
            meta_recorrencia = 10.0

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
            meta_conformidade = 100.0
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