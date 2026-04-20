import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.data_utils import get_col

def normalizar_cursos(df: pd.DataFrame) -> pd.DataFrame:
    """Converte colunas numéricas e trata datas (cópia para não alterar original)."""
    if df is None or df.empty:
        return df
    df = df.copy()
    # Colunas numéricas comuns
    num_cols = ["Inscritos", "Concluídos", "Avaliados", "Aprovados", "Planeado", "Valor da Ação", "Valor Total"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # Datas
    for col in ["Data Inicial", "Data Final"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    return df

def normalizar_questionarios(df: pd.DataFrame) -> pd.DataFrame:
    """Garante que a coluna 'Média' é numérica e que existem as colunas necessárias."""
    if df is None or df.empty:
        return df
    df = df.copy()
    if "Média" in df.columns:
        df["Média"] = pd.to_numeric(df["Média"], errors="coerce")
    # Se existir "Media" sem acento, renomear
    if "Media" in df.columns and "Média" not in df.columns:
        df["Média"] = pd.to_numeric(df["Media"], errors="coerce")
    # Garantir colunas de categorias
    if "Categoria" not in df.columns and "Categoria" in df.columns:
        pass  # já tem
    if "Modalidade" not in df.columns:
        df["Modalidade"] = "Desconhecida"
    if "Respondente" not in df.columns:
        df["Respondente"] = "Formando"
    return df

def mostrar_comparador():
    st.header("⚔️ Comparador entre Centros")

    # ---- Buscar dados das chaves CORRETAS do session_state ----
    df_cursos_raw = st.session_state.get("acoes_editaveis", None)
    df_quest_raw = st.session_state.get("quest_editaveis", None)

    # Normalizar
    df_cursos = normalizar_cursos(df_cursos_raw) if df_cursos_raw is not None else None
    df_quest = normalizar_questionarios(df_quest_raw) if df_quest_raw is not None else None

    has_cursos = df_cursos is not None and not df_cursos.empty
    has_quest = df_quest is not None and not df_quest.empty

    if not has_cursos and not has_quest:
        st.info("📂 Carregue ficheiros de Cursos e/ou Questionários na barra lateral.")
        return

    # ---- Obter centros disponíveis ----
    centros_disponiveis = set()
    if has_cursos and "Centro" in df_cursos.columns:
        centros_disponiveis.update(df_cursos["Centro"].dropna().unique())
    if has_quest and "Centro" in df_quest.columns:
        centros_disponiveis.update(df_quest["Centro"].dropna().unique())

    if not centros_disponiveis:
        st.warning("Nenhum centro encontrado nos dados carregados.")
        return

    centros_disponiveis = sorted(list(centros_disponiveis))

    selecionados = st.multiselect(
        "🏢 Selecione os centros para comparar:",
        centros_disponiveis,
        default=centros_disponiveis[:3] if len(centros_disponiveis) >= 3 else centros_disponiveis,
        help="Compare até 5 centros simultaneamente"
    )

    if len(selecionados) > 5:
        st.warning("⚠️ Selecione no máximo 5 centros para uma visualização clara.")
        selecionados = selecionados[:5]

    if len(selecionados) < 2:
        st.info("👆 Selecione pelo menos 2 centros para iniciar a comparação.")
        return

    # ---- Filtrar dados pelos centros selecionados ----
    df_c_comp = df_cursos[df_cursos["Centro"].isin(selecionados)] if has_cursos else None
    df_q_comp = df_quest[df_quest["Centro"].isin(selecionados)] if has_quest else None

    # ---- Preparar KPIs por centro ----
    kpi_data = []
    for centro in selecionados:
        centro_kpi = {"Centro": centro}

        # Dados dos Cursos
        if has_cursos:
            df_centro = df_c_comp[df_c_comp["Centro"] == centro]

            # Identificar colunas (com suporte a maiúsculas/minúsculas via get_col)
            col_insc = get_col(df_centro, "inscritos")
            col_conc = get_col(df_centro, "concluidos")
            col_aval = get_col(df_centro, "avaliados")
            col_aprov = get_col(df_centro, "aprovados")
            col_planeado = get_col(df_centro, "planeado")

            if col_insc and col_conc:
                total_insc = df_centro[col_insc].sum()
                total_conc = df_centro[col_conc].sum()
                centro_kpi["Taxa Conclusão (%)"] = (total_conc / total_insc * 100) if total_insc > 0 else 0
                centro_kpi["Total Inscritos"] = total_insc
                centro_kpi["Total Concluídos"] = total_conc
            else:
                centro_kpi["Taxa Conclusão (%)"] = None

            if col_aval and col_aprov:
                total_aval = df_centro[col_aval].sum()
                total_aprov = df_centro[col_aprov].sum()
                centro_kpi["Taxa Aprovação (%)"] = (total_aprov / total_aval * 100) if total_aval > 0 else 0
            else:
                centro_kpi["Taxa Aprovação (%)"] = None

            # Número de cursos/ações: usar coluna "Ação" se existir, senão "Curso"
            if "Ação" in df_centro.columns:
                centro_kpi["Nº Cursos"] = df_centro["Ação"].nunique()
            elif "Curso" in df_centro.columns:
                centro_kpi["Nº Cursos"] = df_centro["Curso"].nunique()
            else:
                centro_kpi["Nº Cursos"] = len(df_centro)

        # Dados dos Questionários
        if has_quest:
            df_q_centro = df_q_comp[df_q_comp["Centro"] == centro]
            if not df_q_centro.empty and "Média" in df_q_centro.columns:
                centro_kpi["Satisfação Média"] = df_q_centro["Média"].mean()
                centro_kpi["Nº Respostas"] = len(df_q_centro)
            else:
                centro_kpi["Satisfação Média"] = None
                centro_kpi["Nº Respostas"] = 0

        kpi_data.append(centro_kpi)

    df_kpi = pd.DataFrame(kpi_data)

    # ---- Tabela comparativa ----
    st.subheader("📊 Comparação Rápida de KPIs")
    st.dataframe(
        df_kpi.style.format({
            "Taxa Conclusão (%)": "{:.1f}%",
            "Taxa Aprovação (%)": "{:.1f}%",
            "Satisfação Média": "{:.2f}"
        }, na_rep="—"),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    # ---- Gráficos comparativos ----
    st.subheader("📈 Visualizações Comparativas")
    col1, col2 = st.columns(2)

    with col1:
        if has_cursos and "Taxa Conclusão (%)" in df_kpi.columns:
            df_conc = df_kpi[["Centro", "Taxa Conclusão (%)"]].dropna()
            if not df_conc.empty:
                fig = px.bar(df_conc, x="Centro", y="Taxa Conclusão (%)",
                             title="Taxa de Conclusão", text="Taxa Conclusão (%)",
                             color="Taxa Conclusão (%)", color_continuous_scale="RdYlGn")
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)

    with col2:
        if has_quest and "Satisfação Média" in df_kpi.columns:
            df_sat = df_kpi[["Centro", "Satisfação Média"]].dropna()
            if not df_sat.empty:
                fig = px.bar(df_sat, x="Centro", y="Satisfação Média",
                             title="Satisfação Média", text="Satisfação Média",
                             color="Satisfação Média", color_continuous_scale="RdYlGn")
                fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)

    # ---- Radar por categoria (apenas se existirem dados de questionário) ----
    if has_quest and "Categoria" in df_quest.columns and "Média" in df_quest.columns:
        st.markdown("---")
        st.subheader("🕸️ Radar Comparativo por Categoria")
        df_radar = df_q_comp.groupby(["Centro", "Categoria"])["Média"].mean().reset_index()
        if not df_radar.empty:
            fig_radar = go.Figure()
            cores = px.colors.qualitative.Set2
            for i, centro in enumerate(selecionados):
                df_centro = df_radar[df_radar["Centro"] == centro]
                if not df_centro.empty:
                    fig_radar.add_trace(go.Scatterpolar(
                        r=df_centro["Média"],
                        theta=df_centro["Categoria"],
                        fill='toself',
                        name=centro,
                        line_color=cores[i % len(cores)],
                        opacity=0.7
                    ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
                showlegend=True,
                height=500
            )
            st.plotly_chart(fig_radar, use_container_width=True)

if __name__ == "__main__":
    mostrar_comparador()