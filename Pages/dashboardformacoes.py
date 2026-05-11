import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, datetime, timedelta

# ── Helpers ───────────────────────────────────────────────────────────────────
def normalizar_colunas_dashboard(df: pd.DataFrame) -> pd.DataFrame:
    mapeamento = {"Devedor": "Devedores"}
    df = df.rename(columns={k: v for k, v in mapeamento.items() if k in df.columns})
    return df

def preparar_dados(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = normalizar_colunas_dashboard(df)
    df.drop(columns=["Apagar"], errors="ignore", inplace=True)
    for col in ["Data Inicial", "Data Final"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    colunas_num = [
        "Inscritos", "Aptos", "Inaptos", "Desistentes","Devedores"
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

def normalizar_status_para_grafico(df: pd.DataFrame) -> pd.Series:
    """
    Retorna uma Series com os status normalizados para:
        - 'Finalizada' ← 'FINALIZADA' e 'FECHADA' (maiúsculas/minúsculas)
        - 'Cancelada'  ← 'Cancelada' e 'CANCELADA'
        - Os restantes mantêm o valor original.
    """
    if "Status" not in df.columns:
        return df["Status"] if "Status" in df.columns else pd.Series()
    
    status_norm = df["Status"].astype(str).str.strip().copy()
    
    # Mapeamento (case‑insensitive)
    mapping = {
        "finalizada": "Finalizada",
        "fechada": "Finalizada",
        "cancelada": "Cancelada",
        "CANCELADA": "Cancelada"   # se já existir exactamente assim
    }
    # Aplica mapeamento (convertemos para minúsculas para comparação)
    status_norm = status_norm.apply(
        lambda x: mapping.get(x.lower(), x)
    )
    return status_norm

# ── Painéis de detalhe ────────────────────────────────────────────────────────
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

def painel_detalhe_inaptos_desistentes(df: pd.DataFrame):  # COMENTADO — envolve Inaptos, Desistentes, Devedores
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
    st.markdown("#### 🎯 Divisão por Objetivo de Satisfação")
    valor_min = df_sat[col_sat].min()
    valor_max = df_sat[col_sat].max()
    objetivo = st.slider(
        "Defina o objetivo (valor mínimo para considerar 'acima'):",
        min_value=float(valor_min),
        max_value=float(valor_max),
        value=3.0,
        step=0.1,
        key="objetivo_satisfacao"
    )
    df_acima = df_sat[df_sat[col_sat] >= objetivo].sort_values(col_sat, ascending=False)
    df_abaixo = df_sat[df_sat[col_sat] < objetivo].sort_values(col_sat, ascending=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"#### ✅ Acima do objetivo (≥ {objetivo})")
        if df_acima.empty:
            st.info("Nenhuma ação atinge este objetivo.")
        else:
            st.dataframe(df_acima, use_container_width=True, hide_index=True)
    with col2:
        st.markdown(f"#### ❌ Abaixo do objetivo (< {objetivo})")
        if df_abaixo.empty:
            st.info("Nenhuma ação está abaixo deste objetivo.")
        else:
            st.dataframe(df_abaixo, use_container_width=True, hide_index=True)

def painel_detalhe_valor_recebido(df: pd.DataFrame):
    if "Valor Total Recebido" not in df.columns or "Ação" not in df.columns:
        return
    cols = ["Ação", "Centro", "Valor Total Recebido"]
    if "Valor total a receber" in df.columns:
        cols.append("Valor total a receber")
    df_val = df[cols].dropna(subset=["Valor Total Recebido"])
    df_val = df_val[df_val["Valor Total Recebido"] > 0]
    df_top = df_val.sort_values("Valor Total Recebido", ascending=False).copy()
    st.markdown("### 💰 Valor Recebido e Valor Total a Receber")
    df_top["Valor Total Recebido"] = df_top["Valor Total Recebido"].apply(lambda x: f"€{x:,.0f}".replace(",", "."))
    if "Valor total a receber" in df_top.columns:
        df_top["Valor total a receber"] = df_top["Valor total a receber"].apply(lambda x: f"€{x:,.0f}".replace(",", ".") if pd.notna(x) else "—")
    st.dataframe(df_top, use_container_width=True, hide_index=True)

# ── KPIs ─────────────────────────────────────────────────────────────────────
def secao_kpis(df: pd.DataFrame):
    total_acoes     = df["Ação"].nunique() if "Ação" in df.columns else 0
    total_inscritos = safe_sum(df, "Inscritos")
    total_aptos     = safe_sum(df, "Aptos")
    total_inaptos   = safe_sum(df, "Inaptos")       # COMENTADO
    total_desist    = safe_sum(df, "Desistentes")   # COMENTADO
    total_deved     = safe_sum(df, "Devedores")     # COMENTADO
    t_aprovacao     = taxa(total_aptos, total_inscritos)
    media_sat       = safe_mean(df, "Taxa de satisfação Final")
    media_form      = safe_mean(df, "Avaliação formador")
    valor_receber   = safe_sum(df, "Valor total a receber")
    valor_recebido  = safe_sum(df, "Valor Total Recebido")
    t_cobranca      = taxa(valor_recebido, valor_receber)

    if "mostrar_acoes" not in st.session_state:
        st.session_state.mostrar_acoes = False
    if "mostrar_inscritos" not in st.session_state:
        st.session_state.mostrar_inscritos = False
    if "mostrar_aptos" not in st.session_state:
        st.session_state.mostrar_aptos = False
    if "mostrar_inaptos_desist" not in st.session_state:   # COMENTADO
        st.session_state.mostrar_inaptos_desist = False    # COMENTADO
    if "mostrar_satisfacao" not in st.session_state:
        st.session_state.mostrar_satisfacao = False
    if "mostrar_valor" not in st.session_state:
        st.session_state.mostrar_valor = False

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        if st.button(f"🎓Ações: {fmt_num(total_acoes)}", key="btn_acoes", use_container_width=True):
            st.session_state.mostrar_inscritos = False
            st.session_state.mostrar_aptos = False
            st.session_state.mostrar_inaptos_desist = False   # COMENTADO
            st.session_state.mostrar_satisfacao = False
            st.session_state.mostrar_valor = False
            st.session_state.mostrar_acoes = not st.session_state.mostrar_acoes
            st.rerun()
    with col2:
        if st.button(f"👥Inscritos: {fmt_num(total_inscritos)}", key="btn_inscritos", use_container_width=True):
            st.session_state.mostrar_acoes = False
            st.session_state.mostrar_aptos = False
            st.session_state.mostrar_inaptos_desist = False   # COMENTADO
            st.session_state.mostrar_satisfacao = False
            st.session_state.mostrar_valor = False
            st.session_state.mostrar_inscritos = not st.session_state.mostrar_inscritos
            st.rerun()
    with col3:
        if st.button(f"✅Aptos: {fmt_num(total_aptos)}\n\n 🛃Taxa: {t_aprovacao}%", key="btn_aptos", use_container_width=True):
            st.session_state.mostrar_acoes = False
            st.session_state.mostrar_inscritos = False
            st.session_state.mostrar_inaptos_desist = False   # COMENTADO
            st.session_state.mostrar_satisfacao = False
            st.session_state.mostrar_valor = False
            st.session_state.mostrar_aptos = not st.session_state.mostrar_aptos
            st.rerun()
    with col4:   # COMENTADO — botão Inaptos / Desistentes / Devedores
         if st.button(f"⚠️Desistentes: {fmt_num(total_desist)}\n\n 🙁Inaptos: {fmt_num(total_inaptos)}\n\n 🙎🏼‍♂️Devedores: {fmt_num(total_deved)}",
                      key="btn_inaptos", use_container_width=True):
             st.session_state.mostrar_acoes = False
             st.session_state.mostrar_inscritos = False
             st.session_state.mostrar_aptos = False
             st.session_state.mostrar_satisfacao = False
             st.session_state.mostrar_valor = False
             st.session_state.mostrar_inaptos_desist = not st.session_state.mostrar_inaptos_desist
             st.rerun()
    
    with col5:
        if st.button(f"⭐Satisfação Final: \n\n{media_sat:.2f}" if media_sat else "—", key="btn_satisfacao",
                     use_container_width=True):
            st.session_state.mostrar_acoes = False
            st.session_state.mostrar_inscritos = False
            st.session_state.mostrar_aptos = False
            st.session_state.mostrar_inaptos_desist = False   # COMENTADO
            st.session_state.mostrar_valor = False
            st.session_state.mostrar_satisfacao = not st.session_state.mostrar_satisfacao
            st.rerun()
    
    with col6:
        if st.button(f"💶Valor Recebido: {fmt_euro(valor_recebido)}\n\n 💸Valor A Receber: {fmt_euro(valor_receber)}", key="btn_valor",
                     use_container_width=True):
            st.session_state.mostrar_acoes = False
            st.session_state.mostrar_inscritos = False
            st.session_state.mostrar_aptos = False
            st.session_state.mostrar_inaptos_desist = False   # COMENTADO
            st.session_state.mostrar_satisfacao = False
            st.session_state.mostrar_valor = not st.session_state.mostrar_valor
            st.rerun()

    if st.session_state.mostrar_acoes:
        with st.expander("📌 Detalhe: Ações por Centro", expanded=True):
            painel_detalhe_acoes(df)
    if st.session_state.mostrar_inscritos:
        with st.expander("📌 Detalhe: Top Inscritos", expanded=True):
            painel_detalhe_inscritos(df)
    if st.session_state.mostrar_aptos:
        with st.expander("📌 Detalhe: Top Aptos", expanded=True):
            painel_detalhe_aptos(df)
    if st.session_state.mostrar_inaptos_desist:   # COMENTADO — painel Inaptos/Desistentes/Devedores
        with st.expander("📌 Detalhe: Inaptos / Desistentes", expanded=True):
            painel_detalhe_inaptos_desistentes(df)
    if st.session_state.mostrar_satisfacao:
        with st.expander("📌 Detalhe: Satisfação (melhores/piores)", expanded=True):
            painel_detalhe_satisfacao(df)
    if st.session_state.mostrar_valor:
        with st.expander("📌 Detalhe: Valor Recebido (top)", expanded=True):
            painel_detalhe_valor_recebido(df)

# ── Gráfico de Estado ─────────────────────────────────────────────────────────
def grafico_status(df: pd.DataFrame):
    if "Status" not in df.columns:
        return None

    # ----- NORMALIZAÇÃO DOS ESTADOS APENAS PARA O GRÁFICO -----
    def normalizar(status):
        s = str(status).strip().upper()
        if s in ["FINALIZADA", "FECHADA"]:
            return "Finalizada"
        if s in ["CANCELADA", "CANCELADA"]:
            return "Cancelada"
        return status 
    
    df_chart = df.copy()
    df_chart["Status_Norm"] = df_chart["Status"].apply(normalizar)
    # ---------------------------------------------------------

    counts = df_chart["Status_Norm"].value_counts().reset_index()
    counts.columns = ["Status", "Total"]

    fig = go.Figure(go.Pie(
        labels=counts["Status"],
        values=counts["Total"],
        hole=0.4,
        textinfo="label+percent",
        textposition="auto",
        textfont=dict(size=13, color="white"),
        hoverinfo="label+value+percent",
        hovertemplate="<b>%{label}</b><br>Total: %{value:,.0f}<br>Percent: %{percent:.1f}%<extra></extra>",
        marker=dict(line=dict(color='white', width=2))
    ))
    fig.update_layout(
        title=dict(text="Estado das Ações", font_size=16, x=0.5),
        height=480,
        showlegend=True,
        legend=dict(orientation="v", yanchor="top", y=0.5, xanchor="left", x=1.02, font_size=11),
        margin=dict(t=60, l=20, r=150, b=20)
    )
    st.plotly_chart(fig, use_container_width=True, key="status_chart")

    # Lógica de clique (agora os labels são "Finalizada" ou "Cancelada")
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

def painel_detalhe_estado(df: pd.DataFrame, estado_norm: str):
    if estado_norm is None:
        return

    # Mapeamento para os valores reais na coluna "Status"
    if estado_norm == "Finalizada":
        cond = df["Status"].astype(str).str.upper().isin(["FINALIZADA", "FECHADA"])
    elif estado_norm == "Cancelada":
        cond = df["Status"].astype(str).str.upper().isin(["CANCELADA"])
        # Se tiveres "Cancelada" com C maiúsculo, adiciona: 
        # cond = df["Status"].astype(str).str.upper().isin(["CANCELADA"])
    else:
        cond = df["Status"] == estado_norm

    df_estado = df[cond].copy()
    if df_estado.empty:
        st.info(f"Nenhuma ação com estado equivalente a '{estado_norm}'.")
        return

    st.markdown(f"### 📋 Ações com estado: **{estado_norm}**")
    st.markdown("*Clique novamente na fatia do gráfico para fechar*")

    cols_mostrar = [c for c in ["Centro", "Ação", "Status", "Inscritos", "Aptos", "Taxa de satisfação Final"] if c in df_estado.columns]
    df_show = df_estado[cols_mostrar].reset_index(drop=True)
    st.dataframe(df_show, use_container_width=True, hide_index=True)
    st.markdown("---")

# ── Gráfico Funil ────────────────────────────────────────────────────────────
def grafico_funil(df: pd.DataFrame):
    inscritos = safe_sum(df, "Inscritos")
    aptos = safe_sum(df, "Aptos")
    inaptos = safe_sum(df, "Inaptos")      
    desist  = safe_sum(df, "Desistentes")   
    deved   = safe_sum(df, "Devedores")    

    if inscritos == 0:
        st.info("Sem dados de inscritos.")
        return

    data = {
        "Categoria": ["Inscritos", "Aptos","Inaptos", "Desistentes","Devedores"],
        "Valor": [inscritos, aptos, inaptos, desist,deved],
        "Percentagem": [100.0, (aptos/inscritos)*100, (inaptos/inscritos)*100, (desist/inscritos)*100]    }
    df_plot = pd.DataFrame(data)

    fig = go.Figure(go.Bar(
        x=df_plot["Percentagem"],
        y=df_plot["Categoria"],
        orientation='h',
        text=df_plot.apply(lambda r: f"{r['Valor']:,.0f} ({r['Percentagem']:.1f}%)", axis=1),
        textposition='outside',
        marker_color=['#1f77b4', '#2ca02c', '#ff7f0e', '#d62728'],  # cores de Inaptos, Desist., Devedores removidas   # COMENTADO
        hovertemplate='<b>%{y}</b><br>Valor: %{customdata[0]:,.0f}<br>Percentagem: %{x:.1f}%<extra></extra>',
        customdata=df_plot[["Valor"]].values
    ))
    fig.update_layout(
        title=dict(text="Distribuição de Participantes (percentagem em relação aos inscritos)", font_size=14),
        xaxis=dict(title="Percentagem (%)", range=[0, 105], showgrid=True),
        yaxis=dict(title="", showgrid=False),
        height=350,
        margin=dict(l=10, r=10, t=50, b=10)
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Timeline ─────────────────────────────────────────────────────────────────
def grafico_timeline_mensal_intervalo(df: pd.DataFrame, data_inicio: date, data_fim: date):
    if "Data Inicial" not in df.columns or df["Data Inicial"].isna().all():
        return None, None
    df_t = df.dropna(subset=["Data Inicial"]).copy()
    df_t = df_t[(df_t["Data Inicial"].dt.date >= data_inicio) & (df_t["Data Inicial"].dt.date <= data_fim)]
    if df_t.empty:
        return None, None
    df_t["AnoMês"] = df_t["Data Inicial"].dt.to_period("M")
    df_t["Mês_num"] = df_t["Data Inicial"].dt.month
    df_t["Ano"] = df_t["Data Inicial"].dt.year
    agg = (df_t.groupby(["AnoMês", "Ano", "Mês_num"])
                .agg(Ações=("Ação", "count"),
                     Inscritos=("Inscritos", "sum"),
                     Aptos=("Aptos", "sum"))
                .reset_index())
    agg = agg.sort_values("AnoMês")
    nomes_meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    agg["Rótulo"] = agg.apply(lambda r: f"{nomes_meses[r['Mês_num']-1]} {r['Ano']}", axis=1)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=agg["Rótulo"], y=agg["Ações"], name="Nº Ações",
                         hovertemplate="<b>%{x}</b><br>Ações: %{y}<br><i>Clique para ver detalhe</i><extra></extra>"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=agg["Rótulo"], y=agg["Inscritos"], name="Inscritos", mode="lines+markers",
                             line=dict(width=2.5), marker=dict(size=6)), secondary_y=True)
    fig.add_trace(go.Scatter(x=agg["Rótulo"], y=agg["Aptos"], name="Aptos", mode="lines+markers",
                             line=dict(width=2, dash="dot"), marker=dict(size=5)), secondary_y=True)
    fig.update_layout(title=dict(text=f"Evolução Mensal ({data_inicio.strftime('%b %Y')} a {data_fim.strftime('%b %Y')})", font_size=14),
                      height=310, legend=dict(orientation="h", y=1.12),
                      xaxis=dict(showgrid=False, title="Mês", tickangle=45),
                      yaxis=dict(showgrid=False, title="Nº Ações"),
                      yaxis2=dict(showgrid=False, title="Participantes"), clickmode="event")
    st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="timeline_intervalo")
    return agg, df_t

def grafico_timeline_ano_especifico(df: pd.DataFrame, ano: int):
    if "Data Inicial" not in df.columns or df["Data Inicial"].isna().all():
        return None, None
    df_t = df.dropna(subset=["Data Inicial"]).copy()
    df_ano = df_t[df_t["Data Inicial"].dt.year == ano]
    if df_ano.empty:
        return None, None
    df_ano["Mês"] = df_ano["Data Inicial"].dt.month
    agg = (df_ano.groupby("Mês")
                .agg(Ações=("Ação", "count"),
                     Inscritos=("Inscritos", "sum"),
                     Aptos=("Aptos", "sum"))
                .reset_index())
    meses_completos = pd.DataFrame({"Mês": list(range(1, 13))})
    agg = meses_completos.merge(agg, on="Mês", how="left").fillna(0)
    agg["Ações"] = agg["Ações"].astype(int)
    nomes_meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    agg["Rótulo"] = agg["Mês"].apply(lambda x: nomes_meses[x-1])
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=agg["Rótulo"], y=agg["Ações"], name="Nº Ações",
                         hovertemplate="<b>%{x}</b><br>Ações: %{y}<br><i>Clique para ver detalhe</i><extra></extra>"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=agg["Rótulo"], y=agg["Inscritos"], name="Inscritos", mode="lines+markers",
                             line=dict(width=2.5), marker=dict(size=6)), secondary_y=True)
    fig.add_trace(go.Scatter(x=agg["Rótulo"], y=agg["Aptos"], name="Aptos", mode="lines+markers",
                             line=dict(width=2, dash="dot"), marker=dict(size=5)), secondary_y=True)
    fig.update_layout(title=dict(text=f"Evolução Mensal - {ano}", font_size=14),
                      height=310, legend=dict(orientation="h", y=1.12),
                      xaxis=dict(showgrid=False, title="Mês"),
                      yaxis=dict(showgrid=False, title="Nº Ações"),
                      yaxis2=dict(showgrid=False, title="Participantes"), clickmode="event")
    st.plotly_chart(fig, use_container_width=True, on_select="rerun", key=f"timeline_ano_{ano}")
    return agg, df_ano

