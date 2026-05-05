import streamlit as st
import pandas as pd
import unicodedata
import io

# ═══════════════════════════════════════════════════════════════
# DEFINIÇÃO DE COLUNAS
# ═══════════════════════════════════════════════════════════════

COLUNAS_CURSOS = [
    "Status", "Ação", "Centro", "Data Inicial", "Data Final",
    "Aptos", "Inaptos", "Desistentes", "Inscritos",
    "Devedor", "Valor total a receber", "Valor Total Recebido",
    "Taxa de Satisfação M00",
    "Taxa de Satisfação M01", "Taxa de Satisfação M02", "Taxa de Satisfação M03",
    "Taxa de Satisfação M04", "Taxa de Satisfação M05", "Taxa de Satisfação M06",
    "Taxa de Satisfação M07", "Taxa de Satisfação M08", "Taxa de Satisfação M09",
    "Taxa de Satisfação M10", "Taxa de Satisfação M11", "Taxa de Satisfação M12",
    "Taxa de satisfação Final", "Formador", "Avaliação formador",
]

COLUNAS_FORMANDOS = [
    "Ação", "Data_inicial", "Data_final", "Estado", "Formando",
    "No_formando", "Valor_curso", "Desconto",
    "Valor_curso_final",
    "Total_ja_pago", "Total_a_pagar",
    "Proximo_acordo", "Devedor",
]

CALC_CURSOS    = {"Devedor", "Valor total a receber", "Valor Total Recebido"}
CALC_FORMANDOS = {"Valor_curso_final", "Total_a_pagar", "Devedor"}

_ASSIN_CURSOS     = {"Centro", "Data Inicial", "Data Final", "Formador"}
_ASSIN_FORMANDOS  = {"Formando", "No_formando", "Valor_curso", "Total_ja_pago"}
_ASSIN_QUEST      = {"Shortname", "Módulo", "Respondente", "Tipo", "Valor Médio"}

# ═══════════════════════════════════════════════════════════════
# MAPEAMENTO DE ALIASES
# ═══════════════════════════════════════════════════════════════

ALIASES_FORMANDOS: dict[str, list[str]] = {
    "Ação":           ["Acao", "Acção", "Accao", "Ação de formação", "Acao de formacao",
                       "Codigo acao", "Código ação", "Cod_acao", "Cod acao"],
    "Data_inicial":   ["Data inicial", "DataInicial", "Data_Inicio", "Data inicio",
                       "Data de inicio", "Data de início", "Inicio"],
    "Data_final":     ["Data final", "DataFinal", "Data_Fim", "Data fim",
                       "Data de fim", "Fim"],
    "Estado":         ["Situação", "Situacao", "Estado formando", "Estado_formando",
                       "Situação formando", "Situacao formando", "Status"],
    "Formando":       ["Formando", "Nome de formando", "Nome formando", "Nome_formando",
                       "Nome do formando", "Nome completo", "Designação", "Designacao"],
    "No_formando":    ["No_Formando", "num do formando", "No_formando",
                       "Nº Formando", "N_formando", "Numero formando", "Número formando",
                       "Nformando", "Nº_formando", "No formando", "Num formando",
                       "Número do formando", "ID formando", "Id_formando"],
    "Valor_curso":    ["Valor curso", "ValorCurso", "Valor", "Preco", "Preço",
                       "Custo", "Valor do curso", "Valor formação"],
    "Desconto":       ["Desc", "Desconto aplicado", "Discount"],
    "Total_ja_pago":  ["Total ja pago", "Total pago", "TotalPago", "Valor pago",
                       "Pago", "Já pago", "Ja pago"],
    "Proximo_acordo": ["Proximo acordo", "Próximo acordo", "Acordo", "Próx acordo",
                       "Data acordo", "Prox_acordo"],
}

ALIASES_CURSOS: dict[str, list[str]] = {
    "Ação":                   ["Acao", "Acção", "Cod acao", "Código ação", "Cod_acao"],
    "Data Inicial":           ["Data_Inicial", "DataInicial", "Data inicio", "Data de início"],
    "Data Final":             ["Data_Final", "DataFinal", "Data fim", "Data de fim"],
    "Inscritos":              ["Total inscritos", "Num inscritos", "Nº inscritos"],
    "Aptos":                  ["Total aptos", "Certificados", "Aprovados"],
    "Inaptos":                ["Total inaptos", "Reprovados", "Não aptos"],
    "Desistentes":            ["Total desistentes", "Desistiu", "Desistencias"],
    "Avaliação formador":     ["Avaliacao formador", "Aval formador", "Nota formador"],
    "Taxa de satisfação Final": ["Taxa satisfacao final", "Satisfacao final",
                                  "Taxa final", "Satisfação final"],
}

