import streamlit as st
import sys
import os
import zipfile
import io
from glob import glob
from pathlib import Path
from datetime import datetime
import pandas as pd

# ========================= CONFIGURAÇÃO DE CAMINHOS =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BALANCOS_DIR = os.path.join(BASE_DIR, 'balancos')
sys.path.insert(0, BALANCOS_DIR)

from balancos.main import gerar_balancos, preparar_dados_moodle

# Pastas de saída
PASTA_BALANCO = os.path.join(BALANCOS_DIR, "balanco")
PASTA_RELATORIOS = os.path.join(BALANCOS_DIR, "relatorios")
PASTA_DADOS = os.path.join(BALANCOS_DIR, "dados")          # 👈 NOVO

# Criar pastas se não existirem
os.makedirs(PASTA_BALANCO, exist_ok=True)
os.makedirs(PASTA_RELATORIOS, exist_ok=True)
os.makedirs(PASTA_DADOS, exist_ok=True)                   # 👈 NOVO

# ========================= FUNÇÕES AUXILIARES =========================
def extrair_ano_do_caminho(caminho, pasta_base):
    """
    Extrai o ano a partir da subpasta relativa à pasta_base.
    Exemplo: /.../balanco/2024/BA_xxx.docx -> 2024
    """
    rel_path = os.path.relpath(caminho, pasta_base)
    partes = Path(rel_path).parts
    if len(partes) > 0 and partes[0].isdigit():
        return partes[0]
    # Se estiver directamente na raiz, tenta extrair do nome do ficheiro
    nome = os.path.basename(caminho)
    for parte in nome.split('_'):
        if parte.isdigit() and len(parte) == 4:
            return parte
    return "Desconhecido"

def listar_ficheiros(pasta, extensoes=None):
    """
    Retorna lista de dicionários com info de cada ficheiro.
    """
    if not os.path.exists(pasta):
        return []
    if extensoes is None:
        extensoes = ["*.*"]
    ficheiros = []
    for ext in extensoes:
        for f in glob(os.path.join(pasta, "**", ext), recursive=True):
            stat = os.stat(f)
            ficheiros.append({
                "caminho": f,
                "nome": os.path.basename(f),
                "tamanho_kb": round(stat.st_size / 1024, 2),
                "modificado": datetime.fromtimestamp(stat.st_mtime),
                "ano": extrair_ano_do_caminho(f, pasta),
                "extensao": os.path.splitext(f)[1].lower()
            })
    # Ordenar por data modificação (mais recente primeiro)
    ficheiros.sort(key=lambda x: x["modificado"], reverse=True)
    return ficheiros

def listar_ficheiros_dados(ano):
    """
    Lista todos os ficheiros dentro de dados/<ano>/
    """
    pasta_ano = os.path.join(PASTA_DADOS, str(ano))
    if not os.path.exists(pasta_ano):
        return []
    return listar_ficheiros(pasta_ano, extensoes=["*.*"])

def aplicar_filtros(ficheiros, tipo_filtro, ano_filtro, pesquisa):
    """
    Aplica os filtros da interface.
    """
    resultados = []
    for f in ficheiros:
        # Filtro por tipo (extensão ou categoria)
        if tipo_filtro:
            tipo_ok = False
            for t in tipo_filtro:
                if t == "Excel" and f["extensao"] in [".xlsx", ".xls"]:
                    tipo_ok = True
                elif t == "Word" and f["extensao"] == ".docx":
                    tipo_ok = True
                elif t == "Balanços" and "balanco" in f["caminho"] and f["extensao"] == ".docx":
                    tipo_ok = True
                elif t == "Relatórios" and "relatorios" in f["caminho"] and f["extensao"] in [".xlsx", ".xls"]:
                    tipo_ok = True
                elif t == "Moodle" and "moodle" in f["nome"].lower():
                    tipo_ok = True
            if not tipo_ok:
                continue
        # Filtro por ano
        if ano_filtro != "Todos" and f["ano"] != ano_filtro:
            continue
        # Filtro por pesquisa textual
        if pesquisa and pesquisa.lower() not in f["nome"].lower():
            continue
        resultados.append(f)
    return resultados