def painel_detalhe_mes_generico(df_filtrado: pd.DataFrame, rotulo: str, ano: int, mes_num: int):
    df_mes = df_filtrado[(df_filtrado["Data Inicial"].dt.year == ano) & (df_filtrado["Data Inicial"].dt.month == mes_num)].copy()
    if df_mes.empty:
        return
    nome_mes = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][mes_num-1]
    st.markdown(f"### 📅 Detalhe — **{nome_mes} de {ano}**")
    st.markdown("*Clique novamente na barra do gráfico para fechar*")
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        n_acoes = df_mes["Ação"].nunique() if "Ação" in df_mes.columns else len(df_mes)
        st.metric("Ações", str(n_acoes))
    with k2:
        st.metric("Inscritos", fmt_num(safe_sum(df_mes, "Inscritos")))
    with k3:
        ins = safe_sum(df_mes, "Inscritos")
        apt = safe_sum(df_mes, "Aptos")
        st.metric("Aptos", fmt_num(apt), delta=f"Taxa: {taxa(apt, ins)}%")
    with k4:
        st.metric("Inaptos / Desist.", f"{fmt_num(safe_sum(df_mes,'Inaptos'))} / {fmt_num(safe_sum(df_mes,'Desistentes'))}")  # COMENTADO
        pass
    with k5:
        media_s = safe_mean(df_mes, "Taxa de satisfação Final")
        st.metric("Satisfação Média", f"{media_s:.2f}" if media_s else "—")
    st.markdown("<div style='margin:10px 0'></div>", unsafe_allow_html=True)
    cols_mostrar = [c for c in [
        "Ação", "Centro", "Status", "Formador", "Data Inicial", "Data Final",
        "Inscritos", "Aptos", "Inaptos", "Desistentes","Devedores",   # COMENTADO
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

# ── Gráficos de Avaliação e Receita ──────────────────────────────────────────
def grafico_avaliacao_formador(df: pd.DataFrame):
    if "Formador" not in df.columns or "Avaliação formador" not in df.columns:
        return
    df_f = (df.groupby("Formador")["Avaliação formador"].mean().dropna().sort_values(ascending=True).reset_index())
    df_f.columns = ["Formador", "Avaliação"]
    if df_f.empty:
        return
    fig = go.Figure(go.Bar(x=df_f["Avaliação"], y=df_f["Formador"], orientation="h",
                           text=df_f["Avaliação"].round(2), textposition="outside"))
    fig.update_layout(title=dict(text="Avaliação Média por Formador", font_size=14),
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
                         opacity=.5, text=agg["Receber"].apply(fmt_euro), textposition="outside"))
    fig.add_trace(go.Bar(x=agg["Recebido"], y=agg["Centro"], orientation="h", name="Recebido",
                         opacity=.85, text=agg["Recebido"].apply(fmt_euro), textposition="outside"))
    fig.update_layout(title=dict(text="Receita: Esperada vs Recebida por Centro", font_size=14),
                      barmode="overlay", height=max(230, len(agg) * 40), xaxis=dict(showgrid=False, visible=False),
                      yaxis=dict(showgrid=False), legend=dict(orientation="h", y=1.12))
    st.plotly_chart(fig, use_container_width=True)

# ── Tabela Geral de Ações ─────────────────────────────────────────────────────
def tabela_geral_acoes(df: pd.DataFrame):
    if df.empty:
        st.info("Nenhum dado para exibir.")
        return
    ordem_canonica = [
        "Status", "Ação", "Data Inicial", "Data Final", "Centro",
        "Inscritos", "Aptos", "Inaptos", "Desistentes", "Devedores",   # COMENTADO
        "Taxa de Satisfação M01", "Taxa de Satisfação M02", "Taxa de Satisfação M03",
        "Taxa de Satisfação M04", "Taxa de Satisfação M05", "Taxa de Satisfação M06",
        "Taxa de Satisfação M07", "Taxa de Satisfação M08", "Taxa de Satisfação M09",
        "Taxa de Satisfação M10", "Taxa de Satisfação M11", "Taxa de Satisfação M12",
        "Taxa de satisfação Final", "Nacionalidades(Portugueses/Estrangeiros)",
        "Valor total a receber", "Valor Total Recebido", "Formador", "Avaliação formador"
    ]
    colunas_existentes = [col for col in ordem_canonica if col in df.columns]
    outras_colunas = [col for col in df.columns if col not in ordem_canonica and col != "Apagar"]
    todas_colunas = colunas_existentes + outras_colunas
    st.markdown("---")
    st.markdown(f"### 📋 Todas as Ações ({len(df)} registos)")
    default_cols = todas_colunas[:]
    colunas_selecionadas = st.multiselect("Escolha as colunas a exibir:", options=todas_colunas, default=default_cols, key="tabela_geral_colunas")
    if not colunas_selecionadas:
        st.warning("Selecione pelo menos uma coluna.")
        return
    df_exibir = df[colunas_selecionadas].copy()
    for data_col in ["Data Inicial", "Data Final"]:
        if data_col in df_exibir.columns and pd.api.types.is_datetime64_any_dtype(df_exibir[data_col]):
            df_exibir[data_col] = df_exibir[data_col].dt.strftime("%d/%m/%Y")
    for col in df_exibir.columns:
        if "Valor" in col and pd.api.types.is_numeric_dtype(df_exibir[col]):
            df_exibir[col] = df_exibir[col].apply(lambda x: fmt_euro(x) if pd.notna(x) else "—")
    column_config = {}
    for col in df_exibir.columns:
        if col in ["Inscritos", "Aptos","Inaptos", "Desistentes", "Devedores"]:  # "Inaptos", "Desistentes", "Devedores" removidos   # COMENTADO
            valores = df_exibir[col].dropna()
            if not valores.empty and pd.api.types.is_numeric_dtype(valores):
                max_val = valores.max()
                if pd.notna(max_val) and max_val > 0:
                    column_config[col] = st.column_config.ProgressColumn(col, min_value=0, max_value=int(max_val), format="%d")
        elif "satisfação" in col.lower() or "Satisfação" in col:
            column_config[col] = st.column_config.NumberColumn(col, format="%.2f")
        elif "Avaliação" in col:
            column_config[col] = st.column_config.NumberColumn(col, format="%.2f")
    st.dataframe(df_exibir, use_container_width=True, hide_index=True, column_config=column_config, height=min(600, 35 + len(df_exibir) * 35))

# ── Filtros na sidebar ────────────────────────────────────────────────────────
def aplicar_filtros_dashboard(df: pd.DataFrame) -> pd.DataFrame:
    with st.sidebar:
        st.markdown("## 🔍 Filtros")
        st.markdown("---")
        if "Status" in df.columns:
            valores_status = sorted(df["Status"].dropna().unique().tolist())
            sel_status = st.multiselect("Estado da Ação", options=valores_status, default=valores_status, key="dash_status")
            if sel_status:
                df = df[df["Status"].isin(sel_status)]
        if "Ação" in df.columns:
            def extrair_tipo(nome):
                nome = str(nome).strip()
                if '_' in nome:
                    return nome.split('_')[0]
                if '/' in nome:
                    return nome.split('/')[0]
                return nome[:4] if len(nome) >= 4 else nome
            df = df.copy()
            df["_Tipo"] = df["Ação"].astype(str).apply(extrair_tipo)
            tipos = sorted(df["_Tipo"].dropna().unique().tolist())
            if tipos:
                tipo_sel = st.multiselect("Tipo de Ação", tipos, default=tipos, key="dash_tipo")
                if tipo_sel:
                    df = df[df["_Tipo"].isin(tipo_sel)]
            df = df.drop(columns=["_Tipo"])
        if "Centro" in df.columns:
            centros = sorted(df["Centro"].dropna().unique().tolist())
            sel_centro = st.multiselect("Centro", centros, default=centros, key="dash_centro")
            if sel_centro:
                df = df[df["Centro"].isin(sel_centro)]
        if "Formador" in df.columns:
            formadores = sorted(df["Formador"].dropna().unique().tolist())
            if formadores:
                sel_formador = st.multiselect("Formador", formadores, default=formadores, key="dash_formador")
                if sel_formador:
                    df = df[df["Formador"].isin(sel_formador)]
        todas_datas = pd.Series(dtype="datetime64[ns]")
        
        # ----- FILTRO DE DATAS RELATIVO (com opções rápidas) -----
        todas_datas = pd.Series(dtype="datetime64[ns]")
        for col in ["Data Inicial", "Data Final"]:
            if col in df.columns:
                todas_datas = pd.concat([todas_datas, df[col].dropna()])
        
        if not todas_datas.empty:
            data_min_global = max(todas_datas.min().date(), date(2010, 1, 1))
            data_max_global = todas_datas.max().date()
            
            # Escolha do tipo de filtro
            tipo_filtro_data = st.radio(
                "Tipo de período",
                ["📅 Período rápido", "📆 Intervalo personalizado"],
                horizontal=True,
                key="dash_tipo_periodo"
            )
            
            if tipo_filtro_data == "📅 Período rápido":
                # Gerar opções dinâmicas baseadas nos dados e na data atual
                opcoes = gerar_opcoes_rapidas(df)  # função já existente no teu código
                if opcoes:
                    nomes_opcoes = list(opcoes.keys())
                    # Adicionar opção "Selecionar período"
                    opcao_selecionada = st.selectbox(
                        "Escolha o período",
                        nomes_opcoes,
                        index=0,
                        key="dash_periodo_rapido"
                    )
                    data_inicio_filtro, data_fim_filtro = opcoes[opcao_selecionada]
                    st.caption(f"📅 {data_inicio_filtro.strftime('%d/%m/%Y')} – {data_fim_filtro.strftime('%d/%m/%Y')}")
                else:
                    st.warning("Não foi possível gerar períodos rápidos. Use intervalo personalizado.")
                    data_inicio_filtro = data_min_global
                    data_fim_filtro = data_max_global
            else:
                # Intervalo personalizado (igual ao antigo)
                intervalo = st.date_input(
                    "Intervalo de datas",
                    value=(data_min_global, data_max_global),
                    min_value=date(2010, 1, 1),
                    max_value=data_max_global,
                    key="dash_datas"
                )
                if isinstance(intervalo, (list, tuple)) and len(intervalo) == 2:
                    data_inicio_filtro, data_fim_filtro = intervalo
                else:
                    data_inicio_filtro = data_min_global
                    data_fim_filtro = data_max_global
            
            # Aplicar o filtro de datas (se a coluna existir)
            if "Data Inicial" in df.columns and pd.api.types.is_datetime64_any_dtype(df["Data Inicial"]):
                df_datas = df["Data Inicial"].dt.date
                df = df[(df_datas >= data_inicio_filtro) & (df_datas <= data_fim_filtro)]
        else:
            st.info("Sem datas disponíveis para filtrar.")
        # ---------------------------------------------------------

        # ----- NOVO FILTRO: Ações com data de início ou fim num mês específico -----
        st.markdown("### 📅 Filtro por Mês (Início ou Fim)")
        col1, col2, col3 = st.columns(3)
        with col1:
            anos_disponiveis = sorted(df["Data Inicial"].dt.year.dropna().unique()) if "Data Inicial" in df.columns else []
            if anos_disponiveis:
                ano_sel = st.selectbox("Ano", anos_disponiveis, index=len(anos_disponiveis)-1, key="filtro_ano")
            else:
                ano_sel = datetime.today().year
                st.info("Sem datas disponíveis para filtrar por mês.")
        with col2:
            meses = list(range(1, 13))
            nomes_meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
            mes_sel = st.selectbox("Mês", meses, format_func=lambda x: nomes_meses[x-1], index=datetime.today().month-1, key="filtro_mes")
        with col3:
            tipo_filtro_mes = st.selectbox(
                "Condição",
                ["Início OU Fim no mês", "Apenas Início no mês", "Apenas Fim no mês"],
                index=0,
                key="filtro_tipo_mes"
            )

        if "Data Inicial" in df.columns and "Data Final" in df.columns:
            primeiro_dia = datetime(ano_sel, mes_sel, 1).date()
            ultimo_dia = (datetime(ano_sel, mes_sel, 1) + pd.DateOffset(months=1) - pd.Timedelta(days=1)).date()

            # Criar máscaras
            inicio_no_mes = df["Data Inicial"].dt.date.between(primeiro_dia, ultimo_dia)
            fim_no_mes = df["Data Final"].dt.date.between(primeiro_dia, ultimo_dia)

            if tipo_filtro_mes == "Início OU Fim no mês":
                mask_mes = inicio_no_mes | fim_no_mes
            elif tipo_filtro_mes == "Apenas Início no mês":
                mask_mes = inicio_no_mes
            else:  
                mask_mes = fim_no_mes

            # Aplicar o filtro (se o utilizador quiser ativar/desativar, pode usar um checkbox)
            ativar = st.checkbox("✅ Ativar este filtro", value=False, key="ativar_filtro_mes")
            if ativar and mask_mes.any():
                df = df[mask_mes]
                st.caption(f"📌 Ações com {'início ou fim' if tipo_filtro_mes=='Início OU Fim no mês' else ('início' if tipo_filtro_mes=='Apenas Início no mês' else 'fim')} em {nomes_meses[mes_sel-1]} de {ano_sel}: {mask_mes.sum()}")
            elif ativar and not mask_mes.any():
                st.warning(f"Nenhuma ação encontrada no período selecionado.")

            if st.button("🗑️ Limpar todos os filtros", use_container_width=True):
                for key in ["dash_status", "dash_tipo", "dash_centro", "dash_formador", "dash_datas",
                            "filtro_ano", "filtro_mes", "filtro_tipo_mes", "ativar_filtro_mes"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
    return df
'''
# ── Filtros Opcionais dentro de um Expander ─────────────────────────────────
def mostrar_filtros_opcionais(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mostra filtros opcionais dentro de um expander que só aparece quando o botão é clicado.
    Retorna o DataFrame filtrado.
    """
    
    # Inicializar estado do filtro opcional se não existir
    if "mostrar_filtros_opcionais" not in st.session_state:
        st.session_state.mostrar_filtros_opcionais = False
    
    # Botão para mostrar/esconder filtros opcionais
    col_botao1, col_botao2, col_botao3 = st.columns([1, 2, 1])
    with col_botao2:
        if st.button("🔧 **Filtros Opcionais**", use_container_width=True, key="btn_filtros_opcionais"):
            st.session_state.mostrar_filtros_opcionais = not st.session_state.mostrar_filtros_opcionais
            st.rerun()
    
    # Se o botão foi clicado, mostrar os filtros opcionais
    if st.session_state.mostrar_filtros_opcionais:
        with st.expander("🔍 **Filtros Avançados - Clique para expandir**", expanded=True):
            st.markdown("### 🎯 Filtros Detalhados")
            st.markdown("*Aplique filtros adicionais para refinar ainda mais a análise*")
            st.markdown("---")
            
            df_filtrado = df.copy()
            
            # Organizar filtros em 2 colunas
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📊 Filtros Numéricos")
                
                # Filtro por número mínimo de inscritos
                if "Inscritos" in df_filtrado.columns:
                    min_inscritos = st.number_input(
                        "📝 Mínimo de Inscritos",
                        min_value=0,
                        value=0,
                        step=1,
                        key="filtro_min_inscritos"
                    )
                    if min_inscritos > 0:
                        df_filtrado = df_filtrado[df_filtrado["Inscritos"] >= min_inscritos]
                
                # Filtro por número mínimo de aptos
                if "Aptos" in df_filtrado.columns:
                    min_aptos = st.number_input(
                        "✅ Mínimo de Aptos",
                        min_value=0,
                        value=0,
                        step=1,
                        key="filtro_min_aptos"
                    )
                    if min_aptos > 0:
                        df_filtrado = df_filtrado[df_filtrado["Aptos"] >= min_aptos]
                
                # Filtro por taxa de satisfação mínima
                if "Taxa de satisfação Final" in df_filtrado.columns:
                    min_satisfacao = st.slider(
                        "⭐ Satisfação Mínima (0-5)",
                        min_value=0.0,
                        max_value=5.0,
                        value=0.0,
                        step=0.1,
                        key="filtro_min_satisfacao"
                    )
                    if min_satisfacao > 0:
                        df_filtrado = df_filtrado[df_filtrado["Taxa de satisfação Final"] >= min_satisfacao]
            
            with col2:
                st.markdown("#### 💰 Filtros Financeiros")
                
                # Filtro por valor mínimo recebido
                if "Valor Total Recebido" in df_filtrado.columns:
                    min_valor_recebido = st.number_input(
                        "💶 Valor Mínimo Recebido (€)",
                        min_value=0,
                        value=0,
                        step=1000,
                        key="filtro_min_valor_recebido"
                    )
                    if min_valor_recebido > 0:
                        df_filtrado = df_filtrado[df_filtrado["Valor Total Recebido"] >= min_valor_recebido]
                
                # Filtro por valor mínimo a receber
                if "Valor total a receber" in df_filtrado.columns:
                    min_valor_receber = st.number_input(
                        "💰 Valor Mínimo a Receber (€)",
                        min_value=0,
                        value=0,
                        step=1000,
                        key="filtro_min_valor_receber"
                    )
                    if min_valor_receber > 0:
                        df_filtrado = df_filtrado[df_filtrado["Valor total a receber"] >= min_valor_receber]
                
                # Filtro por taxa de cobrança mínima
                if "Valor Total Recebido" in df_filtrado.columns and "Valor total a receber" in df_filtrado.columns:
                    df_temp = df_filtrado.copy()
                    df_temp["Taxa_Cobranca"] = (df_temp["Valor Total Recebido"] / df_temp["Valor total a receber"] * 100).fillna(0)
                    min_taxa = st.slider(
                        "📈 Taxa de Cobrança Mínima (%)",
                        min_value=0,
                        max_value=100,
                        value=0,
                        step=5,
                        key="filtro_min_taxa"
                    )
                    if min_taxa > 0:
                        df_filtrado = df_filtrado[df_temp["Taxa_Cobranca"] >= min_taxa]
            
            st.markdown("---")
            
            # Terceira linha: Filtros de texto/pesquisa
            st.markdown("#### 🔎 Filtros de Pesquisa")
            
            col3, col4 = st.columns(2)
            
            with col3:
                # Pesquisa por ação
                if "Ação" in df_filtrado.columns:
                    pesquisa_acao = st.text_input(
                        "🔍 Pesquisar Ação (nome contém)",
                        placeholder="Digite parte do nome da ação...",
                        key="filtro_pesquisa_acao"
                    )
                    if pesquisa_acao:
                        df_filtrado = df_filtrado[df_filtrado["Ação"].astype(str).str.contains(pesquisa_acao, case=False, na=False)]
            
            with col4:
                # Pesquisa por formador
                if "Formador" in df_filtrado.columns:
                    pesquisa_formador = st.text_input(
                        "👨‍🏫 Pesquisar Formador",
                        placeholder="Digite parte do nome do formador...",
                        key="filtro_pesquisa_formador"
                    )
                    if pesquisa_formador:
                        df_filtrado = df_filtrado[df_filtrado["Formador"].astype(str).str.contains(pesquisa_formador, case=False, na=False)]
            
            st.markdown("---")
            
            # Botões de ação para os filtros opcionais
            col_acoes1, col_acoes2, col_acoes3 = st.columns(3)
            
            with col_acoes2:
                # Botão para limpar apenas os filtros opcionais
                if st.button("🗑️ Limpar Filtros Opcionais", use_container_width=True, key="limpar_filtros_opcionais"):
                    # Limpar todas as keys dos filtros opcionais
                    filtros_opcionais_keys = [
                        "filtro_min_inscritos", "filtro_min_aptos", "filtro_min_satisfacao",
                        "filtro_min_valor_recebido", "filtro_min_valor_receber", "filtro_min_taxa",
                        "filtro_pesquisa_acao", "filtro_pesquisa_formador"
                    ]
                    for key in filtros_opcionais_keys:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
            
            # Mostrar resumo dos filtros aplicados
            if len(df_filtrado) < len(df):
                st.success(f"✅ Filtros opcionais aplicados: {len(df_filtrado)} ações restantes (de {len(df)} originais)")
            else:
                st.info("ℹ️ Nenhum filtro opcional aplicado")
            
            return df_filtrado
    
    # Se os filtros opcionais não estiverem ativos, retorna o DataFrame original
    return df
'''

# ── Funções de Timeline melhoradas ────────────────────────────────────────────
def gerar_opcoes_rapidas(df: pd.DataFrame):
    if "Data Inicial" not in df.columns or df["Data Inicial"].isna().all():
        return {}
    today = date.today()
    ano_atual = today.year
    data_max = df["Data Inicial"].max().date()
    data_min = max(df["Data Inicial"].min().date(), date(2010, 1, 1))
    opcoes = {
        "Todo o período": (data_min, data_max),
        "Ano atual": (date(ano_atual, 1, 1), date(ano_atual, 12, 31)),
        "Ano passado": (date(ano_atual - 1, 1, 1), date(ano_atual - 1, 12, 31)),
    }
    data_max_ts = pd.Timestamp(data_max)
    ultimos_12_inicio = (data_max_ts - pd.DateOffset(months=11)).date()
    opcoes["Últimos 12 meses"] = (ultimos_12_inicio, data_max)
    opcoes["1º Trimestre (Jan-Mar)"] = (date(ano_atual, 1, 1), date(ano_atual, 3, 31))
    opcoes["2º Trimestre (Abr-Jun)"] = (date(ano_atual, 4, 1), date(ano_atual, 6, 30))
    opcoes["3º Trimestre (Jul-Set)"] = (date(ano_atual, 7, 1), date(ano_atual, 9, 30))
    opcoes["4º Trimestre (Out-Dez)"] = (date(ano_atual, 10, 1), date(ano_atual, 12, 31))
    opcoes["1º Semestre (Jan-Jun)"] = (date(ano_atual, 1, 1), date(ano_atual, 6, 30))
    opcoes["2º Semestre (Jul-Dez)"] = (date(ano_atual, 7, 1), date(ano_atual, 12, 31))
    return opcoes

def grafico_timeline_intervalo_melhorado(df: pd.DataFrame, data_inicio: date, data_fim: date):
    if "Data Inicial" not in df.columns or df["Data Inicial"].isna().all():
        return None, None
    df_t = df.dropna(subset=["Data Inicial"]).copy()
    df_t = df_t[(df_t["Data Inicial"].dt.date >= data_inicio) & (df_t["Data Inicial"].dt.date <= data_fim)]
    if df_t.empty:
        return None, None
    df_t["AnoMês"] = df_t["Data Inicial"].dt.to_period("M")
    df_t["Mês_num"] = df_t["Data Inicial"].dt.month
    df_t["Ano"] = df_t["Data Inicial"].dt.year
    agg = (df_t.groupby(["AnoMês", "Ano", "Mês_num"])
                .agg(Ações=("Ação", "count"),
                     Inscritos=("Inscritos", "sum"),
                     Aptos=("Aptos", "sum"))
                .reset_index().sort_values("AnoMês"))
    nomes_meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    agg["Rótulo"] = agg.apply(lambda r: f"{nomes_meses[r['Mês_num']-1]} {r['Ano']}", axis=1)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=agg["Rótulo"], y=agg["Ações"], name="Nº Ações",
                         hovertemplate="<b>%{x}</b><br>Ações: %{y}<br><i>Clique para detalhe</i><extra></extra>"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=agg["Rótulo"], y=agg["Inscritos"], name="Inscritos", mode="lines+markers",
                             line=dict(width=2.5), marker=dict(size=6)), secondary_y=True)
    fig.add_trace(go.Scatter(x=agg["Rótulo"], y=agg["Aptos"], name="Aptos", mode="lines+markers",
                             line=dict(width=2, dash="dot"), marker=dict(size=5)), secondary_y=True)
    fig.update_layout(
        title=dict(text=f"Evolução Mensal ({data_inicio.strftime('%b %Y')} a {data_fim.strftime('%b %Y')})", font_size=14),
        height=310, legend=dict(orientation="h", y=1.12),
        xaxis=dict(showgrid=False, tickangle=45),
        yaxis=dict(showgrid=False, title="Nº Ações"),
        yaxis2=dict(showgrid=False, title="Participantes"),
        clickmode="event"
    )
    st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="timeline_intervalo")
    return agg, df_t

