import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.data_utils import get_col, aplicar_filtros

st.set_page_config(page_title="Gestão de Qualidade", layout="wide")

def mostrar_qualidade():
    """Função principal da página de qualidade"""
    st.header("🎯 Scorecard de Qualidade Pedagógica")

    df_c_filt = aplicar_filtros(st.session_state.cursos_df)
    df_q_filt = aplicar_filtros(st.session_state.quest_df)

    # Inicializar objetivos
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

    has_cursos = df_c_filt is not None and not df_c_filt.empty
    has_quest = df_q_filt is not None and not df_q_filt.empty

    if has_cursos or has_quest:
        
        # Cálculo dos KPIs
        if has_quest:
            media_sat = df_q_filt["Media"].mean()
            META_SAT = st.session_state.obj_satisfacao
        else:
            media_sat = 0
            META_SAT = st.session_state.obj_satisfacao
        
        if has_cursos:
            c_insc = get_col(df_c_filt, "inscritos")
            c_conc = get_col(df_c_filt, "concluidos")
            t_conc = (df_c_filt[c_conc].sum() / df_c_filt[c_insc].sum() * 100) if c_insc and c_conc else 0
            META_CONC = st.session_state.obj_conclusao
            
            c_aval = get_col(df_c_filt, "avaliados")
            c_aprov = get_col(df_c_filt, "aprovados")
            t_aprov = (df_c_filt[c_aprov].sum() / df_c_filt[c_aval].sum() * 100) if c_aval and c_aprov else 0
            META_APROV = st.session_state.obj_aprovacao
            
            c_planeado = get_col(df_c_filt, "planeado")
            if c_planeado and c_conc:
                t_plano = (df_c_filt[c_conc].sum() / df_c_filt[c_planeado].sum() * 100)
            else:
                t_plano = None
            META_PLANO = st.session_state.obj_plano
        else:
            t_conc = t_aprov = 0
            t_plano = None
            META_CONC = META_APROV = META_PLANO = 0
        
        if has_quest:
            df_formador = df_q_filt[df_q_filt["Respondente"].str.contains("Formador", na=False)]
            media_formador = df_formador["Media"].mean() if not df_formador.empty else None
            META_FORMADOR = st.session_state.obj_formador
        else:
            media_formador = None
            META_FORMADOR = st.session_state.obj_formador
        
        # CSS
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
        
        # ============================================
        # KPI 6 e 7 – Incidentes Operacionais e TMRP (COM PERSISTÊNCIA)
        # ============================================
        st.markdown("---")
        st.subheader("⚠️ Incidentes Operacionais e Resolução")

        # Inicializar estado para os dados de incidentes, se não existir
        if "incidentes_df" not in st.session_state:
            st.session_state.incidentes_df = None
        if "incidentes_filename" not in st.session_state:
            st.session_state.incidentes_filename = None

        # Se já existirem dados carregados, mostrar um resumo e opção para trocar
        if st.session_state.incidentes_df is not None:
            st.success(f"📁 Ficheiro carregado: **{st.session_state.incidentes_filename}**")
            col1, col2 = st.columns([1, 5])
            with col1:
                if st.button("🔄 Carregar novo ficheiro"):
                    st.session_state.incidentes_df = None
                    st.session_state.incidentes_filename = None
                    st.rerun()  # Recarrega a página para mostrar o uploader novamente
            # Usar os dados já armazenados
            df_inc = st.session_state.incidentes_df.copy()
        else:
            # Mostrar uploader apenas quando não há dados em memória
            incidente_file = st.file_uploader(
                "Carregar ficheiro de Incidentes (Excel)",
                type=["xlsx", "xls"],
                key="incidentes_upload"
            )
            if incidente_file is not None:
                try:
                    df_inc = pd.read_excel(incidente_file)
                    df_inc.columns = df_inc.columns.str.strip()
                    # Guardar no session_state
                    st.session_state.incidentes_df = df_inc.copy()
                    st.session_state.incidentes_filename = incidente_file.name
                    st.rerun()  # Recarrega a página para mostrar o estado persistido
                except Exception as e:
                    st.error(f"Erro ao processar ficheiro: {e}")
                    df_inc = None
            else:
                df_inc = None

        # Se não houver dados (nem novo nem persistido), mostrar info e sair
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

        # Persistência: mostrar dados já carregados ou uploader
        if st.session_state.reclamacoes_df is not None:
            st.success(f"📁 Ficheiro de reclamações carregado: **{st.session_state.reclamacoes_filename}**")
            col_reset1, _ = st.columns([1, 5])
            with col_reset1:
                if st.button("🔄 Trocar ficheiro de reclamações"):
                    st.session_state.reclamacoes_df = None
                    st.session_state.reclamacoes_filename = None
                    st.rerun()
            df_recl = st.session_state.reclamacoes_df.copy()
        else:
            recl_file = st.file_uploader(
                "Carregar ficheiro de Reclamações (Excel)",
                type=["xlsx", "xls"],
                key="reclamacoes_upload"
            )
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

        # Calcular e exibir o KPI 8
        if df_recl is not None and has_cursos:
            # Aplicar filtro de centro se existir coluna 'Centro'
            if st.session_state.filtro_centro and 'Centro' in df_recl.columns:
                df_recl = df_recl[df_recl['Centro'].isin(st.session_state.filtro_centro)]
            
            total_reclamacoes = len(df_recl)
            
            # Total de formandos (inscritos) a partir dos cursos filtrados
            c_insc = get_col(df_c_filt, "inscritos")
            if c_insc:
                total_formandos = df_c_filt[c_insc].sum()
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

        # Persistência: mostrar dados já carregados ou uploader
        if st.session_state.acoes_df is not None:
            st.success(f"📁 Ficheiro de Ações de Melhoria carregado: **{st.session_state.acoes_filename}**")
            col_reset, _ = st.columns([1, 5])
            with col_reset:
                if st.button("🔄 Trocar ficheiro de ações"):
                    st.session_state.acoes_df = None
                    st.session_state.acoes_filename = None
                    st.rerun()
            df_acoes = st.session_state.acoes_df.copy()
        else:
            acoes_file = st.file_uploader(
                "Carregar ficheiro de Ações de Melhoria (Excel)",
                type=["xlsx", "xls"],
                key="acoes_upload"
            )
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

        # Inicializar estado para conformidade

        # Persistência
        if st.session_state.conformidade_df is not None:
            st.success(f"📁 Ficheiro de Conformidade Documental carregado: **{st.session_state.conformidade_filename}**")
            col_reset, _ = st.columns([1, 5])
            with col_reset:
                if st.button("🔄 Trocar ficheiro de conformidade"):
                    st.session_state.conformidade_df = None
                    st.session_state.conformidade_filename = None
                    st.rerun()
            df_conf = st.session_state.conformidade_df.copy()
        else:
            conf_file = st.file_uploader(
                "Carregar ficheiro de Conformidade Documental (Excel)",
                type=["xlsx", "xls"],
                key="conformidade_upload"
            )
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
                # Contar conformes
                if 'Conforme' in df_conf.columns:
                    if df_conf['Conforme'].dtype == 'object':
                        conformes = (df_conf['Conforme'].str.lower() == 'sim').sum()
                    else:
                        conformes = (df_conf['Conforme'] == 1).sum()
                else:
                    conformes = 0
                
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
                    st.warning(f"⚠️ Atenção: {total_docs - conformes} documento(s) não conforme(s). Ação corretiva necessária.")
                    nao_conformes = df_conf[df_conf['Conforme'].astype(str).str.lower() != 'sim']
                    with st.expander("📋 Documentos não conformes"):
                        st.dataframe(nao_conformes, use_container_width=True)
                else:
                    st.success("✅ Todos os documentos estão em conformidade. Parabéns!")
                
                # Gráfico de conformidade por curso (opcional)
                if 'Curso' in df_conf.columns:
                    conf_por_curso = df_conf.groupby('Curso')['Conforme'].apply(
                        lambda x: (x.astype(str).str.lower() == 'sim').sum() / len(x) * 100
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
                cat_stats = df_q_filt.groupby("Categoria")["Media"].mean().reset_index()
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=cat_stats["Media"], 
                    theta=cat_stats["Categoria"], 
                    fill='toself', 
                    name='Média'
                ))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False)
                st.plotly_chart(fig_radar, use_container_width=True)

            with col_bar:
                st.subheader("Presencial vs. À Distância")
                mod_comp = df_q_filt.groupby(["Categoria", "Modalidade"])["Media"].mean().reset_index()
                fig_mod = px.bar(
                    mod_comp, 
                    x="Categoria", 
                    y="Media", 
                    color="Modalidade", 
                    barmode="group", 
                    range_y=[0,5]
                )
                st.plotly_chart(fig_mod, use_container_width=True)

    else:
        st.warning("⚠️ Carregue ficheiros de Cursos e/ou Questionários na barra lateral para visualizar os KPIs.")

if __name__ == "__main__":
    mostrar_qualidade()