def exibir_sec_ficheiros(titulo, ficheiros, chave_prefix):
    """
    Exibe uma secção com listagem de ficheiros, botões individuais e acções globais.
    """
    st.subheader(titulo)
    if not ficheiros:
        st.info("Nenhum ficheiro encontrado.")
        return

    # Botões globais
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"📦 Download {titulo} (ZIP)", key=f"zip_{chave_prefix}"):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                for f in ficheiros:
                    zipf.write(f["caminho"], arcname=f["nome"])
            zip_buffer.seek(0)
            st.download_button(
                label="Clique para descarregar",
                data=zip_buffer,
                file_name=f"{chave_prefix}.zip",
                key=f"down_zip_{chave_prefix}"
            )
    with col2:
        if st.button(f"🔥 Apagar Todos ({titulo})", key=f"del_all_{chave_prefix}"):
            for f in ficheiros:
                try:
                    os.remove(f["caminho"])
                except Exception as e:
                    st.error(f"Erro ao apagar {f['nome']}: {e}")
            st.rerun()

    # Listagem individual
    for f in ficheiros:
        col_a, col_b, col_c = st.columns([4, 1, 1])
        with col_a:
            st.write(f"**{f['nome']}**")
            st.caption(f"{f['tamanho_kb']} KB · {f['modificado'].strftime('%d/%m/%Y %H:%M:%S')} · Ano: {f['ano']}")
        with col_b:
            with open(f["caminho"], "rb") as file:
                st.download_button(
                    "📥 Download",
                    data=file,
                    file_name=f["nome"],
                    key=f"down_{chave_prefix}_{f['nome']}"
                )
        with col_c:
            if st.button("🗑️", key=f"del_{chave_prefix}_{f['nome']}"):
                os.remove(f["caminho"])
                st.rerun()

# ========================= NOVA FUNÇÃO PARA EXIBIR DADOS =========================
def exibir_sec_dados():
    """
    Exibe a secção de ficheiros carregados (dados/<ano>)
    """
    st.markdown("---")
    st.subheader("📂 DADOS CARREGADOS PELO UTILIZADOR")
    
    # Descobrir anos disponíveis dentro de dados/
    anos_dados = []
    if os.path.exists(PASTA_DADOS):
        for item in os.listdir(PASTA_DADOS):
            caminho = os.path.join(PASTA_DADOS, item)
            if os.path.isdir(caminho) and item.isdigit():
                anos_dados.append(item)
    if not anos_dados:
        st.info("Nenhum ano com dados carregados ainda. Use a barra lateral para carregar ficheiros.")
        return
    
    ano_selecionado = st.selectbox("Selecionar ano (dados)", sorted(anos_dados), key="ano_dados")
    ficheiros = listar_ficheiros_dados(ano_selecionado)
    
    if not ficheiros:
        st.info(f"Nenhum ficheiro encontrado em dados/{ano_selecionado}")
        return
    
    # Tabela resumo
    df_dados = pd.DataFrame(ficheiros)
    df_dados = df_dados[["nome", "tamanho_kb", "modificado"]]
    df_dados.columns = ["Nome", "Tamanho (KB)", "Modificado em"]
    st.dataframe(df_dados, use_container_width=True)
    
    # Botões globais para este ano
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"📦 Descarregar todos os dados de {ano_selecionado} (ZIP)", key="zip_dados_all"):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                for f in ficheiros:
                    zipf.write(f["caminho"], arcname=f["nome"])
            zip_buffer.seek(0)
            st.download_button(
                label="Clique para descarregar",
                data=zip_buffer,
                file_name=f"dados_{ano_selecionado}.zip",
                key="down_dados_all"
            )
    with col2:
        if st.button(f"🔥 Apagar todos os ficheiros de {ano_selecionado}", key="del_dados_all"):
            for f in ficheiros:
                try:
                    os.remove(f["caminho"])
                except Exception as e:
                    st.error(f"Erro ao apagar {f['nome']}: {e}")
            st.rerun()
    
    # Listagem individual com pré-visualização
    st.write("### Ficheiros individuais")
    for f in ficheiros:
        col_a, col_b, col_c, col_d = st.columns([3, 1, 1, 1])
        with col_a:
            st.write(f"**{f['nome']}**")
            st.caption(f"{f['tamanho_kb']} KB · {f['modificado'].strftime('%d/%m/%Y %H:%M')}")
        with col_b:
            with open(f["caminho"], "rb") as file:
                st.download_button("📥", data=file, file_name=f["nome"], key=f"down_dados_{f['nome']}")
        with col_c:
            # Pré-visualizar se for Excel/CSV
            if f["extensao"] in [".xlsx", ".xls", ".csv"]:
                if st.button("👁️ Pré‑ver", key=f"view_dados_{f['nome']}"):
                    try:
                        if f["extensao"] == ".csv":
                            df_preview = pd.read_csv(f["caminho"])
                        else:
                            df_preview = pd.read_excel(f["caminho"])
                        st.dataframe(df_preview.head(100))
                        st.caption(f"Mostrando primeiras 100 linhas de {f['nome']}")
                    except Exception as e:
                        st.error(f"Erro ao ler o ficheiro: {e}")
        with col_d:
            if st.button("🗑️", key=f"del_dados_{f['nome']}"):
                os.remove(f["caminho"])
                st.rerun()

# ========================= INTERFACE PRINCIPAL =========================
st.set_page_config(layout="wide", page_title="Gestão de Balanços e Relatórios")
st.title("📁 Sistema de Gestão de Ficheiros")

# Verificação de login
if not st.session_state.get("autenticado", False):
    st.warning("Faça login para aceder a esta área.")
    st.stop()

