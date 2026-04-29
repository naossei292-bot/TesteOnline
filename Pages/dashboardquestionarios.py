import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _preparar_dados(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Valor Médio"] = pd.to_numeric(df["Valor Médio"], errors="coerce")

    # Normalizar datas
    for col in ["Datini", "Datfim", "Data"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Coluna auxiliar: mês/ano da data de início
    if "Datini" in df.columns:
        df["_Mês"] = df["Datini"].dt.to_period("M").astype(str)
    elif "Data" in df.columns:
        df["_Mês"] = df["Data"].dt.to_period("M").astype(str)
    else:
        df["_Mês"] = None

    # Limpeza de strings
    for col in ["Centro", "Shortname", "Respondente", "Módulo", "Folha"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().replace({"nan": None, "None": None, "": None})

    # Preencher Shortname vazio para não perder registos de formadores/tutores
    if "Shortname" in df.columns:
        df["Shortname"] = df["Shortname"].fillna("Sem Ação")

    return df


def _fig_bar(df_group, x, y, titulo, horizontal=False):
    if horizontal:
        fig = px.bar(df_group, x=y, y=x, orientation="h", text_auto=".2f")
        fig.update_traces(textposition="outside")
    else:
        fig = px.bar(df_group, x=x, y=y, text_auto=".2f")
        fig.update_traces(textposition="outside")
    fig.update_layout(title_text=titulo, title_font_size=13)
    fig.update_yaxes(showgrid=True)
    fig.update_xaxes(showgrid=False)
    return fig


def _fig_pizza(df_group, names, values, titulo):
    fig = px.pie(df_group, names=names, values=values, hole=0.45)
    fig.update_traces(textinfo="percent+label", textfont_size=11)
    fig.update_layout(title_text=titulo, title_font_size=13, showlegend=False)
    return fig


def _fig_linha_pontos(df_group, x, y, titulo=""):
    """
    Cria um gráfico de linha com pontos marcados e valores visíveis
    """
    fig = go.Figure()
    
    # Adiciona a linha com marcadores e texto
    fig.add_trace(go.Scatter(
        x=df_group[x],
        y=df_group[y],
        mode='lines+markers+text',
        name='Série1',
        line=dict(width=2.5),
        marker=dict(size=12, symbol='circle', line=dict(width=2)),
        text=df_group[y].round(1),
        textposition='top center',
        textfont=dict(size=10)
    ))
    
    # Configuração do layout
    fig.update_layout(
        title=dict(text=titulo, font_size=13),
        xaxis=dict(title=dict(text="", font_size=11), tickangle=0, showgrid=False, tickfont=dict(size=10)),
        yaxis=dict(title=dict(text="Valor Médio", font_size=11), showgrid=True, range=[0.5, 4.5], dtick=0.5, tickfont=dict(size=10))
    )
    
    return fig


def _fig_barras_por_folha(df_group, categoria=None, titulo=""):
    ordem_folhas = ["21a", "21b", "22a", "22b", "23a", "23b", "24a", "24b"]
    if categoria and categoria in df_group.columns:
        fig = px.bar(
            df_group.sort_values(["Folha", categoria]),
            x="Folha",
            y="Valor Médio",
            color=categoria,
            barmode="group",
            category_orders={"Folha": ordem_folhas},
        )
        fig.update_traces(texttemplate="%{y:.2f}", textposition="outside")
    else:
        fig = px.bar(
            df_group.sort_values("Folha"),
            x="Folha",
            y="Valor Médio",
            category_orders={"Folha": ordem_folhas},
        )
        fig.update_traces(texttemplate="%{y:.2f}", textposition="outside")

    fig.update_layout(title_text=titulo, title_font_size=13, barmode="group")
    fig.update_yaxes(showgrid=True, range=[0.5, 4.5], dtick=0.5)
    fig.update_xaxes(showgrid=False, type="category")
    return fig


# ─────────────────────────────────────────────────────────────
# Filtros em cascata na página principal
# ─────────────────────────────────────────────────────────────

def _aplicar_filtros(df: pd.DataFrame, 
                     sel_respondente, 
                     sel_centro, 
                     sel_shortname, 
                     sel_modulo, 
                     sel_data_ini, 
                     sel_data_fim) -> pd.DataFrame:
    """
    Aplica os filtros da interface.
    """
    df_f = df.copy()

    if sel_respondente:
        df_f = df_f[df_f["Respondente"].isin(sel_respondente)]
    if sel_centro:
        df_f = df_f[df_f["Centro"].isin(sel_centro)]
    if sel_shortname:
        df_f = df_f[df_f["Shortname"].isin(sel_shortname)]
    if sel_modulo:
        df_f = df_f[df_f["Módulo"].isin(sel_modulo)]
    if sel_data_ini and sel_data_fim and "Datini" in df_f.columns:
        mask = (
            df_f["Datini"].isna() |
            (
                (df_f["Datini"].dt.date >= sel_data_ini) &
                (df_f["Datini"].dt.date <= sel_data_fim)
            )
        )
        df_f = df_f[mask]

    return df_f


def _mostrar_filtros(df: pd.DataFrame):
    """
    Exibe os filtros em cascata na página principal.
    Os filtros começam vazios e as opções são filtradas baseado nas seleções anteriores.
    """
    with st.expander("🔍 **Filtros**", expanded=True):
        
        # Inicializar session state para os filtros, se necessário
        if 'filtros_inicializados' not in st.session_state:
            st.session_state.filtros_inicializados = True
            st.session_state.sel_respondente = []
            st.session_state.sel_centro = []
            st.session_state.sel_shortname = []
            st.session_state.sel_modulo = []
            st.session_state.sel_data_ini = None
            st.session_state.sel_data_fim = None
        
        # Linha 1: Respondente (primeiro filtro)
        col1, col2 = st.columns(2)
        
        with col1:
            todos_respondentes = sorted(df["Respondente"].dropna().unique())
            sel_respondente = st.multiselect(
                "**1. Respondente**", 
                todos_respondentes, 
                default=st.session_state.sel_respondente,
                key="dash_respondente",
                placeholder="Selecione os respondentes..."
            )
            st.session_state.sel_respondente = sel_respondente
        
        # Filtrar dados baseado no Respondente selecionado
        df_filtrado = df.copy()
        if sel_respondente:
            df_filtrado = df_filtrado[df_filtrado["Respondente"].isin(sel_respondente)]
        
        with col2:
            todos_centros = sorted(df_filtrado["Centro"].dropna().unique())
            # Garantir que o filtro de centro só mostra opções do respondente selecionado
            sel_centro = st.multiselect(
                "**2. Centro**", 
                todos_centros, 
                default=[c for c in st.session_state.sel_centro if c in todos_centros],
                key="dash_centro",
                placeholder="Selecione os centros..."
            )
            st.session_state.sel_centro = sel_centro
        
        # Filtrar também por Centro
        if sel_centro:
            df_filtrado = df_filtrado[df_filtrado["Centro"].isin(sel_centro)]
        
        # Linha 2: Ação/Shortname e Módulo
        col3, col4 = st.columns(2)
        
        with col3:
            todos_shortnames = sorted(df_filtrado["Shortname"].dropna().unique())
            sel_shortname = st.multiselect(
                "**3. Ação / Shortname**", 
                todos_shortnames, 
                default=[s for s in st.session_state.sel_shortname if s in todos_shortnames],
                key="dash_shortname",
                placeholder="Selecione as ações..."
            )
            st.session_state.sel_shortname = sel_shortname
        
        # Filtrar por Shortname
        if sel_shortname:
            df_filtrado = df_filtrado[df_filtrado["Shortname"].isin(sel_shortname)]
        
        with col4:
            todos_modulos = sorted(df_filtrado["Módulo"].dropna().unique())
            sel_modulo = st.multiselect(
                "**4. Módulo**", 
                todos_modulos, 
                default=[m for m in st.session_state.sel_modulo if m in todos_modulos],
                key="dash_modulo",
                placeholder="Selecione os módulos..."
            )
            st.session_state.sel_modulo = sel_modulo
        
        # Filtrar por Módulo
        if sel_modulo:
            df_filtrado = df_filtrado[df_filtrado["Módulo"].isin(sel_modulo)]
        
        # Linha 3: Período (Data Início)
        col5, col6 = st.columns(2)
        
        with col5:
            datas_validas = df_filtrado["Datini"].dropna()
            if not datas_validas.empty:
                d_min = datas_validas.min().date()
                d_max = datas_validas.max().date()
                
                # Garantir que as datas selecionadas estão dentro do range
                if st.session_state.sel_data_ini and st.session_state.sel_data_ini < d_min:
                    st.session_state.sel_data_ini = d_min
                if st.session_state.sel_data_fim and st.session_state.sel_data_fim > d_max:
                    st.session_state.sel_data_fim = d_max
                
                sel_data_ini = st.date_input(
                    "**5. Data Início**", 
                    value=st.session_state.sel_data_ini if st.session_state.sel_data_ini else d_min,
                    min_value=d_min, 
                    max_value=d_max, 
                    key="dash_d_ini"
                )
                st.session_state.sel_data_ini = sel_data_ini
            else:
                sel_data_ini = None
        
        with col6:
            if not datas_validas.empty:
                sel_data_fim = st.date_input(
                    "**6. Data Fim**", 
                    value=st.session_state.sel_data_fim if st.session_state.sel_data_fim else d_max,
                    min_value=d_min, 
                    max_value=d_max, 
                    key="dash_d_fim"
                )
                st.session_state.sel_data_fim = sel_data_fim
            else:
                sel_data_fim = None
        
        # Informação sobre quantos registos estão disponíveis
        st.info(f"📊 **{len(df_filtrado):,}** registos disponíveis com os filtros atuais.", icon="ℹ️")
    
    return (st.session_state.sel_respondente, 
            st.session_state.sel_centro, 
            st.session_state.sel_shortname, 
            st.session_state.sel_modulo, 
            st.session_state.sel_data_ini, 
            st.session_state.sel_data_fim)


# ─────────────────────────────────────────────────────────────
# Página principal da dashboard
# ─────────────────────────────────────────────────────────────

def mostrar_questionarios_dashboard():
    """
    Página principal da dashboard. Permite carregar um ficheiro Excel/CSV
    exportado a partir da página Questionários, ou usar os dados em sessão.
    """
    st.set_page_config(layout="wide", page_title="Dashboard de Satisfação")
    
    st.title("📊 Dashboard de Satisfação")
    st.markdown("Análise de questionários por Centro, Ação, Data e Respondente")
    st.markdown("---")

    # Upload directo de ficheiro (Excel/CSV)
    with st.expander("📂 **Carregar ficheiro de dados**", expanded=False):
        uploaded_file = st.file_uploader(
            "Carregue o ficheiro exportado do módulo Questionários (Excel ou CSV)",
            type=["xlsx", "csv"],
            key="dash_upload"
        )

    # Escolher fonte dos dados
    if uploaded_file is not None:
        if uploaded_file.name.endswith(".xlsx"):
            df_raw = pd.read_excel(uploaded_file)
        else:
            df_raw = pd.read_csv(uploaded_file)
        st.success(f"✅ Dados carregados do ficheiro: {len(df_raw)} registos")
        # Resetar filtros quando novo ficheiro é carregado
        st.session_state.sel_respondente = []
        st.session_state.sel_centro = []
        st.session_state.sel_shortname = []
        st.session_state.sel_modulo = []
        st.session_state.sel_data_ini = None
        st.session_state.sel_data_fim = None
    elif "quest_editaveis" in st.session_state and not st.session_state.quest_editaveis.empty:
        df_raw = st.session_state.quest_editaveis.drop(columns=["Apagar"], errors="ignore").copy()
    else:
        st.warning(
            "⚠️ Sem dados. Carregue um ficheiro exportado da página Questionários "
            "ou aceda a essa página e carregue os ficheiros primeiro.",
            icon="📋"
        )
        return

    # Preparar dados e garantir Shortname preenchido
    df_raw = _preparar_dados(df_raw)

    if df_raw.empty:
        st.info("ℹ️ Nenhum dado válido encontrado.")
        return

    # Mostrar filtros em cascata na página principal
    sel_respondente, sel_centro, sel_shortname, sel_modulo, sel_data_ini, sel_data_fim = _mostrar_filtros(df_raw)

    # Aplicar filtros
    df = _aplicar_filtros(df_raw, sel_respondente, sel_centro, sel_shortname, sel_modulo, sel_data_ini, sel_data_fim)

    if df.empty:
        st.info("ℹ️ Nenhum registo corresponde aos filtros selecionados. Tente alargar os critérios de filtragem.")
        return

    st.markdown("---")

    # KPIs
    st.markdown("### 📈 Indicadores Gerais")
    n_total = len(df_raw)
    n_filtrado = len(df)
    vm_geral = df["Valor Médio"].mean()
    vm_max = df.groupby("Shortname")["Valor Médio"].mean().max() if not df.empty else 0
    vm_min = df.groupby("Shortname")["Valor Médio"].mean().min() if not df.empty else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("Registos filtrados", f"{n_filtrado:,}".replace(",", "."), f"de {n_total:,}".replace(",", "."))
    with k2:
        st.metric("Cursos (Shortnames)", df["Shortname"].nunique())
    with k3:
        st.metric("Centros", df["Centro"].nunique() if df["Centro"].notna().any() else "—")
    with k4:
        st.metric("Média geral", f"{vm_geral:.2f}" if pd.notna(vm_geral) else "—")
    with k5:
        st.metric("Média max/min", f"{vm_max:.2f}" if pd.notna(vm_max) else "—", f"min: {vm_min:.2f}" if pd.notna(vm_min) else "—")

    st.markdown("")

    # Linha 1: por Centro e por Respondente
    st.markdown("### 📊 Satisfação por Centro e Respondente")
    c1, c2 = st.columns([3, 2])

    with c1:
        if df["Centro"].notna().any():
            df_centro = (
                df.groupby("Centro")["Valor Médio"]
                .mean().round(2).reset_index()
                .sort_values("Valor Médio", ascending=True)
                .rename(columns={"Valor Médio": "Média"})
            )
            st.plotly_chart(
                _fig_bar(df_centro, "Centro", "Média",
                         "Valor Médio por Centro", horizontal=True),
                use_container_width=True
            )
        else:
            st.info("Carregue o ficheiro Excel de Ações para ver dados por Centro.")

    with c2:
        if df["Respondente"].notna().any():
            df_resp = (
                df.groupby("Respondente")["Valor Médio"]
                .mean().round(2).reset_index()
                .rename(columns={"Valor Médio": "Média"})
            )
            st.plotly_chart(
                _fig_pizza(df_resp, "Respondente", "Média", "Satisfação Média por Respondente"),
                use_container_width=True
            )

    # Gráfico de barras por folha/pergunta
    st.markdown("### 📈 Evolução da Satisfação")

    if "Folha" in df.columns and "Valor Médio" in df.columns:
        ordem_folhas = ["21a", "21b", "22a", "22b", "23a", "23b", "24a", "24b"]
        df_folha = df[df["Folha"].isin(ordem_folhas)].copy()

        if not df_folha.empty:
            df_folha["Folha"] = pd.Categorical(df_folha["Folha"], categories=ordem_folhas, ordered=True)

            if "Pergunta" in df_folha.columns and df_folha["Pergunta"].notna().any():
                letras_validas = ["A", "B", "C", "D", "E", "F"]
                df_folha["Pergunta Letra"] = (
                    df_folha["Pergunta"].astype(str)
                    .str.strip()
                    .str.upper()
                    .str.extract(r'^([A-Z])')[0]
                )
                df_folha = df_folha[df_folha["Pergunta Letra"].isin(letras_validas)]

                df_plot = (
                    df_folha.groupby(["Folha", "Pergunta Letra"])["Valor Médio"]
                    .mean().round(2).reset_index()
                    .rename(columns={"Pergunta Letra": "Pergunta"})
                )
                st.plotly_chart(
                    _fig_barras_por_folha(
                        df_plot,
                        categoria="Pergunta",
                        titulo="Satisfação Média por Folha e Pergunta"
                    ),
                    use_container_width=True
                )
            else:
                df_plot = (
                    df_folha.groupby("Folha")["Valor Médio"]
                    .mean().round(2).reset_index()
                )
                st.plotly_chart(
                    _fig_barras_por_folha(
                        df_plot,
                        categoria=None,
                        titulo="Satisfação Média por Folha"
                    ),
                    use_container_width=True
                )
        else:
            st.info("ℹ️ Não existem folhas 21a-24b nos dados atuais para este gráfico.")
    elif "_Mês" in df.columns and "Valor Médio" in df.columns:
        df_meses = (
            df.groupby("_Mês")["Valor Médio"]
            .mean().round(2).reset_index()
            .sort_values("_Mês")
        )
        st.plotly_chart(
            _fig_linha_pontos(df_meses, "_Mês", "Valor Médio", "Evolução Mensal da Satisfação"),
            use_container_width=True
        )
    elif "Shortname" in df.columns and "Valor Médio" in df.columns:
        df_acoes = (
            df.groupby("Shortname")["Valor Médio"]
            .mean().round(2).reset_index()
            .sort_values("Shortname")
        )
        st.plotly_chart(
            _fig_linha_pontos(df_acoes, "Shortname", "Valor Médio", "Satisfação Média por Ação"),
            use_container_width=True
        )
    else:
        st.info("ℹ️ Adicione uma coluna 'Pergunta', 'Shortname' ou tenha dados mensais para ver o gráfico de evolução.")

    # Tabela resumo Filtrada
    st.markdown("### 📋 Tabela Resumo")
    COLS_RESUMO = [c for c in ["Centro", "Shortname", "Datini", "Respondente",
                               "Módulo", "Folha", "Pergunta", "Valor Médio"] if c in df.columns]
    df_resumo = df[COLS_RESUMO].copy()
    if "Datini" in df_resumo.columns:
        df_resumo["Datini"] = df_resumo["Datini"].dt.strftime("%d/%m/%Y")

    st.dataframe(
        df_resumo.reset_index(drop=True),
        use_container_width=True,
        height=280,
        hide_index=True,
    )
    st.caption(f"A mostrar {len(df_resumo):,} registos filtrados.".replace(",", "."))


if __name__ == "__main__":
    mostrar_questionarios_dashboard()