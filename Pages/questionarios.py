import io
import re

import streamlit as st
import pandas as pd

# ─────────────────────────────────────────────────────────────
# Parsing helpers
# ─────────────────────────────────────────────────────────────

# item formats aceites:
#   M00_21b.A01  → Módulo=M00, Folha=21b, Pergunta=A01
#   23a.D01      → Módulo=None, Folha=23a, Pergunta=D01
RE_ITEM = re.compile(r'^(?:(M\d+)_)?([^.]+)\.(.+)$')

FOLHA_META = {
    "21a": {"Respondente": "Formando",               "Modalidade": "Presencial",  "Tipo": "Módulo"},
    "21b": {"Respondente": "Formando",               "Modalidade": "À Distância", "Tipo": "Módulo"},
    "22a": {"Respondente": "Formando",               "Modalidade": "Presencial",  "Tipo": "Ação"},
    "22b": {"Respondente": "Formando",               "Modalidade": "À Distância", "Tipo": "Ação"},
    "23a": {"Respondente": "Formador",               "Modalidade": "Presencial",  "Tipo": "Ação"},
    "23b": {"Respondente": "Tutor",                  "Modalidade": "À Distância", "Tipo": "Ação"},
    "24a": {"Respondente": "Coordenação Pedagógica", "Modalidade": "Presencial",  "Tipo": "Formador"},
    "24b": {"Respondente": "Coordenação Pedagógica", "Modalidade": "À Distância", "Tipo": "Tutor"},
}


def parsear_item(item_str: str) -> dict:
    """Parseia item → {Módulo, Folha, Pergunta, Respondente, Modalidade, Tipo}.
    Aceita formato com módulo (M00_21b.A01) e sem módulo (23a.D01).
    Corrige duplo underscore automaticamente (ex: M00__21b → M00_21b)."""
    
    # NORMALIZAÇÃO: substitui duplo underscore por simples
    item_str = str(item_str).strip().replace("__", "_")
    
    m = RE_ITEM.match(item_str)
    if not m:
        return {"Módulo": None, "Folha": None, "Pergunta": None,
                "Respondente": None, "Modalidade": None, "Tipo": None}
    modulo  = m.group(1)          # None se não tiver prefixo M00_
    folha   = m.group(2)
    pergunta = m.group(3)
    meta = FOLHA_META.get(folha, {"Respondente": None, "Modalidade": None, "Tipo": None})
    return {
        "Módulo":      modulo,
        "Folha":       folha,
        "Pergunta":    pergunta,
        "Respondente": meta["Respondente"],
        "Modalidade":  meta["Modalidade"],
        "Tipo":        meta["Tipo"],
    }

def processar_acoes_xlsx(ficheiro) -> pd.DataFrame:
    """Lê ações_por_centro.xlsx → DataFrame com Ação, Datini, Datfim, Centro, U_status.
       Cria também uma chave normalizada _acao_key para merge case‑insensitive."""
    import unicodedata

    df = pd.read_excel(ficheiro)
    df.columns = df.columns.str.strip()

    # Normalizar strings em todas as colunas (remove espaços)
    for col in df.columns:
        try:
            stripped = df[col].astype(str).str.strip()
            df[col] = stripped.where(df[col].notna(), other=None)
        except Exception:
            pass

    def norm(s):
        return unicodedata.normalize("NFC", str(s)).lower().strip()

    rename = {}
    for col in df.columns:
        cn = norm(col)
        if cn in ("ação", "acao"):
            rename[col] = "Ação"
        elif cn == "datini":
            rename[col] = "Datini"
        elif cn == "datfim":
            rename[col] = "Datfim"
        elif cn == "deslocal":
            rename[col] = "Centro"
        elif cn in ("u_status", "ustatus", "status"):
            rename[col] = "U_status"

    df = df.rename(columns=rename)

    # Garantir colunas necessárias
    colunas_necessarias = ["Ação", "Datini", "Datfim", "Centro", "U_status"]
    for col in colunas_necessarias:
        if col not in df.columns:
            df[col] = None

    # Criar chave normalizada para merge (case‑insensitive, sem espaços)
    df["_acao_key"] = df["Ação"].astype(str).str.strip().str.lower()

    return df[colunas_necessarias + ["_acao_key"]].copy()


