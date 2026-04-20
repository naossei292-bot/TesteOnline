import pandas as pd


def _safe_int(val):
    """Converte valor para int, devolvendo 0 se NaN ou inválido."""
    try:
        if pd.isna(val):
            return 0
        return int(val)
    except (TypeError, ValueError):
        return 0


def _safe_float(val, decimais=2):
    """Converte valor para float arredondado, devolvendo 0.0 se inválido."""
    try:
        if pd.isna(val):
            return 0.0
        return round(float(val), decimais)
    except (TypeError, ValueError):
        return 0.0


def _formatar_data(val):
    """Formata data para string dd/mm/aaaa, ou devolve string original."""
    try:
        if pd.isna(val):
            return ""
        return pd.to_datetime(val, dayfirst=True).strftime("%d/%m/%Y")
    except Exception:
        return str(val).strip()


def _limpar_texto(val) -> str:
    """Converte para string, descartando 'nan' e espaços extra."""
    s = str(val).strip()
    return "" if s.lower() == "nan" else s


# ─────────────────────────────────────────────
# TABELA 1 — Ações de formação da região
# Fonte: Modelo Execução Fisica.xlsx
# ─────────────────────────────────────────────

def gerar_tabela_acoes(df: pd.DataFrame, regiao: str) -> dict:
    """
    Filtra as ações da região e devolve a lista 'acoes' para o template.
    Versão robusta com melhor limpeza e debug.
    """
    df = df.copy()
    df.columns = df.columns.str.strip()   # Remove espaços nas colunas

    # ====================== DEBUG ======================
    print(f"\n🔍 DEBUG Filtro - Região solicitada: '{regiao}'")
    print(f"   Colunas disponíveis: {list(df.columns)}")

    # Procurar a coluna Deslocal (tolerante a maiúsculas/minúsculas e espaços)
    col_deslocal = None
    for col in df.columns:
        if col.strip().lower() == "deslocal":
            col_deslocal = col
            break

    if col_deslocal is None:
        print(f"   ❌ ERRO: Coluna 'Deslocal' não encontrada!")
        return {"acoes": []}

    print(f"   Coluna usada para filtro: '{col_deslocal}'")

    # Limpeza forte da coluna: substitui NaN por string vazia e converte para string
    df[col_deslocal] = df[col_deslocal].fillna('').astype(str).str.strip()

    # Mostrar valores únicos (já todos strings, ordenação segura)
    valores_unicos = sorted(df[col_deslocal].unique())
    print(f"   Valores únicos em Deslocal ({len(valores_unicos)}): {valores_unicos[:30]}")  # limita a 30

    # Filtro principal
    df_regiao = df[df[col_deslocal] == regiao].copy()

    print(f"   ✅ Linhas encontradas para '{regiao}': {len(df_regiao)}")

    if len(df_regiao) == 0:
        print(f"   ⚠️ AVISO: Nenhuma linha encontrada. Testando filtro parcial...")
        # Usar contains para ver se há correspondência aproximada
        df_parcial = df[df[col_deslocal].str.contains(regiao, na=False, case=False)]
        print(f"   Linhas com contains '{regiao}': {len(df_parcial)}")

    # ====================== PROCESSAR AÇÕES ======================
    acoes = []
    for _, row in df_regiao.iterrows():
        formandos = _safe_int(row.get("Total_formandos"))
        horas = _safe_int(row.get("Nhoras"))
        desistencias = _safe_int(row.get("Desistentes"))
        volume = formandos * horas

        acoes.append({
            "DATINI":             _formatar_data(row.get("Datini")),
            "DATFIM":             _formatar_data(row.get("Datfim")),
            "U_ID":               _limpar_texto(row.get("U_id", "")),
            "NUM_FORMANDOS":      formandos,
            "DESISTENCIAS_CURSO": desistencias,
            "HORAS_FORMACAO":     horas,
            "VOLUME_FORMACAO":    volume,
            "LOCAL_ACAO":         _limpar_texto(row.get("Localizacao", "")),
        })

    return {"acoes": acoes}


# ─────────────────────────────────────────────
# TABELA 2 — Cursos por tipologia do centro
# Fonte: Modelo Formacao Centros.xlsx (folha da região)
# ─────────────────────────────────────────────

