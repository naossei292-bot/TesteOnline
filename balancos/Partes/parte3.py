import pandas as pd
import re
from pathlib import Path
from docx import Document
import logging
from datetime import datetime
import os

# Configurar logging - CRIAR A PASTA LOGS SE NÃO EXISTIR
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)  # ← CRIA A PASTA SE NÃO EXISTIR

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Mostrar no terminal
        logging.FileHandler(logs_dir / f'parte3_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')  # Guardar em ficheiro
    ]
)
logger = logging.getLogger(__name__)

def calcular_parte3(regiao, df_acoes, ano):
    logger.info("="*70)
    logger.info(f"📄 PARTE 3 - Processando região: {regiao} | Ano: {ano}")
    logger.info("="*70)
    
    indicadores = {}
    estagios_resultados = {
        "estagios": [],
        "NUM_FORMANDOS_TOTAL": 0,
        "FORMANDOS_ESTAGIO_TOTAL": 0,
        "FORMANDOS_ESTAGIO_TAXA_TOTAL": 0.0,
        "FORMANDOS_NAOESTAGIO_TAXA_TOTAL": 0.0,
    }

    nome_limpo = re.sub(r'[^a-zA-Z0-9_]', '_', regiao.strip())

    # ====================== PROCURAR EXCEL ======================
    logger.info(f"📂 Procurando relatório Excel para {regiao}...")
    pasta_relatorios = Path(__file__).parent.parent / "relatorios" / str(ano)
    logger.info(f"   Pasta base: {pasta_relatorios}")
    
    if not pasta_relatorios.exists():
        logger.warning(f"⚠ Pasta não encontrada: {pasta_relatorios}")
        return {**indicadores, **estagios_resultados}

    possiveis_nomes = [
        f"Relatório_{nome_limpo}.xlsx",
        f"Relatorio_{nome_limpo}.xlsx",
        f"Relatório_{regiao.replace(' ', '_')}.xlsx",
        f"Relatorio_{regiao.replace(' ', '_')}.xlsx",
    ]
    
    logger.info(f"   A procurar por: {possiveis_nomes}")

    caminho_excel = None
    for nome in possiveis_nomes:
        candidato = pasta_relatorios / nome
        if candidato.exists():
            caminho_excel = candidato
            logger.info(f" ✅ Ficheiro encontrado: {caminho_excel}")
            break
        else:
            logger.debug(f"   ❌ Não encontrado: {candidato}")

    if not caminho_excel:
        logger.warning(f"⚠ Nenhum relatório encontrado para '{regiao}'")
        logger.info(f"   Conteúdo da pasta {pasta_relatorios}:")
        if pasta_relatorios.exists():
            for f in pasta_relatorios.iterdir():
                logger.info(f"      - {f.name}")
        return {**indicadores, **estagios_resultados}

    # ====================== PROCESSAR EXCEL ======================
    logger.info("📊 Processando Excel...")
    padrao_codigo = re.compile(r"^[A-Z]\d+(\.\d+)*$")

    try:
        xls = pd.ExcelFile(caminho_excel)
        logger.info(f"   Folhas encontradas: {xls.sheet_names}")

        for sheet_name in xls.sheet_names:
            if sheet_name in ["Resumo", "Folha1", "Sheet1", "Instruções"]:
                logger.debug(f"   Ignorando folha: {sheet_name}")
                continue

            logger.debug(f"   Processando folha: {sheet_name}")
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)

            for i in range(df.shape[0]):
                if df.shape[1] <= 5:
                    continue

                celula_codigo = str(df.iat[i, 5]).strip() if pd.notna(df.iat[i, 5]) else ""
                valor = df.iat[i, 4] if pd.notna(df.iat[i, 4]) else None

                if padrao_codigo.fullmatch(celula_codigo) and isinstance(valor, (int, float)):
                    codigo_word = celula_codigo.replace(".", "_")
                    indicadores[codigo_word] = round(float(valor), 3)

        logger.info(f" ✅ Extraídos {len(indicadores)} indicadores para o Word")
        if indicadores:
            logger.debug(f"   Exemplo: {list(indicadores.items())[:5]}")

    except Exception as e:
        logger.error(f"❌ Erro ao processar Excel: {e}")
        import traceback
        traceback.print_exc()
        return {**indicadores, **estagios_resultados}

    # ====================== 2. ESTÁGIOS - PROCURA DINÂMICA POR ANO ======================
    logger.info("\n" + "="*70)
    logger.info(f"📊 Processando estágios para {regiao} | Ano: {ano}")
    logger.info("="*70)

    base_path = Path(__file__).parent.parent
    logger.info(f"   Base path: {base_path}")

    # 🔴 FUNÇÃO PARA PROCURAR O FICHEIRO DE ESTÁGIOS COM LOGS DETALHADOS
    def encontrar_ficheiro_estagios(base_path, ano):
        """Procura o ficheiro Modelo Estagios.xlsx em várias localizações possíveis"""
        
        logger.info(f"\n🔍 A PROCURAR ficheiro de estágios para o ano {ano}...")
        
        # Lista de possíveis caminhos (por ordem de preferência)
        possiveis_caminhos = [
            # 1. Na pasta do ano específico (estrutura desejada)
            (base_path / "dados" / str(ano) / "Modelo Estagios.xlsx", "Pasta do ano"),
            (base_path / "dados" / str(ano) / "Modelo_Estagios.xlsx", "Pasta do ano (com underscore)"),
            
            # 2. Na raiz da pasta dados
            (base_path / "dados" / "Modelo Estagios.xlsx", "Raiz da pasta dados"),
            (base_path / "dados" / "Modelo_Estagios.xlsx", "Raiz da pasta dados (com underscore)"),
            
            # 3. Caminho relativo
            (Path(f"dados/{ano}/Modelo Estagios.xlsx"), "Caminho relativo - pasta ano"),
            (Path("dados/Modelo Estagios.xlsx"), "Caminho relativo - raiz"),
        ]
        
        logger.info(f"📁 A verificar {len(possiveis_caminhos)} possíveis localizações:")
        
        for caminho, descricao in possiveis_caminhos:
            logger.info(f"   🔎 {descricao}: {caminho}")
            if caminho.exists():
                logger.info(f"   ✅ ENCONTRADO! → {caminho}")
                return caminho
            else:
                logger.debug(f"   ❌ Não encontrado")
        
        # Se não encontrou, listar o que existe na pasta dados
        logger.warning(f"\n⚠ Nenhum ficheiro de estágios encontrado!")
        logger.info(f"\n📁 A explorar pasta 'dados' em: {base_path / 'dados'}")
        
        pasta_dados = base_path / "dados"
        if pasta_dados.exists():
            logger.info("   Conteúdo da pasta 'dados':")
            for item in pasta_dados.iterdir():
                if item.is_dir():
                    logger.info(f"      📁 PASTA: {item.name}/")
                    # Verificar se dentro da subpasta existe o ficheiro
                    ficheiro_estagios = item / "Modelo Estagios.xlsx"
                    if ficheiro_estagios.exists():
                        logger.info(f"         ✅ ENCONTRADO: {ficheiro_estagios}")
                    else:
                        # Listar ficheiros .xlsx dentro da subpasta
                        xlsx_files = list(item.glob("*.xlsx"))
                        if xlsx_files:
                            logger.info(f"         📄 Ficheiros .xlsx nesta pasta:")
                            for f in xlsx_files:
                                logger.info(f"            - {f.name}")
                        else:
                            logger.info(f"         (sem ficheiros .xlsx)")
                elif item.suffix == '.xlsx':
                    logger.info(f"      📄 FICHEIRO: {item.name}")
        else:
            logger.warning(f"      Pasta 'dados' não encontrada em {pasta_dados}")
        
        # Tentar listar também a partir do diretório atual
        logger.info(f"\n📁 A explorar 'dados' a partir do diretório atual:")
        pasta_dados_atual = Path("dados")
        if pasta_dados_atual.exists():
            for item in pasta_dados_atual.iterdir():
                if item.is_dir():
                    logger.info(f"      📁 {item.name}/")
                    ficheiro_estagios = item / "Modelo Estagios.xlsx"
                    if ficheiro_estagios.exists():
                        logger.info(f"         ✅ ENCONTRADO: {ficheiro_estagios}")
                elif item.suffix == '.xlsx':
                    logger.info(f"      📄 {item.name}")
        else:
            logger.warning(f"      Pasta 'dados' não encontrada no diretório atual")
        
        return None

    try:
        # Usar a função para encontrar o ficheiro
        logger.info("\n" + "-"*50)
        logger.info("🎯 INICIANDO BUSCA PELO FICHEIRO DE ESTÁGIOS")
        logger.info("-"*50)
        
        caminho_estagios = encontrar_ficheiro_estagios(base_path, ano)
        
        if caminho_estagios is None:
            logger.error(f"❌ ERRO: Ficheiro de estágios NÃO ENCONTRADO para o ano {ano}")
            logger.info("="*70)
            return {**indicadores, **estagios_resultados}
        
        logger.info(f"\n✅ SUCESSO: Ficheiro de estágios ENCONTRADO em:")
        logger.info(f"   {caminho_estagios}")
        logger.info(f"   Tamanho: {caminho_estagios.stat().st_size} bytes")
        logger.info(f"   Última modificação: {datetime.fromtimestamp(caminho_estagios.stat().st_mtime)}")
        
        # Verificar se o DataFrame df_acoes tem dados
        logger.info(f"\n📊 Verificando df_acoes para {regiao}:")
        df_regiao = df_acoes.copy() if df_acoes is not None else pd.DataFrame()
        logger.info(f"   df_acoes é None? {df_acoes is None}")
        logger.info(f"   Número de linhas: {len(df_regiao)}")
        logger.info(f"   Colunas disponíveis: {df_regiao.columns.tolist() if not df_regiao.empty else 'DataFrame vazio'}")

        if df_regiao.empty:
            logger.warning(" ⚠ Sem dados de ações para esta região (DataFrame vazio)")
            return {**indicadores, **estagios_resultados}
        
        if "U_id" not in df_regiao.columns:
            logger.warning(f" ⚠ Coluna 'U_id' não encontrada no DataFrame")
            logger.info(f"   Colunas disponíveis: {df_regiao.columns.tolist()}")
            return {**indicadores, **estagios_resultados}
        
        logger.info(f"   Primeiras U_ids: {df_regiao['U_id'].head().tolist()}")
        
        # Ler o ficheiro de estágios
        logger.info(f"\n📖 A ler ficheiro de estágios: {caminho_estagios}")
        df_estagios = pd.read_excel(caminho_estagios)
        df_estagios.columns = df_estagios.columns.str.strip()
        
        logger.info(f"   Ficheiro lido com sucesso!")
        logger.info(f"   Número de linhas: {len(df_estagios)}")
        logger.info(f"   Colunas disponíveis: {df_estagios.columns.tolist()}")
        
        # Verificar se as colunas necessárias existem
        colunas_necessarias = ["U_id", "Exp"]
        for col in colunas_necessarias:
            if col not in df_estagios.columns:
                logger.warning(f" ⚠ Coluna '{col}' NÃO encontrada no ficheiro de estágios")
                logger.info(f"    Colunas disponíveis: {df_estagios.columns.tolist()}")
                return {**indicadores, **estagios_resultados}
            else:
                logger.info(f"   ✅ Coluna '{col}' encontrada")

        # Preparar dados para merge
        df_regiao["U_id"] = df_regiao["U_id"].astype(str).str.strip()
        df_estagios["U_id"] = df_estagios["U_id"].astype(str).str.strip()
        
        logger.info(f"\n🔗 A fazer merge dos dados...")
        logger.info(f"   U_ids únicas em df_regiao: {df_regiao['U_id'].nunique()}")
        logger.info(f"   U_ids únicas em df_estagios: {df_estagios['U_id'].nunique()}")
        
        # Encontrar U_ids que existem em ambos
        uids_regiao = set(df_regiao["U_id"])
        uids_estagios = set(df_estagios["U_id"])
        uids_comuns = uids_regiao.intersection(uids_estagios)
        
        logger.info(f"   U_ids em comum: {len(uids_comuns)}")
        if uids_comuns:
            logger.debug(f"   Exemplos: {list(uids_comuns)[:5]}")
        else:
            logger.warning("   ⚠ NENHUMA U_id em comum entre os dois DataFrames!")
            logger.info(f"   U_ids do df_regiao (primeiras 5): {list(uids_regiao)[:5]}")
            logger.info(f"   U_ids do df_estagios (primeiras 5): {list(uids_estagios)[:5]}")
        
        df_merge = pd.merge(df_regiao, df_estagios, on="U_id", how="left")
        logger.info(f"   Merge concluído. Total de linhas: {len(df_merge)}")
        
        # Processar dados
        df_merge["NUM_FORMANDOS"] = pd.to_numeric(df_merge["Total_formandos"], errors="coerce").fillna(0)
        df_merge["Exp"] = pd.to_numeric(df_merge["Exp"], errors="coerce").fillna(0)
        
        df_merge["TIPO_CURSO"] = df_merge["U_id"].str.split("/").str[0].str.replace("_BL", "", regex=False)
        
        logger.info(f"\n📊 A agrupar por tipo de curso...")
        agrupado = df_merge.groupby("TIPO_CURSO").agg({
            "NUM_FORMANDOS": "sum",
            "Exp": "sum"
        }).reset_index()
        
        logger.info(f"   Cursos encontrados: {len(agrupado)}")
        for _, row in agrupado.iterrows():
            logger.info(f"      - {row['TIPO_CURSO']}: {int(row['NUM_FORMANDOS'])} formandos, {int(row['Exp'])} estágios")
        
        lista_estagios = []
        total_formandos = 0
        total_estagio = 0
        
        for _, row in agrupado.iterrows():
            formandos = int(row["NUM_FORMANDOS"])
            estagio = int(row["Exp"])
            if formandos > 0:
                taxa_estagio = round((estagio / formandos) * 100, 0)
                taxa_nao = round(100 - taxa_estagio, 0)
                
                lista_estagios.append({
                    "TIPO_CURSO": row["TIPO_CURSO"],
                    "NUM_FORMANDOS": formandos,
                    "FORMANDOS_ESTAGIO": estagio,
                    "FORMANDOS_ESTAGIO_TAXA": int(taxa_estagio),
                    "FORMANDOS_NAOESTAGIO_TAXA": int(taxa_nao)
                })
                
                total_formandos += formandos
                total_estagio += estagio
        
        taxa_total = round((total_estagio / total_formandos) * 100, 0) if total_formandos > 0 else 0
        
        estagios_resultados.update({
            "estagios": lista_estagios,
            "NUM_FORMANDOS_TOTAL": total_formandos,
            "FORMANDOS_ESTAGIO_TOTAL": total_estagio,
            "FORMANDOS_ESTAGIO_TAXA_TOTAL": f"{int(taxa_total)}%",
            "FORMANDOS_NAOESTAGIO_TAXA_TOTAL": f"{int(100 - taxa_total)}%"
        })
        
        logger.info(f"\n✅ RESULTADO FINAL DOS ESTÁGIOS:")
        logger.info(f"   Total de formandos: {total_formandos}")
        logger.info(f"   Total em estágio: {total_estagio}")
        logger.info(f"   Taxa de estágio: {int(taxa_total)}%")
        logger.info(f"   Cursos processados: {len(lista_estagios)}")
        
    except Exception as e:
        logger.error(f"⚠ Erro ao processar estágios: {e}")
        import traceback
        traceback.print_exc()
    
    logger.info("="*70)
    logger.info(f"🏁 Fim do processamento da Parte 3 para {regiao}")
    logger.info("="*70 + "\n")
    
    return {**indicadores, **estagios_resultados}