def processar_csv(ficheiro) -> pd.DataFrame:
    """Lê mdl_course.csv → DataFrame com colunas expandidas e chave normalizada."""
    try:
        df = pd.read_csv(ficheiro, sep=";", encoding="utf-8")
    except UnicodeDecodeError:
        ficheiro.seek(0)
        df = pd.read_csv(ficheiro, sep=";", encoding="latin-1")

    df.columns = df.columns.str.strip()

    # Expandir item (com correção de duplo underscore)
    parsed = df["item"].apply(parsear_item).apply(pd.Series)
    df = pd.concat([df, parsed], axis=1)

    df["valor_medio"] = pd.to_numeric(df["valor_medio"], errors="coerce")

    df = df.rename(columns={
        "shortname":   "Shortname",
        "data_ini":    "Data",
        "item":        "Item",
        "valor_medio": "Valor Médio",
    })

    # Criar chave normalizada para merge
    df["_shortname_key"] = df["Shortname"].astype(str).str.strip().str.lower()

    return df


def juntar_dados(df_csv: pd.DataFrame, df_acoes: pd.DataFrame) -> pd.DataFrame:
    """
    Faz o join usando as chaves normalizadas (_shortname_key e _acao_key).
    Traz Centro, Datini, Datfim e U_status do Excel.
    """
    if df_acoes.empty:
        df_csv["Centro"]   = None
        df_csv["Datini"]   = None
        df_csv["Datfim"]   = None
        df_csv["U_status"] = None
        return df_csv

    # Selecionar colunas do Excel necessárias, incluindo a chave normalizada
    cols_join = ["_acao_key", "Datini", "Datfim", "Centro", "U_status"]
    df_join = df_acoes[cols_join].rename(columns={"_acao_key": "_shortname_key"})

    # Merge usando a chave normalizada
    df_resultado = df_csv.merge(df_join, on="_shortname_key", how="left")

    # Remover as colunas auxiliares (opcional, mas fica mais limpo)
    df_resultado.drop(columns=["_shortname_key"], inplace=True, errors="ignore")

    return df_resultado


# ─────────────────────────────────────────────────────────────
# Funções auxiliares de estado (igual à página de cursos)
# ─────────────────────────────────────────────────────────────

COLUNAS_DADOS = [
    "Shortname", "Centro", "Datini", "Datfim", "U_status",
    "Módulo", "Folha", "Pergunta", "Item",
    "Respondente", "Modalidade", "Tipo",
    "Valor Médio", "Data",
]


def garantir_todas_colunas(df: pd.DataFrame) -> pd.DataFrame:
    for col in COLUNAS_DADOS:
        if col not in df.columns:
            df[col] = None
    if "Apagar" not in df.columns:
        df.insert(0, "Apagar", False)
    cols = ["Apagar"] + [c for c in COLUNAS_DADOS if c in df.columns]
    return df[cols]


def dfs_diferentes(df1: pd.DataFrame, df2: pd.DataFrame) -> bool:
    if df1.shape != df2.shape:
        return True
    try:
        return not df1.fillna("__NA__").astype(str).equals(
            df2.fillna("__NA__").astype(str)
        )
    except Exception:
        return True