def gerar_tabela_cursos(df_centros: pd.DataFrame) -> dict:
    """
    Lê a folha do centro (já carregada com header=2) e devolve a lista
    'cursos' para o template.

    Cada item contém:
      - TIPO_CURSO              : tipologia (ex. BAS, DL, EUFCD)
      - DURACAO_MEDIA           : duração média em dias
      - NUM_ACOES               : número de ações
      - HORAS_FORMACAO          : total de horas de formação
      - NUM_FORMANDOS           : número de formandos
      - DESISTENCIAS_CURSO      : número de desistências
      - VOLUME_FORMACAO         : volume de formação (horas/formando)
      - VOLUME_FORMACAO_AREA    : taxa de desistência (%)
    """
    df = df_centros.copy()
    df.columns = df.columns.str.strip()

    col_tipo      = "Tipologia de Curso"
    col_duracao   = "Duração Média (Dias)"
    col_acoes     = "Nº de Ações"
    col_horas     = "Total de Horas de Formação"
    col_desist    = "Desistências"
    col_formandos = "Nº de Formandos"
    col_volume    = "Volume de Formação (Horas/Formando)"
    col_taxa      = "Taxa de Desistência (%)"

    # Apenas linhas com tipologia preenchida
    df_valido = df[df[col_tipo].notna()].copy()

    cursos = []
    for _, row in df_valido.iterrows():
        cursos.append({
            "TIPO_CURSO":           _limpar_texto(row.get(col_tipo, "")),
            "DURACAO_MEDIA":        _safe_int(row.get(col_duracao)),
            "NUM_ACOES":            _safe_int(row.get(col_acoes)),
            "HORAS_FORMACAO":       _safe_int(row.get(col_horas)),
            "NUM_FORMANDOS":        _safe_int(row.get(col_formandos)),
            "DESISTENCIAS_CURSO":   _safe_int(row.get(col_desist)),
            "VOLUME_FORMACAO":      _safe_float(row.get(col_volume)),
            "VOLUME_FORMACAO_AREA": _safe_float(row.get(col_taxa)),
        })

    return {"cursos": cursos}


# ─────────────────────────────────────────────
# TABELA 3 — Totais calculados
# Os totais do rodapé da tabela 2 (cursos) vêm da soma das linhas
# dessa tabela. Os totais do rodapé da tabela 1 (ações) vêm das acoes.
# ─────────────────────────────────────────────

def calcular_totais_parte2(acoes: list, cursos: list) -> dict:
    """
    Calcula totais priorizando SEMPRE os dados das ações da região.
    Só usa a tabela de cursos se realmente tiver dados úteis.
    """
    # Prioridade 1: Usar sempre os dados das ações (tabela 1)
    if acoes and len(acoes) > 0:
        print(f"   → Usando totais das AÇÕES da região ({len(acoes)} ações)")
        num_acoes       = len(acoes)
        horas_total     = sum(a.get("HORAS_FORMACAO", 0)     for a in acoes)
        formandos_total = sum(a.get("NUM_FORMANDOS", 0)      for a in acoes)
        desist_total    = sum(a.get("DESISTENCIAS_CURSO", 0) for a in acoes)
        volume_total    = sum(a.get("VOLUME_FORMACAO", 0)    for a in acoes)
    
    # Prioridade 2: Só usar cursos se não houver ações
    elif cursos and len(cursos) > 0:
        print(f"   → Usando totais da tabela de CURSOS ({len(cursos)} tipologias)")
        num_acoes       = sum(c.get("NUM_ACOES", 0)          for c in cursos)
        horas_total     = sum(c.get("HORAS_FORMACAO", 0)     for c in cursos)
        formandos_total = sum(c.get("NUM_FORMANDOS", 0)      for c in cursos)
        desist_total    = sum(c.get("DESISTENCIAS_CURSO", 0) for c in cursos)
        volume_total    = sum(c.get("VOLUME_FORMACAO", 0)    for c in cursos)
    else:
        print("   → Nenhum dado disponível")
        num_acoes = horas_total = formandos_total = desist_total = volume_total = 0

    return {
        "NUM_TOTAL_ACOES":       num_acoes,
        "HORAS_FORMACAO_TOTAL":  int(horas_total),
        "NUM_FORMANDOS_TOTAL":   int(formandos_total),
        "DESISTENCIAS_TOTAL":    int(desist_total),
        "VOLUME_FORMACAO_TOTAL": int(volume_total),
    }