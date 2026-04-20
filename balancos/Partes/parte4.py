import pandas as pd
import re
from pathlib import Path
import numpy as np # Adicionado para facilitar a checagem de valores nulos

SCRIPT_DIR = Path(__file__).parent.parent

def calcular_parte4(regiao, ano):
    resultados = {}
    nome_limpo = re.sub(r'[^a-zA-Z0-9_]', '_', regiao.strip())
    caminho = SCRIPT_DIR / "relatorios" / str(ano) / f"Relatório_{nome_limpo}.xlsx"

    if not caminho.exists():
        print(f"⚠ Relatório não encontrado: {caminho}")
        return resultados

    padrao = re.compile(r"^[A-Z]\d+(\.\d+)*$")
    xls = pd.ExcelFile(caminho)

    # =========================
    # LER RELATÓRIO
    # =========================
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet, header=None)

        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                celula = str(df.iat[i, j]).strip() if pd.notna(df.iat[i, j]) else ""

                if padrao.fullmatch(celula):
                    codigo = celula.replace(".", "_")
                    if j > 0:
                        valor = df.iat[i, j - 1]
                        
                        # Tentamos converter, se falhar ou for vazio, guardamos como None
                        try:
                            if pd.isna(valor) or str(valor).strip() == "":
                                resultados[codigo] = None
                            else:
                                resultados[codigo] = round(float(valor), 3)
                        except:
                            resultados[codigo] = None

    # =========================
    # PRIORIDADE E FALLBACK LOGIC
    # =========================
    resultados_parte4 = {}

    # 1. Primeiro, identificamos todos os códigos da Parte 4 que TÊM valor real
    for codigo, valor in resultados.items():
        if codigo.startswith(("A4_", "B4_", "C4_", "D4_", "E4_")):
            # Só adicionamos se o valor não for None
            if valor is not None:
                resultados_parte4[codigo] = valor

    # 2. Fazemos o fallback da Parte 3 para a Parte 4
    for codigo, valor in resultados.items():
        if codigo.startswith(("A3_", "B3_", "C3_", "D3_", "E3_")):
            codigo4 = codigo.replace("3_", "4_", 1)

            # CONDIÇÃO DE SUBSTITUIÇÃO:
            # Se o código4 não existe OU se ele existe mas o valor é None/vazio
            if codigo4 not in resultados_parte4 or resultados_parte4[codigo4] is None:
                # Só substitui se o valor da Parte 3 for válido
                if valor is not None:
                    resultados_parte4[codigo4] = valor

    print(f"✅ Parte 4: {len(resultados_parte4)} indicadores processados (com validação de valor)")
    return resultados_parte4