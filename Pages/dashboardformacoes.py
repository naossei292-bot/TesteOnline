import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Paleta de cores centralizada ──────────────────────────────────────────────
COR_PRIMARIA   = "#1E3A5F"
COR_SECUNDARIA = "#2E86AB"
COR_ACENTO     = "#F6AE2D"
COR_SUCESSO    = "#2DC653"
COR_PERIGO     = "#E63946"
COR_NEUTRO     = "#8D99AE"
GRADIENTE      = ["#1E3A5F", "#2E86AB", "#54C6EB", "#F6AE2D", "#F26419"]

LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Segoe UI, sans-serif", color="#2d2d2d"),
    margin=dict(l=10, r=10, t=40, b=10),
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def preparar_dados(df: pd.DataFrame) -> pd.DataFrame:
    """Limpa e converte tipos para garantir cálculos correctos."""
    df = df.copy()
    df.drop(columns=["Apagar"], errors="ignore", inplace=True)
    for col in ["Data Inicial", "Data Final"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    for col in ["Inscritos", "Concluídos", "Avaliados", "Aprovados",
                "Planeado", "Valor da Ação", "Valor Total"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def safe_sum(df, col):
    if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
        return df[col].sum()
    return 0


def taxa(parte, total):
    return round(parte / total * 100, 1) if total > 0 else 0


# ── Cards de métricas ─────────────────────────────────────────────────────────

def cartao_metrica(label: str, valor: str, delta: str = None,
                   cor: str = COR_PRIMARIA, icone: str = "📊"):
    delta_html = (
        f'<p style="margin:0;font-size:.78rem;color:{COR_SUCESSO};'
        f'font-weight:600;">{delta}</p>'
        if delta else ""
    )
    st.markdown(
        f"""
        <div style="
            background:white;
            border-radius:14px;
            padding:20px 22px;
            border-left:5px solid {cor};
            box-shadow:0 2px 12px rgba(0,0,0,.07);
            height:100%;
        ">
          <p style="margin:0 0 4px;font-size:.78rem;color:{COR_NEUTRO};
                    text-transform:uppercase;letter-spacing:.06em;font-weight:600;">
            {icone} {label}
          </p>
          <p style="margin:0;font-size:1.9rem;font-weight:700;color:{cor};
                    line-height:1.1;">
            {valor}
          </p>
          {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Secção: KPIs ──────────────────────────────────────────────────────────────

def secao_kpis(df: pd.DataFrame):
    total_acoes     = df["Ação"].nunique() if "Ação" in df.columns else 0
    total_inscritos = safe_sum(df, "Inscritos")
    total_conc      = safe_sum(df, "Concluídos")
    total_aval      = safe_sum(df, "Avaliados")
    total_apr       = safe_sum(df, "Aprovados")
    total_valor     = safe_sum(df, "Valor Total")

    t_conc  = taxa(total_conc, total_inscritos)
    t_apr   = taxa(total_apr,  total_conc) if total_conc > 0 else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        cartao_metrica("Ações", f"{total_acoes:,}",       icone="🎓", cor=COR_PRIMARIA)
    with c2:
        cartao_metrica("Inscritos", f"{total_inscritos:,.0f}",  icone="👥", cor=COR_SECUNDARIA)
    with c3:
        cartao_metrica("Concluídos", f"{total_conc:,.0f}",      icone="✅", cor=COR_SUCESSO)
    with c4:
        cartao_metrica("Taxa Conclusão", f"{t_conc}%",          icone="📈", cor=COR_ACENTO)
    with c5:
        cartao_metrica("Taxa Aprovação", f"{t_apr}%",           icone="🏆", cor="#9B5DE5")
    with c6:
        cartao_metrica("Valor Total",
                       f"€{total_valor:,.0f}".replace(",", "."),
                       icone="💶", cor=COR_PERIGO)


# ── Secção: Status ────────────────────────────────────────────────────────────

def grafico_status(df: pd.DataFrame):
    if "Status" not in df.columns:
        return
    counts = df["Status"].value_counts().reset_index()
    counts.columns = ["Status", "Total"]

    cores_status = {
        "FINALIZADA": COR_SUCESSO,
        "ABERTA":     COR_SECUNDARIA,
        "CANCELADA":  COR_PERIGO,
        "SUSPENSA":   COR_ACENTO,
    }
    cor_lista = [cores_status.get(s, COR_NEUTRO) for s in counts["Status"]]

    fig = go.Figure(go.Pie(
        labels=counts["Status"],
        values=counts["Total"],
        hole=.55,
        marker=dict(colors=cor_lista, line=dict(color="white", width=2)),
        textinfo="label+percent",
        textfont=dict(size=12),
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text="Estado das Ações", font=dict(size=14, color=COR_PRIMARIA)),
        showlegend=False,
        height=260,
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Secção: Inscritos por Centro ──────────────────────────────────────────────

def grafico_por_centro(df: pd.DataFrame):
    if "Centro" not in df.columns or "Inscritos" not in df.columns:
        return
    agg = (df.groupby("Centro")["Inscritos"]
             .sum()
             .sort_values(ascending=True)
             .reset_index())
    agg.columns = ["Centro", "Inscritos"]

    fig = px.bar(
        agg, x="Inscritos", y="Centro", orientation="h",
        color="Inscritos",
        color_continuous_scale=["#54C6EB", COR_PRIMARIA],
        text="Inscritos",
    )
    fig.update_traces(textposition="outside", textfont=dict(size=11))
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text="Inscritos por Centro", font=dict(size=14, color=COR_PRIMARIA)),
        coloraxis_showscale=False,
        height=max(220, len(agg) * 34),
        xaxis=dict(showgrid=False, visible=False),
        yaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Secção: Funil de participação ─────────────────────────────────────────────

def grafico_funil(df: pd.DataFrame):
    stages = [
        ("Inscritos",   safe_sum(df, "Inscritos"),   COR_SECUNDARIA),
        ("Concluídos",  safe_sum(df, "Concluídos"),  COR_ACENTO),
        ("Avaliados",   safe_sum(df, "Avaliados"),   "#9B5DE5"),
        ("Aprovados",   safe_sum(df, "Aprovados"),   COR_SUCESSO),
    ]
    labels = [s[0] for s in stages]
    values = [s[1] for s in stages]
    cores  = [s[2] for s in stages]

    fig = go.Figure(go.Funnel(
        y=labels, x=values,
        marker=dict(color=cores, line=dict(color="white", width=1)),
        textinfo="value+percent initial",
        textfont=dict(size=12),
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text="Funil de Participação", font=dict(size=14, color=COR_PRIMARIA)),
        height=260,
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Secção: Timeline de ações ────────────────────────────────────────────────

def grafico_timeline(df: pd.DataFrame):
    if "Data Inicial" not in df.columns or df["Data Inicial"].isna().all():
        return

    df_t = df.dropna(subset=["Data Inicial"]).copy()
    df_t["Mês"] = df_t["Data Inicial"].dt.to_period("M").dt.to_timestamp()

    agg = (df_t.groupby("Mês")
               .agg(Ações=("Ação", "count"), Inscritos=("Inscritos", "sum"))
               .reset_index())

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=agg["Mês"], y=agg["Ações"],
               name="Nº Ações", marker_color=COR_SECUNDARIA,
               opacity=.75),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=agg["Mês"], y=agg["Inscritos"],
                   name="Inscritos", mode="lines+markers",
                   line=dict(color=COR_ACENTO, width=2.5),
                   marker=dict(size=6)),
        secondary_y=True,
    )
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text="Evolução Mensal", font=dict(size=14, color=COR_PRIMARIA)),
        height=280,
        legend=dict(orientation="h", y=1.12),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False, title="Nº Ações"),
        yaxis2=dict(showgrid=False, title="Inscritos"),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Secção: Top ações ─────────────────────────────────────────────────────────

def tabela_top_acoes(df: pd.DataFrame, n: int = 10):
    cols_req = ["Ação", "Centro", "Inscritos", "Concluídos", "Aprovados", "Status"]
    cols_ok  = [c for c in cols_req if c in df.columns]
    if not cols_ok:
        st.info("Colunas necessárias não disponíveis para mostrar top ações.")
        return

    # Ordenar e selecionar top n
    df_top = (df[cols_ok]
              .sort_values("Inscritos", ascending=False)
              .head(n)
              .reset_index(drop=True))

    # Calcular % Conclusão (se possível)
    if "Inscritos" in df_top.columns and "Concluídos" in df_top.columns:
        # Evitar divisão por zero e tratar NaNs
        df_top["% Conclusão"] = (
            (df_top["Concluídos"] / df_top["Inscritos"]) * 100
        ).round(1).fillna(0).astype(str) + "%"

    # Determinar o valor máximo para a barra de progresso (evitar NaN)
    max_inscritos = df_top["Inscritos"].max()
    if pd.isna(max_inscritos):
        max_inscritos = 100  # valor padrão se não houver dados válidos

    st.dataframe(
        df_top,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Inscritos":  st.column_config.ProgressColumn(
                "Inscritos",
                min_value=0,
                max_value=int(max_inscritos),  # agora seguro
                format="%d"
            ),
            "% Conclusão": st.column_config.TextColumn("% Conclusão"),
        },
    )

def aplicar_filtros_dashboard(df: pd.DataFrame) -> pd.DataFrame:
    with st.sidebar:
        st.markdown(
            f'<h3 style="color:{COR_PRIMARIA};margin-bottom:4px;">🔍 Filtros</h3>',
            unsafe_allow_html=True,
        )
        st.markdown("---")

        # ---------- 1. Status ----------
        if "Status" in df.columns:
            opcoes_status = ["Todos"] + sorted(df["Status"].dropna().unique().tolist())
            status_sel = st.multiselect("Estado da Ação", opcoes_status[1:],
                                        default=opcoes_status[1:],
                                        key="dash_status")
            if status_sel:
                df = df[df["Status"].isin(status_sel)]

        # ---------- 2. Tipo de Ação (corrigido, sem duplicação) ----------
        # Cria a coluna "Tipo" apenas se não existir e se a coluna "Ação" existir
        if "Tipo" not in df.columns and "Ação" in df.columns:
            def extrair_tipo(nome_acao: str) -> str:
                """Extrai o tipo: 4 caracteres, mas se o 4º for '_' devolve só 3."""
                nome_acao = str(nome_acao)
                if len(nome_acao) >= 4 and nome_acao[3] == '_':
                    return nome_acao[:3]
                else:
                    return nome_acao[:4]
            df["Tipo"] = df["Ação"].astype(str).apply(extrair_tipo)

        # Se a coluna "Tipo" existe (foi criada ou já estava), mostra o filtro
        if "Tipo" in df.columns:
            tipos_disponiveis = sorted(df["Tipo"].dropna().unique().tolist())
            if tipos_disponiveis:
                tipo_sel = st.multiselect("Tipo de Ação", tipos_disponiveis,
                                          default=tipos_disponiveis,
                                          key="dash_tipo")   # chave única
                if tipo_sel:
                    df = df[df["Tipo"].isin(tipo_sel)]

        # ---------- 3. Formador ----------
        if "Formador" in df.columns:
            formadores = sorted(df["Formador"].dropna().unique().tolist())
            if formadores:
                formador_sel = st.multiselect("Formador", formadores,
                                              default=formadores,
                                              key="dash_formador")
                if formador_sel:
                    df = df[df["Formador"].isin(formador_sel)]

        # ---------- 4. Centro ----------
        if "Centro" in df.columns:
            opcoes_centro = sorted(df["Centro"].dropna().unique().tolist())
            centro_sel = st.multiselect("Centro", opcoes_centro,
                                        default=opcoes_centro,
                                        key="dash_centro")
            if centro_sel:
                df = df[df["Centro"].isin(centro_sel)]

        # ---------- 5. Intervalo de datas (CORRIGIDO) ----------
        todas_datas = pd.Series(dtype='datetime64[ns]')
        if "Data Inicial" in df.columns:
            todas_datas = pd.concat([todas_datas, df["Data Inicial"].dropna()])
        if "Data Final" in df.columns:
            todas_datas = pd.concat([todas_datas, df["Data Final"].dropna()])
        
        if not todas_datas.empty:
            dmin = todas_datas.min().date()
            dmax = todas_datas.max().date()
            
            intervalo = st.date_input(
                "Período (Data Inicial ou Final)",
                value=(dmin, dmax),
                min_value=dmin,
                max_value=dmax,
                key="dash_datas"
            )
            if isinstance(intervalo, (list, tuple)) and len(intervalo) == 2:
                df = df[
                    (df["Data Inicial"].dt.date >= intervalo[0]) &
                    (df["Data Inicial"].dt.date <= intervalo[1])
                ]

        st.markdown("---")
        st.caption(f"🗂 {len(df)} ações filtradas")

    # Remove a coluna auxiliar "Tipo" se foi criada apenas para filtro
    if "Tipo" in df.columns and "Tipo" not in st.session_state.get("acoes_editaveis", pd.DataFrame()).columns:
        df = df.drop(columns=["Tipo"])

    return df
# ── Entry-point ───────────────────────────────────────────────────────────────

def mostrar_dashboard():
    # ── Cabeçalho ──
    st.markdown(
        f"""
        <div style="
            background:linear-gradient(135deg,{COR_PRIMARIA},{COR_SECUNDARIA});
            border-radius:16px;padding:28px 32px;margin-bottom:28px;
            box-shadow:0 4px 20px rgba(30,58,95,.2);
        ">
          <h1 style="margin:0;color:white;font-size:1.9rem;font-weight:700;">
            📊 Dashboard de Formações
          </h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,.75);font-size:.95rem;">
            Análise interativa — filtre pelo painel lateral
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Verificar dados ──
    df_raw = st.session_state.get("acoes_editaveis", pd.DataFrame())
    if df_raw.empty:
        st.info("ℹ️ Sem dados disponíveis. Carregue dados na página **Análise de Formações**.")
        return

    df = preparar_dados(df_raw)
    df = aplicar_filtros_dashboard(df)

    if df.empty:
        st.warning("Nenhuma ação corresponde aos filtros seleccionados.")
        return

    # ── KPIs ──
    secao_kpis(df)
    st.markdown("<div style='margin:20px 0'></div>", unsafe_allow_html=True)

    # ── Linha 1: Status + Funil ──
    c1, c2 = st.columns([1, 1.4])
    with c1:
        grafico_status(df)
    with c2:
        grafico_funil(df)

    # ── Linha 2: Timeline ──
    grafico_timeline(df)

    # ── Linha 3: Centro + Top Ações ──
    c3, c4 = st.columns([1, 1.6])
    with c3:
        grafico_por_centro(df)
    with c4:
        st.markdown(
            f'<p style="font-size:.95rem;font-weight:600;color:{COR_PRIMARIA};'
            f'margin-bottom:6px;">🏅 Top Ações por Inscrições</p>',
            unsafe_allow_html=True,
        )
        tabela_top_acoes(df)


if __name__ == "__main__":
    mostrar_dashboard()