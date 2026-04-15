import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import hmac  # ⚠️ CRÍTICO - necessário para a autenticação funcionar

# --------------------------
# CONFIGURAÇÃO DA PÁGINA
# --------------------------
st.set_page_config(page_title="Dashboard KPI & Qualidade", layout="wide")

st.markdown("<style>[data-testid='stMetricValue'] { font-size: 25px; }</style>", unsafe_allow_html=True)

# ============================================
# 🔒 SISTEMA DE AUTENTICAÇÃO (PROTEÇÃO POR PALAVRA-PASSE)
# ============================================

def verificar_autenticacao():
    """Verifica se o utilizador está autenticado com a palavra-passe dos Secrets"""
    
    # Se já está autenticado nesta sessão, continua
    if st.session_state.get("autenticado", False):
        return True
    
    # Título da página de login
    st.title("🔒 Acesso Restrito")
    st.markdown("### Esta aplicação é privada")
    st.markdown("Introduza a palavra-passe para continuar.")
    
    # Campo para a password
    password_input = st.text_input(
        "Palavra-passe:",
        type="password",
        key="login_password"
    )
    
    # Botão para submeter
    if st.button("🔓 Entrar", use_container_width=True):
        # Busca a password correta dos Secrets
        try:
            password_correta = st.secrets["password"]
        except KeyError:
            st.error("⚠️ Erro de configuração: Password não definida nos Secrets")
            st.info("Contacte o administrador da aplicação.")
            return False
        
        # Compara as passwords de forma segura
        if hmac.compare_digest(password_input, password_correta):
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("❌ Palavra-passe incorreta!")
            return False
    
    return False

# ============================================
# VERIFICA AUTENTICAÇÃO ANTES DE MOSTRAR A APP
# ============================================

if not verificar_autenticacao():
    st.stop()

# ============================================
# SE CHEGOU AQUI, ESTÁ AUTENTICADO!
# ============================================

# Mostrar mensagem de boas-vindas e opção de logout
col_logout1, col_logout2 = st.columns([6, 1])
with col_logout2:
    if st.button("🚪 Sair", help="Terminar sessão"):
        st.session_state.clear()
        st.rerun()
# --------------------------
# INICIALIZAÇÃO DO ESTADO
# --------------------------
if 'cursos_df' not in st.session_state: st.session_state.cursos_df = None
if 'quest_df' not in st.session_state: st.session_state.quest_df = None
if 'filtro_centro' not in st.session_state: st.session_state.filtro_centro = []

# --------------------------
# FUNÇÕES DE PROCESSAMENTO
# --------------------------

def get_col(df, name):
    if df is None: return None
    for col in df.columns:
        if str(col).strip().lower() == name.lower(): return col
    return None

def aplicar_filtros(df):
    if df is None: return None
    temp_df = df.copy()
    if st.session_state.filtro_centro:
        col_c = get_col(temp_df, "Centro")
        if col_c:
            temp_df = temp_df[temp_df[col_c].isin(st.session_state.filtro_centro)]
    return temp_df

def processar_questionarios_excel(file):
    # Extração do nome do centro via nome do ficheiro (Ex: Relatório_Alverca -> Alverca)
    nome_arquivo = file.name.replace(".xlsx", "").replace(".xls", "")
    centro_extraido = nome_arquivo.split("_")[-1] if "_" in nome_arquivo else "Geral"
    
    xl = pd.ExcelFile(file)
    todos_resultados = []
    abas_alvo = ['21a', '21b', '22a', '22b', '23a', '23b', '24a', '24b']
   
    for aba in xl.sheet_names:
        if aba not in abas_alvo: continue
        df_aba = xl.parse(aba, header=None)
        curso_atual = "Não Identificado"
        modalidade = "Presencial" if 'a' in aba else "À Distância"
       
        if '21' in aba or '22' in aba: tipo_resp = "Formando"
        elif '23' in aba: tipo_resp = "Formador/Tutor"
        else: tipo_resp = "Coordenação"

        for i in range(len(df_aba)):
            linha = df_aba.iloc[i].astype(str).values
            if "Curso" in linha: curso_atual = str(df_aba.iloc[i, 1])
            if "Categorias/Subcategorias" in linha:
                j = i + 1
                while j < len(df_aba):
                    pergunta = str(df_aba.iloc[j, 0])
                    media_val = df_aba.iloc[j, 1]
                    if "Resultados por categoria" in pergunta or pd.isna(df_aba.iloc[j, 0]): break
                    try:
                        cat_letra = pergunta[0] if pergunta[0].isalpha() else "Outros"
                        val_num = float(str(media_val).replace(",", "."))
                        todos_resultados.append({
                            "Centro": centro_extraido,
                            "Curso": curso_atual, 
                            "Modalidade": modalidade, 
                            "Respondente": tipo_resp,
                            "Categoria": cat_letra, 
                            "Pergunta": pergunta, 
                            "Media": val_num
                        })
                    except: pass
                    j += 1
    return pd.DataFrame(todos_resultados)

# --------------------------
# BARRA LATERAL
# --------------------------
st.sidebar.title("📁 Gestão de Dados")

with st.sidebar.expander("📚 Dados de Cursos (Moodle)", expanded=True):
    files_cursos = st.file_uploader("Upload CSV Cursos", type=["csv"], accept_multiple_files=True)
    if files_cursos:
        dfs = [pd.read_csv(f).rename(columns=lambda x: x.strip()) for f in files_cursos]
        st.session_state.cursos_df = pd.concat(dfs, ignore_index=True)

