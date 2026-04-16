import pandas as pd
import os
import argparse

from docxtpl                   import DocxTemplate
from jinja2                    import Environment, ChainableUndefined
from pathlib                   import Path
from Partes.parte1             import calcular_parte1
from Partes.parte2             import gerar_tabela_acoes, gerar_tabela_cursos, calcular_totais_parte2
from Partes.parte3             import calcular_parte3
from Partes.parte4             import calcular_parte4
from Partes.parte5             import calcular_parte5
from Partes.parte6             import calcular_parte6
from Partes.parte7             import calcular_parte7
from Partes.PreencherRelatorio import preparar_dados_moodle

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent


# -------------------------
# AUXILIARES
# -------------------------
def limpar_colunas(df):
    df.columns = df.columns.str.strip()
    return df


def carregar_excel(ano):
    """Carrega os ficheiros Excel para o ano especificado"""
    df = limpar_colunas(pd.read_excel(SCRIPT_DIR / f"dados/{ano}/Modelo Execução Fisica.xlsx"))
    df_notas = limpar_colunas(pd.read_excel(SCRIPT_DIR / f"dados/{ano}/Media Notas.xlsx"))
    xls_centros = pd.ExcelFile(SCRIPT_DIR / f"dados/{ano}/Modelo Formacao Centros.xlsx")

    df["Deslocal"] = df["Deslocal"].astype(str).str.strip()

    return df, df_notas, xls_centros


def gerar_balancos(ano):    
    balanco_dir = SCRIPT_DIR / "balanco"
    balanco_dir.mkdir(exist_ok=True)

    df, df_notas, xls_centros = carregar_excel(ano)

    regioes = xls_centros.sheet_names
    env = Environment(undefined=ChainableUndefined)

    for regiao in regioes:
        print(f"\n{'='*60}")
        print(f"📍 A criar balanço para: {regiao}")
        print(f"{'='*60}")

        # ====================== CARREGAR DADOS ======================
        df_centros = limpar_colunas(
            pd.read_excel(xls_centros, sheet_name=regiao, header=2)
        )

        doc = DocxTemplate(SCRIPT_DIR /"Modelos"/ "Modelo.docx")

        # ====================== PARTE 2 - TABELA DE AÇÕES + TOTAIS ======================
        dados_acoes  = gerar_tabela_acoes(df, regiao)      # Tabela 1 - Ações da região
        dados_cursos = gerar_tabela_cursos(df_centros)     # Tabela 2 - Cursos por tipologia

        # ←←← CÁLCULO DOS TOTAIS APENAS PARA ESTA REGIÃO
        dados_totais_parte2 = calcular_totais_parte2(
            dados_acoes["acoes"], 
            dados_cursos["cursos"]
        )

        # Converter para DataFrame só para debug
        df_acoes_regiao = df[df["Deslocal"] == regiao].copy()

        print(f"\n📊 Dados de ações para {regiao}: {len(df_acoes_regiao)} registos")

        # ====================== OUTRAS PARTES ======================
        dados_parte1 = calcular_parte1(df, regiao)
        dados_parte3 = calcular_parte3(regiao, df_acoes_regiao, ano)
        dados_parte4 = calcular_parte4(regiao, ano)
        dados_parte5 = calcular_parte5(regiao, ano)
        dados_parte6 = calcular_parte6(df, df_notas, regiao)
        dados_parte7 = calcular_parte7(ano, regiao)

        # ====================== CONTEXT ======================
        context = {
            "REGIAO": regiao,
            "ANO": ano,
            "ANO_SEGUINTE": ano + 1,
            
            **dados_parte1,
            **dados_acoes,
            **dados_cursos,
            **dados_parte3,
            **dados_parte4,
            **dados_parte5,
            **dados_parte6,
            **dados_totais_parte2,
            **dados_parte7,
        }
        
        # ====================== DEBUG DOS TOTAIS ======================
        print(f"\n🔢 TOTAIS CALCULADOS PARA {regiao.upper()}:")
        print(f"   Formandos Total    : {dados_totais_parte2.get('NUM_FORMANDOS_TOTAL', 0)}")
        print(f"   Desistências Total : {dados_totais_parte2.get('DESISTENCIAS_TOTAL', 0)}")
        print(f"   Horas Total        : {dados_totais_parte2.get('HORAS_FORMACAO_TOTAL', 0)}")
        print(f"   Volume Formação    : {dados_totais_parte2.get('VOLUME_FORMACAO_TOTAL', 0)}")
        print(f"   Nº Total Ações     : {dados_totais_parte2.get('NUM_TOTAL_ACOES', 0)}")

        # ====================== GERAR DOCUMENTO ======================
        doc.render(context, jinja_env=env)

        pasta_ano = SCRIPT_DIR / "balanco" / str(ano)
        pasta_ano.mkdir(parents=True, exist_ok=True)

        caminho = pasta_ano / f"BA_{regiao}_{ano}.docx"
        doc.save(str(caminho))

        print(f"\n✅ Criado: {caminho}")
        print(f"{'='*60}\n")


