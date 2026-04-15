import pandas as pd
import streamlit as st

def processar_questionarios_excel(file):
    """Processa ficheiros Excel de questionários"""
    # Extração do nome do centro via nome do ficheiro
    nome_arquivo = file.name.replace(".xlsx", "").replace(".xls", "")
    centro_extraido = nome_arquivo.split("_")[-1] if "_" in nome_arquivo else "Geral"
    
    xl = pd.ExcelFile(file)
    todos_resultados = []
    abas_alvo = ['21a', '21b', '22a', '22b', '23a', '23b', '24a', '24b']
   
    for aba in xl.sheet_names:
        if aba not in abas_alvo:
            continue
        df_aba = xl.parse(aba, header=None)
        curso_atual = "Não Identificado"
        modalidade = "Presencial" if 'a' in aba else "À Distância"
       
        if '21' in aba or '22' in aba:
            tipo_resp = "Formando"
        elif '23' in aba:
            tipo_resp = "Formador/Tutor"
        else:
            tipo_resp = "Coordenação"

        for i in range(len(df_aba)):
            linha = df_aba.iloc[i].astype(str).values
            if "Curso" in linha:
                curso_atual = str(df_aba.iloc[i, 1])
            if "Categorias/Subcategorias" in linha:
                j = i + 1
                while j < len(df_aba):
                    pergunta = str(df_aba.iloc[j, 0])
                    media_val = df_aba.iloc[j, 1]
                    if "Resultados por categoria" in pergunta or pd.isna(df_aba.iloc[j, 0]):
                        break
                    try:
                        cat_letra = pergunta[0] if pergunta[0].isalpha() else "Outros"
                        val_num = float(str(media_val).replace(",", "."))
                        todos_resultados.append({
                            "Centro": centro_extraido,
                            "Curso": curso_atual, 
                            "Modalidade": modalidade, 
                            "Respondente": tipo_resp,
                            "Categoria": cat_letra, 
                            "Pergunta": pergunta, 
                            "Media": val_num
                        })
                    except:
                        pass
                    j += 1
    return pd.DataFrame(todos_resultados)