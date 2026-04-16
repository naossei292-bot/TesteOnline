import pandas as pd
import re
from pathlib import Path
import numpy as np

SCRIPT_DIR = Path(__file__).parent.parent

def calcular_parte5(regiao, ano):
    resultados = {}
    nome_limpo = re.sub(r'[^a-zA-Z0-9_]', '_', regiao.strip())
    caminho = SCRIPT_DIR / "relatorios" / str(ano) / f"Relatório_{nome_limpo}.xlsx"

    if not caminho.exists():
        print(f"⚠ Relatório não encontrado: {caminho}")
        return resultados

    padrao = re.compile(r"^[A-Z]\d+(\.\d+)*$")
    xls = pd.ExcelFile(caminho)

    # ==========================================
    # 1. LER TODO O RELATÓRIO (Dicionário Base)
    # ==========================================
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet, header=None)
        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                celula = str(df.iat[i, j]).strip() if pd.notna(df.iat[i, j]) else ""

                if padrao.fullmatch(celula):
                    codigo = celula.replace(".", "_")
                    if j > 0:
                        valor = df.iat[i, j - 1]
                        try:
                            # Validação rigorosa de número
                            if pd.isna(valor) or str(valor).strip() == "":
                                resultados[codigo] = None
                            else:
                                resultados[codigo] = round(float(valor), 3)
                        except:
                            resultados[codigo] = None

    # ==========================================
    # 2. LÓGICA DE MÉDIA E FALLBACK (Parte 5)
    # ==========================================
    resultados_parte5 = {}
    
    # Vamos iterar sobre todos os códigos encontrados que sejam Parte 3 ou Parte 4
    # para gerar o correspondente na Parte 5
    todos_os_codigos = list(resultados.keys())
    
    for codigo in todos_os_codigos:
        # Só nos interessam prefixos A, B, C, D, E das partes 3 ou 4
        if not codigo.startswith(("A3_", "B3_", "C3_", "D3_", "E3_", "A4_", "B4_", "C4_", "D4_", "E4_")):
            continue
            
        # Criamos a base do código para a parte 5 (ex: A3_1_1 -> A_1_1)
        # Usamos o sufixo (tudo depois do primeiro underscore)
        sufixo = codigo.split("_", 1)[1] if "_" in codigo else ""
        prefixo_letra = codigo[0] # A, B, C...
        
        codigo3 = f"{prefixo_letra}3_{sufixo}"
        codigo4 = f"{prefixo_letra}4_{sufixo}"
        codigo5 = f"{prefixo_letra}5_{sufixo}"

        # Se já processámos este código 5, saltamos
        if codigo5 in resultados_parte5:
            continue

        v3 = resultados.get(codigo3)
        v4 = resultados.get(codigo4)

        # Caso 1: Temos os dois valores válidos -> Fazemos a média
        if v3 is not None and v4 is not None:
            resultados_parte5[codigo5] = round((v3 + v4) / 2, 3)
        
        # Caso 2: Só temos o valor da Parte 4
        elif v4 is not None:
            resultados_parte5[codigo5] = v4
            
        # Caso 3: Só temos o valor da Parte 3
        elif v3 is not None:
            resultados_parte5[codigo5] = v3

    print(f"✅ Parte 5: {len(resultados_parte5)} indicadores processados (Média 3/4 + Fallback)")
    return resultados_parte5