# ═══════════════════════════════════════════════════════════════
# FUNÇÕES DE NORMALIZAÇÃO E MAPEAMENTO
# ═══════════════════════════════════════════════════════════════

def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", str(texto))
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto.lower().strip().replace(" ", "").replace("_", "").replace("º", "").replace("ª", "")

def mapear_colunas(df: pd.DataFrame, aliases: dict[str, list[str]]) -> tuple[pd.DataFrame, dict]:
    colunas_originais = {col: _normalizar(col) for col in df.columns}
    renomear = {}
    log = {}
    for destino, lista_aliases in aliases.items():
        destino_norm = _normalizar(destino)
        all_aliases_norm = [destino_norm] + [_normalizar(a) for a in lista_aliases]
        for col_orig, col_norm in colunas_originais.items():
            if col_orig in renomear.values():
                continue
            if col_norm in all_aliases_norm:
                if col_orig != destino:
                    renomear[col_orig] = destino
                log[destino] = col_orig
                break
    if renomear:
        df = df.rename(columns=renomear)
    return df, log

def mesclar_colunas_duplicadas(df: pd.DataFrame) -> pd.DataFrame:
    if not df.columns.duplicated().any():
        return df
    for col in df.columns[df.columns.duplicated()].unique():
        colunas_iguais = [c for c in df.columns if c == col]
        if len(colunas_iguais) > 1:
            df[colunas_iguais[0]] = df[colunas_iguais[0]].fillna(df[colunas_iguais[1]])
            df = df.loc[:, ~df.columns.duplicated(keep='first')]
    return df

# ═══════════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES
# ═══════════════════════════════════════════════════════════════

def exportar_excel(df: pd.DataFrame, sheet_name: str = "Dados") -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output.getvalue()

def dfs_diferentes(df1: pd.DataFrame, df2: pd.DataFrame) -> bool:
    if df1.shape != df2.shape:
        return True
    try:
        return not df1.fillna("__NA__").astype(str).equals(df2.fillna("__NA__").astype(str))
    except Exception:
        return True

def garantir_colunas(df: pd.DataFrame, colunas: list) -> pd.DataFrame:
    for col in colunas:
        if col not in df.columns:
            df[col] = None
    if "Apagar" not in df.columns:
        df.insert(0, "Apagar", False)
    ordem = ["Apagar"] + [c for c in colunas if c in df.columns]
    return df[ordem]

