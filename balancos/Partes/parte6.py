import pandas as pd
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent


def calcular_parte6(df: pd.DataFrame, df_notas: pd.DataFrame, regiao: str) -> dict:
    """
    Parte 6 - Avaliação das Aprendizagens dos Formandos
    Calcula médias de notas e formandos aprovados/desistentes por tipo de formação
    (Presencial, b-Learning) para a região indicada.

    Fontes:
        - df       : Modelo Execução Fisica.xlsx  (ações + formandos + desistentes)
        - df_notas : Media Notas.xlsx             (médias de notas por ação)

    Retorna um dicionário com as variáveis para o template Word:
        NOTAS_FORMANDOS_PRES        - Média de notas Presencial
        NUM_FORMANDOS_APROV_PRES    - Formandos aprovados Presencial
        NUM_DESISTENTES_PRES        - Formandos desistentes Presencial

        NOTAS_FORMANDOS_BL          - Média de notas b-Learning
        NUM_FORMANDOS_APROV_BL      - Formandos aprovados b-Learning
        NUM_DESISTENTES_BL          - Formandos desistentes b-Learning

        NOTAS_FORMANDOS_EL          - (vazio - não preenchido por enquanto)
        NUM_FORMANDOS_APROV_EL      - (vazio)
        NUM_DESISTENTES_EL          - (vazio)

        MEDIA_NOTAS                         - Média geral de notas
        TOTAL_NUM_FORMANDOS_APROV           - Total de formandos aprovados
        TOTAL_NUM_FORMANDOS_DESISTENTES     - Total de formandos desistentes
    """

    print(f"\n{'='*60}")
    print(f" 📄 PARTE 6 - Avaliação das Aprendizagens | Região: {regiao}")
    print(f"{'='*60}")

    # ─────────────────────────────────────────────
    # 1. PREPARAR E FILTRAR EXECUÇÃO FÍSICA
    # ─────────────────────────────────────────────
    df = df.copy()
    df.columns = df.columns.str.strip()

    # Encontrar coluna Deslocal de forma tolerante
    col_deslocal = next(
        (c for c in df.columns if c.strip().lower() == "deslocal"), None
    )
    if col_deslocal is None:
        print(" ❌ ERRO: Coluna 'Deslocal' não encontrada!")
        return _resultado_vazio()

    df[col_deslocal] = df[col_deslocal].astype(str).str.strip()
    df_regiao = df[df[col_deslocal] == regiao].copy()

    print(f" 🔍 Linhas encontradas para '{regiao}': {len(df_regiao)}")

    if df_regiao.empty:
        print(" ⚠ Nenhuma linha para esta região.")
        return _resultado_vazio()

    # Normalizar U_id
    df_regiao["U_id"] = df_regiao["U_id"].astype(str).str.strip().str.upper()

    # Converter colunas numéricas
    df_regiao["Total_formandos"] = pd.to_numeric(df_regiao["Total_formandos"], errors="coerce").fillna(0)
    df_regiao["Desistentes"]     = pd.to_numeric(df_regiao["Desistentes"],     errors="coerce").fillna(0)

    # ─────────────────────────────────────────────
    # 2. SEPARAR POR TIPO
    #    Presencial → sem "_BL" e sem "_EL" no U_id
    #    b-Learning → contém "_BL"
    #    e-Learning → contém "_EL"  (reservado para o futuro)
    # ─────────────────────────────────────────────
    mask_bl = df_regiao["U_id"].str.contains("_BL", na=False)
    mask_el = df_regiao["U_id"].str.contains("_EL", na=False)
    mask_pres = ~mask_bl & ~mask_el

    df_pres = df_regiao[mask_pres].copy()
    df_bl   = df_regiao[mask_bl].copy()
    # df_el = df_regiao[mask_el].copy()  # Reservado

    print(f"   Presencial : {len(df_pres)} ações")
    print(f"   b-Learning : {len(df_bl)} ações")

    # ─────────────────────────────────────────────
    # 3. CALCULAR FORMANDOS APROVADOS E DESISTENTES
    #    Aprovados = Total_formandos - Desistentes
    # ─────────────────────────────────────────────
    def totais(df_tipo):
        total     = int(df_tipo["Total_formandos"].sum())
        desist    = int(df_tipo["Desistentes"].sum())
        aprovados = max(total - desist, 0)
        return aprovados, desist

    aprov_pres, desist_pres = totais(df_pres)
    aprov_bl,   desist_bl   = totais(df_bl)

    print(f"\n   [Presencial] Aprovados: {aprov_pres} | Desistentes: {desist_pres}")
    print(f"   [b-Learning] Aprovados: {aprov_bl}   | Desistentes: {desist_bl}")

    # ─────────────────────────────────────────────
    # 4. CALCULAR MÉDIAS DE NOTAS
    #    Fonte: Media Notas.xlsx — cruzamento por U_id
    # ─────────────────────────────────────────────
    media_pres = _calcular_media_notas(df_pres, df_notas, "Presencial")
    media_bl   = _calcular_media_notas(df_bl,   df_notas, "b-Learning")

    # Média geral ponderada pelo número de formandos
    total_formandos_pres = int(df_pres["Total_formandos"].sum())
    total_formandos_bl   = int(df_bl["Total_formandos"].sum())
    total_geral          = total_formandos_pres + total_formandos_bl

    if total_geral > 0:
        media_geral = round(
            (media_pres * total_formandos_pres + media_bl * total_formandos_bl) / total_geral, 2
        )
    else:
        media_geral = 0.0

    print(f"\n   Média Presencial : {media_pres}")
    print(f"   Média b-Learning : {media_bl}")
    print(f"   Média Geral      : {media_geral}")

    # ─────────────────────────────────────────────
    # 5. MONTAR RESULTADO
    # ─────────────────────────────────────────────
    return {
        # Presencial
        "NOTAS_FORMANDOS_PRES":     media_pres,
        "NUM_FORMANDOS_APROV_PRES": aprov_pres,
        "NUM_DESISTENTES_PRES":     desist_pres,

        # b-Learning
        "NOTAS_FORMANDOS_BL":       media_bl,
        "NUM_FORMANDOS_APROV_BL":   aprov_bl,
        "NUM_DESISTENTES_BL":       desist_bl,

        # e-Learning (reservado - vazio por enquanto)
        "NOTAS_FORMANDOS_EL":       "",
        "NUM_FORMANDOS_APROV_EL":   "",
        "NUM_DESISTENTES_EL":       "",

        # Totais gerais
        "MEDIA_NOTAS":                      media_geral,
        "TOTAL_NUM_FORMANDOS_APROV":        aprov_pres + aprov_bl,
        "TOTAL_NUM_FORMANDOS_DESISTENTES":  desist_pres + desist_bl,
    }


