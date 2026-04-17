import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.data_utils import get_col, aplicar_filtros

st.set_page_config(page_title="Gestão de Qualidade", layout="wide")

def mostrar_qualidade():
    st.header("🎯 Scorecard de Qualidade Pedagógica")

    # ----- Dados dos Cursos (da página "Análise de Formações") -----
    df_cursos_raw = st.session_state.get("acoes_editaveis", None)
    if df_cursos_raw is not None and not df_cursos_raw.empty:
        if "Apagar" in df_cursos_raw.columns:
            df_cursos_raw = df_cursos_raw.drop(columns=["Apagar"])
        # Conversões de tipo
        for col in ["Inscritos", "Concluídos", "Avaliados", "Aprovados", "Planeado", "Valor da Ação", "Valor Total"]:
            if col in df_cursos_raw.columns:
                df_cursos_raw[col] = pd.to_numeric(df_cursos_raw[col], errors="coerce")
        for col in ["Data Inicial", "Data Final"]:
            if col in df_cursos_raw.columns:
                df_cursos_raw[col] = pd.to_datetime(df_cursos_raw[col], errors="coerce", dayfirst=True)
    else:
        df_cursos_raw = None

    # ----- Dados dos Questionários (se existirem) -----
    df_quest_raw = st.session_state.get("quest_editaveis", None)

    # Deve ser:
    df_c_filt = aplicar_filtros(df_cursos_raw) if df_cursos_raw is not None else None
    df_q_filt = aplicar_filtros(df_quest_raw) if df_quest_raw is not None else None

    has_cursos = df_c_filt is not None and not df_c_filt.empty   # booleano
    has_quest = df_q_filt is not None and not df_q_filt.empty

    df_cursos = df_c_filt   # <--- NOVA variável para o DataFrame

    # Inicializar objetivos (mantém o que já tinhas)
    if 'obj_satisfacao' not in st.session_state:
        st.session_state.obj_satisfacao = 4.2
    # ... resto das inicializações
    if 'obj_conclusao' not in st.session_state:
        st.session_state.obj_conclusao = 85.0
    if 'obj_aprovacao' not in st.session_state:
        st.session_state.obj_aprovacao = 80.0
    if 'obj_plano' not in st.session_state:
        st.session_state.obj_plano = 95.0
    if 'obj_formador' not in st.session_state:
        st.session_state.obj_formador = 4.3
    if 'acoes_df' not in st.session_state:
        st.session_state.acoes_df = None
    if 'acoes_filename' not in st.session_state:
        st.session_state.acoes_filename = None
    if "reclamacoes_df" not in st.session_state:
            st.session_state.reclamacoes_df = None
    if "reclamacoes_filename" not in st.session_state:
            st.session_state.reclamacoes_filename = None
    if "conformidade_df" not in st.session_state:
        st.session_state.conformidade_df = None
    if "conformidade_filename" not in st.session_state:
        st.session_state.conformidade_filename = None


    if has_cursos or has_quest:
        
        # Cálculo dos KPIs
        if has_quest:
            media_sat = df_q_filt["Média"].mean()
            META_SAT = st.session_state.obj_satisfacao
        else:
            media_sat = 0
            META_SAT = st.session_state.obj_satisfacao
        
        if has_cursos:
            if "Inscritos" in df_cursos.columns and "Concluídos" in df_cursos.columns:
                total_insc = df_cursos["Inscritos"].sum()
                total_conc = df_cursos["Concluídos"].sum()
                t_conc = (total_conc / total_insc * 100) if total_insc > 0 else 0
            else:
                t_conc = 0
            META_CONC = st.session_state.obj_conclusao
            
            c_aval = get_col(df_cursos, "avaliados")
            c_aprov = get_col(df_cursos, "aprovados")
            t_aprov = (df_cursos[c_aprov].sum() / df_cursos[c_aval].sum() * 100) if c_aval and c_aprov else 0
            META_APROV = st.session_state.obj_aprovacao
            META_PLANO = st.session_state.obj_plano
            if "Concluídos" in df_cursos.columns and "Planeado" in df_cursos.columns:
                total_conc = df_cursos["Concluídos"].sum()
                total_plan = df_cursos["Planeado"].sum()
                if total_plan > 0:
                    t_plano = (total_conc / total_plan) * 100
                else:
                    t_plano = None
            else:
                t_plano = None
        else:
            t_conc = t_aprov = 0
            t_plano = None
            META_CONC = META_APROV = META_PLANO = 0
        
        if has_quest:
            df_formador = df_q_filt[df_q_filt["Respondente"].str.contains("Formador", na=False)]
            media_formador = df_formador["Média"].mean() if not df_formador.empty else None
            META_FORMADOR = st.session_state.obj_formador
        else:
            media_formador = None
            META_FORMADOR = st.session_state.obj_formador
        
        # CSS