def converter_numericos_cursos(df: pd.DataFrame) -> pd.DataFrame:
    num_cols = [
        "Inscritos", "Aptos", "Inaptos", "Desistentes", "Devedor",
        "Valor total a receber", "Valor Total Recebido", "Avaliação formador",
        "Taxa de Satisfação M00",
    ] + [f"Taxa de Satisfação M{i:02d}" for i in range(1, 13)] + ["Taxa de satisfação Final"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

# ═══════════════════════════════════════════════════════════════
# LÓGICA DE CÁLCULO
# ═══════════════════════════════════════════════════════════════

def calcular_formandos(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    for col in ["Valor_curso", "Desconto", "Total_ja_pago"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["Valor_curso_final"] = df.get("Valor_curso", 0) - df.get("Desconto", 0)
    df["Total_a_pagar"]     = df["Valor_curso_final"] - df.get("Total_ja_pago", 0)
    df["Devedor"]           = df["Total_a_pagar"].apply(lambda x: x > 0 if pd.notna(x) else False)
    return df

def recalcular_cursos(df_cursos: pd.DataFrame, df_formandos: pd.DataFrame) -> pd.DataFrame:
    if df_cursos is None or df_cursos.empty:
        return df_cursos if df_cursos is not None else pd.DataFrame()
    for col in ["Devedor", "Valor total a receber", "Valor Total Recebido"]:
        if col not in df_cursos.columns:
            df_cursos[col] = 0
    if df_formandos is None or df_formandos.empty or "Ação" not in df_formandos.columns:
        df_cursos["Devedor"] = df_cursos["Valor total a receber"] = df_cursos["Valor Total Recebido"] = 0
        return df_cursos
    df_f = calcular_formandos(df_formandos.copy())
    df_f["Ação"] = df_f["Ação"].astype(str).str.strip()
    agg = df_f.groupby("Ação", as_index=False).agg(
        _dev=("Devedor", lambda x: x.eq(True).sum()),
        _rec=("Total_a_pagar", "sum"),
        _pago=("Total_ja_pago", "sum")
    )
    agg["Ação"] = agg["Ação"].astype(str).str.strip()
    cols_fixas = [c for c in df_cursos.columns if c not in CALC_CURSOS]
    df_res = df_cursos[cols_fixas].copy()
    df_res["_key"] = df_res["Ação"].astype(str).str.strip()
    agg["_key"] = agg["Ação"].astype(str).str.strip()
    df_res = df_res.merge(agg[["_key", "_dev", "_rec", "_pago"]], on="_key", how="left")
    df_res["Devedor"] = df_res["_dev"].fillna(0).astype(int)
    df_res["Valor total a receber"] = df_res["_rec"].fillna(0)
    df_res["Valor Total Recebido"] = df_res["_pago"].fillna(0)
    df_res.drop(columns=["_key", "_dev", "_rec", "_pago"], inplace=True, errors="ignore")
    return df_res

# ═══════════════════════════════════════════════════════════════
# PROCESSAMENTO DE QUESTIONÁRIOS
# ═══════════════════════════════════════════════════════════════

def _escala_para_pct(valor: float) -> float:
    """Converte escala 1-4 para percentagem 0-100%."""
    return round((valor / 4.0) * 100, 1)

def processar_questionarios(df_q: pd.DataFrame, df_cursos: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Lê o ficheiro de questionários exportado e preenche na tabela de Ações:
    - Taxa de Satisfação MXX  → média dos Formandos por módulo (escala 1-4 → %)
    - Taxa de satisfação Final → média dos Formandos no questionário de Ação global (escala 1-4 → %)
    - Avaliação formador       → média das avaliações de Formador/Tutor por Coord. Pedagógica (escala 1-4 → %)

    Retorna (df_cursos_atualizado, lista_de_log).
    """
    log: list[str] = []
    df_q = df_q.copy()

    # Verificar colunas obrigatórias
    colunas_necessarias = {"Shortname", "Módulo", "Respondente", "Tipo", "Valor Médio", "Item"}
    faltam = colunas_necessarias - set(df_q.columns)
    if faltam:
        log.append(f"❌ Ficheiro de questionários sem colunas: `{'`, `'.join(faltam)}`")
        return df_cursos, log

    df_q["Shortname"]    = df_q["Shortname"].astype(str).str.strip()
    df_q["Módulo"]       = df_q["Módulo"].astype(str).str.strip()
    df_q["Respondente"]  = df_q["Respondente"].astype(str).str.strip()
    df_q["Tipo"]         = df_q["Tipo"].astype(str).str.strip()
    df_q["Item"]         = df_q["Item"].astype(str).str.strip()
    df_q["Valor Médio"]  = pd.to_numeric(df_q["Valor Médio"], errors="coerce")

    acoes_processadas = 0
    acoes_sem_dados   = []

    df_cursos = df_cursos.copy()

    # Garantir que as colunas de satisfação existem
    for col in COLUNAS_CURSOS:
        if col not in df_cursos.columns:
            df_cursos[col] = None

    for acao in df_cursos["Ação"].dropna().unique():
        acao_str = str(acao).strip()
        if not acao_str or acao_str in ("None", "nan"):
            continue

        mask_acao = df_q["Shortname"] == acao_str
        df_acao = df_q[mask_acao]

        if df_acao.empty:
            acoes_sem_dados.append(acao_str)
            continue

        idx = df_cursos[df_cursos["Ação"].astype(str).str.strip() == acao_str].index
        if len(idx) == 0:
            continue

        acoes_processadas += 1
        modulos_preenchidos = []

        # ── 1. Satisfação por módulo (Respondente=Formando, Tipo=Módulo, excl. Obs) ──
        df_mod = df_acao[
            (df_acao["Respondente"] == "Formando") &
            (df_acao["Tipo"] == "Módulo") &
            (~df_acao["Item"].str.endswith(".Obs"))
        ]
        for modulo in sorted(df_mod["Módulo"].dropna().unique()):
            modulo_str = str(modulo).strip()
            col_sat = f"Taxa de Satisfação {modulo_str}"   # ex: "Taxa de Satisfação M00"
            avg = df_mod[df_mod["Módulo"] == modulo]["Valor Médio"].mean()
            if pd.notna(avg):
                pct = _escala_para_pct(avg)
                if col_sat in df_cursos.columns:
                    df_cursos.loc[idx, col_sat] = pct
                    modulos_preenchidos.append(f"{modulo_str}={pct}%")

        # ── 2. Satisfação Final (Respondente=Formando, Tipo=Ação, excl. Obs) ──
        df_final = df_acao[
            (df_acao["Respondente"] == "Formando") &
            (df_acao["Tipo"] == "Ação") &
            (~df_acao["Item"].str.endswith(".Obs"))
        ]
        if not df_final.empty:
            avg_final = df_final["Valor Médio"].mean()
            if pd.notna(avg_final):
                pct_final = _escala_para_pct(avg_final)
                df_cursos.loc[idx, "Taxa de satisfação Final"] = pct_final
                modulos_preenchidos.append(f"Final={pct_final}%")

        # ── 3. Avaliação do Formador (Tipo=Formador ou Tutor, excl. Sug) ──
        df_form = df_acao[
            (df_acao["Tipo"].isin(["Formador", "Tutor"])) &
            (~df_acao["Item"].str.endswith(".Sug"))
        ]
        if not df_form.empty:
            avg_form = df_form["Valor Médio"].mean()
            if pd.notna(avg_form):
                pct_form = _escala_para_pct(avg_form)
                df_cursos.loc[idx, "Avaliação formador"] = pct_form
                modulos_preenchidos.append(f"Formador={pct_form}%")

        log.append(
            f"&nbsp;&nbsp;&nbsp;&nbsp;📝 **{acao_str}** → {', '.join(modulos_preenchidos) if modulos_preenchidos else 'sem dados'}"
        )

    log.insert(0, f"✅ Questionários: **{acoes_processadas}** ação(ões) atualizadas.")
    if acoes_sem_dados:
        log.append(f"&nbsp;&nbsp;&nbsp;&nbsp;⚠️ Ações sem dados no ficheiro: `{'`, `'.join(acoes_sem_dados[:10])}`{'…' if len(acoes_sem_dados) > 10 else ''}")

    return df_cursos, log


def detectar_questionario(df: pd.DataFrame) -> bool:
    """Retorna True se o DataFrame parecer um ficheiro de questionários exportado."""
    cols_norm = {_normalizar(c) for c in df.columns}
    assin_norm = {_normalizar(c) for c in _ASSIN_QUEST}
    return len(assin_norm & cols_norm) >= 4


# ═══════════════════════════════════════════════════════════════
# LEITURA E PREPARAÇÃO DE FICHEIROS
# ═══════════════════════════════════════════════════════════════

def ler_ficheiro(f) -> pd.DataFrame:
    nome = f.name.lower()
    if nome.endswith(".csv"):
        df = pd.read_csv(f)
    else:
        df = pd.read_excel(f, header=0)
        if df.shape[1] < 3:
            f.seek(0)
            df = pd.read_excel(f, header=1)
    df.columns = df.columns.astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)
    return df

def detectar_tipo_ficheiro(df: pd.DataFrame) -> str:
    if detectar_questionario(df):
        return "questionario"
    cols_norm = {_normalizar(c) for c in df.columns}
    score_c = sum(1 for s in _ASSIN_CURSOS if _normalizar(s) in cols_norm)
    score_f = sum(1 for s in _ASSIN_FORMANDOS if _normalizar(s) in cols_norm)
    df_m, _ = mapear_colunas(df.copy(), ALIASES_FORMANDOS)
    cols_m = set(df_m.columns)
    score_f_alias = len(cols_m & _ASSIN_FORMANDOS)
    score_f = max(score_f, score_f_alias)
    if score_c == 0 and score_f == 0:
        return "desconhecido"
    return "cursos" if score_c >= score_f else "formandos"

def preparar_cursos(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df, log = mapear_colunas(df, ALIASES_CURSOS)
    df = mesclar_colunas_duplicadas(df)
    for col in COLUNAS_CURSOS:
        if col not in df.columns:
            df[col] = None
    df = df[COLUNAS_CURSOS].copy()
    df.insert(0, "Apagar", False)
    return df, log

def preparar_formandos(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df, log = mapear_colunas(df, ALIASES_FORMANDOS)
    df = mesclar_colunas_duplicadas(df)
    for col in COLUNAS_FORMANDOS:
        if col not in df.columns:
            df[col] = None
    df = df[COLUNAS_FORMANDOS].copy()
    df.insert(0, "Apagar", False)
    return calcular_formandos(df), log

# ═══════════════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def mostrar_cursos():
    st.header("📚 Análise de Formações")

    defaults = {
        "acoes_df":          pd.DataFrame(columns=["Apagar"] + COLUNAS_CURSOS),
        "formandos_df":      pd.DataFrame(columns=["Apagar"] + COLUNAS_FORMANDOS),
        "editor_key_cursos": 0,
        "editor_key_form":   0,
        "uploader_key":      0,
        "uploader_key_q":    0,
        "colunas_vis":       [c for c in COLUNAS_CURSOS if not c.startswith("Taxa de Satisfação M") or c in ("Taxa de Satisfação M00", "Taxa de Satisfação M01", "Taxa de Satisfação M02")],
    }
    for k, v in defaults.items():
        if k not in st.session_state or st.session_state[k] is None:
            st.session_state[k] = v

    st.session_state.acoes_df = recalcular_cursos(st.session_state.acoes_df, st.session_state.formandos_df)

    # ── Carregamento de Ações e Formandos ──────────────────────────────────────
    with st.expander("📤 Carregar ficheiros (Ações e/ou Formandos)", expanded=False):
        st.markdown("Selecione **um ou mais ficheiros**. O sistema identifica automaticamente se cada ficheiro é de **Ações**, **Formandos** ou **Questionários** e mapeia as colunas.")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            modo_cursos = st.radio("Modo para Ações:", ["Substituir", "Adicionar"], horizontal=True, key="modo_up_cursos")
        with col_m2:
            modo_form   = st.radio("Modo para Formandos:", ["Substituir", "Adicionar"], horizontal=True, key="modo_up_form")

        ficheiros = st.file_uploader(
            "Selecione ficheiros Excel (.xlsx) ou CSV",
            type=None, accept_multiple_files=True,
            key=f"upload_{st.session_state.uploader_key}"
        )

        if ficheiros:
            novos_cursos, novos_formandos = [], []
            linhas_log = []
            quest_pendentes = []   # questionários carregados antes de haver ações

            for f in ficheiros:
                try:
                    df_raw = ler_ficheiro(f)
                    tipo = detectar_tipo_ficheiro(df_raw)

                    if tipo == "questionario":
                        # Processamento imediato se já existirem ações
                        if not st.session_state.acoes_df.empty and "Ação" in st.session_state.acoes_df.columns:
                            df_atualizado, log_q = processar_questionarios(df_raw, st.session_state.acoes_df)
                            st.session_state.acoes_df = df_atualizado
                            st.session_state.editor_key_cursos += 1
                            linhas_log.append(f"📊 **{f.name}** → **Questionários**")
                            linhas_log.extend(log_q)
                        else:
                            quest_pendentes.append((f.name, df_raw))
                            linhas_log.append(f"⚠️ **{f.name}** → Questionários detetado mas sem Ações carregadas. Carregue primeiro as Ações.")

                    elif tipo == "cursos":
                        df_pronto, log_map = preparar_cursos(df_raw)
                        novos_cursos.append(df_pronto)
                        linhas_log.append(f"✅ **{f.name}** → **Ações** ({len(df_raw)} linhas)")
                        if log_map:
                            mapeados = ", ".join(f"`{orig}` → `{dest}`" for dest, orig in log_map.items() if orig != dest)
                            if mapeados:
                                linhas_log.append(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ Colunas remapeadas: {mapeados}")

                    elif tipo == "formandos":
                        df_pronto, log_map = preparar_formandos(df_raw)
                        novos_formandos.append(df_pronto)
                        linhas_log.append(f"✅ **{f.name}** → **Formandos** ({len(df_raw)} linhas)")
                        for dest, orig in log_map.items():
                            if str(orig) != str(dest):
                                linhas_log.append(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ `{orig}` → `{dest}`")
                        vazias = [c for c in ["Estado", "No_formando", "Formando"] if c not in log_map and c not in df_raw.columns]
                        if vazias:
                            linhas_log.append(f"&nbsp;&nbsp;&nbsp;&nbsp;⚠️ Colunas não encontradas: `{'`, `'.join(vazias)}`")
                        linhas_log.append(f"&nbsp;&nbsp;&nbsp;&nbsp;ℹ️ Colunas originais: `{'`, `'.join(df_raw.columns.tolist())}`")
                    else:
                        linhas_log.append(f"⚠️ **{f.name}** → tipo não reconhecido. Colunas: `{'`, `'.join(df_raw.columns.tolist())}`")
                except Exception as e:
                    linhas_log.append(f"❌ **{f.name}** → erro: `{e}`")

            if novos_cursos:
                df_nc = pd.concat(novos_cursos, ignore_index=True)
                st.session_state.acoes_df = df_nc if modo_cursos == "Substituir" else pd.concat([st.session_state.acoes_df, df_nc], ignore_index=True)
                st.session_state.editor_key_cursos += 1

                # Aplicar questionários pendentes agora que temos ações
                for nome_q, df_q in quest_pendentes:
                    df_atualizado, log_q = processar_questionarios(df_q, st.session_state.acoes_df)
                    st.session_state.acoes_df = df_atualizado
                    linhas_log.append(f"&nbsp;&nbsp;&nbsp;&nbsp;✅ Questionários de **{nome_q}** aplicados após carregar Ações.")
                    linhas_log.extend(log_q)

            if novos_formandos:
                df_nf = pd.concat(novos_formandos, ignore_index=True)
                st.session_state.formandos_df = df_nf if modo_form == "Substituir" else pd.concat([st.session_state.formandos_df, df_nf], ignore_index=True)
                st.session_state.editor_key_form += 1

            if novos_cursos or novos_formandos:
                st.session_state.acoes_df = recalcular_cursos(st.session_state.acoes_df, st.session_state.formandos_df)
                st.session_state.uploader_key += 1

            for linha in linhas_log:
                st.markdown(linha, unsafe_allow_html=True)
            if novos_cursos or novos_formandos or any(t == "questionario" for t in []):
                st.rerun()
            if linhas_log:
                st.rerun()

    # ── Carregamento de Questionários (secção dedicada) ───────────────────────
    with st.expander("📊 Importar Questionários de Satisfação", expanded=False):
        st.markdown(
            "Carregue o ficheiro exportado de questionários. O sistema irá preencher automaticamente "
            "as colunas de **Taxa de Satisfação por módulo**, **Taxa de satisfação Final** e "
            "**Avaliação do Formador** nas ações correspondentes."
        )
        st.info(
            "ℹ️ **Lógica de cálculo (escala 1-4 → %):**\n"
            "- **Taxa de Satisfação MXX** — média das respostas dos Formandos por módulo\n"
            "- **Taxa de satisfação Final** — média das respostas dos Formandos ao questionário global da Ação\n"
            "- **Avaliação formador** — média das avaliações de Formador/Tutor feitas pela Coordenação Pedagógica",
            icon="📋"
        )

        if st.session_state.acoes_df.empty or "Ação" not in st.session_state.acoes_df.columns or \
           st.session_state.acoes_df["Ação"].dropna().empty:
            st.warning("⚠️ Não existem Ações carregadas. Carregue primeiro o ficheiro de Ações.")
        else:
            ações_disponiveis = st.session_state.acoes_df["Ação"].dropna().unique()
            st.caption(f"Ações disponíveis para associação: {len(ações_disponiveis)} ação(ões)")

        fich_quest = st.file_uploader(
            "Selecione o ficheiro de questionários (.xlsx ou .csv)",
            type=None,
            accept_multiple_files=False,
            key=f"upload_q_{st.session_state.uploader_key_q}"
        )

        modo_quest = st.radio(
            "Modo de importação:",
            ["Atualizar (sobrescreve satisfação/formador existentes)", "Manter valores existentes (só preenche vazios)"],
            horizontal=False,
            key="modo_quest"
        )

        if fich_quest:
            try:
                df_q_raw = ler_ficheiro(fich_quest)
                if not detectar_questionario(df_q_raw):
                    st.error(f"❌ O ficheiro não parece ser de questionários. Colunas detetadas: `{'`, `'.join(df_q_raw.columns.tolist())}`")
                else:
                    st.success(f"✅ Ficheiro reconhecido como **Questionários** ({len(df_q_raw)} linhas, {df_q_raw['Shortname'].nunique() if 'Shortname' in df_q_raw.columns else '?'} ações).")

                    # Preview das ações presentes no ficheiro
                    if "Shortname" in df_q_raw.columns:
                        sn_set = set(df_q_raw["Shortname"].astype(str).str.strip().unique())
                        acoes_set = set(st.session_state.acoes_df["Ação"].astype(str).str.strip().unique()) if "Ação" in st.session_state.acoes_df.columns else set()
                        matches = sn_set & acoes_set
                        sem_match = sn_set - acoes_set
                        st.caption(f"🔗 Ações encontradas em ambos os ficheiros: **{len(matches)}** | Apenas no questionário (serão ignoradas): **{len(sem_match)}**")

                    if st.button("▶️ Aplicar Questionários às Ações", type="primary", use_container_width=True):
                        df_base = st.session_state.acoes_df.copy()

                        if "Manter valores existentes" in modo_quest:
                            # Guardar valores existentes não-nulos
                            cols_sat = ["Taxa de Satisfação M00"] + [f"Taxa de Satisfação M{i:02d}" for i in range(1, 13)] + ["Taxa de satisfação Final", "Avaliação formador"]
                            snap = {col: df_base[col].copy() for col in cols_sat if col in df_base.columns}
                            df_atualizado, log_q = processar_questionarios(df_q_raw, df_base)
                            # Restaurar valores que já existiam
                            for col, serie_orig in snap.items():
                                mascara_tinha = serie_orig.notna()
                                df_atualizado.loc[mascara_tinha, col] = serie_orig[mascara_tinha]
                        else:
                            df_atualizado, log_q = processar_questionarios(df_q_raw, df_base)

                        st.session_state.acoes_df = df_atualizado
                        st.session_state.editor_key_cursos += 1
                        st.session_state.uploader_key_q += 1

                        for linha in log_q:
                            st.markdown(linha, unsafe_allow_html=True)
                        st.rerun()
            except Exception as e:
                st.error(f"❌ Erro ao processar ficheiro: `{e}`")

    st.markdown("---")
    st.subheader("📋 Tabela por Ação")
    st.caption("**Devedor**, **Valor total a receber** e **Valor Total Recebido** são calculados automaticamente a partir da tabela de Formandos.")
    with st.expander("⚙️ Opções da tabela de Ações", expanded=True):
        colunas_vis = st.multiselect("Colunas a visualizar/editar:", options=COLUNAS_CURSOS, default=st.session_state.colunas_vis, key="sel_col_cursos")
        if set(colunas_vis) != set(st.session_state.colunas_vis):
            st.session_state.colunas_vis = colunas_vis
            st.rerun()
        df_cv = garantir_colunas(st.session_state.acoes_df.copy(), st.session_state.colunas_vis)
        df_cv = converter_numericos_cursos(df_cv)
        cfg_c = {"Apagar": st.column_config.CheckboxColumn("Apagar", default=False)}
        for col in CALC_CURSOS:
            if col in df_cv.columns:
                cfg_c[col] = st.column_config.NumberColumn(col, disabled=True, help="Calculado a partir dos Formandos")
        edited_c = st.data_editor(df_cv, use_container_width=True, num_rows="dynamic", height=400, key=f"ed_c_{st.session_state.editor_key_cursos}", column_config=cfg_c)
        if dfs_diferentes(edited_c, df_cv):
            base = st.session_state.acoes_df.copy()
            for col in edited_c.columns:
                if col not in CALC_CURSOS:
                    base[col] = edited_c[col].values
            st.session_state.acoes_df = recalcular_cursos(converter_numericos_cursos(base), st.session_state.formandos_df)
            st.session_state.editor_key_cursos += 1
            st.rerun()
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🗑️ Limpar todas as ações", use_container_width=True):
            st.session_state.acoes_df = pd.DataFrame(columns=["Apagar"] + COLUNAS_CURSOS)
            st.session_state.editor_key_cursos += 1
            st.rerun()
    with c2:
        if st.button("✖️ Apagar selecionadas (ações)", use_container_width=True):
            df = st.session_state.acoes_df.copy()
            mask = df.get("Apagar", pd.Series(False, index=df.index)) == True
            if mask.any():
                df = df[~mask].reset_index(drop=True)
                df["Apagar"] = False
                st.session_state.acoes_df = recalcular_cursos(converter_numericos_cursos(df), st.session_state.formandos_df)
                st.session_state.editor_key_cursos += 1
                st.rerun()
            else:
                st.warning("Nenhuma linha marcada.")
    with c3:
        df_exp_c = st.session_state.acoes_df.drop(columns=["Apagar"], errors="ignore")
        st.download_button("📥 Exportar Ações (Excel)", data=exportar_excel(df_exp_c, "Ações"), file_name="acoes_exportadas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    st.markdown("---")
    st.subheader("👥 Tabela por Formando")
    st.caption("**Valor_curso_final**, **Total_a_pagar** e **Devedor** são calculados automaticamente. Qualquer alteração atualiza os totais da tabela de Ações.")
    with st.expander("⚙️ Opções da tabela de Formandos", expanded=True):
        df_fv = garantir_colunas(st.session_state.formandos_df.copy(), COLUNAS_FORMANDOS)
        df_fv = calcular_formandos(df_fv)
        if 'No_formando' in df_fv.columns:
            df_fv['No_formando'] = df_fv['No_formando'].astype(str).replace('nan', '').replace('None', '')
        cfg_f = {
            "Apagar": st.column_config.CheckboxColumn("Apagar", default=False),
            "Valor_curso_final": st.column_config.NumberColumn("Valor_curso_final", disabled=True),
            "Total_a_pagar": st.column_config.NumberColumn("Total_a_pagar", disabled=True),
            "Devedor": st.column_config.CheckboxColumn("Devedor", disabled=True),
        }
        edited_f = st.data_editor(df_fv, use_container_width=True, num_rows="dynamic", height=400, key=f"ed_f_{st.session_state.editor_key_form}", column_config=cfg_f)
        if dfs_diferentes(edited_f, df_fv):
            base_f = st.session_state.formandos_df.copy()
            for col in edited_f.columns:
                if col not in CALC_FORMANDOS:
                    base_f[col] = edited_f[col].values
            base_f = calcular_formandos(base_f)
            st.session_state.formandos_df = base_f
            st.session_state.acoes_df = recalcular_cursos(st.session_state.acoes_df, st.session_state.formandos_df)
            st.session_state.editor_key_form += 1
            st.rerun()
    f1, f2, f3 = st.columns(3)
    with f1:
        if st.button("🗑️ Limpar todos os formandos", use_container_width=True):
            st.session_state.formandos_df = pd.DataFrame(columns=["Apagar"] + COLUNAS_FORMANDOS)
            st.session_state.acoes_df = recalcular_cursos(st.session_state.acoes_df, st.session_state.formandos_df)
            st.session_state.editor_key_form += 1
            st.rerun()
    with f2:
        if st.button("✖️ Apagar selecionados (formandos)", use_container_width=True):
            df = st.session_state.formandos_df.copy()
            mask = df.get("Apagar", pd.Series(False, index=df.index)) == True
            if mask.any():
                df = df[~mask].reset_index(drop=True)
                df["Apagar"] = False
                st.session_state.formandos_df = calcular_formandos(df)
                st.session_state.acoes_df = recalcular_cursos(st.session_state.acoes_df, st.session_state.formandos_df)
                st.session_state.editor_key_form += 1
                st.rerun()
            else:
                st.warning("Nenhum formando marcado.")
    with f3:
        df_exp_f = st.session_state.formandos_df.drop(columns=["Apagar"], errors="ignore")
        st.download_button("📥 Exportar Formandos (Excel)", data=exportar_excel(df_exp_f, "Formandos"), file_name="formandos_exportadas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    st.markdown("---")
    df_m = st.session_state.acoes_df.drop(columns=["Apagar"], errors="ignore").copy()
    df_m = converter_numericos_cursos(df_m)
    if "Ação" in df_m.columns:
        df_m["Ação"] = df_m["Ação"].replace({"": None, "None": None, "nan": None})
        df_m = df_m.dropna(subset=["Ação"])
        df_m = df_m[df_m["Ação"].astype(str).str.strip() != ""]
    if not df_m.empty:
        st.subheader("📊 Resumo Geral")
        def fmt_eur(v): return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
        total_acoes = df_m["Ação"].nunique()
        total_inscritos = df_m["Inscritos"].sum() if "Inscritos" in df_m.columns else 0
        total_aptos = df_m["Aptos"].sum() if "Aptos" in df_m.columns else 0
        taxa_aprov = (total_aptos / total_inscritos * 100) if total_inscritos > 0 else 0
        media_sat = df_m["Taxa de satisfação Final"].mean() if "Taxa de satisfação Final" in df_m.columns else 0
        total_a_rec = df_m["Valor total a receber"].sum() if "Valor total a receber" in df_m.columns else 0
        total_rec = df_m["Valor Total Recebido"].sum() if "Valor Total Recebido" in df_m.columns else 0
        total_dev = df_m["Devedor"].sum() if "Devedor" in df_m.columns else 0
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        r1c1.metric("Total de Ações", total_acoes)
        r1c2.metric("Total de Inscrições", f"{int(total_inscritos):,}".replace(",", "."))
        r1c3.metric("Taxa de Aprovação", f"{taxa_aprov:.1f}%")
        r1c4.metric("Satisfação Final Média", f"{media_sat:.1f}%" if media_sat else "—")
        r2c1, r2c2, r2c3 = st.columns(3)
        r2c1.metric("Valor Total a Receber", fmt_eur(total_a_rec))
        r2c2.metric("Valor Total Recebido", fmt_eur(total_rec))
        r2c3.metric("Total de Devedores", int(total_dev))
    else:
        st.info("ℹ️ Nenhum curso com dados válidos. Carregue ficheiros ou adicione dados manualmente.")

if __name__ == "__main__":
    mostrar_cursos()