def _gerar_excel_com_filtros(df: pd.DataFrame) -> io.BytesIO:
    """Gera um Excel formatado com AutoFilter nativo em todas as colunas."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Questionários"

    # ── Estilos ──────────────────────────────────────────────
    COR_CABECALHO  = "1F4E79"   # azul escuro
    COR_FILTRO     = "2E75B6"   # azul médio para colunas de filtro principais
    COLS_DESTAQUE  = {"Centro", "Shortname", "Datini", "Datfim", "Respondente"}

    header_base = Font(bold=True, color="FFFFFF", name="Arial", size=10)
    header_fill_principal = PatternFill("solid", fgColor=COR_FILTRO)
    header_fill_normal    = PatternFill("solid", fgColor=COR_CABECALHO)
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left   = Alignment(horizontal="left",   vertical="center")
    borda_fina = Border(
        left=Side(style="thin", color="BFBFBF"),
        right=Side(style="thin", color="BFBFBF"),
        bottom=Side(style="thin", color="BFBFBF"),
    )

    cols = list(df.columns)

    # ── Cabeçalho ─────────────────────────────────────────────
    ws.row_dimensions[1].height = 30
    for ci, col_name in enumerate(cols, start=1):
        cell = ws.cell(row=1, column=ci, value=col_name)
        cell.font  = header_base
        cell.fill  = header_fill_principal if col_name in COLS_DESTAQUE else header_fill_normal
        cell.alignment = align_center
        cell.border = borda_fina

    # ── Dados ─────────────────────────────────────────────────
    fill_par   = PatternFill("solid", fgColor="DCE6F1")   # azul muito claro
    fill_impar = PatternFill("solid", fgColor="FFFFFF")
    fonte_dado = Font(name="Arial", size=9)

    for ri, row_data in enumerate(df.itertuples(index=False), start=2):
        fill = fill_par if ri % 2 == 0 else fill_impar
        for ci, value in enumerate(row_data, start=1):
            cell = ws.cell(row=ri, column=ci, value=value)
            cell.font      = fonte_dado
            cell.fill      = fill
            cell.alignment = align_left
            cell.border    = borda_fina

    # ── Larguras de coluna automáticas ────────────────────────
    LARGURAS = {
        "Centro": 14, "Shortname": 18, "Datini": 13, "Datfim": 13,
        "Respondente": 22, "Modalidade": 14, "Tipo": 12,
        "Módulo": 10, "Folha": 10, "Pergunta": 12, "Item": 18,
        "Valor Médio": 13, "Data": 13,
    }
    for ci, col_name in enumerate(cols, start=1):
        largura = LARGURAS.get(col_name, 16)
        ws.column_dimensions[get_column_letter(ci)].width = largura

    # ── Congelar primeira linha ────────────────────────────────
    ws.freeze_panes = "A2"

    # ── AutoFilter em todas as colunas ────────────────────────
    ultima_col = get_column_letter(len(cols))
    ws.auto_filter.ref = f"A1:{ultima_col}{ws.max_row}"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────
# Página Streamlit
# ─────────────────────────────────────────────────────────────

def mostrar_questionarios():
    st.header("📋 Base de Dados de Satisfação")

    COLUNAS_COM_APAGAR = ["Apagar"] + COLUNAS_DADOS

    # ── Inicializar estado ─────────────────────────────────────
    if "quest_uploader_key" not in st.session_state:
        st.session_state.quest_uploader_key = 0
    if "quest_editor_key" not in st.session_state:
        st.session_state.quest_editor_key = 0
    if "quest_editaveis" not in st.session_state:
        st.session_state.quest_editaveis = pd.DataFrame(columns=COLUNAS_COM_APAGAR)
    if "quest_acoes_df" not in st.session_state:
        st.session_state.quest_acoes_df = pd.DataFrame(
            columns=["Ação", "Datini", "Datfim", "Centro", "U_status"]
        )

    # Garantir todas as colunas no estado atual
    st.session_state.quest_editaveis = garantir_todas_colunas(
        st.session_state.quest_editaveis.copy()
    )

    # (exportação inclui sempre todas as colunas, ordenadas com as de filtro à esquerda)

    # ── Carregar ficheiros ──────────────────────────────────────
    st.subheader("📤 Carregar Ficheiros")

    st.info(
        "**Ficheiro de Ações (Excel):** `ações_por_centro.xlsx` — fornece Ação, Datini, Datfim, Centro.  \n"
        "**Ficheiro de Questionários (CSV):** `mdl_course.csv` — fornece Shortname, Item, Valor Médio.  \n"
        "A correlação é feita automaticamente: **Shortname (CSV) = Ação (Excel)**."
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        modo_carga = st.radio(
            "Modo:", ["Substituir dados existentes", "Adicionar ao final"],
            horizontal=True, key="modo_carga_quest",
        )
    with c2:
        ficheiros = st.file_uploader(
            "Carregar ficheiros (Excel de Ações e/ou CSV de Questionários)",
            type=None,
            accept_multiple_files=True,
            key=f"carga_quest_upload_{st.session_state.quest_uploader_key}",
        )
    with c3:
        # Botão de reset
        if st.button("🗑️ Limpar todos os dados", use_container_width=True, key="btn_limpar_quest"):
            st.session_state.quest_editaveis = pd.DataFrame(columns=COLUNAS_COM_APAGAR)
            st.session_state.quest_acoes_df = pd.DataFrame(
                columns=["Ação", "Datini", "Datfim", "Centro", "U_status"]
            )
            st.session_state.quest_excel_cache = None
            st.session_state.quest_editor_key += 1
            st.rerun()

    if ficheiros:
        dfs_csv   = []
        dfs_acoes = []

        for f in ficheiros:
            nome = f.name.lower()
            try:
                if nome.endswith(".xlsx") or nome.endswith(".xls"):
                    df_acao = processar_acoes_xlsx(f)
                    if df_acao.empty:
                        st.warning(f"⚠️ Sem dados extraídos de: {f.name}")
                    else:
                        dfs_acoes.append(df_acao)
                        st.success(f"✅ {f.name} → {len(df_acao)} ações carregadas")

                elif nome.endswith(".csv"):
                    df_csv = processar_csv(f)
                    if df_csv.empty:
                        st.warning(f"⚠️ Sem dados extraídos de: {f.name}")
                    else:
                        dfs_csv.append(df_csv)
                        st.success(f"✅ {f.name} → {len(df_csv)} registos, {df_csv['Shortname'].nunique()} cursos")
                else:
                    st.warning(f"Formato não suportado: {f.name}")

            except Exception as e:
                st.error(f"Erro em {f.name}: {e}")

        if dfs_acoes:
            df_acoes_novo = pd.concat(dfs_acoes, ignore_index=True).drop_duplicates(subset=["Ação"])
            if modo_carga == "Substituir dados existentes":
                st.session_state.quest_acoes_df = df_acoes_novo
            else:
                st.session_state.quest_acoes_df = pd.concat(
                    [st.session_state.quest_acoes_df, df_acoes_novo], ignore_index=True
                ).drop_duplicates(subset=["Ação"])
            # Forçar re-join se já há CSV carregado
            if not st.session_state.quest_editaveis.drop(columns=["Apagar"], errors="ignore").empty:
                df_csv_atual = st.session_state.quest_editaveis.drop(
                    columns=["Apagar", "Centro", "Datini", "Datfim", "U_status"], errors="ignore"
                )
                df_rejoin = juntar_dados(df_csv_atual, st.session_state.quest_acoes_df)
                df_rejoin = garantir_todas_colunas(df_rejoin)
                df_rejoin["Apagar"] = False
                st.session_state.quest_editaveis = df_rejoin

        # Processar CSVs e fazer join com ações
        if dfs_csv:
            df_csv_total = pd.concat(dfs_csv, ignore_index=True)
            df_joined = juntar_dados(df_csv_total, st.session_state.quest_acoes_df)
            df_joined = garantir_todas_colunas(df_joined)
            df_joined["Apagar"] = False

            if modo_carga == "Substituir dados existentes":
                st.session_state.quest_editaveis = df_joined
            else:
                st.session_state.quest_editaveis = pd.concat(
                    [st.session_state.quest_editaveis, df_joined], ignore_index=True
                )

            n_match = df_joined["Centro"].notna().sum()
            n_total = len(df_joined)
            if n_match > 0:
                st.info(f"🔗 Correlação: {n_match}/{n_total} registos com Centro identificado via Excel.")
            else:
                st.info("ℹ️ Nenhuma correspondência encontrada entre Shortname e Ação do Excel. "
                        "Carregue também o ficheiro Excel de Ações para enriquecer os dados.")

        if dfs_csv or dfs_acoes:
            st.session_state.quest_uploader_key += 1
            st.session_state.quest_editor_key   += 1
            st.rerun()

    st.markdown("---")

    # ── Filtros ────────────────────────────────────────────────
    df_atual = garantir_todas_colunas(st.session_state.quest_editaveis.copy())

    with st.expander("🔍 Filtrar visualização"):
        if not df_atual.empty and df_atual["Shortname"].notna().any():
            col_f1, col_f2, col_f3 = st.columns(3)

            with col_f1:
                centros = sorted(df_atual["Centro"].dropna().unique())
                filtro_centro = st.multiselect("Centro", centros, default=centros, key="fq_centro")
            with col_f2:
                modulos = sorted(df_atual["Módulo"].dropna().unique())
                filtro_modulo = st.multiselect("Módulo", modulos, default=modulos, key="fq_modulo")
            with col_f3:
                folhas = sorted(df_atual["Folha"].dropna().unique())
                filtro_folha = st.multiselect("Folha", folhas, default=folhas, key="fq_folha")

            col_f4, col_f5 = st.columns(2)
            with col_f4:
                respondentes = sorted(df_atual["Respondente"].dropna().unique())
                filtro_respondente = st.multiselect("Respondente", respondentes, default=respondentes, key="fq_respondente")
            with col_f5:
                modalidades = sorted(df_atual["Modalidade"].dropna().unique())
                filtro_modalidade = st.multiselect("Modalidade", modalidades, default=modalidades, key="fq_modalidade")

            # Filtro de datas
            col_d1, col_d2 = st.columns(2)
            df_datas = df_atual.copy()
            df_datas["Datini_dt"] = pd.to_datetime(df_datas["Datini"], errors="coerce")
            data_min = df_datas["Datini_dt"].min()
            data_max = df_datas["Datini_dt"].max()

            with col_d1:
                if pd.notna(data_min):
                    filtro_data_ini = st.date_input("Data início (a partir de)", value=data_min.date(), key="fq_data_ini")
                else:
                    filtro_data_ini = None
            with col_d2:
                if pd.notna(data_max):
                    filtro_data_fim = st.date_input("Data início (até)", value=data_max.date(), key="fq_data_fim")
                else:
                    filtro_data_fim = None

            df_filtrado = df_atual.copy()
            if filtro_centro:
                df_filtrado = df_filtrado[df_filtrado["Centro"].isin(filtro_centro) | df_filtrado["Centro"].isna()]
            if filtro_modulo:
                df_filtrado = df_filtrado[df_filtrado["Módulo"].isin(filtro_modulo)]
            if filtro_folha:
                df_filtrado = df_filtrado[df_filtrado["Folha"].isin(filtro_folha)]
            if filtro_respondente:
                df_filtrado = df_filtrado[df_filtrado["Respondente"].isin(filtro_respondente)]
            if filtro_modalidade:
                df_filtrado = df_filtrado[df_filtrado["Modalidade"].isin(filtro_modalidade)]
            if filtro_data_ini and filtro_data_fim:
                df_datas_f = df_filtrado.copy()
                df_datas_f["Datini_dt"] = pd.to_datetime(df_datas_f["Datini"], errors="coerce")
                mask_data = (
                    df_datas_f["Datini_dt"].isna() |
                    (
                        (df_datas_f["Datini_dt"].dt.date >= filtro_data_ini) &
                        (df_datas_f["Datini_dt"].dt.date <= filtro_data_fim)
                    )
                )
                df_filtrado = df_filtrado[mask_data.values]

            if not df_filtrado.empty:
                st.markdown(f"**📋 Visualização filtrada:** {len(df_filtrado)} registos")
                st.dataframe(
                    df_filtrado.drop(columns=["Apagar"], errors="ignore"),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Nenhum registo corresponde aos filtros selecionados.")
        else:
            st.info("Carregue ficheiros para ativar os filtros.")

    # ── Adicionar linhas ───────────────────────────────────────
    st.markdown("---")
    st.subheader("➕ Adicionar linhas vazias")
    col_add1, col_add2 = st.columns([1, 2])
    with col_add1:
        num_linhas = st.number_input("Nº de linhas", min_value=1, max_value=10000,
                                     value=5, step=1, key="num_linhas_quest")
    with col_add2:
        if st.button("➕ Adicionar linhas", use_container_width=True):
            novas = pd.DataFrame({col: [None] * num_linhas for col in COLUNAS_DADOS})
            novas.insert(0, "Apagar", False)
            st.session_state.quest_editaveis = pd.concat(
                [st.session_state.quest_editaveis, novas], ignore_index=True
            )
            st.session_state.quest_editor_key += 1
            st.rerun()

    # ── Exportar (ANTES do editor) ─────────────────────────────
    # FIX: O botão de download ficava depois do data_editor. O auto-update
    # chama st.rerun() que interrompe a execução — o botão nunca é renderizado.
    # Solução: pré-gerar o Excel em session_state antes do editor.
    # Persiste entre reruns e entre mudanças de página.
    if "quest_excel_cache" not in st.session_state:
        st.session_state.quest_excel_cache = None

    df_para_export = st.session_state.quest_editaveis.drop(columns=["Apagar"], errors="ignore").copy()
    tem_dados = not df_para_export.empty and df_para_export["Shortname"].notna().any()
    if tem_dados:
        COLS_FILTRO_EXP    = ["Centro", "Shortname", "Datini", "Datfim", "U_status",
                              "Respondente", "Modalidade", "Tipo"]
        COLS_REST_EXP      = [c for c in COLUNAS_DADOS if c not in COLS_FILTRO_EXP]
        ordem_exp          = [c for c in COLS_FILTRO_EXP + COLS_REST_EXP if c in df_para_export.columns]
        df_exp             = df_para_export[ordem_exp].copy()
        def formatar_data_se_valida(valor):
            """Se for uma data (datetime ou string convertível), devolve dd/mm/aaaa.
            Caso contrário, devolve o valor original (None, string, etc.)."""
            if pd.isna(valor):
                return None
            # Se já for Timestamp, formata diretamente
            if isinstance(valor, pd.Timestamp):
                return valor.strftime("%d/%m/%Y")
            # Tenta converter string para data
            try:
                dt = pd.to_datetime(valor, errors="coerce")
                if pd.notna(dt):
                    return dt.strftime("%d/%m/%Y")
                else:
                    return valor  # não é data, mantém original (ex: "FINALIZADA")
            except Exception:
                return valor

        for col_data in ["Datini", "Datfim", "Data"]:
            if col_data in df_exp.columns:
                df_exp[col_data] = df_exp[col_data].apply(formatar_data_se_valida)
        st.session_state.quest_excel_cache = _gerar_excel_com_filtros(df_exp)

    st.markdown("---")
    st.subheader("📎 Exportar dados com filtros")
    st.caption("O ficheiro Excel inclui **filtros nativos** em todas as colunas — Centro, Ação, Data, Respondente, U_status, etc.")
    if st.session_state.quest_excel_cache is not None:
        st.download_button(
            label="📥 Descarregar Excel com filtros",
            data=st.session_state.quest_excel_cache,
            file_name="questionarios_exportados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="download_quest_excel",
        )
    else:
        st.info("Carregue dados para activar a exportação.")

    # ── Tabela editável ────────────────────────────────────────
    st.markdown("---")
    st.subheader("✏️ Tabela de questionários")

    edited_df = st.data_editor(
        df_atual,
        use_container_width=True,
        num_rows="dynamic",
        height=420,
        key=f"quest_editor_{st.session_state.quest_editor_key}",
        column_config={
            "Apagar":      st.column_config.CheckboxColumn("Apagar", default=False),
            "Valor Médio": st.column_config.NumberColumn("Valor Médio", format="%.2f"),
        },
    )

    # Auto-update robusto
    if dfs_diferentes(edited_df, df_atual):
        st.session_state.quest_editaveis = edited_df
        st.session_state.quest_editor_key += 1
        st.rerun()

    # ── Botão apagar selecionados ──────────────────────────────
    st.markdown("---")
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

    # ── Métricas ───────────────────────────────────────────────
    df_m = st.session_state.quest_editaveis.drop(columns=["Apagar"], errors="ignore").copy()
    df_m = df_m[df_m["Shortname"].notna()]
    df_m = df_m[~df_m["Shortname"].astype(str).str.strip().isin(["", "None", "nan"])]
    df_m["Valor Médio"] = pd.to_numeric(df_m["Valor Médio"], errors="coerce")

    if not df_m.empty:
        st.markdown("---")
        st.subheader("📊 Resumo Geral")

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Cursos (Shortnames)", df_m["Shortname"].nunique())
        m2.metric("Centros",  df_m["Centro"].nunique() if "Centro" in df_m else 0)
        m3.metric("Módulos",  df_m["Módulo"].nunique() if "Módulo" in df_m else 0)
        m4.metric("Registos", len(df_m))
        media_geral = df_m["Valor Médio"].mean()
        m5.metric("Valor Médio Geral", f"{media_geral:.2f}" if pd.notna(media_geral) else "—")

        if all(c in df_m.columns for c in ["Módulo", "Folha", "Respondente", "Valor Médio"]):
            resumo = (
                df_m.groupby(["Módulo", "Folha", "Respondente"])["Valor Médio"]
                .mean().round(3).reset_index()
                .rename(columns={"Valor Médio": "Média"})
                .sort_values(["Módulo", "Folha"])
            )
            if not resumo.empty:
                st.subheader("📋 Médias por Módulo / Folha / Respondente")
                st.dataframe(resumo, use_container_width=True, hide_index=True)

        if "Centro" in df_m.columns and df_m["Centro"].notna().any():
            resumo_centro = (
                df_m.groupby("Centro")["Valor Médio"]
                .mean().round(3).reset_index()
                .rename(columns={"Valor Médio": "Média"})
                .sort_values("Média", ascending=False)
            )
            if not resumo_centro.empty:
                st.subheader("🏢 Médias por Centro")
                st.dataframe(resumo_centro, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ Carregue ficheiros para ver os dados.")


if __name__ == "__main__":
    mostrar_questionarios()