with st.sidebar.expander("📋 Dados de QuestionáriosCristiano", expanded=True):
    files_quest = st.file_uploader("Upload XLSX Questionários", type=["xlsx"], accept_multiple_files=True)
    if files_quest:
        dfs_q = [processar_questionarios_excel(f) for f in files_quest]
        st.session_state.quest_df = pd.concat(dfs_q, ignore_index=True)

# Filtros Globais (Unificados)
st.sidebar.markdown("---")
lista_centros = set()
if st.session_state.cursos_df is not None:
    lista_centros.update(st.session_state.cursos_df["Centro"].unique())
if st.session_state.quest_df is not None:
    lista_centros.update(st.session_state.quest_df["Centro"].unique())

st.session_state.filtro_centro = st.sidebar.multiselect(
    "Filtrar por Centro", sorted(list(lista_centros)), default=st.session_state.filtro_centro
)

# --------------------------
# NAVEGAÇÃO
# --------------------------
pagina = st.radio("📌 Navegação", ["📚 Cursos", "📋 Questionários", "🎯 Gestão de Qualidade", "⚔️ Comparador Versus"], horizontal=True)

# --------------------------
# PÁGINA 1: CURSOS
# --------------------------
if pagina == "📚 Cursos":
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

# --------------------------
# PÁGINA 2: QUESTIONÁRIOS
# --------------------------
elif pagina == "📋 Questionários":
    df_q = aplicar_filtros(st.session_state.quest_df) 
    
    if df_q is not None:
        st.subheader("📋 Base de Dados de Satisfação")
        
        # --- FUNÇÃO AUXILIAR CORRIGIDA ---
        def checklist_com_select_all(lista_itens, titulo, chave_unica):
            with st.popover(titulo, use_container_width=True):
                c_btn1, c_btn2 = st.columns(2)
                
                # Botão Selecionar Tudo
                if c_btn1.button("Selecionar Tudo", key=f"all_btn_{chave_unica}"):
                    for item in lista_itens:
                        st.session_state[f"chk_{chave_unica}_{item}"] = True
                    st.rerun()

                # Botão Limpar Tudo
                if c_btn2.button("Limpar Tudo", key=f"none_btn_{chave_unica}"):
                    for item in lista_itens:
                        st.session_state[f"chk_{chave_unica}_{item}"] = False
                    st.rerun()

                selecionados = []
                for item in lista_itens:
                    chave_item = f"chk_{chave_unica}_{item}"
                    
                    # Se o item ainda não estiver no estado, começa como True
                    if chave_item not in st.session_state:
                        st.session_state[chave_item] = True
                    
                    # O checkbox lê e escreve diretamente na chave do session_state
                    if st.checkbox(str(item), key=chave_item):
                        selecionados.append(item)
                return selecionados

        # --- LINHA 1 DE FILTROS ---
        col1, col2, col3 = st.columns(3)

        with col1:
            all_mods = sorted(df_q["Modalidade"].unique())
            sel_mod = checklist_com_select_all(all_mods, "Filtrar Modalidade", "mods")

        with col2:
            all_resps = sorted(df_q["Respondente"].unique())
            sel_resp = checklist_com_select_all(all_resps, "Filtrar Respondentes", "resps")
            
        # Filtragem intermédia (Cascata)
        df_temp = df_q[(df_q["Modalidade"].isin(sel_mod)) & (df_q["Respondente"].isin(sel_resp))]

        with col3:
            all_cursos = sorted(df_temp["Curso"].unique())
            sel_cursos = checklist_com_select_all(all_cursos, "Filtrar Cursos", "cursos")

        # --- LINHA 2 DE FILTROS ---
        col4, col5 = st.columns(2)

        df_temp = df_temp[df_temp["Curso"].isin(sel_cursos)]

        with col4:
            all_cats = sorted(df_temp["Categoria"].unique())
            sel_cat = checklist_com_select_all(all_cats, "Filtrar Categorias", "cats")

        with col5:
            # Filtra a lista de perguntas com base nas categorias selecionadas acima
            lista_pergs_filtrada = sorted(df_temp[df_temp["Categoria"].isin(sel_cat)]["Pergunta"].unique())
            sel_perg = checklist_com_select_all(lista_pergs_filtrada, "Filtrar Perguntas", "pergs")

        # --- FILTRAGEM FINAL ---
        df_display = df_temp[
            (df_temp["Categoria"].isin(sel_cat)) & 
            (df_temp["Pergunta"].isin(sel_perg))
        ]

        # --- EXIBIÇÃO ---
        if not df_display.empty:
            st.write(f"Exibindo **{len(df_display)}** registos.")
            st.dataframe(df_display, use_container_width=True)
        else:
            st.warning("Selecione os itens nos filtros acima para visualizar os dados.")
        
    else:
        st.info("Carregue ficheiros de Questionários na barra lateral para ativar os filtros.")

# --------------------------
# PÁGINA 3: GESTÃO DE QUALIDADE
# --------------------------
elif pagina == "🎯 Gestão de Qualidade":
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
# --------------------------
# PÁGINA 4: COMPARADOR VERSUS
# --------------------------
elif pagina == "⚔️ Comparador Versus":
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