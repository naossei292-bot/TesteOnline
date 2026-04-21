import io

import streamlit as st
import pandas as pd
import re

# ─────────────────────────────────────────────────────────────
# Metadados fixos por folha
# ─────────────────────────────────────────────────────────────
SHEET_META = {
    "21a": {"Respondente": "Formando",              "Modalidade": "Presencial",   "Tipo": "Módulo"},
    "21b": {"Respondente": "Formando",              "Modalidade": "À Distância",  "Tipo": "Módulo"},
    "22a": {"Respondente": "Formando",              "Modalidade": "Presencial",   "Tipo": "Ação"},
    "22b": {"Respondente": "Formando",              "Modalidade": "À Distância",  "Tipo": "Ação"},
    "23a": {"Respondente": "Formador",              "Modalidade": "Presencial",   "Tipo": "Ação"},
    "23b": {"Respondente": "Tutor",                 "Modalidade": "À Distância",  "Tipo": "Ação"},
    "24a": {"Respondente": "Coordenação Pedagógica","Modalidade": "Presencial",   "Tipo": "Formador"},
    "24b": {"Respondente": "Coordenação Pedagógica","Modalidade": "À Distância",  "Tipo": "Tutor"},
}

RE_PERGUNTA  = re.compile(r'^[A-Z]\d{2}\s*[-–]')
RE_CATEGORIA = re.compile(r'^([A-Z])\d{2}')
IGNORAR = {
    "FIM DE TABELA", "começo de tabela", "Column1", "Categorias/Subcategorias",
    "Resultados por categoria", "Nº total de Formandos",
    "Nº de respostas:", "% Respostas:", "Ref. da ação",
}


def _extrair_uma_coluna(df: pd.DataFrame, col_pergunta: int, col_media: int,
                        centro: str, sheet_name: str) -> list[dict]:
    meta = SHEET_META.get(sheet_name, {"Respondente": sheet_name,
                                       "Modalidade": "?", "Tipo": "?"})
    registos = []
    curso_atual   = None
    n_formandos   = None
    n_respostas   = None
    pct_respostas = None
    dentro_bloco  = False

    for _, row in df.iterrows():
        cel0 = row[col_pergunta]
        cel1 = row[col_media]
        s0 = str(cel0).strip() if pd.notna(cel0) else ""
        s1 = str(cel1).strip() if pd.notna(cel1) else ""

        if s0 == "Curso":
            curso_atual   = s1 if s1 not in ("", "nan") else None
            n_formandos   = None
            n_respostas   = None
            pct_respostas = None
            dentro_bloco  = True
            continue

        if not dentro_bloco:
            continue

        if s0 == "Nº total de Formandos":
            try: n_formandos = float(cel1)
            except: pass
            continue
        if s0 == "Nº de respostas:":
            try: n_respostas = float(cel1)
            except: pass
            continue
        if s0 == "% Respostas:":
            try: pct_respostas = float(cel1)
            except: pass
            continue

        if s0.startswith("FIM DE TABELA"):
            dentro_bloco = False
            curso_atual  = None
            continue
        if s0 in IGNORAR or not s0:
            continue
        if re.match(r'^[A-Z] [-–]', s0):
            continue

        if RE_PERGUNTA.match(s0) and curso_atual:
            m = RE_CATEGORIA.match(s0)
            categoria = m.group(1) if m else "Outra"
            try:
                media_val = float(cel1)
                media_exibida = f"{media_val:.0f}%" if "%" in s0 else media_val
            except:
                media_exibida = None

            registos.append({
                "Centro":       centro,
                "Curso":        curso_atual,
                "Folha":        sheet_name,
                "Respondente":  meta["Respondente"],
                "Modalidade":   meta["Modalidade"],
                "Tipo":         meta["Tipo"],
                "Categoria":    categoria,
                "Pergunta":     s0,
                "Média":        media_exibida,
                "Nº Formandos": n_formandos,
                "Nº Respostas": n_respostas,
                "% Respostas":  pct_respostas,
            })
    return registos


def extrair_centro_do_nome(nome: str) -> str:
    nome_sem_ext = nome.rsplit(".", 1)[0]
    parts = re.split(r"[_\-]", nome_sem_ext)
    for part in reversed(parts):
        part = part.strip()
        if part and re.match(r'^[A-Za-zÀ-ÿ]', part):
            return part.capitalize()
    return ""