def obter_ano():
    """Solicita ao utilizador o ano para processamento"""
    while True:
        try:
            ano = int(input("\n📅 Digite o ano (ex: 2022): "))
            if ano > 0:
                return ano
            else:
                print("❌ Por favor, digite um ano válido!")
        except ValueError:
            print("❌ Por favor, digite um número válido!")


def mostrar_menu():
    """Mostra o menu interativo"""
    print("\n" + "="*50)
    print("   GESTOR DE RELATÓRIOS E BALANÇOS")
    print("="*50)
    print("1️⃣  Gerar apenas BALANÇOS")
    print("2️⃣  Gerar apenas RELATÓRIOS Excel")
    print("3️⃣  Gerar AMBOS (Balanços + Relatórios)")
    print("0️⃣  Sair")
    print("="*50)
    
    while True:
        opcao = input("\n👉 Escolha uma opção (0-3): ").strip()
        if opcao in ['0', '1', '2', '3']:
            return opcao
        else:
            print("❌ Opção inválida! Escolha 0, 1, 2 ou 3.")


# -------------------------
# MENU PRINCIPAL
# -------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Gerar relatórios e balanços')
    parser.add_argument('--ano', type=int, help='Ano para processamento')
    parser.add_argument('--operacao', type=int, choices=[1, 2, 3], 
                        help='1: Apenas balanços, 2: Apenas relatórios, 3: Ambos')
    
    args = parser.parse_args()
    
    if args.ano and args.operacao:
        # ====================== MODO AUTOMÁTICO (Chamado pelo servidor) ======================
        print(f"\n🚀 Executando em modo automático:")
        print(f"   Ano: {args.ano}")
        print(f"   Operação: {args.operacao}")
        
        # Criar pastas do ano se necessário
        ano_str = str(args.ano)
        dados_ano_dir = Path(SCRIPT_DIR) / "dados" / ano_str
        relatorios_ano_dir = Path(SCRIPT_DIR) / "relatorios" / ano_str
        
        dados_ano_dir.mkdir(parents=True, exist_ok=True)
        relatorios_ano_dir.mkdir(parents=True, exist_ok=True)
        
        if args.operacao in [2, 3]:  # Inclui relatórios
            print(f"📁 Preparando relatórios para {args.ano}...")
            preparar_dados_moodle(args.ano)
        
        if args.operacao in [1, 3]:  # Inclui balanços
            print(f"📁 Gerando balanços para {args.ano}...")
            gerar_balancos(args.ano)
        
        print("\n✅ Processamento concluído!")
        
    else:
        # ====================== MODO INTERATIVO (Para testes rápidos) ======================
        print("\n" + "="*50)
        print("   BEM-VINDO AO GESTOR DE RELATÓRIOS")
        print("="*50)
        print("💡 Dica: Use este menu para testes rápidos")
        print("   O servidor web usa o modo automático")
        print("="*50)
        
        while True:
            opcao = mostrar_menu()
            
            if opcao == "0":
                print("\n👋 Programa encerrado. Até mais!")
                break
                
            elif opcao == "1":
                ano = obter_ano()
                print(f"\n📁 Gerando balanços para {ano}...")
                
                # Criar pasta do ano se necessário
                dados_ano_dir = Path(SCRIPT_DIR) / "dados" / str(ano)
                dados_ano_dir.mkdir(parents=True, exist_ok=True)
                
                gerar_balancos(ano)
                input("\n✅ Processo concluído! Pressione ENTER para continuar...")
                
            elif opcao == "2":
                ano = obter_ano()
                print(f"\n📁 Preparando relatórios para {ano}...")
                
                # Criar pastas do ano se necessário
                dados_ano_dir = Path(SCRIPT_DIR) / "dados" / str(ano)
                relatorios_ano_dir = Path(SCRIPT_DIR) / "relatorios" / str(ano)
                dados_ano_dir.mkdir(parents=True, exist_ok=True)
                relatorios_ano_dir.mkdir(parents=True, exist_ok=True)
                
                preparar_dados_moodle(ano)
                input("\n✅ Processo concluído! Pressione ENTER para continuar...")
                
            elif opcao == "3":
                ano = obter_ano()
                print(f"\n📁 Processando ano {ano} (Relatórios + Balanços)...")
                
                # Criar pastas do ano se necessário
                dados_ano_dir = Path(SCRIPT_DIR) / "dados" / str(ano)
                relatorios_ano_dir = Path(SCRIPT_DIR) / "relatorios" / str(ano)
                dados_ano_dir.mkdir(parents=True, exist_ok=True)
                relatorios_ano_dir.mkdir(parents=True, exist_ok=True)
                
                preparar_dados_moodle(ano)
                gerar_balancos(ano)
                input("\n✅ Processo concluído! Pressione ENTER para continuar...")