# ======================== BARRA LATERAL (Configurações) ========================
# ============================================
# MENU DE NAVEGAÇÃO
# ============================================
st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 Navegação")

# Botões de navegação na sidebar
if st.sidebar.button("📚 Cursos", use_container_width=True, key="nav_cursos"):
    st.session_state.pagina = "📚 Cursos"
    st.rerun()

if st.sidebar.button("📋 Questionários", use_container_width=True, key="nav_quest"):
    st.session_state.pagina = "📋 Questionários"
    st.rerun()

if st.sidebar.button("🎯 Gestão de Qualidade", use_container_width=True, key="nav_qualidade"):
    st.session_state.pagina = "🎯 Gestão de Qualidade"
    st.rerun()

if st.sidebar.button("⚔️ Comparador Versus", use_container_width=True, key="nav_comparador"):
    st.session_state.pagina = "⚔️ Comparador Versus"
    st.rerun()

with st.sidebar:
    st.header("⚙️ Configurações")
    ano_exec = st.number_input("Ano", min_value=2000, max_value=2030, step=1, value=2025)
    operacao = st.selectbox(
        "Operação",
        ["Gerar balanços e relatórios (completo)", "Apenas balanços", "Apenas relatórios"]
    )
    
    st.divider()
    st.subheader("📥 Carregar múltiplos ficheiros")
    
    # Permite selecionar vários ficheiros de uma vez
    ficheiros_carregados = st.file_uploader(
        "Selecione um ou mais ficheiros (Excel/CSV)",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True
    )
    
    if st.button("🚀 EXECUTAR", type="primary"):
        if not ficheiros_carregados:
            st.error("Por favor, carregue pelo menos um ficheiro antes de executar.")
        else:
            with st.spinner("A processar ficheiros..."):
                # Garantir que a pasta de dados do ano existe
                dados_ano_dir = os.path.join(PASTA_DADOS, str(ano_exec))
                os.makedirs(dados_ano_dir, exist_ok=True)
                
                # Guardar cada ficheiro carregado
                for ficheiro in ficheiros_carregados:
                    caminho_destino = os.path.join(dados_ano_dir, ficheiro.name)
                    with open(caminho_destino, "wb") as f:
                        f.write(ficheiro.getbuffer())
                    st.success(f"✓ {ficheiro.name} guardado em {caminho_destino}")
                
                # Agora executar as funções principais
                try:
                    if operacao in ["Gerar balanços e relatórios (completo)", "Apenas relatórios"]:
                        preparar_dados_moodle(ano_exec)
                        st.success(f"Relatórios Excel preparados para {ano_exec}!")
                    if operacao in ["Gerar balanços e relatórios (completo)", "Apenas balanços"]:
                        gerar_balancos(ano_exec)
                        st.success(f"Balanços gerados para {ano_exec}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro durante a execução: {e}")

# ======================== ÁREA DE FILTROS (Balanços e Relatórios) ========================
st.markdown("---")
st.subheader("🔍 Filtros rápidos")
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    tipo_filtro = st.multiselect(
        "Tipo de ficheiro",
        ["Excel", "Word", "Balanços", "Relatórios", "Moodle"]
    )
with col_f2:
    # Obter anos disponíveis a partir das pastas de balanços e relatórios
    anos_disponiveis = {"Todos"}
    for pasta in [PASTA_BALANCO, PASTA_RELATORIOS]:
        if os.path.exists(pasta):
            for root, dirs, _ in os.walk(pasta):
                for d in dirs:
                    if d.isdigit() and len(d) == 4:
                        anos_disponiveis.add(d)
                for f in glob(os.path.join(root, "*.*")):
                    ano = extrair_ano_do_caminho(f, pasta)
                    if ano != "Desconhecido":
                        anos_disponiveis.add(ano)
    ano_filtro = st.selectbox("Filtrar por Ano", sorted(anos_disponiveis))
with col_f3:
    pesquisa = st.text_input("Pesquisar por nome", placeholder="digite parte do nome...")

# ======================== CARREGAR FICHEIROS (Balanços e Relatórios) ========================
balancos_raw = listar_ficheiros(PASTA_BALANCO, extensoes=["*.docx"])
relatorios_raw = listar_ficheiros(PASTA_RELATORIOS, extensoes=["*.xlsx", "*.xls"])

balancos_filtrados = aplicar_filtros(balancos_raw, tipo_filtro, ano_filtro, pesquisa)
relatorios_filtrados = aplicar_filtros(relatorios_raw, tipo_filtro, ano_filtro, pesquisa)

# ======================== EXIBIR SECÇÕES ========================
st.markdown("---")
exibir_sec_ficheiros("📄 BALANÇOS", balancos_filtrados, "balancos")
st.markdown("---")
exibir_sec_ficheiros("📊 RELATÓRIOS EXCEL", relatorios_filtrados, "relatorios")

# ======================== NOVA SECÇÃO: DADOS CARREGADOS ========================
exibir_sec_dados()