# ─────────────────────────────────────────────
# AUXILIARES
# ─────────────────────────────────────────────

def _calcular_media_notas(df_tipo: pd.DataFrame, df_notas: pd.DataFrame, label: str) -> float:
    """
    Cruza as ações do tipo com o ficheiro de notas (Media Notas.xlsx)
    e devolve a média ponderada pelo número de formandos.
    Se não houver cruzamento, devolve 0.0.
    """
    if df_tipo.empty or df_notas is None or df_notas.empty:
        return 0.0

    df_notas = df_notas.copy()
    df_notas.columns = df_notas.columns.str.strip()

    # Tentar identificar a coluna de U_id nas notas
    col_uid_notas = next(
        (c for c in df_notas.columns if c.strip().lower() in ("u_id", "uid", "u id", "código", "codigo")),
        None
    )
    # Tentar identificar coluna de nota/média
    col_nota = next(
        (c for c in df_notas.columns if any(p in c.strip().lower() for p in ("média", "media", "nota", "classificação", "classificacao"))),
        None
    )

    if col_uid_notas is None or col_nota is None:
        print(f"   ⚠ [{label}] Não foi possível identificar colunas de U_id ou Nota em Media Notas.xlsx")
        print(f"     Colunas disponíveis: {list(df_notas.columns)}")
        return 0.0

    df_notas[col_uid_notas] = df_notas[col_uid_notas].astype(str).str.strip().str.upper()
    df_notas[col_nota]      = pd.to_numeric(df_notas[col_nota], errors="coerce")

    # Merge com as ações do tipo
    df_merge = df_tipo.merge(
        df_notas[[col_uid_notas, col_nota]],
        left_on="U_id",
        right_on=col_uid_notas,
        how="left"
    )

    df_merge[col_nota]          = df_merge[col_nota].fillna(0)
    df_merge["Total_formandos"] = pd.to_numeric(df_merge["Total_formandos"], errors="coerce").fillna(0)

    total_formandos = df_merge["Total_formandos"].sum()
    if total_formandos == 0:
        return 0.0

    # Média ponderada: soma(nota * formandos) / total_formandos
    media = round(
        (df_merge[col_nota] * df_merge["Total_formandos"]).sum() / total_formandos,
        2
    )
    return media


def _resultado_vazio() -> dict:
    """Devolve um dicionário com todos os valores a zero/vazio."""
    return {
        "NOTAS_FORMANDOS_PRES":             0.0,
        "NUM_FORMANDOS_APROV_PRES":         0,
        "NUM_DESISTENTES_PRES":             0,

        "NOTAS_FORMANDOS_BL":               0.0,
        "NUM_FORMANDOS_APROV_BL":           0,
        "NUM_DESISTENTES_BL":               0,

        "NOTAS_FORMANDOS_EL":               "",
        "NUM_FORMANDOS_APROV_EL":           "",
        "NUM_DESISTENTES_EL":               "",

        "MEDIA_NOTAS":                      0.0,
        "TOTAL_NUM_FORMANDOS_APROV":        0,
        "TOTAL_NUM_FORMANDOS_DESISTENTES":  0,
    }