def grafico_timeline_ano_especifico_melhorado(df: pd.DataFrame, ano: int):
    if "Data Inicial" not in df.columns or df["Data Inicial"].isna().all():
        return None, None
    df_ano = df[df["Data Inicial"].dt.year == ano].copy()
    if df_ano.empty:
        return None, None
    df_ano["Mês"] = df_ano["Data Inicial"].dt.month
    agg = (df_ano.groupby("Mês")
                 .agg(Ações=("Ação", "count"),
                      Inscritos=("Inscritos", "sum"),
                      Aptos=("Aptos", "sum"))
                 .reset_index())
    meses_completos = pd.DataFrame({"Mês": range(1,13)})
    agg = meses_completos.merge(agg, on="Mês", how="left").fillna(0)
    agg["Ações"] = agg["Ações"].astype(int)
    nomes_meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    agg["Rótulo"] = agg["Mês"].apply(lambda x: nomes_meses[x-1])
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=agg["Rótulo"], y=agg["Ações"], name="Nº Ações",
                         hovertemplate="<b>%{x}</b><br>Ações: %{y}<br><i>Clique para detalhe</i><extra></extra>"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=agg["Rótulo"], y=agg["Inscritos"], name="Inscritos", mode="lines+markers",
                             line=dict(width=2.5), marker=dict(size=6)), secondary_y=True)
    fig.add_trace(go.Scatter(x=agg["Rótulo"], y=agg["Aptos"], name="Aptos", mode="lines+markers",
                             line=dict(width=2, dash="dot"), marker=dict(size=5)), secondary_y=True)
    fig.update_layout(
        title=dict(text=f"Evolução Mensal - {ano}", font_size=14),
        height=310, legend=dict(orientation="h", y=1.12),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False, title="Nº Ações"),
        yaxis2=dict(showgrid=False, title="Participantes"),
        clickmode="event"
    )
    st.plotly_chart(fig, use_container_width=True, on_select="rerun", key=f"timeline_ano_{ano}")
    return agg, df_ano

