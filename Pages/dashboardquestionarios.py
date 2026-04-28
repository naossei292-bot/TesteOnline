import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ─────────────────────────────────────────────────────────────
# Paleta e estilos globais
# ─────────────────────────────────────────────────────────────
COR_PRIMARIA   = "#1F4E79"
COR_SECUNDARIA = "#2E75B6"
COR_ACENTO     = "#70AD47"
COR_AVISO      = "#ED7D31"
COR_FUNDO_CARD = "#F0F4FA"
COR_TEXTO      = "#1A2535"

PALETA = [
    "#2E75B6", "#70AD47", "#ED7D31", "#FFC000",
    "#5B9BD5", "#A9D18E", "#F4B183", "#FFD966",
    "#1F4E79", "#375623", "#843C0C", "#7F6000",
]

PLOTLY_LAYOUT = dict(
    font_family="Segoe UI, sans-serif",
    font_color=COR_TEXTO,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=16, r=16, t=36, b=16),
    colorway=PALETA,
)


def _css():
    st.markdown("""
    <style>
    /* Fundo e tipografia geral */
    [data-testid="stAppViewContainer"] { background: #F5F8FC; }
    [data-testid="stSidebar"] {
        background: #1F4E79 !important;
        border-right: none;
    }
    [data-testid="stSidebar"] * { color: #E8F0FB !important; }
    [data-testid="stSidebar"] .stMultiSelect span,
    [data-testid="stSidebar"] .stDateInput input {
        background: #2E75B6 !important;
        color: #fff !important;
    }
    [data-testid="stSidebar"] label { color: #C5D8F0 !important; font-size: 0.78rem !important; }
    [data-testid="stSidebar"] h2 { color: #fff !important; font-size: 1rem !important; }

    /* Cards KPI */
    .kpi-card {
        background: #fff;
        border-radius: 12px;
        padding: 18px 20px 14px;
        box-shadow: 0 2px 8px rgba(31,78,121,.10);
        border-left: 5px solid #2E75B6;
        margin-bottom: 4px;
    }
    .kpi-card.verde  { border-color: #70AD47; }
    .kpi-card.laranja{ border-color: #ED7D31; }
    .kpi-card.amarelo{ border-color: #FFC000; }
    .kpi-label { font-size: .72rem; font-weight: 600; letter-spacing: .06em;
                 text-transform: uppercase; color: #6B7C93; margin-bottom: 2px; }
    .kpi-value { font-size: 1.9rem; font-weight: 700; color: #1F4E79; line-height: 1.1; }
    .kpi-sub   { font-size: .72rem; color: #8FA3B8; margin-top: 2px; }

    /* Títulos de secção */
    .sec-title {
        font-size: .8rem; font-weight: 700; letter-spacing: .08em;
        text-transform: uppercase; color: #2E75B6;
        border-bottom: 2px solid #2E75B6;
        padding-bottom: 4px; margin: 18px 0 10px;
    }

    /* Gráficos */
    [data-testid="stPlotlyChart"] > div { border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)


def _kpi(label, value, sub="", cor=""):
    cls = f"kpi-card {cor}".strip()
    st.markdown(
        f'<div class="{cls}">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-sub">{sub}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _sec(titulo):
    st.markdown(f'<div class="sec-title">{titulo}</div>', unsafe_allow_html=True)


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

    return df


def _fig_bar(df_group, x, y, titulo, cor=COR_SECUNDARIA, horizontal=False):
    if horizontal:
        fig = px.bar(df_group, x=y, y=x, orientation="h",
                     text_auto=".2f", color_discrete_sequence=[cor])
        fig.update_traces(textposition="outside")
    else:
        fig = px.bar(df_group, x=x, y=y,
                     text_auto=".2f", color_discrete_sequence=[cor])
        fig.update_traces(textposition="outside")
    fig.update_layout(title_text=titulo, title_font_size=13, **PLOTLY_LAYOUT)
    fig.update_yaxes(showgrid=True, gridcolor="#EEF2F8")
    fig.update_xaxes(showgrid=False)
    return fig


def _fig_pizza(df_group, names, values, titulo):
    fig = px.pie(df_group, names=names, values=values,
                 color_discrete_sequence=PALETA, hole=0.45)
    fig.update_traces(textinfo="percent+label", textfont_size=11)
    fig.update_layout(title_text=titulo, title_font_size=13,
                      showlegend=False, **PLOTLY_LAYOUT)
    return fig


def _fig_linha(df_group, x, y, cor=None, titulo=""):
    fig = px.line(df_group.sort_values(x), x=x, y=y, markers=True,
                  color_discrete_sequence=[cor or COR_SECUNDARIA])
    fig.update_traces(line_width=2.5, marker_size=7)
    fig.update_layout(title_text=titulo, title_font_size=13, **PLOTLY_LAYOUT)
    fig.update_yaxes(showgrid=True, gridcolor="#EEF2F8")
    return fig


# NOVA FUNÇÃO - Gráfico de linha com pontos estilo o da imagem
def _fig_linha_pontos(df_group, x, y, titulo="", cor=COR_SECUNDARIA):
    """
    Cria um gráfico de linha com pontos marcados e valores visíveis,
    similar ao exemplo da imagem com eixo Y de 0.5 a 4.5
    """
    fig = go.Figure()
    
    # Adiciona a linha com marcadores e texto
    fig.add_trace(go.Scatter(
        x=df_group[x],
        y=df_group[y],
        mode='lines+markers+text',
        name='Série1',
        line=dict(color=cor, width=2.5),
        marker=dict(
            size=12,
            color=cor,
            symbol='circle',
            line=dict(color='white', width=2)
        ),
        text=df_group[y].round(1),
        textposition='top center',
        textfont=dict(size=10, color=COR_TEXTO)
    ))
    
    # Configuração do layout
    fig.update_layout(
        title=dict(text=titulo, font_size=13),
        xaxis=dict(
            title=dict(text="", font_size=11),
            tickangle=0,
            showgrid=False,
            tickfont=dict(size=10)
        ),
        yaxis=dict(
            title=dict(text="Valor Médio", font_size=11),
            showgrid=True,
            gridcolor="#EEF2F8",
            range=[0.5, 4.5],
            dtick=0.5,
            tickfont=dict(size=10)
        ),
        **PLOTLY_LAYOUT
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
            color_discrete_sequence=PALETA,
        )
        fig.update_traces(texttemplate="%{y:.2f}", textposition="outside")
    else:
        fig = px.bar(
            df_group.sort_values("Folha"),
            x="Folha",
            y="Valor Médio",
            color_discrete_sequence=[COR_SECUNDARIA],
            category_orders={"Folha": ordem_folhas},
        )
        fig.update_traces(texttemplate="%{y:.2f}", textposition="outside")

    fig.update_layout(
        title_text=titulo,
        title_font_size=13,
        barmode="group",
        **PLOTLY_LAYOUT
    )
    fig.update_yaxes(showgrid=True, gridcolor="#EEF2F8", range=[0.5, 4.5], dtick=0.5)
    fig.update_xaxes(showgrid=False, type="category")
    return fig


# ─────────────────────────────────────────────────────────────
# Sidebar de filtros
# ─────────────────────────────────────────────────────────────

def _sidebar_filtros(df: pd.DataFrame) -> pd.DataFrame:
    with st.sidebar:
        st.markdown("## 🎛️ Filtros")
        st.markdown("---")

        # ── Respondente ──────────────────────────────────────
        st.markdown("**Respondente**")
        todos_respondentes = sorted(df["Respondente"].dropna().unique())
        sel_respondente = st.multiselect(
            "Respondente", todos_respondentes, default=todos_respondentes,
            key="dash_respondente", label_visibility="collapsed",
        )

        st.markdown("---")

        # ── Centro ───────────────────────────────────────────
        st.markdown("**Centro**")
        todos_centros = sorted(df["Centro"].dropna().unique())
        sel_centro = st.multiselect(
            "Centro", todos_centros, default=todos_centros,
            key="dash_centro", label_visibility="collapsed",
        )

        st.markdown("---")

        # ── Ação / Shortname ─────────────────────────────────
        st.markdown("**Ação / Shortname**")
        # Filtrar shortnames já depois do filtro de centro para reduzir opções
        df_pre = df.copy()
        if sel_centro:
            df_pre = df_pre[df_pre["Centro"].isin(sel_centro) | df_pre["Centro"].isna()]
        todos_shortnames = sorted(df_pre["Shortname"].dropna().unique())
        sel_shortname = st.multiselect(
            "Ação", todos_shortnames, default=todos_shortnames,
            key="dash_shortname", label_visibility="collapsed",
        )

        st.markdown("---")

        # ── Data de início ───────────────────────────────────
        st.markdown("**Período (Data Início)**")
        datas_validas = df["Datini"].dropna()
        if not datas_validas.empty:
            d_min = datas_validas.min().date()
            d_max = datas_validas.max().date()
            sel_data_ini = st.date_input("De", value=d_min, min_value=d_min, max_value=d_max, key="dash_d_ini")
            sel_data_fim = st.date_input("Até", value=d_max, min_value=d_min, max_value=d_max, key="dash_d_fim")
        else:
            sel_data_ini = None
            sel_data_fim = None

        st.markdown("---")

        # ── Módulo ───────────────────────────────────────────
        st.markdown("**Módulo**")
        todos_modulos = sorted(df["Módulo"].dropna().unique())
        sel_modulo = st.multiselect(
            "Módulo", todos_modulos, default=todos_modulos,
            key="dash_modulo", label_visibility="collapsed",
        )

    # ── Aplicar filtros ──────────────────────────────────────
    df_f = df.copy()

    if sel_respondente:
        df_f = df_f[df_f["Respondente"].isin(sel_respondente)]
    if sel_centro:
        df_f = df_f[df_f["Centro"].isin(sel_centro) | df_f["Centro"].isna()]
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


# ─────────────────────────────────────────────────────────────
# Página principal
# ─────────────────────────────────────────────────────────────

def mostrar_questionarios_dashboard():
    st.set_page_config(layout="wide") if False else None   # já definido no main
    _css()

    st.markdown(
        f'<h1 style="color:{COR_PRIMARIA};font-size:1.6rem;margin-bottom:0;">'
        '📊 Dashboard de Satisfação</h1>'
        f'<p style="color:#6B7C93;font-size:.85rem;margin-top:2px;">'
        'Análise de questionários por Centro, Ação, Data e Respondente</p>',
        unsafe_allow_html=True,
    )

    # ── Verificar dados disponíveis ──────────────────────────
    if "quest_editaveis" not in st.session_state or st.session_state.quest_editaveis.empty:
        st.warning(
            "⚠️ Sem dados carregados. Aceda à página **Questionários** e carregue os ficheiros primeiro.",
            icon="📋"
        )
        return

    df_raw = st.session_state.quest_editaveis.drop(columns=["Apagar"], errors="ignore").copy()
    df_raw = _preparar_dados(df_raw)

    # Remover linhas sem shortname
    df_raw = df_raw[df_raw["Shortname"].notna()]
    if df_raw.empty:
        st.info("ℹ️ Nenhum dado válido encontrado.")
        return

    # ── Sidebar + filtros ────────────────────────────────────
    df = _sidebar_filtros(df_raw)

    if df.empty:
        st.info("ℹ️ Nenhum registo corresponde aos filtros selecionados.")
        return

    n_total    = len(df_raw)
    n_filtrado = len(df)

    # ── KPIs ─────────────────────────────────────────────────
    _sec("Indicadores Gerais")

    vm_geral = df["Valor Médio"].mean()
    vm_max   = df.groupby("Shortname")["Valor Médio"].mean().max()
    vm_min   = df.groupby("Shortname")["Valor Médio"].mean().min()

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: _kpi("Registos filtrados", f"{n_filtrado:,}".replace(",","."), f"de {n_total:,}".replace(",","."))
    with k2: _kpi("Cursos (Shortnames)", df["Shortname"].nunique(), "únicos")
    with k3: _kpi("Centros", df["Centro"].nunique() if df["Centro"].notna().any() else "—", "", "verde")

    st.markdown("")

    # ── Linha 1: por Centro e por Respondente ────────────────
    _sec("Satisfação por Centro e Respondente")
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
                         "Valor Médio por Centro", COR_SECUNDARIA, horizontal=True),
                use_container_width=True
            )
        else:
            st.info("Carregue o ficheiro Excel de Ações para ver dados por Centro.")

    with c2:
        if df["Respondente"].notna().any():
            df_resp = (
                df["Respondente"].value_counts(dropna=True)
                .rename_axis("Respondente")
                .reset_index(name="Registos")
            )
            st.plotly_chart(
                _fig_pizza(df_resp, "Respondente", "Registos", "Distribuição por Respondente"),
                use_container_width=True
            )

    # ── NOVO GRÁFICO DE LINHA COM PONTOS ─────────────────────
    _sec("Evolução da Satisfação")
    
    # Verifica se existe coluna de Folha e valor médio para o gráfico principal
    if "Folha" in df.columns and "Valor Médio" in df.columns:
        ordem_folhas = ["21a", "21b", "22a", "22b", "23a", "23b", "24a", "24b"]
        df_folha = df[df["Folha"].isin(ordem_folhas)].copy()

        if not df_folha.empty:
            df_folha["Folha"] = pd.Categorical(df_folha["Folha"], categories=ordem_folhas, ordered=True)

            if "Pergunta" in df_folha.columns and df_folha["Pergunta"].notna().any():
                # Normaliza a pergunta para usar apenas a letra inicial A-F e remover N, P, R, S, O
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
                    .mean()
                    .round(2)
                    .reset_index()
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
                    .mean()
                    .round(2)
                    .reset_index()
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
        # Alternativa: usar meses como eixo X
        df_meses = (
            df.groupby("_Mês")["Valor Médio"]
            .mean()
            .round(2)
            .reset_index()
            .sort_values("_Mês")
        )
        
        st.plotly_chart(
            _fig_linha_pontos(
                df_meses,
                "_Mês",
                "Valor Médio",
                "Evolução Mensal da Satisfação"
            ),
            use_container_width=True
        )
    elif "Shortname" in df.columns and "Valor Médio" in df.columns:
        # Alternativa: usar ações como eixo X
        df_acoes = (
            df.groupby("Shortname")["Valor Médio"]
            .mean()
            .round(2)
            .reset_index()
            .sort_values("Shortname")
        )
        
        st.plotly_chart(
            _fig_linha_pontos(
                df_acoes,
                "Shortname",
                "Valor Médio",
                "Satisfação Média por Ação"
            ),
            use_container_width=True
        )
    else:
        st.info("ℹ️ Adicione uma coluna 'Pergunta', 'Shortname' ou tenha dados mensais para ver o gráfico de evolução.")

    # ── Tabela resumo filtrada ─────────────────────────────────
    _sec("Tabela Resumo")
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

    total_mostrado = len(df_resumo)
    st.caption(f"A mostrar {total_mostrado:,} registos filtrados.".replace(",", "."))


if __name__ == "__main__":
    mostrar_questionarios_dashboard()