def processar_relatorio(ficheiro, modo="left_only") -> pd.DataFrame:
    centro = extrair_centro_do_nome(ficheiro.name)
    xls    = pd.ExcelFile(ficheiro)
    todos  = []

    for sheet_name in xls.sheet_names:
        if sheet_name not in SHEET_META:
            continue
        df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        todos.extend(_extrair_uma_coluna(df, 0, 1, centro, sheet_name))
        if modo == "both":
            regs_dir = _extrair_uma_coluna(df, 3, 4, centro, sheet_name)
            for r in regs_dir:
                r["Agregado"] = True
            todos.extend(regs_dir)

    df_out = pd.DataFrame(todos)
    if not df_out.empty and "Agregado" not in df_out.columns:
        df_out["Agregado"] = False
    return df_out


# ─────────────────────────────────────────────────────────────
# Página Streamlit
# ─────────────────────────────────────────────────────────────
def mostrar_questionarios():
    st.header("📋 Base de Dados de Satisfação")

    COLUNAS_DADOS = [
        "Centro", "Curso", "Folha", "Respondente", "Modalidade",
        "Tipo", "Categoria", "Pergunta", "Média",
        "Nº Formandos", "Nº Respostas", "% Respostas",
    ]
    COLUNAS_COM_APAGAR = ["Apagar"] + COLUNAS_DADOS

    # ── Inicializar contadores de key ──────────────────────────
    # quest_uploader_key: muda a key do file_uploader após cada upload,
    #   fazendo o Streamlit criar um widget novo e limpar os ficheiros.
    #   Sem isto, após st.rerun() o uploader ainda "vê" os ficheiros
    #   e processa-os de novo em loop infinito.
    # quest_editor_key: muda a key do data_editor para forçar
    #   re-renderização com os dados novos.
    for key in ("quest_uploader_key", "quest_editor_key"):
        if key not in st.session_state:
            st.session_state[key] = 0

    # --- Seletor de colunas ---
    if "colunas_quest_selecionadas" not in st.session_state:
        st.session_state.colunas_quest_selecionadas = COLUNAS_DADOS.copy()

    st.subheader("📋 Escolha as colunas que pretende visualizar/editar")
    colunas_escolhidas = st.multiselect(
        "Selecione as colunas (a coluna 'Apagar' é sempre mostrada):",
        options=COLUNAS_DADOS,
        default=st.session_state.colunas_quest_selecionadas,
        key="seletor_colunas_quest",
    )

    if st.button("🗑️ Remover colunas não selecionadas", use_container_width=True):
        st.session_state.colunas_quest_selecionadas = colunas_escolhidas
        if "quest_editaveis" in st.session_state and not st.session_state.quest_editaveis.empty:
            df_at = st.session_state.quest_editaveis
            if "Apagar" in df_at.columns:
                apagar  = df_at["Apagar"]
                outras  = {c: df_at[c] for c in st.session_state.colunas_quest_selecionadas if c in df_at.columns}
                novo_df = pd.DataFrame(outras)
                novo_df.insert(0, "Apagar", apagar)
                st.session_state.quest_editaveis = novo_df
            else:
                st.session_state.quest_editaveis = pd.DataFrame(columns=COLUNAS_COM_APAGAR)
        st.session_state.quest_editor_key += 1
        st.rerun()

    colunas_dados      = st.session_state.colunas_quest_selecionadas
    colunas_com_apagar = ["Apagar"] + colunas_dados

    if "quest_editaveis" not in st.session_state:
        st.session_state.quest_editaveis = pd.DataFrame(columns=colunas_com_apagar)

    # ── Carregar ficheiros ──────────────────────────────────────
    st.subheader("📤 Carregar Relatórios Excel")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        modo_carga = st.radio(
            "Modo:", ["Substituir dados existentes", "Adicionar ao final"],
            horizontal=True, key="modo_carga_quest",
        )
    with c2:
        # KEY DINÂMICA — essencial para limpar o uploader após cada upload
        ficheiros = st.file_uploader(
            "Relatórios Excel (Relatório_Centro.xlsx)",
            type=None,
            accept_multiple_files=True,
            key=f"carga_quest_upload_{st.session_state.quest_uploader_key}",
        )
    with c3:
        try:
            with open("assets/Relatório_Alverca.xlsx", "rb") as f:
                conteudo_exemplo = f.read()
            st.download_button(
                label="📥 Descarregar ficheiro exemplo preenchido (Excel)",
                data=conteudo_exemplo,
                file_name="Relatório_Alverca.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except FileNotFoundError:
            st.error("⚠️ Ficheiro de exemplo não encontrado. Verifique o caminho 'assets/Relatório_Alverca.xlsx'.")
    with c4:
        try:
            with open("assets/Questionario_para_preencher.xlsx", "rb") as f:
                conteudo_exemplo = f.read()
            st.download_button(
                label="📥 Descarregar ficheiro exemplo vazio (Excel)",
                data=conteudo_exemplo,
                file_name="Questionario_para_preencher.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except FileNotFoundError:
            st.error("⚠️ Ficheiro de exemplo vazio não encontrado. Verifique o caminho 'assets/Questionario_para_preencher.xlsx'.")

    if ficheiros:
        lista_dfs = []
        for f in ficheiros:
            nome = f.name.lower()
            try:
                if nome.endswith(".xlsx"):
                    df_novo = processar_relatorio(f, modo="left_only")
                    if df_novo.empty:
                        st.warning(f"⚠️ Sem dados extraídos de: {f.name}")
                        continue
                    for col in COLUNAS_DADOS:
                        if col not in df_novo.columns:
                            df_novo[col] = None
                    df_novo = df_novo[colunas_dados]
                    df_novo.insert(0, "Apagar", False)
                    lista_dfs.append(df_novo)
                    st.success(f"✅ {f.name} → {len(df_novo)} perguntas de {df_novo['Curso'].nunique()} cursos")
                elif nome.endswith(".csv"):
                    df_csv = pd.read_csv(f)
                    df_csv.columns = df_csv.columns.str.strip()
                    for col in colunas_dados:
                        if col not in df_csv.columns:
                            df_csv[col] = None
                    df_csv = df_csv[colunas_dados]
                    df_csv.insert(0, "Apagar", False)
                    lista_dfs.append(df_csv)
                else:
                    st.warning(f"Formato não suportado: {f.name}")
            except Exception as e:
                st.error(f"Erro em {f.name}: {e}")

        if lista_dfs:
            df_total = pd.concat(lista_dfs, ignore_index=True)
            if modo_carga == "Substituir dados existentes":
                st.session_state.quest_editaveis = df_total
            else:
                st.session_state.quest_editaveis = pd.concat(
                    [st.session_state.quest_editaveis, df_total], ignore_index=True
                )
            # Incrementar AMBAS as keys antes do rerun:
            # uploader_key → o file_uploader vai ter uma key nova na próxima
            #                renderização, aparecendo vazio (sem os ficheiros antigos)
            # editor_key   → o data_editor vai ser recriado com os dados novos
            st.session_state.quest_uploader_key += 1
            st.session_state.quest_editor_key   += 1
            st.rerun()

    # ── DataFrame atual ────────────────────────────────────────
    df_atual = st.session_state.quest_editaveis.copy()
    if "Apagar" not in df_atual.columns:
        df_atual.insert(0, "Apagar", False)

    # ── Filtros de visualização ────────────────────────────────
    with st.expander("🔍 Filtrar visualização (consulta apenas)"):
        if not df_atual.empty:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                modalidades = sorted(df_atual["Modalidade"].dropna().unique()) if "Modalidade" in df_atual.columns else []
                filtro_modalidade = st.multiselect("Modalidade", modalidades, default=modalidades, key="filtro_modalidade")
            with col_f2:
                respondentes = sorted(df_atual["Respondente"].dropna().unique()) if "Respondente" in df_atual.columns else []
                filtro_respondente = st.multiselect("Respondente", respondentes, default=respondentes, key="filtro_respondente")

            col_f3, col_f4 = st.columns(2)
            with col_f3:
                cursos = sorted(df_atual["Curso"].dropna().unique()) if "Curso" in df_atual.columns else []
                filtro_curso = st.multiselect("Curso", cursos, default=cursos, key="filtro_curso")
            with col_f4:
                categorias = sorted(df_atual["Categoria"].dropna().unique()) if "Categoria" in df_atual.columns else []
                filtro_categoria = st.multiselect("Categoria", categorias, default=categorias, key="filtro_categoria")

            df_temp = df_atual.copy()
            if filtro_modalidade:
                df_temp = df_temp[df_temp["Modalidade"].isin(filtro_modalidade)]
            if filtro_respondente:
                df_temp = df_temp[df_temp["Respondente"].isin(filtro_respondente)]
            if filtro_curso:
                df_temp = df_temp[df_temp["Curso"].isin(filtro_curso)]
            if filtro_categoria:
                df_temp = df_temp[df_temp["Categoria"].isin(filtro_categoria)]

            perguntas = sorted(df_temp["Pergunta"].dropna().unique()) if "Pergunta" in df_temp.columns else []
            filtro_pergunta = st.multiselect("Pergunta", perguntas, default=perguntas, key="filtro_pergunta")

            df_filtrado = df_temp.copy()
            if filtro_pergunta:
                df_filtrado = df_filtrado[df_filtrado["Pergunta"].isin(filtro_pergunta)]

            if not df_filtrado.empty:
                st.markdown(f"**📋 Visualização filtrada:** {len(df_filtrado)} registos")
                st.dataframe(df_filtrado.drop(columns=["Apagar"], errors="ignore"), use_container_width=True)
            else:
                st.info("Nenhum registo corresponde aos filtros selecionados.")
        else:
            st.info("Carregue ficheiros para ativar os filtros.")

    # ── Adicionar linhas ───────────────────────────────────────
    st.markdown("---")
    st.subheader("➕ Adicionar linhas")
    col_add1, col_add2 = st.columns([1, 2])
    with col_add1:
        num_linhas = st.number_input("Nº de linhas", min_value=1, max_value=10000,
                                     value=5, step=1, key="num_linhas_quest")
    with col_add2:
        if st.button("➕ Adicionar múltiplas linhas vazias", use_container_width=True):
            novas_linhas = pd.DataFrame({col: [None] * num_linhas for col in colunas_dados})
            novas_linhas.insert(0, "Apagar", False)
            st.session_state.quest_editaveis = pd.concat(
                [st.session_state.quest_editaveis, novas_linhas], ignore_index=True
            )
            st.session_state.quest_editor_key += 1
            st.rerun()

    # ── Tabela editável ────────────────────────────────────────
    st.markdown("---")
    st.subheader("✏️ Tabela de questionários (edição completa)")

    edited_df = st.data_editor(
        df_atual,
        use_container_width=True,
        num_rows="dynamic",
        height=420,
        key=f"quest_editor_{st.session_state.quest_editor_key}",
        column_config={"Apagar": st.column_config.CheckboxColumn("Apagar", default=False)},
    )

    if not edited_df.equals(df_atual):
        st.session_state.quest_editaveis = edited_df
        st.session_state.quest_editor_key += 1
        st.rerun()

    # ── Botões de eliminação ───────────────────────────────────
    st.markdown("---")
    cb1, cb2 = st.columns(2)
    with cb1:
        if st.button("🗑️ Limpar todos os dados", use_container_width=True):
            st.session_state.quest_editaveis = pd.DataFrame(columns=colunas_com_apagar)
            st.session_state.quest_editor_key += 1
            st.rerun()
    with cb2:
        if st.button("✖️ Apagar selecionados", use_container_width=True):
            df = st.session_state.quest_editaveis.copy()
            mask = df.get("Apagar", pd.Series(False, index=df.index)) == True
            if mask.any():
                df = df[~mask].reset_index(drop=True)
                df["Apagar"] = False
                st.session_state.quest_editaveis = df
                st.session_state.quest_editor_key += 1
                st.rerun()
            else:
                st.warning("Nenhuma linha marcada.")

    # ── Exportar dados ─────────────────────────────────────────
    st.markdown("---")
    st.subheader("📎 Exportar dados")

    df_export = st.session_state.quest_editaveis.drop(columns=["Apagar"], errors="ignore")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False, sheet_name="Questionários")
    output.seek(0)

    st.download_button(
        label="📥 Descarregar dados em Excel",
        data=output,
        file_name="dados_questionarios_exportados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key="download_questionarios_excel",
    )

    # ── Métricas ───────────────────────────────────────────────
    df_m = st.session_state.quest_editaveis.drop(columns=["Apagar"], errors="ignore")
    if "Curso" in df_m.columns:
        df_m = df_m[df_m["Curso"].notna()]
        df_m = df_m[~df_m["Curso"].astype(str).str.strip().isin(["", "None", "nan"])]

    if not df_m.empty:
        st.markdown("---")
        st.subheader("📊 Resumo Geral")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Centros",  df_m["Centro"].nunique() if "Centro" in df_m.columns else 0)
        m2.metric("Cursos",   df_m["Curso"].nunique())
        m3.metric("Registos", len(df_m))
        media_col   = pd.to_numeric(df_m["Média"], errors="coerce").dropna()
        media_geral = media_col.mean() if not media_col.empty else 0
        m4.metric("Média Geral", f"{media_geral:.2f}")

        if "Centro" in df_m.columns:
            centros = sorted(df_m["Centro"].dropna().unique())
            if centros:
                st.caption(f"🏢 Centros carregados: {', '.join(centros)}")

        if all(c in df_m.columns for c in ["Centro", "Respondente", "Categoria"]):
            df_m = df_m.copy()
            df_m["Média_num"] = pd.to_numeric(df_m["Média"], errors="coerce")
            resumo = (
                df_m.groupby(["Centro", "Respondente", "Categoria"])["Média_num"]
                .mean()
                .round(3)
                .reset_index()
                .rename(columns={"Média_num": "Média Categoria"})
            )
            if not resumo.empty:
                st.subheader("📋 Médias por Centro / Respondente / Categoria")
                st.dataframe(resumo, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ Carregue ficheiros Excel para ver os dados.")


if __name__ == "__main__":
    mostrar_questionarios()