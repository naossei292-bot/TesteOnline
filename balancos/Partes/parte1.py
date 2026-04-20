import pandas as pd

def calcular_parte1(df, regiao):
    df = df.copy()
    df.columns = df.columns.str.strip()

    # Encontrar coluna Deslocal de forma segura
    col_deslocal = None
    for col in df.columns:
        if str(col).strip().lower() == "deslocal":
            col_deslocal = col
            break

    if col_deslocal is None:
        print(f"❌ ERRO: Coluna 'Deslocal' não encontrada em calcular_parte1!")
        return {}

    df[col_deslocal] = df[col_deslocal].astype(str).str.strip()

    dados = df[df[col_deslocal] == regiao].copy()

    print(f"🔍 calcular_parte1 -> '{regiao}' | Linhas encontradas: {len(dados)}")

    if len(dados) == 0:
        print(f"   ⚠️ Nenhuma linha para {regiao} em parte1!")

    # resto da função (mantém quase igual)
    dados["U_id"] = dados["U_id"].astype(str).str.upper().str.strip()

    dados["Nhoras"] = pd.to_numeric(dados["Nhoras"], errors="coerce")
    dados["Total_formandos"] = pd.to_numeric(dados["Total_formandos"], errors="coerce")
    dados["Desistentes"] = pd.to_numeric(dados["Desistentes"], errors="coerce")

    dados["TIPO"] = "PRES"
    dados.loc[dados["U_id"].str.contains("_BL", na=False), "TIPO"] = "BL"
    dados.loc[dados["U_id"].str.contains("_EL", na=False), "TIPO"] = "EL"

    dados["VOLUME"] = dados["Nhoras"] * dados["Total_formandos"]

    resumo = dados.groupby("TIPO").agg(
        NUM_ACOES=("U_id", "count"),
        HORAS=("Nhoras", "sum"),
        FORMANDOS=("Total_formandos", "sum"),
        VOLUME=("VOLUME", "sum"),
        DESISTENCIAS=("Desistentes", "sum")
    ).fillna(0)

    pres = resumo.loc["PRES"] if "PRES" in resumo.index else {}
    bl = resumo.loc["BL"] if "BL" in resumo.index else {}
    el = resumo.loc["EL"] if "EL" in resumo.index else {}

    return {
        "NUM_TOTAL_ACOES": int(resumo["NUM_ACOES"].sum()),
        "NUM_ACOES_PRES": int(pres.get("NUM_ACOES", 0)),
        "NUM_ACOES_BL": int(bl.get("NUM_ACOES", 0)),
        "NUM_ACOES_EL": int(el.get("NUM_ACOES", 0)),

        "HORAS_FORMACAO": resumo["HORAS"].sum(),
        "HORAS_FORMACAO_PRES": pres.get("HORAS", 0),
        "HORAS_FORMACAO_BL": bl.get("HORAS", 0),
        "HORAS_FORMACAO_EL": el.get("HORAS", 0),

        "NUM_FORMANDOS_TOTAL": resumo["FORMANDOS"].sum(),
        "NUM_FORMANDOS_TOTAL_PRES": pres.get("FORMANDOS", 0),
        "NUM_FORMANDOS_TOTAL_BL": bl.get("FORMANDOS", 0),
        "NUM_FORMANDOS_TOTAL_EL": el.get("FORMANDOS", 0),

        "VOLUME_FORMACAO_TOTAL": resumo["VOLUME"].sum(),
        "VOLUME_FORMACAO_TOTAL_PRES": pres.get("VOLUME", 0),
        "VOLUME_FORMACAO_TOTAL_BL": bl.get("VOLUME", 0),
        "VOLUME_FORMACAO_TOTAL_EL": el.get("VOLUME", 0),

        "DESISTENCIAS_TOTAL": resumo["DESISTENCIAS"].sum(),
        "DESISTENCIAS_TOTAL_PRES": pres.get("DESISTENCIAS", 0),
        "DESISTENCIAS_TOTAL_BL": bl.get("DESISTENCIAS", 0),
        "DESISTENCIAS_TOTAL_EL": el.get("DESISTENCIAS", 0)
    }