def painel_detalhe_mes_melhorado(df_filtrado: pd.DataFrame, ano: int, mes_num: int):
    df_mes = df_filtrado[(df_filtrado["Data Inicial"].dt.year == ano) & (df_filtrado["Data Inicial"].dt.month == mes_num)].copy()
    if df_mes.empty:
        return
    nome_mes = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][mes_num-1]
    st.markdown(f"### 📅 Detalhe — **{nome_mes} de {ano}**")
    st.markdown("*Clique novamente na barra do gráfico para fechar*")
    cols = st.columns(5)
    with cols[0]:
        n_acoes = df_mes["Ação"].nunique() if "Ação" in df_mes.columns else len(df_mes)
        st.metric("Ações", str(n_acoes))
    with cols[1]:
        st.metric("Inscritos", fmt_num(safe_sum(df_mes, "Inscritos")))
    with cols[2]:
        ins = safe_sum(df_mes, "Inscritos")
        apt = safe_sum(df_mes, "Aptos")
        st.metric("Aptos", fmt_num(apt), delta=f"Taxa: {taxa(apt, ins)}%")
    with cols[3]:
        st.metric("Inaptos / Desist.", f"{fmt_num(safe_sum(df_mes,'Inaptos'))} / {fmt_num(safe_sum(df_mes,'Desistentes'))}")  # COMENTADO
        pass
    with cols[4]:
        media_s = safe_mean(df_mes, "Taxa de satisfação Final")
        st.metric("Satisfação Média", f"{media_s:.2f}" if media_s else "—")
    st.markdown("---")
    cols_mostrar = [c for c in [
        "Ação", "Centro", "Status", "Formador", "Data Inicial", "Data Final",
        "Inscritos", "Aptos", "Inaptos", "Desistentes",   # COMENTADO
        "Taxa de satisfação Final", "Avaliação formador",
        "Valor total a receber", "Valor Total Recebido",
    ] if c in df_mes.columns]
    df_show = df_mes[cols_mostrar].reset_index(drop=True)
    for col_data in ["Data Inicial", "Data Final"]:
        if col_data in df_show.columns:
            df_show[col_data] = df_show[col_data].dt.strftime("%d/%m/%Y")
    st.dataframe(df_show, use_container_width=True, hide_index=True, height=min(400, 55 + len(df_show)*35))

