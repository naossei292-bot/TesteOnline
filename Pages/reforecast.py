import streamlit as st
import pandas as pd
from io import BytesIO


def mostrar_reforecast():
    st.header("🔄 Reprojeção do 2º Semestre")

    st.markdown("---")
    st.subheader("📁 Carregar snapshot do 1º semestre")

    snap_file = st.file_uploader(
        "Carregue o ficheiro 'reforecast_AAAA-MM-DD.xlsx' exportado na página de Qualidade",
        type=["xlsx", "xls"],
        key="upload_snapshot_reforecast"
    )

    if snap_file is None:
        st.info("⬆️ Carregue o snapshot para começar a reprojeção.")
        return

    # --- Ler e validar o snapshot ---
    try:
        df = pd.read_excel(snap_file)
    except Exception as e:
        st.error(f"Erro ao ler o ficheiro: {e}")
        return

    obrigatorias = ['Centro', 'Código curso', 'Previstas', 'Finalizadas']
    em_falta = [c for c in obrigatorias if c not in df.columns]
    if em_falta:
        st.error(f"Colunas obrigatórias em falta: {em_falta}")
        st.info(f"Colunas encontradas: {list(df.columns)}")
        return

    # Garantir tipos numéricos
    df['Previstas'] = pd.to_numeric(df['Previstas'], errors='coerce').fillna(0)
    df['Finalizadas'] = pd.to_numeric(df['Finalizadas'], errors='coerce').fillna(0)

    data_retrato = str(df['Data Retrato'].iloc[0]) if 'Data Retrato' in df.columns and len(df) else "—"
    st.success(f"✅ Snapshot carregado: **{len(df)}** linhas | Data do retrato: **{data_retrato}**")

    # --- Preparar tabela editável ---
    df_edit = df[['Centro', 'Código curso', 'Previstas', 'Finalizadas']].copy()
    # Quanto faltaria para cumprir o alvo anual original (sugestão de ponto de partida)
    falta_original = (df_edit['Previstas'] - df_edit['Finalizadas']).clip(lower=0)
    df_edit['Alvo 2º Semestre'] = falta_original.astype(int)

    st.markdown("---")
    st.subheader("✏️ Definir alvo do 2º semestre")
    st.info(
        "Edite apenas a coluna **Alvo 2º Semestre**. "
        "A coluna *Finalizadas* é o histórico do 1º semestre e está bloqueada. "
        "O *Novo Total Anual* é calculado automaticamente."
    )

    edited = st.data_editor(
        df_edit,
        use_container_width=True,
        column_config={
            "Centro": st.column_config.TextColumn("Centro", disabled=True),
            "Código curso": st.column_config.TextColumn("Código curso", disabled=True),
            "Previstas": st.column_config.NumberColumn("Previstas (anual orig.)", disabled=True),
            "Finalizadas": st.column_config.NumberColumn("Finalizadas (1º sem)", disabled=True),
            "Alvo 2º Semestre": st.column_config.NumberColumn("Alvo 2º Semestre", min_value=0, step=1),
        },
        key="editor_reforecast",
        hide_index=True,
    )

    # --- Recalcular com base no que foi editado ---
    res = edited.copy()
    res['Alvo 2º Semestre'] = pd.to_numeric(res['Alvo 2º Semestre'], errors='coerce').fillna(0)
    res['Novo Total Anual'] = res['Finalizadas'] + res['Alvo 2º Semestre']
    # Diferença face ao plano anual original (positivo = subiu a fasquia; negativo = baixou)
    res['Δ vs. Plano Orig.'] = res['Novo Total Anual'] - res['Previstas']

    # --- Resumo agregado ---
    st.markdown("---")
    st.subheader("📊 Impacto no total anual")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Plano anual original", f"{res['Previstas'].sum():.0f}")
    with c2:
        st.metric("Finalizado (1º sem)", f"{res['Finalizadas'].sum():.0f}")
    with c3:
        st.metric("Alvo 2º semestre", f"{res['Alvo 2º Semestre'].sum():.0f}")
    with c4:
        novo_total = res['Novo Total Anual'].sum()
        delta = novo_total - res['Previstas'].sum()
        st.metric("Novo total anual", f"{novo_total:.0f}", delta=f"{delta:+.0f} vs. orig.")

    # --- Tabela final calculada ---
    with st.expander("📋 Ver reprojeção detalhada", expanded=True):
        st.dataframe(res, use_container_width=True, hide_index=True)

    # --- Download do resultado editado ---
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        res.to_excel(writer, index=False, sheet_name="Reprojecao 2Sem")
    buffer.seek(0)

    st.download_button(
        label="📥 Baixar reprojeção editada",
        data=buffer,
        file_name=f"reprojecao_2sem_{data_retrato}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

if __name__ == "__main__":
    mostrar_reforecast()