# CSS adaptado para modo claro/escuro
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
        
        # Exibição dos KPIs
        col1, col2, col3 = st.columns(3)
        
        with col1:
            delta_sat = media_sat - META_SAT
            delta_color = "▲" if delta_sat >= 0 else "▼"
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">🎓 Satisfação dos Formandos</div>
                <div class="kpi-value">{media_sat:.2f} / 5</div>
                <div class="kpi-meta">Objetivo: ≥ {META_SAT} | {delta_color} {abs(delta_sat):.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            delta_conc = t_conc - META_CONC
            delta_color = "▲" if delta_conc >= 0 else "▼"
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">✅ Taxa de Conclusão</div>
                <div class="kpi-value">{t_conc:.1f}%</div>
                <div class="kpi-meta">Objetivo: ≥ {META_CONC}% | {delta_color} {abs(delta_conc):.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            delta_aprov = t_aprov - META_APROV
            delta_color = "▲" if delta_aprov >= 0 else "▼"
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">📝 Taxa de Aprovação</div>
                <div class="kpi-value">{t_aprov:.1f}%</div>
                <div class="kpi-meta">Objetivo: ≥ {META_APROV}% | {delta_color} {abs(delta_aprov):.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
        
        col4, col5, col6 = st.columns(3)
        
        with col4:
            if t_plano is not None:
                delta_plano = t_plano - META_PLANO
                delta_color = "▲" if delta_plano >= 0 else "▼"
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-title">📅 Cumprimento do Plano</div>
                    <div class="kpi-value">{t_plano:.1f}%</div>
                    <div class="kpi-meta">Objetivo: ≥ {META_PLANO}% | {delta_color} {abs(delta_plano):.1f}%</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-title">📅 Cumprimento do Plano</div>
                    <div class="kpi-value">N/D</div>
                    <div class="kpi-meta">⚠️ Adicione coluna "Planeado"</div>
                </div>
                """, unsafe_allow_html=True)

            # 👇 NOVO BOTÃO E TABELA EDITÁVEL
            with st.expander("✏️ Editar formações realizadas / planeadas"):
                if df_cursos is not None and not df_cursos.empty:
                    # Verificar se as colunas necessárias existem
                    col_id = get_col(df_cursos, "Ação")  # ou "Ação"
                    col_conc = get_col(df_cursos, "Concluídos")
                    col_plan = get_col(df_cursos, "Planeado")

                    if col_id and col_conc and col_plan:
                        # Criar um DataFrame apenas com as colunas de interesse
                        df_edit = df_cursos[[col_id, col_conc, col_plan]].copy()
                        df_edit.columns = ["ID Ação", "Formações Realizadas", "Formações Planeadas"]
                        
                        # Garantir que os valores são numéricos
                        df_edit["Formações Realizadas"] = pd.to_numeric(df_edit["Formações Realizadas"], errors="coerce").fillna(0).astype(int)
                        df_edit["Formações Planeadas"] = pd.to_numeric(df_edit["Formações Planeadas"], errors="coerce").fillna(0).astype(int)
                        
                        # Exibir tabela editável
                        edited_df = st.data_editor(
                            df_edit,
                            use_container_width=True,
                            num_rows="dynamic",  # permite adicionar/remover linhas se necessário
                            column_config={
                                "ID Ação": st.column_config.TextColumn("ID Ação", required=True),
                                "Formações Realizadas": st.column_config.NumberColumn("Formações Realizadas", min_value=0, step=1),
                                "Formações Planeadas": st.column_config.NumberColumn("Formações Planeadas", min_value=0, step=1),
                            },
                            key="planeamento_editor"
                        )
                        
                        # Botão para guardar alterações
                        if st.button("💾 Guardar alterações", key="save_planeamento"):
                            # Atualizar o DataFrame original (df_cursos) com os valores editados
                            for idx, row in edited_df.iterrows():
                                acao_id = row["ID Ação"]
                                novos_realizados = row["Formações Realizadas"]
                                novos_planeados = row["Formações Planeadas"]
                                
                                # Encontrar a linha correspondente no df_cursos
                                mask = df_cursos[col_id] == acao_id
                                if mask.any():
                                    df_cursos.loc[mask, col_conc] = novos_realizados
                                    df_cursos.loc[mask, col_plan] = novos_planeados
                            
                            # Atualizar o session_state para persistir as alterações
                            st.session_state.acoes_editaveis = df_cursos
                            st.success("✅ Dados atualizados! A página vai recarregar para mostrar os novos KPIs.")
                            st.rerun()
                    else:
                        st.warning("Colunas necessárias não encontradas. Verifique se existem 'Ação', 'Concluídos' e 'Planeado'.")
                else:
                    st.info("Nenhum curso carregado.")
        
        with col5:
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
                    <div class="kpi-meta">⚠️ Sem dados disponíveis</div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")  # separador opcional
        col7, col8 = st.columns(2)

        with col7:
            # KPI 5.1 - Ações com mais de um formador
            if has_cursos and "Formador" in df_cursos.columns:
                # Função para contar formadores numa célula
                def contar_formadores(valor):
                    if pd.isna(valor):
                        return 0
                    valor_str = str(valor)
                    # Separadores comuns: vírgula, ponto e vírgula, " e ", "/"
                    if ',' in valor_str or ';' in valor_str or ' e ' in valor_str or '/' in valor_str:
                        # Conta o número de nomes (simplificado)
                        # Substituir separadores por vírgula e dividir
                        for sep in [';', ' e ', '/']:
                            valor_str = valor_str.replace(sep, ',')
                        nomes = [n.strip() for n in valor_str.split(',') if n.strip()]
                        return len(nomes)
                    else:
                        return 1 if valor_str.strip() else 0
                
                df_cursos['num_formadores'] = df_cursos['Formador'].apply(contar_formadores)
                total_acoes = len(df_cursos)
                acoes_multiformador = (df_cursos['num_formadores'] > 1).sum()
                perc_multiformador = (acoes_multiformador / total_acoes * 100) if total_acoes > 0 else 0
                
                meta_multiformador = 20.0  # objetivo ajustável
                delta_multiformador = perc_multiformador - meta_multiformador
                delta_color = "▲" if delta_multiformador >= 0 else "▼"
                
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-title">👥 Ações com >1 Formador</div>
                    <div class="kpi-value">{acoes_multiformador} / {total_acoes}</div>
                    <div class="kpi-meta">{perc_multiformador:.1f}% das ações | Meta: ≥ {meta_multiformador}% | {delta_color} {abs(delta_multiformador):.1f}%</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-title">👥 Ações com >1 Formador</div>
                    <div class="kpi-value">N/D</div>
                    <div class="kpi-meta">⚠️ Coluna "Formador" não encontrada</div>
                </div>
                """, unsafe_allow_html=True)

        with col8:
            # (pode deixar vazio ou colocar outro KPI, ex: média de formadores por ação)
            if has_cursos and "Formador" in df_cursos.columns:
                media_formadores = df_cursos['num_formadores'].mean()
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-title">📊 Média de Formadores por Ação</div>
                    <div class="kpi-value">{media_formadores:.2f}</div>
                    <div class="kpi-meta">Total de ações: {total_acoes}</div>
                </div>
                """, unsafe_allow_html=True)

        # ============================================
        # KPI 5.1 – Taxa de Substituição de Formadores (CORRIGIDO)
        # ============================================
        st.markdown("---")
        st.subheader("👥 Substituição de Formadores")

        if has_cursos and "Formador" in df_cursos.columns and "Ação" in df_cursos.columns:
            # Função de normalização
            import unicodedata
            def normalizar_string(texto):
                if pd.isna(texto):
                    return ""
                texto = str(texto).strip().lower()
                texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
                return texto

            # Guardar snapshot original (apenas na primeira vez)
            if "formadores_originais" not in st.session_state:
                originais = df_cursos[["Ação", "Formador"]].copy()
                originais["Formador_Norm"] = originais["Formador"].apply(normalizar_string)
                st.session_state.formadores_originais = originais
                # Também guardar os valores originais para exibição (opcional)
                st.session_state.formadores_originais_exibicao = df_cursos[["Ação", "Formador"]].copy()

            # Preparar DataFrame para edição
            df_edit_formadores = df_cursos[["Ação", "Formador"]].copy()
            df_edit_formadores.columns = ["ID Ação", "Formador Atual"]
            # Adicionar coluna com o original (apenas para referência visual)
            original_map = st.session_state.formadores_originais_exibicao.set_index("Ação")["Formador"].to_dict()
            df_edit_formadores["Formador Original"] = df_edit_formadores["ID Ação"].map(original_map)
            df_edit_formadores = df_edit_formadores[["ID Ação", "Formador Original", "Formador Atual"]]

            st.info("✏️ Edite o campo 'Formador Atual' para simular uma substituição. O KPI será atualizado automaticamente.")

            # Data editor
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

            # Botão guardar
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
                    # Atualizar também o snapshot de exibição? Não, porque mantemos o original.
                    st.success("✅ Formadores atualizados! A página vai recarregar.")
                    st.rerun()

            # Calcular substituições usando normalização (sem precisar de guardar novamente)
            # Obter mapas normalizados
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
            meta_subst = 10.0
            delta_subst = taxa_substituicao - meta_subst
            delta_str = f"▲ {delta_subst:.1f}%" if delta_subst > 0 else f"▼ {abs(delta_subst):.1f}%"

            col_kpi1, col_kpi2 = st.columns(2)
            with col_kpi1:
                st.metric(
                    label="🔄 Taxa de Substituição de Formadores",
                    value=f"{taxa_substituicao:.1f}%",
                    delta=delta_str,
                    help="Percentagem de cursos onde o formador atual é diferente do original. Objetivo: ≤ 10%"
                )
            with col_kpi2:
                st.metric(
                    label="📊 Cursos com substituição",
                    value=f"{substituicoes} / {total}",
                    help="Número de cursos onde o formador foi trocado"
                )

            # Botão para redefinir base de comparação
            if st.button("🔄 Redefinir formadores originais (basear nos atuais)"):
                # Atualizar snapshot com os valores atuais normalizados
                novos_originais = df_cursos[["Ação", "Formador"]].copy()
                novos_originais["Formador_Norm"] = novos_originais["Formador"].apply(normalizar_string)
                st.session_state.formadores_originais = novos_originais
                st.session_state.formadores_originais_exibicao = df_cursos[["Ação", "Formador"]].copy()
                st.success("Base de comparação redefinida. A taxa de substituição voltará a 0%.")
                st.rerun()
        else:
            st.info("Carregue um ficheiro de cursos com as colunas 'Ação' e 'Formador' para calcular a taxa de substituição.")

        # ============================================
        # KPI 6 e 7 – Incidentes Operacionais e TMRP (COM PERSISTÊNCIA)
        # ============================================
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
            # Três colunas: modo de carga, upload, download
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

        if df_inc is None:

            st.info("⬆️ Carregue um ficheiro Excel com os dados de incidentes para visualizar os KPIs 6 e 7.")
        else:
            # Processamento dos dados de incidentes (conversão de datas, etc.)
            try:
                # Converter datas
                if 'Data' in df_inc.columns:
                    df_inc['Data'] = pd.to_datetime(df_inc['Data'], errors='coerce')
                if 'Data_Abertura' in df_inc.columns:
                    df_inc['Data_Abertura'] = pd.to_datetime(df_inc['Data_Abertura'], errors='coerce')
                if 'Data_Resolução' in df_inc.columns:
                    df_inc['Data_Resolução'] = pd.to_datetime(df_inc['Data_Resolução'], errors='coerce')
                
                # Extrair TMRP em horas
                if 'TMRP' in df_inc.columns:
                    df_inc['TMRP_horas'] = df_inc['TMRP'].astype(str).str.extract(r'(\d+(?:\.\d+)?)')[0]
                    df_inc['TMRP_horas'] = pd.to_numeric(df_inc['TMRP_horas'], errors='coerce')
                else:
                    if 'Data_Abertura' in df_inc and 'Data_Resolução' in df_inc:
                        df_inc['TMRP_horas'] = (df_inc['Data_Resolução'] - df_inc['Data_Abertura']).dt.total_seconds() / 3600
                    else:
                        df_inc['TMRP_horas'] = None
                
                # Aplicar filtro de centro
                if st.session_state.filtro_centro and 'Centro' in df_inc.columns:
                    df_inc = df_inc[df_inc['Centro'].isin(st.session_state.filtro_centro)]
                
                if not df_inc.empty:
                    total_incidentes = len(df_inc)
                    
                    # Evolução mensal
                    if 'Data' in df_inc.columns:
                        df_inc['AnoMes'] = df_inc['Data'].dt.to_period('M')
                        incidentes_mensal = df_inc.groupby('AnoMes').size().reset_index(name='Quantidade')
                        incidentes_mensal['AnoMes'] = incidentes_mensal['AnoMes'].astype(str)
                    else:
                        incidentes_mensal = None
                    
                    tmrp_medio = df_inc['TMRP_horas'].mean() if df_inc['TMRP_horas'].notna().any() else None
                    meta_tmrp = 48
                    
                    col_inc1, col_inc2 = st.columns(2)
                    with col_inc1:
                        st.metric(
                            label="📌 Nº Total de Incidentes Operacionais",
                            value=f"{total_incidentes}",
                            help="Número de não conformidades operacionais (falta de sala, equipamentos, erros administrativos)"
                        )
                    with col_inc2:
                        if tmrp_medio is not None:
                            delta_tmrp = tmrp_medio - meta_tmrp
                            delta_str = f"▲ {delta_tmrp:.0f}h" if delta_tmrp > 0 else f"▼ {abs(delta_tmrp):.0f}h"
                            st.metric(
                                label="⏱️ Tempo Médio de Resolução (TMRP)",
                                value=f"{tmrp_medio:.1f} h",
                                delta=delta_str,
                                help="Objetivo: ≤ 48h"
                            )
                        else:
                            st.metric(label="⏱️ Tempo Médio de Resolução (TMRP)", value="Dados insuficientes")
                    
                    if incidentes_mensal is not None and not incidentes_mensal.empty:
                        fig_inc_mensal = px.line(
                            incidentes_mensal,
                            x='AnoMes',
                            y='Quantidade',
                            markers=True,
                            title="Evolução Mensal do Número de Incidentes",
                            labels={'AnoMes': 'Mês', 'Quantidade': 'Nº de Incidentes'}
                        )
                        st.plotly_chart(fig_inc_mensal, use_container_width=True)
                    
                    with st.expander("📋 Detalhe dos Incidentes"):
                        st.dataframe(df_inc, use_container_width=True)
                else:
                    st.info("Nenhum incidente após aplicação dos filtros.")
            except Exception as e:
                st.error(f"Erro ao processar ficheiro de incidentes: {e}")
        
        # ============================================
        # KPI 8 – Taxa de Reclamações
        # ============================================
        st.markdown("---")
        st.subheader("📢 Taxa de Reclamações")

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
                recl_file = st.file_uploader(
                    "Carregar ficheiro de Reclamações (Excel)",
                    type=["xlsx", "xls"], key="reclamacoes_upload"
                )
            with c3:
                try:
                    with open("assets/reclamacoes.xlsx", "rb") as f:
                        conteudo_recl = f.read()
                    st.download_button(
                        label="📥 Exemplo Reclamações (Excel)",
                        data=conteudo_recl,
                        file_name="reclamacoes.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
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
                    st.error(f"Erro ao processar ficheiro de reclamações: {e}")
                    df_recl = None
            else:
                df_recl = None

        # Cálculo do KPI 8 (mantenha igual)
        if df_recl is not None and df_cursos is not None:
            # Aplicar filtro de centro se existir coluna 'Centro'
            if st.session_state.filtro_centro and 'Centro' in df_recl.columns:
                df_recl = df_recl[df_recl['Centro'].isin(st.session_state.filtro_centro)]
            
            total_reclamacoes = len(df_recl)
            
            # Total de formandos (inscritos) a partir dos cursos filtrados
            c_insc = get_col(df_cursos, "inscritos")
            if c_insc:
                total_formandos = df_cursos[c_insc].sum()
            else:
                total_formandos = 0
            
            if total_formandos > 0:
                taxa_reclamacoes = (total_reclamacoes / total_formandos) * 100
            else:
                taxa_reclamacoes = 0
            
            meta_reclamacao = 5.0  # 5%
            delta_recl = taxa_reclamacoes - meta_reclamacao
            delta_color = "▲" if delta_recl > 0 else "▼"
            
            col_recl1, col_recl2 = st.columns(2)
            with col_recl1:
                st.metric(
                    label="📋 Nº Total de Reclamações",
                    value=f"{total_reclamacoes}",
                    help="Quantidade de reclamações registadas"
                )
            with col_recl2:
                st.metric(
                    label="📊 Taxa de Reclamações por Formando",
                    value=f"{taxa_reclamacoes:.2f}%",
                    delta=f"{delta_color} {abs(delta_recl):.2f}%",
                    help="Objetivo: ≤ 5%"
                )
            
            # Gráfico de barras com reclamações por curso (opcional)
            if 'Curso' in df_recl.columns:
                recl_por_curso = df_recl.groupby('Curso').size().reset_index(name='Reclamações')
                fig_recl = px.bar(
                    recl_por_curso,
                    x='Curso',
                    y='Reclamações',
                    title="Reclamações por Curso",
                    labels={'Curso': 'Curso', 'Reclamações': 'Nº de Reclamações'}
                )
                st.plotly_chart(fig_recl, use_container_width=True)
            
            with st.expander("📋 Lista de Reclamações"):
                st.dataframe(df_recl, use_container_width=True)
        else:
            if not has_cursos:
                st.warning("Carregue o ficheiro de Cursos para calcular a taxa de reclamações.")
            else:
                st.info("⬆️ Carregue um ficheiro Excel com os dados de reclamações para visualizar o KPI 8.")

        # ============================================
        # KPI 9 – Ações de Melhoria Implementadas e Recorrência
        # ============================================
        st.markdown("---")
        st.subheader("🔧 Ações de Melhoria e Recorrência")

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
                acoes_file = st.file_uploader(
                    "Carregar ficheiro de Ações de Melhoria (Excel)",
                    type=["xlsx", "xls"], key="acoes_upload"
                )
            with c3:
                try:
                    with open("assets/acoes_melhoria.xlsx", "rb") as f:
                        conteudo_acoes = f.read()
                    st.download_button(
                        label="📥 Exemplo Ações de Melhoria (Excel)",
                        data=conteudo_acoes,
                        file_name="acoes_melhoria.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
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
            # Aplicar filtro de centro se existir a coluna
            if st.session_state.filtro_centro and 'Centro' in df_acoes.columns:
                df_acoes = df_acoes[df_acoes['Centro'].isin(st.session_state.filtro_centro)]
            
            if not df_acoes.empty:
                total_acoes = len(df_acoes)
                # Garantir que as colunas estão em formato adequado
                if 'Implementada' in df_acoes.columns:
                    # Converter para booleano: "Sim"/"Não" ou 1/0
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
                
                perc_implementadas = (implementadas / total_acoes) * 100 if total_acoes > 0 else 0
                perc_recorrencia = (recorrencias / total_acoes) * 100 if total_acoes > 0 else 0
                
                meta_implementadas = 80.0
                meta_recorrencia = 10.0
                
                col_acoes1, col_acoes2 = st.columns(2)
                with col_acoes1:
                    delta_imp = perc_implementadas - meta_implementadas
                    delta_imp_str = f"▲ {delta_imp:.1f}%" if delta_imp >= 0 else f"▼ {abs(delta_imp):.1f}%"
                    st.metric(
                        label="✅ Ações de Melhoria Implementadas",
                        value=f"{perc_implementadas:.1f}%",
                        delta=delta_imp_str,
                        help=f"Objetivo: ≥ {meta_implementadas}%"
                    )
                with col_acoes2:
                    delta_rec = perc_recorrencia - meta_recorrencia
                    delta_rec_str = f"▲ {delta_rec:.1f}%" if delta_rec > 0 else f"▼ {abs(delta_rec):.1f}%"
                    st.metric(
                        label="⚠️ Recorrência de Problemas",
                        value=f"{perc_recorrencia:.1f}%",
                        delta=delta_rec_str,
                        help=f"Objetivo: ≤ {meta_recorrencia}%"
                    )
                
                # Gráfico de evolução temporal (opcional)
                if 'Data_Implementacao' in df_acoes.columns:
                    df_acoes['Data_Implementacao'] = pd.to_datetime(df_acoes['Data_Implementacao'], errors='coerce')
                    df_acoes['Mes'] = df_acoes['Data_Implementacao'].dt.to_period('M').astype(str)
                    acoes_por_mes = df_acoes.groupby('Mes').size().reset_index(name='Quantidade')
                    if not acoes_por_mes.empty:
                        fig_acoes = px.bar(
                            acoes_por_mes,
                            x='Mes',
                            y='Quantidade',
                            title="Ações de Melhoria por Mês",
                            labels={'Mes': 'Mês', 'Quantidade': 'Nº de Ações'}
                        )
                        st.plotly_chart(fig_acoes, use_container_width=True)
                
                with st.expander("📋 Lista de Ações de Melhoria"):
                    st.dataframe(df_acoes, use_container_width=True)
            else:
                st.info("Nenhuma ação de melhoria após aplicação dos filtros.")
        else:
            st.info("⬆️ Carregue um ficheiro Excel com as Ações de Melhoria para visualizar o KPI 9.")




                # ============================================
        # KPI 10 – Conformidade Documental (DGERT/PSP)
        # ============================================
        st.markdown("---")
        st.subheader("📄 Conformidade Documental (DGERT/PSP)")

        if "conformidade_df" not in st.session_state:
            st.session_state.conformidade_df = None
        if "conformidade_filename" not in st.session_state:
            st.session_state.conformidade_filename = None

        def is_conforme(valor):
            if pd.isna(valor):
                return False
            # Converter para string, minúsculas e remover acentos
            import unicodedata
            valor_str = str(valor).lower()
            # Remover acentos (ex: "não" -> "nao")
            valor_str = unicodedata.normalize('NFKD', valor_str).encode('ASCII', 'ignore').decode('ASCII')
            # Verificar se é considerado conforme
            return valor_str in ['sim', 's', '1', 'true']

        # Persistência
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
            conf_file = st.file_uploader(
                "Carregar ficheiro de Conformidade Documental (Excel)",
                type=["xlsx", "xls"], key="conformidade_upload"
            )
        with c3:
            try:
                with open("assets/conformidade_documental.xlsx", "rb") as f:
                    conteudo_conf = f.read()
                st.download_button(
                    label="📥 Exemplo Conformidade (Excel)",
                    data=conteudo_conf,
                    file_name="conformidade_documental.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
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
            # Aplicar filtro de centro se existir
            if st.session_state.filtro_centro and 'Centro' in df_conf.columns:
                df_conf = df_conf[df_conf['Centro'].isin(st.session_state.filtro_centro)]
            
            if not df_conf.empty:
                total_docs = len(df_conf)
                # Contar conformes usando a função normalizada
                conformes = df_conf['Conforme'].apply(is_conforme).sum()
                
                taxa_conformidade = (conformes / total_docs) * 100 if total_docs > 0 else 0
                meta_conformidade = 100.0
                delta_conf = taxa_conformidade - meta_conformidade
                delta_conf_str = f"▲ {delta_conf:.1f}%" if delta_conf >= 0 else f"▼ {abs(delta_conf):.1f}%"
                
                st.metric(
                    label="📑 Taxa de Conformidade Documental",
                    value=f"{taxa_conformidade:.1f}%",
                    delta=delta_conf_str,
                    help="Objetivo: 100% (crítico para DGERT/PSP)"
                )
                
                # Se não for 100%, mostrar detalhes das não conformidades
                if taxa_conformidade < 100:
                    nao_conformes = df_conf[~df_conf['Conforme'].apply(is_conforme)]
                    st.warning(f"⚠️ Atenção: {len(nao_conformes)} documento(s) não conforme(s). Ação corretiva necessária.")
                    with st.expander("📋 Documentos não conformes"):
                        st.dataframe(nao_conformes, use_container_width=True)
                else:
                    st.success("✅ Todos os documentos estão em conformidade. Parabéns!")
                
                # Gráfico de conformidade por curso (opcional)
                if 'Curso' in df_conf.columns:
                    conf_por_curso = df_conf.groupby('Curso').apply(
                        lambda g: (g['Conforme'].apply(is_conforme).sum() / len(g)) * 100
                    ).reset_index(name='Taxa_Conformidade_%')
                    fig_conf = px.bar(
                        conf_por_curso,
                        x='Curso',
                        y='Taxa_Conformidade_%',
                        title="Conformidade Documental por Curso",
                        labels={'Curso': 'Curso', 'Taxa_Conformidade_%': 'Taxa de Conformidade (%)'},
                        range_y=[0, 100]
                    )
                    fig_conf.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="Meta 100%")
                    st.plotly_chart(fig_conf, use_container_width=True)
                
                with st.expander("📋 Lista completa de documentos"):
                    st.dataframe(df_conf, use_container_width=True)
            else:
                st.info("Nenhum dado de conformidade após aplicação dos filtros.")
    else:
            st.info("⬆️ Carregue um ficheiro Excel com os dados de Conformidade Documental para visualizar o KPI 10.")

        # Visualizações adicionais
    if has_quest:
            st.markdown("---")
            col_rad, col_bar = st.columns(2)

            with col_rad:
                st.subheader("Equilíbrio de Qualidade (Radar)")
                cat_stats = df_q_filt.groupby("Categoria")["Média"].mean().reset_index()
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=cat_stats["Média"], 
                    theta=cat_stats["Categoria"], 
                    fill='toself', 
                    name='Média'
                ))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False)
                st.plotly_chart(fig_radar, use_container_width=True)

            with col_bar:
                st.subheader("Presencial vs. À Distância")
                mod_comp = df_q_filt.groupby(["Categoria", "Modalidade"])["Média"].mean().reset_index()
                fig_mod = px.bar(
                    mod_comp, 
                    x="Categoria", 
                    y="Média", 
                    color="Modalidade", 
                    barmode="group", 
                    range_y=[0,5]
                )
                st.plotly_chart(fig_mod, use_container_width=True)

    else:
        st.warning("⚠️ Carregue ficheiros de Cursos e/ou Questionários na barra lateral para visualizar os KPIs.")

if __name__ == "__main__":
    mostrar_qualidade()