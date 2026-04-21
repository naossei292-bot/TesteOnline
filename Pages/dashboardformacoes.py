import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re

# ── Paleta de cores ────────────────────────────────────────────────────────────
COR_PRIMARIA   = "#1E3A5F"
COR_SECUNDARIA = "#2E86AB"
COR_ACENTO     = "#F6AE2D"
COR_SUCESSO    = "#2DC653"
COR_PERIGO     = "#E63946"
COR_NEUTRO     = "#8D99AE"
COR_ROXO       = "#9B5DE5"
GRADIENTE      = ["#1E3A5F", "#2E86AB", "#54C6EB", "#F6AE2D", "#F26419"]

LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Segoe UI, sans-serif", color="#2d2d2d"),
    margin=dict(l=10, r=10, t=40, b=10),
)

# ── Helpers ───────────────────────────────────────────────────────────────────
def preparar_dados(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.drop(columns=["Apagar"], errors="ignore", inplace=True)
    for col in ["Data Inicial", "Data Final"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    colunas_num = [
        "Inscritos", "Aptos", "Inaptos", "Desistentes", "Devedores",
        "Taxa de satisfação Final", "Avaliação formador",
        "Valor total a receber", "Valor Total Recebido",
        "Taxa de Satisfação M01", "Taxa de Satisfação M02", "Taxa de Satisfação M03",
        "Taxa de Satisfação M04", "Taxa de Satisfação M05", "Taxa de Satisfação M06",
        "Taxa de Satisfação M07", "Taxa de Satisfação M08", "Taxa de Satisfação M09",
        "Taxa de Satisfação M10", "Taxa de Satisfação M11", "Taxa de Satisfação M12",
    ]
    for col in colunas_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "Ação" in df.columns:
        df = df[df["Ação"].notna()]
        df = df[df["Ação"].astype(str).str.strip() != ""]
        df = df[~df["Ação"].astype(str).isin(["None", "nan", "NaN"])]
    return df

def safe_sum(df, col):
    if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
        return df[col].sum()
    return 0

def safe_mean(df, col):
    if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
        v = df[col].dropna()
        return v.mean() if not v.empty else 0
    return 0

def taxa(parte, total):
    return round(parte / total * 100, 1) if total > 0 else 0

def fmt_euro(v):
    return f"€{v:,.0f}".replace(",", ".")

def fmt_num(v):
    return f"{v:,.0f}".replace(",", ".")

def cartao_metrica(label, valor, subtexto=None, cor=COR_PRIMARIA, icone="📊"):
    sub_html = f'<p style="margin:4px 0 0;font-size:.75rem;color:{COR_NEUTRO};">{subtexto}</p>' if subtexto else ""
    st.markdown(
        f"""
        <div style="background:white;border-radius:14px;padding:18px 20px;
            border-left:5px solid {cor};box-shadow:0 2px 12px rgba(0,0,0,.07);height:100%;">
          <p style="margin:0 0 4px;font-size:.72rem;color:{COR_NEUTRO};
                    text-transform:uppercase;letter-spacing:.07em;font-weight:600;">
            {icone} {label}
          </p>
          <p style="margin:0;font-size:1.85rem;font-weight:700;color:{cor};line-height:1.1;">
            {valor}
          </p>
          {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Painéis de detalhe (conteúdo das tabelas) ─────────────────────────────────
def painel_detalhe_acoes(df: pd.DataFrame):
    if "Centro" not in df.columns or "Ação" not in df.columns:
        return
    df_centro = df.groupby("Centro")["Ação"].nunique().reset_index()
    df_centro.columns = ["Centro", "Nº Ações"]
    df_centro = df_centro.sort_values("Nº Ações", ascending=False)
    st.markdown("### 📍 Ações por Centro")
    st.dataframe(df_centro, use_container_width=True, hide_index=True)

def painel_detalhe_inscritos(df: pd.DataFrame):
    if "Ação" not in df.columns or "Inscritos" not in df.columns:
        return
    df_top = df[["Ação", "Centro", "Inscritos"]].dropna(subset=["Inscritos"])
    df_top = df_top.sort_values("Inscritos", ascending=False)
    st.markdown("### 🧑‍🎓 Ações ordenadas por Inscritos")
    st.dataframe(df_top, use_container_width=True, hide_index=True)

def painel_detalhe_aptos(df: pd.DataFrame):
    if "Ação" not in df.columns or "Aptos" not in df.columns:
        return
    df_todas = df[["Ação", "Centro", "Aptos"]].dropna(subset=["Aptos"])
    df_todas = df_todas.sort_values("Aptos", ascending=False)
    st.markdown("### ✅ Ações ordenadas por Aptos")
    st.dataframe(df_todas, use_container_width=True, hide_index=True)

def painel_detalhe_inaptos_desistentes(df: pd.DataFrame):
    if "Ação" not in df.columns:
        return
    cols = ["Ação", "Centro"]
    if "Inaptos" in df.columns:
        cols.append("Inaptos")
    if "Desistentes" in df.columns:
        cols.append("Desistentes")
    if "Devedores" in df.columns:
        cols.append("Devedores")
    df_filt = df[cols].copy()
    mask = (df_filt.get("Inaptos", 0) > 0) | (df_filt.get("Desistentes", 0) > 0) | (df_filt.get("Devedores", 0) > 0)
    df_filt = df_filt[mask].sort_values(["Inaptos", "Desistentes", "Devedores"], ascending=False)
    if df_filt.empty:
        st.info("Nenhuma ação com inaptos, desistentes ou devedores.")
        return
    st.markdown("### ⚠️ Ações com Inaptos / Desistentes / Devedores")
    st.dataframe(df_filt, use_container_width=True, hide_index=True)

def painel_detalhe_satisfacao(df: pd.DataFrame):
    col_sat = "Taxa de satisfação Final"
    if col_sat not in df.columns or "Ação" not in df.columns:
        return
    df_sat = df[["Ação", "Centro", col_sat]].dropna(subset=[col_sat])
    if df_sat.empty:
        st.info("Sem dados de satisfação.")
        return
    melhor = df_sat.sort_values(col_sat, ascending=False)
    pior = df_sat.sort_values(col_sat, ascending=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### ⭐ Melhores Taxas de Satisfação")
        st.dataframe(melhor, use_container_width=True, hide_index=True)
    with col2:
        st.markdown("#### ❌ Piores Taxas de Satisfação")
        st.dataframe(pior, use_container_width=True, hide_index=True)

def painel_detalhe_valor_recebido(df: pd.DataFrame):
    if "Valor Total Recebido" not in df.columns or "Ação" not in df.columns:
        return
    cols = ["Ação", "Centro", "Valor Total Recebido"]
    if "Valor total a receber" in df.columns:
        cols.append("Valor total a receber")
    df_val = df[cols].dropna(subset=["Valor Total Recebido"])
    df_val = df_val[df_val["Valor Total Recebido"] > 0]
    df_top = df_val.sort_values("Valor Total Recebido", ascending=False).copy()
    st.markdown("### 💰 Ações com maior valor recebido")
    df_top["Valor Total Recebido"] = df_top["Valor Total Recebido"].apply(lambda x: f"€{x:,.0f}".replace(",", "."))
    if "Valor total a receber" in df_top.columns:
        df_top["Valor total a receber"] = df_top["Valor total a receber"].apply(lambda x: f"€{x:,.0f}".replace(",", ".") if pd.notna(x) else "—")
    st.dataframe(df_top, use_container_width=True, hide_index=True)

# ── KPIs com exclusão mútua (apenas um painel aberto de cada vez) ─────────────
def secao_kpis(df: pd.DataFrame):
    total_acoes     = df["Ação"].nunique() if "Ação" in df.columns else 0
    total_inscritos = safe_sum(df, "Inscritos")
    total_aptos     = safe_sum(df, "Aptos")
    total_inaptos   = safe_sum(df, "Inaptos")
    total_desist    = safe_sum(df, "Desistentes")
    total_deved     = safe_sum(df, "Devedores")
    t_aprovacao     = taxa(total_aptos, total_inscritos)
    media_sat       = safe_mean(df, "Taxa de satisfação Final")
    media_form      = safe_mean(df, "Avaliação formador")
    valor_receber   = safe_sum(df, "Valor total a receber")
    valor_recebido  = safe_sum(df, "Valor Total Recebido")
    t_cobranca      = taxa(valor_recebido, valor_receber)

    # Inicializar estados
    if "mostrar_acoes" not in st.session_state:
        st.session_state.mostrar_acoes = False
    if "mostrar_inscritos" not in st.session_state:
        st.session_state.mostrar_inscritos = False
    if "mostrar_aptos" not in st.session_state:
        st.session_state.mostrar_aptos = False
    if "mostrar_inaptos_desist" not in st.session_state:
        st.session_state.mostrar_inaptos_desist = False
    if "mostrar_satisfacao" not in st.session_state:
        st.session_state.mostrar_satisfacao = False
    if "mostrar_valor" not in st.session_state:
        st.session_state.mostrar_valor = False

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        if st.button(f"🎓 Ações\n\n{fmt_num(total_acoes)}", key="btn_acoes", use_container_width=True,
                     help="Clique para ver distribuição por centro"):
            st.session_state.mostrar_inscritos = False
            st.session_state.mostrar_aptos = False
            st.session_state.mostrar_inaptos_desist = False
            st.session_state.mostrar_satisfacao = False
            st.session_state.mostrar_valor = False
            st.session_state.mostrar_acoes = not st.session_state.mostrar_acoes
            st.rerun()
    with c2:
        if st.button(f"👥 Inscritos\n\n{fmt_num(total_inscritos)}", key="btn_inscritos", use_container_width=True,
                     help="Clique para ver as ações com mais inscritos"):
            st.session_state.mostrar_acoes = False
            st.session_state.mostrar_aptos = False
            st.session_state.mostrar_inaptos_desist = False
            st.session_state.mostrar_satisfacao = False
            st.session_state.mostrar_valor = False
            st.session_state.mostrar_inscritos = not st.session_state.mostrar_inscritos
            st.rerun()
    with c3:
        if st.button(f"✅ Aptos\n\n{fmt_num(total_aptos)}\nTaxa: {t_aprovacao}%", key="btn_aptos", use_container_width=True,
                     help="Clique para ver as ações com mais aptos"):
            st.session_state.mostrar_acoes = False
            st.session_state.mostrar_inscritos = False
            st.session_state.mostrar_inaptos_desist = False
            st.session_state.mostrar_satisfacao = False
            st.session_state.mostrar_valor = False
            st.session_state.mostrar_aptos = not st.session_state.mostrar_aptos
            st.rerun()
    with c4:
        if st.button(f"⚠️ Inaptos / Desist.\n\n{fmt_num(total_inaptos)} / {fmt_num(total_desist)}\nDevedores: {fmt_num(total_deved)}",
                     key="btn_inaptos", use_container_width=True, help="Clique para ver ações com inaptos ou desistentes"):
            st.session_state.mostrar_acoes = False
            st.session_state.mostrar_inscritos = False
            st.session_state.mostrar_aptos = False
            st.session_state.mostrar_satisfacao = False
            st.session_state.mostrar_valor = False
            st.session_state.mostrar_inaptos_desist = not st.session_state.mostrar_inaptos_desist
            st.rerun()
    with c5:
        if st.button(f"⭐ Satisfação Final\n\n{media_sat:.2f}" if media_sat else "—", key="btn_satisfacao",
                     use_container_width=True, help=f"Clique para ver melhores/piores satisfações\nAvaliação formador: {media_form:.2f}" if media_form else None):
            st.session_state.mostrar_acoes = False
            st.session_state.mostrar_inscritos = False
            st.session_state.mostrar_aptos = False
            st.session_state.mostrar_inaptos_desist = False
            st.session_state.mostrar_valor = False
            st.session_state.mostrar_satisfacao = not st.session_state.mostrar_satisfacao
            st.rerun()
    with c6:
        if st.button(f"💶 Valor Recebido\n\n{fmt_euro(valor_recebido)}\nCobrança: {t_cobranca}%", key="btn_valor",
                     use_container_width=True, help=f"Clique para ver ações com maior recebimento\nEsperado: {fmt_euro(valor_receber)}"):
            st.session_state.mostrar_acoes = False
            st.session_state.mostrar_inscritos = False
            st.session_state.mostrar_aptos = False
            st.session_state.mostrar_inaptos_desist = False
            st.session_state.mostrar_satisfacao = False
            st.session_state.mostrar_valor = not st.session_state.mostrar_valor
            st.rerun()

    # Exibir apenas o painel que está ativo
    if st.session_state.mostrar_acoes:
        with st.expander("📌 Detalhe: Ações por Centro", expanded=True):
            painel_detalhe_acoes(df)
    if st.session_state.mostrar_inscritos:
        with st.expander("📌 Detalhe: Top Inscritos", expanded=True):
            painel_detalhe_inscritos(df)
    if st.session_state.mostrar_aptos:
        with st.expander("📌 Detalhe: Top Aptos", expanded=True):
            painel_detalhe_aptos(df)
    if st.session_state.mostrar_inaptos_desist:
        with st.expander("📌 Detalhe: Inaptos / Desistentes", expanded=True):
            painel_detalhe_inaptos_desistentes(df)
    if st.session_state.mostrar_satisfacao:
        with st.expander("📌 Detalhe: Satisfação (melhores/piores)", expanded=True):
            painel_detalhe_satisfacao(df)
    if st.session_state.mostrar_valor:
        with st.expander("📌 Detalhe: Valor Recebido (top)", expanded=True):
            painel_detalhe_valor_recebido(df)

# ── Gráfico de Estado (com clique funcional) ─────────────────────────────────
def grafico_status(df: pd.DataFrame):
    if "Status" not in df.columns:
        return None
    counts = df["Status"].value_counts().reset_index()
    counts.columns = ["Status", "Total"]

    cores_status = {
        "Finalizado": COR_SUCESSO,  "FINALIZADA": COR_SUCESSO,
        "Em curso":   COR_SECUNDARIA, "ABERTA":  COR_SECUNDARIA,
        "Cancelado":  COR_PERIGO,   "CANCELADA":  COR_PERIGO,
        "Suspenso":   COR_ACENTO,   "SUSPENSA":   COR_ACENTO,
    }
    cor_lista = [cores_status.get(s, COR_NEUTRO) for s in counts["Status"]]

    fig = go.Figure(go.Pie(
        labels=counts["Status"], values=counts["Total"],
        hole=.58,
        marker=dict(colors=cor_lista, line=dict(color="white", width=2)),
        textinfo="label+percent", textfont=dict(size=11),
        customdata=counts["Status"],
        hovertemplate="<b>%{label}</b><br>Total: %{value}<br>Percent: %{percent}<br><i>Clique para ver detalhe</i><extra></extra>"
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text="Estado das Ações", font=dict(size=14, color=COR_PRIMARIA)),
        showlegend=False, height=260,
        clickmode="event",
    )
    st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="status_chart")
    
    selecao = st.session_state.get("status_chart", {}).get("selection", {})
    estado_selecionado = st.session_state.get("estado_selecionado", None)
    
    if selecao and selecao.get("points"):
        ponto = selecao["points"][0]
        label = ponto.get("label")
        if label:
            if estado_selecionado == label:
                st.session_state.estado_selecionado = None
            else:
                st.session_state.estado_selecionado = label
            st.session_state["status_chart"]["selection"] = {}
            st.rerun()
    
    return st.session_state.get("estado_selecionado")

def painel_detalhe_estado(df: pd.DataFrame, estado: str):
    if estado is None:
        return
    df_estado = df[df["Status"] == estado].copy()
    if df_estado.empty:
        st.info(f"Nenhuma ação com estado '{estado}'.")
        return
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,{COR_PRIMARIA}12,{COR_SECUNDARIA}18);
            border:1.5px solid {COR_SECUNDARIA}55; border-radius:14px; padding:16px 22px; margin:14px 0 10px;">
          <h3 style="margin:0;color:{COR_PRIMARIA};font-size:1.05rem;font-weight:700;">
            📋 Ações com estado <strong>{estado}</strong>
            <span style="font-size:.78rem;color:{COR_NEUTRO};font-weight:400;margin-left:8px;">
              Clique novamente na fatia para fechar
            </span>
          </h3>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols_mostrar = [c for c in ["Centro", "Ação", "Status", "Inscritos", "Aptos", "Taxa de satisfação Final"] if c in df_estado.columns]
    df_show = df_estado[cols_mostrar].reset_index(drop=True)
    st.dataframe(df_show, use_container_width=True, hide_index=True)
    st.markdown("---")

# ── Gráfico Funil ────────────────────────────────────────────────────────────
def grafico_funil(df: pd.DataFrame):
    inscritos = safe_sum(df, "Inscritos")
    aptos     = safe_sum(df, "Aptos")
    inaptos   = safe_sum(df, "Inaptos")
    desist    = safe_sum(df, "Desistentes")
    deved     = safe_sum(df, "Devedores")
    stages = [
        ("Inscritos",   inscritos, COR_SECUNDARIA),
        ("Aptos",       aptos,     COR_SUCESSO),
        ("Inaptos",     inaptos,   COR_PERIGO),
        ("Desistentes", desist,    COR_ACENTO),
        ("Devedores",   deved,     COR_ROXO),
    ]
    fig = go.Figure(go.Funnel(
        y=[s[0] for s in stages],
        x=[s[1] for s in stages],
        marker=dict(color=[s[2] for s in stages], line=dict(color="white", width=1)),
        textinfo="value+percent initial",
        textfont=dict(size=12),
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text="Distribuição de Participantes", font=dict(size=14, color=COR_PRIMARIA)),
        height=280,
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Timeline ─────────────────────────────────────────────────────────────────
def grafico_timeline(df: pd.DataFrame):
    if "Data Inicial" not in df.columns or df["Data Inicial"].isna().all():
        return None
    df_t = df.dropna(subset=["Data Inicial"]).copy()
    df_t["Mês"] = df_t["Data Inicial"].dt.to_period("M").dt.to_timestamp()
    agg = (df_t.groupby("Mês")
               .agg(Ações=("Ação", "count"),
                    Inscritos=("Inscritos", "sum"),
                    Aptos=("Aptos", "sum"))
               .reset_index())
    mes_sel = st.session_state.get("timeline_mes_selecionado")
    if mes_sel is not None:
        cores_barras = [COR_ACENTO if m == mes_sel else COR_SECUNDARIA for m in agg["Mês"]]
        opacidades   = [1.0 if m == mes_sel else 0.4 for m in agg["Mês"]]
    else:
        cores_barras = [COR_SECUNDARIA] * len(agg)
        opacidades   = [0.7] * len(agg)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=agg["Mês"], y=agg["Ações"], name="Nº Ações",
                         marker=dict(color=cores_barras, opacity=opacidades),
                         hovertemplate="<b>%{x|%b %Y}</b><br>Ações: %{y}<br><i>Clique para ver detalhe</i><extra></extra>"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=agg["Mês"], y=agg["Inscritos"], name="Inscritos", mode="lines+markers",
                             line=dict(color=COR_ACENTO, width=2.5), marker=dict(size=6)), secondary_y=True)
    fig.add_trace(go.Scatter(x=agg["Mês"], y=agg["Aptos"], name="Aptos", mode="lines+markers",
                             line=dict(color=COR_SUCESSO, width=2, dash="dot"), marker=dict(size=5)), secondary_y=True)
    fig.add_annotation(text="💡 Clique numa barra para ver o detalhe do mês", xref="paper", yref="paper",
                       x=1, y=1.18, showarrow=False, font=dict(size=10, color=COR_NEUTRO), align="right")
    fig.update_layout(**LAYOUT_BASE, title=dict(text="Evolução Mensal — Ações, Inscritos e Aptos",
                      font=dict(size=14, color=COR_PRIMARIA)), height=310, legend=dict(orientation="h", y=1.12),
                      xaxis=dict(showgrid=False), yaxis=dict(showgrid=False, title="Nº Ações"),
                      yaxis2=dict(showgrid=False, title="Participantes"), clickmode="event")
    st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="timeline_chart")
    
    selecao = st.session_state.get("timeline_chart", {}).get("selection", {})
    if selecao and selecao.get("points"):
        ponto = selecao["points"][0]
        x_val = ponto.get("x")
        if x_val:
            try:
                mes_clicado = pd.Timestamp(x_val)
                if mes_sel is not None and mes_clicado == mes_sel:
                    st.session_state.timeline_mes_selecionado = None
                else:
                    st.session_state.timeline_mes_selecionado = mes_clicado
                st.session_state["timeline_chart"]["selection"] = {}
                st.rerun()
            except Exception:
                pass
    return st.session_state.get("timeline_mes_selecionado")

def painel_detalhe_mes(df: pd.DataFrame, mes: pd.Timestamp):
    if "Data Inicial" not in df.columns:
        return
    nome_mes = mes.strftime("%B %Y").capitalize()
    df_mes = df[df["Data Inicial"].dt.to_period("M").dt.to_timestamp() == mes].copy()
    if df_mes.empty:
        return
    st.markdown(f"""<div style="background:linear-gradient(135deg,{COR_PRIMARIA}12,{COR_SECUNDARIA}18);
                border:1.5px solid {COR_SECUNDARIA}55; border-radius:14px; padding:16px 22px; margin:14px 0 10px;">
                <h3 style="margin:0;color:{COR_PRIMARIA};font-size:1.05rem;font-weight:700;">
                📅 Detalhe — <strong>{nome_mes}</strong>
                <span style="font-size:.78rem;color:{COR_NEUTRO};font-weight:400;margin-left:8px;">
                Clique novamente na barra para fechar</span></h3></div>""", unsafe_allow_html=True)
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        n_acoes = df_mes["Ação"].nunique() if "Ação" in df_mes.columns else len(df_mes)
        cartao_metrica("Ações", str(n_acoes), icone="🎓", cor=COR_PRIMARIA)
    with k2:
        cartao_metrica("Inscritos", fmt_num(safe_sum(df_mes, "Inscritos")), icone="👥", cor=COR_SECUNDARIA)
    with k3:
        ins = safe_sum(df_mes, "Inscritos")
        apt = safe_sum(df_mes, "Aptos")
        cartao_metrica("Aptos", fmt_num(apt), subtexto=f"Taxa: {taxa(apt, ins)}%", icone="✅", cor=COR_SUCESSO)
    with k4:
        cartao_metrica("Inaptos / Desist.", f"{fmt_num(safe_sum(df_mes,'Inaptos'))} / {fmt_num(safe_sum(df_mes,'Desistentes'))}",
                       icone="⚠️", cor=COR_PERIGO)
    with k5:
        media_s = safe_mean(df_mes, "Taxa de satisfação Final")
        cartao_metrica("Satisfação Média", f"{media_s:.2f}" if media_s else "—", icone="⭐", cor=COR_ACENTO)
    st.markdown("<div style='margin:10px 0'></div>", unsafe_allow_html=True)
    cols_mostrar = [c for c in [
        "Ação", "Centro", "Status", "Formador", "Data Inicial", "Data Final",
        "Inscritos", "Aptos", "Inaptos", "Desistentes",
        "Taxa de satisfação Final", "Avaliação formador",
        "Valor total a receber", "Valor Total Recebido",
    ] if c in df_mes.columns]
    df_show = df_mes[cols_mostrar].reset_index(drop=True)
    for col_data in ["Data Inicial", "Data Final"]:
        if col_data in df_show.columns:
            df_show[col_data] = df_show[col_data].dt.strftime("%d/%m/%Y")
    col_cfg = {}
    if "Inscritos" in df_show.columns:
        max_ins = df_show["Inscritos"].max()
        if pd.notna(max_ins) and max_ins > 0:
            col_cfg["Inscritos"] = st.column_config.ProgressColumn("Inscritos", min_value=0, max_value=int(max_ins), format="%d")
    if "Taxa de satisfação Final" in df_show.columns:
        col_cfg["Taxa de satisfação Final"] = st.column_config.NumberColumn("Satisfação", format="%.2f")
    if "Valor total a receber" in df_show.columns:
        col_cfg["Valor total a receber"] = st.column_config.NumberColumn("€ A Receber", format="€%.0f")
    if "Valor Total Recebido" in df_show.columns:
        col_cfg["Valor Total Recebido"] = st.column_config.NumberColumn("€ Recebido", format="€%.0f")
    st.dataframe(df_show, use_container_width=True, hide_index=True, column_config=col_cfg,
                 height=min(420, 55 + len(df_show) * 35))
    st.markdown("---")

# ── Gráficos de Avaliação e Receita ───────────────────────────────────────────
def grafico_avaliacao_formador(df: pd.DataFrame):
    if "Formador" not in df.columns or "Avaliação formador" not in df.columns:
        return
    df_f = (df.groupby("Formador")["Avaliação formador"].mean().dropna().sort_values(ascending=True).reset_index())
    df_f.columns = ["Formador", "Avaliação"]
    if df_f.empty:
        return
    cores = [COR_SUCESSO if v >= 4 else (COR_ACENTO if v >= 3 else COR_PERIGO) for v in df_f["Avaliação"]]
    fig = go.Figure(go.Bar(x=df_f["Avaliação"], y=df_f["Formador"], orientation="h", marker_color=cores,
                           text=df_f["Avaliação"].round(2), textposition="outside"))
    fig.update_layout(**LAYOUT_BASE, title=dict(text="Avaliação Média por Formador", font=dict(size=14, color=COR_PRIMARIA)),
                      height=max(220, len(df_f) * 36), xaxis=dict(showgrid=False, visible=False, range=[0, 5.5]),
                      yaxis=dict(showgrid=False))
    st.plotly_chart(fig, use_container_width=True)

def grafico_receita(df: pd.DataFrame):
    if "Valor total a receber" not in df.columns or "Valor Total Recebido" not in df.columns or "Centro" not in df.columns:
        return
    agg = (df.groupby("Centro").agg(Receber=("Valor total a receber", "sum"), Recebido=("Valor Total Recebido", "sum"))
           .sort_values("Receber", ascending=True).reset_index())
    agg = agg[(agg["Receber"] > 0) | (agg["Recebido"] > 0)]
    if agg.empty:
        return
    fig = go.Figure()
    fig.add_trace(go.Bar(x=agg["Receber"], y=agg["Centro"], orientation="h", name="A Receber",
                         marker_color=COR_NEUTRO, opacity=.5, text=agg["Receber"].apply(fmt_euro), textposition="outside"))
    fig.add_trace(go.Bar(x=agg["Recebido"], y=agg["Centro"], orientation="h", name="Recebido",
                         marker_color=COR_SUCESSO, opacity=.85, text=agg["Recebido"].apply(fmt_euro), textposition="outside"))
    fig.update_layout(**LAYOUT_BASE, title=dict(text="Receita: Esperada vs Recebida por Centro", font=dict(size=14, color=COR_PRIMARIA)),
                      barmode="overlay", height=max(230, len(agg) * 40), xaxis=dict(showgrid=False, visible=False),
                      yaxis=dict(showgrid=False), legend=dict(orientation="h", y=1.12))
    st.plotly_chart(fig, use_container_width=True)

# ── TABELA GERAL (substitui a antiga "Top Ações") ─────────────────────────────
def tabela_geral_acoes(df: pd.DataFrame):
    """
    Exibe a tabela completa de todas as ações (após filtros) com possibilidade de selecionar colunas.
    """
    if df.empty:
        st.info("Nenhum dado para exibir.")
        return

    # Lista de colunas disponíveis (excluímos colunas que não interessam)
    colunas_excluir = ["Apagar", "_Tipo", "Data Inicial", "Data Final"]  # Data serão tratadas à parte
    colunas_disponiveis = [c for c in df.columns if c not in colunas_excluir and not c.startswith("_")]

    # Se existirem colunas de data, adicionamo‑las formatadas
    colunas_data = []
    for data_col in ["Data Inicial", "Data Final"]:
        if data_col in df.columns:
            colunas_data.append(data_col)
            colunas_disponiveis.append(data_col)  # para aparecer na seleção

    # Ordenar colunas para melhor apresentação
    colunas_disponiveis.sort()

    st.markdown("---")
    st.markdown(f'<p style="font-size:.95rem;font-weight:600;color:{COR_PRIMARIA};margin-bottom:6px;">📋 Todas as Ações ({len(df)} registos)</p>', unsafe_allow_html=True)

    # Seletor de colunas
    colunas_selecionadas = st.multiselect(
        "Escolha as colunas a exibir:",
        options=colunas_disponiveis,
        default=colunas_disponiveis[:10],  # mostra as primeiras 10 por padrão
        key="tabela_geral_colunas"
    )

    if not colunas_selecionadas:
        st.warning("Selecione pelo menos uma coluna.")
        return

    # Construir DataFrame a exibir
    df_exibir = df[colunas_selecionadas].copy()

    # Formatar colunas de data (se estiverem presentes e forem datetime)
    for data_col in colunas_data:
        if data_col in df_exibir.columns and pd.api.types.is_datetime64_any_dtype(df_exibir[data_col]):
            df_exibir[data_col] = df_exibir[data_col].dt.strftime("%d/%m/%Y")

    # Formatar valores monetários (colunas que começam com "Valor")
    for col in df_exibir.columns:
        if "Valor" in col and pd.api.types.is_numeric_dtype(df_exibir[col]):
            df_exibir[col] = df_exibir[col].apply(lambda x: fmt_euro(x) if pd.notna(x) else "—")

    # Configuração de colunas para o st.dataframe
    column_config = {}
    for col in df_exibir.columns:
        if col in ["Inscritos", "Aptos", "Inaptos", "Desistentes", "Devedores"]:
            max_val = df_exibir[col].max() if pd.api.types.is_numeric_dtype(df_exibir[col]) else 100
            if pd.notna(max_val) and max_val > 0:
                column_config[col] = st.column_config.ProgressColumn(
                    col, min_value=0, max_value=int(max_val), format="%d"
                )
        elif "satisfação" in col.lower() or "Satisfação" in col:
            column_config[col] = st.column_config.NumberColumn(col, format="%.2f")
        elif "Avaliação" in col:
            column_config[col] = st.column_config.NumberColumn(col, format="%.2f")

    # Exibir tabela com scroll e ordenação interativa
    st.dataframe(
        df_exibir,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
        height=min(600, 35 + len(df_exibir) * 35)
    )

# ── Filtros na sidebar ────────────────────────────────────────────────────────
def aplicar_filtros_dashboard(df: pd.DataFrame) -> pd.DataFrame:
    with st.sidebar:
        st.markdown(f'<h3 style="color:{COR_PRIMARIA};margin-bottom:4px;">🔍 Filtros</h3>', unsafe_allow_html=True)
        st.markdown("---")
        if "Status" in df.columns:
            opts = sorted(df["Status"].dropna().unique().tolist())
            sel = st.multiselect("Estado da Ação", opts, default=opts, key="dash_status")
            if sel:
                df = df[df["Status"].isin(sel)]
        if "Ação" in df.columns:
            def extrair_tipo(nome):
                nome = str(nome)
                if len(nome) >= 4 and nome[3] == '_':
                    return nome[:3]
                return nome[:4]
            df = df.copy()
            df["_Tipo"] = df["Ação"].astype(str).apply(extrair_tipo)
            tipos = sorted(df["_Tipo"].dropna().unique().tolist())
            if tipos:
                tipo_sel = st.multiselect("Tipo de Ação", tipos, default=tipos, key="dash_tipo")
                if tipo_sel:
                    df = df[df["_Tipo"].isin(tipo_sel)]
            df = df.drop(columns=["_Tipo"])
        if "Centro" in df.columns:
            opts = sorted(df["Centro"].dropna().unique().tolist())
            sel = st.multiselect("Centro", opts, default=opts, key="dash_centro")
            if sel:
                df = df[df["Centro"].isin(sel)]
        if "Formador" in df.columns:
            opts = sorted(df["Formador"].dropna().unique().tolist())
            if opts:
                sel = st.multiselect("Formador", opts, default=opts, key="dash_formador")
                if sel:
                    df = df[df["Formador"].isin(sel)]
        todas_datas = pd.Series(dtype="datetime64[ns]")
        for col in ["Data Inicial", "Data Final"]:
            if col in df.columns:
                todas_datas = pd.concat([todas_datas, df[col].dropna()])
        if not todas_datas.empty:
            dmin = todas_datas.min().date()
            dmax = todas_datas.max().date()
            intervalo = st.date_input("Período (Data Inicial)", value=(dmin, dmax), min_value=dmin, max_value=dmax, key="dash_datas")
            if isinstance(intervalo, (list, tuple)) and len(intervalo) == 2:
                di = df["Data Inicial"].dt.date if "Data Inicial" in df.columns else None
                if di is not None:
                    df = df[(di >= intervalo[0]) & (di <= intervalo[1])]
        st.markdown("---")
        st.caption(f"🗂 {len(df)} ações filtradas")
    return df

# ── Dashboard principal ───────────────────────────────────────────────────────
def mostrar_dashboard():
    st.markdown("""
        <style>
            div[data-testid="stButton"] button {
                background-color: white; border-left: 5px solid #1E3A5F;
                border-radius: 14px; padding: 18px 20px;
                box-shadow: 0 2px 12px rgba(0,0,0,.07); height: 100%;
                text-align: left; white-space: pre-line;
                font-family: 'Segoe UI', sans-serif;
            }
            div[data-testid="stButton"] button p { margin: 0; font-size: 1rem; }
            div[data-testid="stButton"] button .st-emotion-cache-1v0mbdj {
                font-size: 2.2rem !important; font-weight: 700 !important; line-height: 1.2 !important;
            }
            .stMarkdown div div p:first-of-type { font-size: 1rem; }
            .stMarkdown div div p:last-of-type { font-size: 2.2rem !important; font-weight: 700; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""<div style="background:linear-gradient(135deg,{COR_PRIMARIA},{COR_SECUNDARIA});
                border-radius:16px;padding:28px 32px;margin-bottom:28px;box-shadow:0 4px 20px rgba(30,58,95,.2);">
                <h1 style="margin:0;color:white;font-size:1.9rem;font-weight:700;">📊 Dashboard de Formações</h1>
                <p style="margin:6px 0 0;color:rgba(255,255,255,.75);font-size:.95rem;">
                Análise interativa — filtre pelo painel lateral</p></div>""", unsafe_allow_html=True)

    df_raw = st.session_state.get("acoes_editaveis", pd.DataFrame())
    if df_raw.empty:
        st.info("ℹ️ Sem dados disponíveis. Carregue dados na página **Análise de Formações**.")
        return

    df = preparar_dados(df_raw)
    df = aplicar_filtros_dashboard(df)
    if df.empty:
        st.warning("Nenhuma ação corresponde aos filtros seleccionados.")
        return

    secao_kpis(df)
    st.markdown("---")

    c1, c2 = st.columns([1, 1.4])
    with c1:
        estado_sel = grafico_status(df)
        if estado_sel is not None:
            painel_detalhe_estado(df, estado_sel)
    with c2:
        grafico_funil(df)
    st.markdown("---")

    mes_selecionado = grafico_timeline(df)
    if mes_selecionado is not None:
        painel_detalhe_mes(df, mes_selecionado)
    st.markdown("---")

    c5, c6 = st.columns([1.2, 1])
    with c5:
        grafico_receita(df)
    with c6:
        grafico_avaliacao_formador(df)

    # Nova tabela geral (em vez do antigo top 10)
    tabela_geral_acoes(df)

if __name__ == "__main__":
    mostrar_dashboard()