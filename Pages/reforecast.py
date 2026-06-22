import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from openpyxl import load_workbook

COL_REAL_LABEL = "Número REAL"  # rótulo limpo (a coluna real chama-se 'Número \nREAL')


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — Editor do Número REAL no PFE (com filtros, preserva folhas/fórmulas)
# ════════════════════════════════════════════════════════════════════════════
def _achar_folhas_ano(sheet_names, ano):
    """Devolve {tipo: nome_folha} APENAS para as folhas do ano indicado."""
    folhas = {}
    for s in sheet_names:
        sl = s.lower()
        if str(ano) in sl:
            if "vsp" in sl:
                folhas["VSP"] = s
            elif "ld" in sl:
                folhas["LD"] = s
    return folhas


def _col_numero_real_pandas(df):
    for c in df.columns:
        if "real" in str(c).strip().lower():
            return c
    return None


def _idx_col_real_openpyxl(ws):
    for c in range(1, ws.max_column + 1):
        v = ws.cell(row=1, column=c).value
        if v and "real" in str(v).strip().lower():
            return c
    return None


def _orig_real(v):
    return None if pd.isna(v) else float(v)


def _editor_pfe():
    ano = datetime.now().year

    pfe_file = st.file_uploader(
        f"Carregue o ficheiro da projeção anual (PFE). "
        f"Só serão editadas as folhas de **{ano}**; as de outros anos ficam intactas.",
        type=["xlsx", "xls"],
        key="upload_pfe_reforecast",
    )
    if pfe_file is None:
        st.info("⬆️ Carregue a projeção anual para editar o Número REAL.")
        return

    file_bytes = pfe_file.getvalue()  # ler UMA vez (pandas + openpyxl)
    try:
        xl = pd.ExcelFile(BytesIO(file_bytes))
    except Exception as e:
        st.error(f"Erro ao ler o ficheiro: {e}")
        return

    folhas_ano = _achar_folhas_ano(xl.sheet_names, ano)
    if not folhas_ano:
        st.error(f"⚠️ Não encontrei folhas do ano {ano}. Folhas no ficheiro: {xl.sheet_names}")
        return

    st.success(f"✅ Folhas de {ano}: " + " | ".join(f"{t} → '{n}'" for t, n in folhas_ano.items()))
    st.info(
        "✏️ Só a coluna **Número REAL** é editável. Use os filtros para localizar o que "
        "quer alterar; as edições são guardadas por linha e mantêm-se ao mudar o filtro. "
        "Tudo o resto (fórmulas, folhas de outros anos) é preservado no ficheiro descarregado."
    )

    # Reset do store se o ficheiro mudou (evita arrastar edições de um ficheiro anterior)
    if st.session_state.get("_pfe_file_name") != pfe_file.name:
        st.session_state.pfe_real = {}
        st.session_state._pfe_file_name = pfe_file.name
    if "pfe_real" not in st.session_state:
        st.session_state.pfe_real = {}

    for tipo, nome_folha in folhas_ano.items():
        st.markdown(f"### 📄 {nome_folha}")
        df = pd.read_excel(BytesIO(file_bytes), sheet_name=nome_folha)

        col_real = _col_numero_real_pandas(df)
        if col_real is None:
            st.warning(f"A folha '{nome_folha}' não tem coluna 'Número REAL'. Foi ignorada.")
            continue

        df["_row"] = df.index + 2  # linha real do Excel (header = linha 1)

        # Seed do store desta folha {linha_excel: valor original}
        store = st.session_state.pfe_real.setdefault(nome_folha, {})
        for r, v in zip(df["_row"], df[col_real]):
            store.setdefault(int(r), _orig_real(v))

        contexto = [
            c for c in ["Centro de Formação", "Código curso", "Designação completa"]
            if c in df.columns
        ]
        tem_centro = "Centro de Formação" in df.columns
        tem_cod = "Código curso" in df.columns

        # ---- Filtros (por folha) ----
        fc1, fc2 = st.columns(2)
        sel_centro, sel_cod = [], []
        with fc1:
            if tem_centro:
                centros = sorted(df["Centro de Formação"].dropna().astype(str).unique())
                sel_centro = st.multiselect(
                    f"🏢 Centro — {tipo}", centros, default=centros, key=f"pfe_fc_{tipo}"
                )
        with fc2:
            if tem_cod:
                codigos = sorted(df["Código curso"].dropna().astype(str).unique())
                sel_cod = st.multiselect(
                    f"📚 Código curso — {tipo}", codigos, default=codigos, key=f"pfe_fcod_{tipo}"
                )

        df_f = df.copy()
        if tem_centro and sel_centro:
            df_f = df_f[df_f["Centro de Formação"].astype(str).isin(sel_centro)]
        if tem_cod and sel_cod:
            df_f = df_f[df_f["Código curso"].astype(str).isin(sel_cod)]

        if df_f.empty:
            st.info("Nenhuma linha para os filtros selecionados nesta folha.")
        else:
            df_f = df_f.copy()
            df_f[COL_REAL_LABEL] = pd.to_numeric(df_f["_row"].map(store), errors="coerce")

            cols_show = contexto + [COL_REAL_LABEL]
            col_cfg = {c: st.column_config.TextColumn(c, disabled=True) for c in contexto}
            col_cfg[COL_REAL_LABEL] = st.column_config.NumberColumn(
                COL_REAL_LABEL, min_value=0, step=1, format="%d"
            )

            # a chave inclui os filtros: ao mudar, o editor re-semeia a partir do store
            fkey = "c:" + "_".join(sorted(sel_centro)) + "|k:" + "_".join(sorted(sel_cod))
            edit = st.data_editor(
                df_f[cols_show], use_container_width=True, hide_index=True,
                num_rows="fixed", column_config=col_cfg, key=f"pfe_ed_{tipo}_{fkey}",
            )

            # Gravar de volta no store PELA LINHA REAL (nunca pela posição)
            for excel_row, val in zip(df_f["_row"].tolist(), edit[COL_REAL_LABEL].tolist()):
                v = pd.to_numeric(val, errors="coerce")
                store[int(excel_row)] = None if pd.isna(v) else float(v)

        total_folha = sum(v for v in store.values() if v is not None)
        st.caption(f"Σ Número REAL ({tipo}, folha completa): **{total_folha:.0f}** ações")

    # ---- Gerar o ficheiro: aplicar o store a cada folha, preservando o resto ----
    wb = load_workbook(BytesIO(file_bytes))
    for tipo, nome_folha in folhas_ano.items():
        ws = wb[nome_folha]
        c_real = _idx_col_real_openpyxl(ws)
        if c_real is None:
            continue
        store = st.session_state.pfe_real.get(nome_folha, {})
        for excel_row, val in store.items():
            cell = ws.cell(row=int(excel_row), column=c_real)
            if val is None or pd.isna(val):
                cell.value = None
            else:
                fv = float(val)
                cell.value = int(fv) if fv.is_integer() else fv

    out = BytesIO()
    wb.save(out)
    out.seek(0)

    st.markdown("---")
    st.download_button(
        "📥 Descarregar projeção anual editada", data=out.getvalue(),
        file_name=f"PFE_{ano}_editado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — Reprojeção do 2º semestre (snapshot) com filtro por Centro
# ════════════════════════════════════════════════════════════════════════════
def _reforecast_snapshot():
    st.subheader("📁 Carregar snapshot do 1º semestre")

    snap_file = st.file_uploader(
        "Carregue o ficheiro 'reforecast_AAAA-MM-DD.xlsx' exportado na página de Qualidade",
        type=["xlsx", "xls"],
        key="upload_snapshot_reforecast",
    )
    if snap_file is None:
        st.info("⬆️ Carregue o snapshot para começar a reprojeção.")
        return

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

    df['Previstas'] = pd.to_numeric(df['Previstas'], errors='coerce').fillna(0)
    df['Finalizadas'] = pd.to_numeric(df['Finalizadas'], errors='coerce').fillna(0)
    df['_chave'] = (df['Centro'].astype(str).str.strip()
                    + ' || ' + df['Código curso'].astype(str).str.strip())

    data_retrato = str(df['Data Retrato'].iloc[0]) if 'Data Retrato' in df.columns and len(df) else "—"
    st.success(f"✅ Snapshot carregado: **{len(df)}** linhas | Data do retrato: **{data_retrato}**")

    if df['_chave'].duplicated().any():
        n_dup = int(df['_chave'].duplicated().sum())
        st.warning(
            f"⚠️ {n_dup} linha(s) com Centro+Código curso repetido. "
            "Como a edição é gravada por essa combinação, linhas repetidas partilhariam o mesmo alvo. "
            "Confirma que o snapshot tem combinações únicas."
        )

    # Reset dos alvos se o ficheiro mudou
    if st.session_state.get('_reforecast_snap_name') != snap_file.name:
        st.session_state.alvo_reforecast = {}
        st.session_state._reforecast_snap_name = snap_file.name
    if 'alvo_reforecast' not in st.session_state:
        st.session_state.alvo_reforecast = {}

    # Seed: sugestão de alvo = quanto falta para o plano anual original
    sugestao = (df['Previstas'] - df['Finalizadas']).clip(lower=0).astype(int)
    for chave, s in zip(df['_chave'], sugestao):
        st.session_state.alvo_reforecast.setdefault(chave, int(s))

    # ---- Filtro por Centro ----
    st.markdown("---")
    centros = sorted(df['Centro'].dropna().astype(str).unique())
    sel = st.multiselect(
        "🏢 Filtrar por Centro (para análise centro a centro)",
        centros, default=centros, key="reforecast_centro_filter",
    )
    df_view = df[df['Centro'].astype(str).isin(sel)].copy() if sel else df.copy()
    df_view = df_view.reset_index(drop=True)

    if df_view.empty:
        st.info("Nenhuma linha para os centros selecionados.")
        return

    st.subheader("✏️ Definir alvo do 2º semestre")
    st.info(
        "Edite apenas a coluna **Alvo 2º Semestre**. As edições são guardadas por "
        "Centro+Código curso, por isso mantêm-se quando muda o filtro."
    )

    df_view['Alvo 2º Semestre'] = df_view['_chave'].map(st.session_state.alvo_reforecast).fillna(0).astype(int)

    cols_edit = ['Centro', 'Código curso', 'Previstas', 'Finalizadas', 'Alvo 2º Semestre']
    edit = st.data_editor(
        df_view[cols_edit],
        use_container_width=True, hide_index=True, num_rows="fixed",
        column_config={
            "Centro": st.column_config.TextColumn("Centro", disabled=True),
            "Código curso": st.column_config.TextColumn("Código curso", disabled=True),
            "Previstas": st.column_config.NumberColumn("Previstas (anual orig.)", disabled=True),
            "Finalizadas": st.column_config.NumberColumn("Finalizadas (1º sem)", disabled=True),
            "Alvo 2º Semestre": st.column_config.NumberColumn("Alvo 2º Semestre", min_value=0, step=1),
        },
        key="editor_reforecast_" + "_".join(sorted(sel)),
    )

    for chave, alvo in zip(df_view['_chave'].tolist(), edit['Alvo 2º Semestre'].tolist()):
        v = pd.to_numeric(alvo, errors='coerce')
        st.session_state.alvo_reforecast[chave] = 0 if pd.isna(v) else int(v)

    full = df.copy()
    full['Alvo 2º Semestre'] = full['_chave'].map(st.session_state.alvo_reforecast).fillna(0).astype(int)
    full['Novo Total Anual'] = full['Finalizadas'] + full['Alvo 2º Semestre']
    full['Δ vs. Plano Orig.'] = full['Novo Total Anual'] - full['Previstas']

    filt = full[full['Centro'].astype(str).isin(sel)] if sel else full
    parcial = bool(sel) and len(sel) < len(centros)

    st.markdown("---")
    st.subheader("📊 Impacto no 2º semestre" + (f" — {len(sel)} centro(s)" if parcial else " (todos os centros)"))
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Plano anual original", f"{filt['Previstas'].sum():.0f}")
    with c2:
        st.metric("Finalizado (1º sem)", f"{filt['Finalizadas'].sum():.0f}")
    with c3:
        st.metric("Alvo 2º semestre", f"{filt['Alvo 2º Semestre'].sum():.0f}")
    with c4:
        nt = filt['Novo Total Anual'].sum()
        st.metric("Novo total anual", f"{nt:.0f}", delta=f"{nt - filt['Previstas'].sum():+.0f} vs. orig.")
    if parcial:
        st.caption(
            f"🌍 Global (todos os centros): novo total anual = {full['Novo Total Anual'].sum():.0f} "
            f"(plano orig. {full['Previstas'].sum():.0f})"
        )

    cols_final = ['Centro', 'Código curso', 'Previstas', 'Finalizadas',
                  'Alvo 2º Semestre', 'Novo Total Anual', 'Δ vs. Plano Orig.']
    with st.expander("📋 Ver reprojeção detalhada (centros filtrados)", expanded=True):
        st.dataframe(filt[cols_final], use_container_width=True, hide_index=True)

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        full[cols_final].to_excel(writer, index=False, sheet_name="Reprojecao 2Sem")
    buffer.seek(0)
    st.download_button(
        "📥 Baixar reprojeção editada (todos os centros)", data=buffer,
        file_name=f"reprojecao_2sem_{data_retrato}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


def mostrar_reforecast():
    st.header("🔄 Reprojeção do 2º Semestre")
    tab1, tab2 = st.tabs(["✏️ Editar Projeção (Número Real)", "📊 Reprojeção 2º Semestre"])
    with tab1:
        _editor_pfe()
    with tab2:
        _reforecast_snapshot()


if __name__ == "__main__":
    mostrar_reforecast()