# ── Dashboard principal ───────────────────────────────────────────────────────
def mostrar_dashboard():
    st.title("📊 Dashboard de Formações")
    st.markdown("Análise interativa — filtre pelo painel lateral")

    df_raw = st.session_state.get("acoes_df", pd.DataFrame())
    if df_raw.empty:
        st.info("ℹ️ Sem dados disponíveis. Carregue dados na página **Análise de Formações**.")
        return

    df = preparar_dados(df_raw)
    df = aplicar_filtros_dashboard(df)
    #df = mostrar_filtros_opcionais(df)
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

    st.markdown("### 📈 Evolução Mensal (todos os meses disponíveis)")

    if "Data Inicial" in df.columns and not df["Data Inicial"].isna().all():
        df_t = df.dropna(subset=["Data Inicial"]).copy()
        df_t["AnoMês"] = df_t["Data Inicial"].dt.to_period("M")
        df_t["Mês_num"] = df_t["Data Inicial"].dt.month
        df_t["Ano"] = df_t["Data Inicial"].dt.year

        agg = (df_t.groupby(["AnoMês", "Ano", "Mês_num"])
                    .agg(Ações=("Ação", "count"),
                         Inscritos=("Inscritos", "sum"),
                         Aptos=("Aptos", "sum"))
                    .reset_index()
                    .sort_values("AnoMês"))

        if not agg.empty:
            nomes_meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
            agg["Rótulo"] = agg.apply(lambda r: f"{nomes_meses[r['Mês_num']-1]} {r['Ano']}", axis=1)

            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=agg["Rótulo"], y=agg["Ações"], name="Nº Ações",
                                 hovertemplate="<b>%{x}</b><br>Ações: %{y}<br><i>Clique para detalhe</i><extra></extra>"),
                          secondary_y=False)
            fig.add_trace(go.Scatter(x=agg["Rótulo"], y=agg["Inscritos"], name="Inscritos", mode="lines+markers",
                                     line=dict(width=2.5), marker=dict(size=6)), secondary_y=True)
            fig.add_trace(go.Scatter(x=agg["Rótulo"], y=agg["Aptos"], name="Aptos", mode="lines+markers",
                                     line=dict(width=2, dash="dot"), marker=dict(size=5)), secondary_y=True)
            fig.update_layout(
                title=dict(text=f"Evolução Mensal (total de {len(agg)} meses)", font_size=14),
                height=310, legend=dict(orientation="h", y=1.12),
                xaxis=dict(showgrid=False, tickangle=45),
                yaxis=dict(showgrid=False, title="Nº Ações"),
                yaxis2=dict(showgrid=False, title="Participantes"),
                clickmode="event"
            )
            st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="timeline_sem_filtro")

            chart_key = "timeline_sem_filtro"
            selecao = st.session_state.get(chart_key, {}).get("selection", {})
            rotulo_sel = st.session_state.get("rotulo_mes_sem_filtro", None)

            if selecao and selecao.get("points"):
                ponto = selecao["points"][0]
                rotulo = ponto.get("x")
                if rotulo:
                    if rotulo_sel == rotulo:
                        st.session_state.rotulo_mes_sem_filtro = None
                    else:
                        st.session_state.rotulo_mes_sem_filtro = rotulo
                    st.session_state[chart_key]["selection"] = {}
                    st.rerun()

            if st.session_state.get("rotulo_mes_sem_filtro") is not None:
                rotulo = st.session_state.rotulo_mes_sem_filtro
                partes = rotulo.split()
                if len(partes) == 2:
                    nome_mes = partes[0]
                    ano = int(partes[1])
                    mes_num = nomes_meses.index(nome_mes) + 1
                    df_mes = df_t[(df_t["Data Inicial"].dt.year == ano) & (df_t["Data Inicial"].dt.month == mes_num)].copy()
                    if not df_mes.empty:
                        painel_detalhe_mes_melhorado(df_mes, ano, mes_num)
        else:
            st.info("Sem dados para construir o gráfico de evolução mensal.")
    else:
        st.info("Não existem datas para construir o gráfico de evolução mensal.")
    st.markdown("---")

    c5, c6 = st.columns([1.2, 1])
    with c5:
        grafico_receita(df)
    with c6:
        grafico_avaliacao_formador(df)

    tabela_geral_acoes(df)

if __name__ == "__main__":
    mostrar_dashboard()