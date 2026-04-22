import streamlit as st
import sys
import os
import zipfile
import io
import traceback
import pandas as pd
from glob import glob
from pathlib import Path
from datetime import datetime

# ========================= CONFIGURAÇÃO DE CAMINHOS =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BALANCOS_DIR = os.path.join(BASE_DIR, 'balancos')
sys.path.insert(0, BALANCOS_DIR)

from balancos.main import gerar_balancos, preparar_dados_moodle

# Pastas de saída
PASTA_BALANCO = os.path.join(BALANCOS_DIR, "balanco")
PASTA_RELATORIOS = os.path.join(BALANCOS_DIR, "relatorios")
PASTA_DADOS = os.path.join(BALANCOS_DIR, "dados")

# Criar pastas se não existirem
os.makedirs(PASTA_BALANCO, exist_ok=True)
os.makedirs(PASTA_RELATORIOS, exist_ok=True)
os.makedirs(PASTA_DADOS, exist_ok=True)

# ========================= FUNÇÕES AUXILIARES =========================
def extrair_ano_do_caminho(caminho, pasta_base):
    """
    Extrai o ano a partir da subpasta relativa à pasta_base.
    """
    rel_path = os.path.relpath(caminho, pasta_base)
    partes = Path(rel_path).parts
    if len(partes) > 0 and partes[0].isdigit():
        return partes[0]
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
    Aplica os filtros da interface. (ano_filtro é agora sempre um ano específico)
    """
    resultados = []
    for f in ficheiros:
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
        # Agora ano_filtro nunca é "Todos", comparamos diretamente
        if f["ano"] != ano_filtro:
            continue
        if pesquisa and pesquisa.lower() not in f["nome"].lower():
            continue
        resultados.append(f)
    return resultados

# ======================== CSS PERSONALIZADO ========================
st.markdown("""
<style>
    .file-card {
        background-color: #f9f9fb;
        border-radius: 16px;
        padding: 1rem;
        margin-bottom: 1rem;
        border: 1px solid #e9ecef;
        transition: all 0.2s ease;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .file-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border-color: #cbd5e1;
    }
    .file-name {
        font-weight: 600;
        font-size: 1rem;
        color: #1e293b;
        word-break: break-word;
    }
    .file-meta {
        font-size: 0.8rem;
        color: #64748b;
        margin-top: 0.25rem;
    }
    .stButton button {
        border-radius: 20px;
        transition: 0.2s;
    }
    hr {
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ======================== FUNÇÕES DE EXIBIÇÃO ========================
def exibir_sec_ficheiros(titulo, ficheiros, chave_prefix, mostrar_titulo=True):
    """
    Exibe uma secção com listagem de ficheiros em formato de cards.
    """
    if mostrar_titulo:
        st.markdown(f"## {titulo}")
    
    if not ficheiros:
        st.info("Nenhum ficheiro encontrado.", icon="ℹ️")
        return

    total_size_kb = sum(f["tamanho_kb"] for f in ficheiros)
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric("📄 Total de ficheiros", len(ficheiros))
    with col_m2:
        st.metric("💾 Tamanho total", f"{total_size_kb:.2f} KB")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button(f"📦 Descarregar tudo (ZIP)", key=f"zip_{chave_prefix}", width='stretch'):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                for f in ficheiros:
                    zipf.write(f["caminho"], arcname=f["nome"])
            zip_buffer.seek(0)
            st.download_button(
                label="✅ Clique para descarregar",
                data=zip_buffer,
                file_name=f"{chave_prefix}.zip",
                key=f"down_zip_{chave_prefix}"
            )
    with col_btn2:
        if st.button(f"🔥 Apagar todos", key=f"del_all_{chave_prefix}", width='stretch'):
            for f in ficheiros:
                try:
                    os.remove(f["caminho"])
                except Exception as e:
                    st.error(f"Erro ao apagar {f['nome']}: {e}")
            st.rerun()

    st.markdown("---")

    for f in ficheiros:
        with st.container():
            st.markdown(f'<div class="file-card">', unsafe_allow_html=True)
            col_a, col_b, col_c = st.columns([4, 1, 1])
            with col_a:
                if f["extensao"] == ".docx":
                    icon = "📘"
                elif f["extensao"] in [".xlsx", ".xls"]:
                    icon = "📊"
                else:
                    icon = "📄"
                st.markdown(f'<div class="file-name">{icon} {f["nome"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="file-meta">{f["tamanho_kb"]} KB · Modificado: {f["modificado"].strftime("%d/%m/%Y %H:%M")} · Ano: {f["ano"]}</div>', unsafe_allow_html=True)
            with col_b:
                with open(f["caminho"], "rb") as file:
                    st.download_button(
                        "📥 Download",
                        data=file,
                        file_name=f["nome"],
                        key=f"down_{chave_prefix}_{f['nome']}",
                        width='stretch'
                    )
            with col_c:
                if st.button("🗑️ Apagar", key=f"del_{chave_prefix}_{f['nome']}", width='stretch'):
                    os.remove(f["caminho"])
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

def _exibir_card_dados(f):
    """Auxiliar para exibir um card de ficheiro de dados."""
    with st.container():
        st.markdown(f'<div class="file-card">', unsafe_allow_html=True)
        col_a, col_b, col_c, col_d = st.columns([3, 1, 1, 1])
        with col_a:
            icon = "📊" if f["extensao"] in [".xlsx", ".xls", ".csv"] else "📄"
            st.markdown(f'<div class="file-name">{icon} {f["nome"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="file-meta">{f["tamanho_kb"]} KB · {f["modificado"].strftime("%d/%m/%Y %H:%M")}</div>', unsafe_allow_html=True)
        with col_b:
            with open(f["caminho"], "rb") as file:
                st.download_button("📥", data=file, file_name=f["nome"], key=f"down_dados_{f['nome']}", width='stretch')
        with col_c:
            if f["extensao"] in [".xlsx", ".xls", ".csv"]:
                if st.button("👁️ Pré‑ver", key=f"view_dados_{f['nome']}", width='stretch'):
                    try:
                        if f["extensao"] == ".csv":
                            df_preview = pd.read_csv(f["caminho"])
                        else:
                            df_preview = pd.read_excel(f["caminho"])
                        st.dataframe(df_preview.head(100))
                        st.caption(f"Mostrando primeiras 100 linhas de {f['nome']}")
                    except Exception as e:
                        st.error(f"Erro ao ler: {e}")
        with col_d:
            if st.button("🗑️", key=f"del_dados_{f['nome']}", width='stretch'):
                os.remove(f["caminho"])
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

def exibir_sec_dados(ano, mostrar_titulo=True):
    """
    Exibe a secção de ficheiros carregados para um ano específico.
    """
    if mostrar_titulo:
        st.markdown("## 📂 DADOS CARREGADOS PELO UTILIZADOR")
    
    ficheiros = listar_ficheiros_dados(ano)
    
    if not ficheiros:
        st.info(f"Nenhum ficheiro encontrado em dados/{ano}")
        return
    
    total_size = sum(f["tamanho_kb"] for f in ficheiros)
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric("📄 Ficheiros", len(ficheiros))
    with col_m2:
        st.metric("💾 Tamanho total", f"{total_size:.2f} KB")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button(f"📦 Descarregar todos os dados de {ano} (ZIP)", key="zip_dados_all", width='stretch'):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                for f in ficheiros:
                    zipf.write(f["caminho"], arcname=f["nome"])
            zip_buffer.seek(0)
            st.download_button(
                label="✅ Clique para descarregar",
                data=zip_buffer,
                file_name=f"dados_{ano}.zip",
                key="down_dados_all"
            )
    with col_btn2:
        if st.button(f"🔥 Apagar todos os ficheiros de {ano}", key="del_dados_all", width='stretch'):
            for f in ficheiros:
                try:
                    os.remove(f["caminho"])
                except Exception as e:
                    st.error(f"Erro ao apagar {f['nome']}: {e}")
            st.rerun()
    
    st.markdown("---")
    
    for f in ficheiros:
        _exibir_card_dados(f)

# ========================= FUNÇÃO PRINCIPAL =========================
def mostrar_relatorios():
    """
    Função que desenha a interface de gestão de balanços e relatórios.
    """
    st.title("📁 Sistema de Gestão de Ficheiros")

    # ======================== BARRA LATERAL (Configurações) ========================
    with st.sidebar:
        st.header("⚙️ Configurações")
        ano_exec = st.number_input("Ano", min_value=2000, max_value=2030, step=1, value=2025)
        operacao = st.selectbox(
            "Operação",
            ["Gerar balanços e relatórios (completo)", "Apenas balanços", "Apenas relatórios"]
        )
        st.divider()

        # ========== NOVO BOTÃO PARA DESCARREGAR A PASTA "Modelos" ==========
        st.subheader("📁 Descarregar modelos")
        caminho_modelos = os.path.join(BALANCOS_DIR, "Modelos")
        if os.path.exists(caminho_modelos) and os.path.isdir(caminho_modelos):
            # Botão que aciona a criação do ZIP
            if st.button("⬇️ Descarregar * pasta 'Modelos' (ZIP)", key="download_modelos_btn"):
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(caminho_modelos):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # Guarda na ZIP com o caminho relativo a "Modelos"
                            arcname = os.path.relpath(file_path, start=BALANCOS_DIR)
                            zipf.write(file_path, arcname=arcname)
                zip_buffer.seek(0)
                st.download_button(
                    label="✅ Clique para descarregar",
                    data=zip_buffer,
                    file_name="Modelos.zip",
                    key="download_modelos_zip"
                )
        else:
            st.info("Pasta 'Modelos' não encontrada dentro de 'balancos'.", icon="⚠️")
        st.divider()

        st.subheader("📥 Carregar múltiplos ficheiros")
        
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
                    dados_ano_dir = os.path.join(PASTA_DADOS, str(ano_exec))
                    os.makedirs(dados_ano_dir, exist_ok=True)
                    
                    for ficheiro in ficheiros_carregados:
                        caminho_destino = os.path.join(dados_ano_dir, ficheiro.name)
                        with open(caminho_destino, "wb") as f:
                            f.write(ficheiro.getbuffer())
                        st.success(f"✓ {ficheiro.name} guardado em {caminho_destino}")
                    
                    try:
                        if operacao in ["Gerar balanços e relatórios (completo)", "Apenas relatórios"]:
                            preparar_dados_moodle(ano_exec)
                            st.success(f"Relatórios Excel preparados para {ano_exec}!")
                        if operacao in ["Gerar balanços e relatórios (completo)", "Apenas balanços"]:
                            gerar_balancos(ano_exec)
                            st.success(f"Balanços gerados para {ano_exec}!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro durante a execução:\n\n{traceback.format_exc()}")

    # ======================== ÁREA DE FILTROS (Balanços, Relatórios e Dados) ========================
    st.markdown("---")
    st.subheader("🔍 Filtros rápidos")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        tipo_filtro = st.multiselect(
            "Tipo de ficheiro",
            ["Excel", "Word", "Balanços", "Relatórios", "Moodle"]
        )
    with col_f2:
        # Recolher anos disponíveis para balanços, relatórios e dados (sem "Todos")
        anos_disponiveis = set()
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
        # Adicionar anos das pastas de dados
        if os.path.exists(PASTA_DADOS):
            for item in os.listdir(PASTA_DADOS):
                if os.path.isdir(os.path.join(PASTA_DADOS, item)) and item.isdigit():
                    anos_disponiveis.add(item)
        # Ordenar e remover "Todos" (que já não é adicionado)
        anos_ordenados = sorted(anos_disponiveis)
        # Se não houver anos, definir um valor padrão
        if not anos_ordenados:
            anos_ordenados = ["2025"]  # valor dummy para evitar erro
        ano_filtro = st.selectbox("Filtrar por Ano", anos_ordenados)
    with col_f3:
        pesquisa = st.text_input("Pesquisar por nome", placeholder="digite parte do nome...")

    # ======================== CARREGAR FICHEIROS (Balanços e Relatórios) ========================
    balancos_raw = listar_ficheiros(PASTA_BALANCO, extensoes=["*.docx"])
    relatorios_raw = listar_ficheiros(PASTA_RELATORIOS, extensoes=["*.xlsx", "*.xls"])

    balancos_filtrados = aplicar_filtros(balancos_raw, tipo_filtro, ano_filtro, pesquisa)
    relatorios_filtrados = aplicar_filtros(relatorios_raw, tipo_filtro, ano_filtro, pesquisa)

    # ======================== EXIBIR SECÇÕES COM EXPANSORES ========================
    st.markdown("---")

    with st.expander("📄 BALANÇOS", expanded=False):
        exibir_sec_ficheiros("", balancos_filtrados, "balancos", mostrar_titulo=False)

    st.markdown("---")

    with st.expander("📊 RELATÓRIOS EXCEL", expanded=False):
        exibir_sec_ficheiros("", relatorios_filtrados, "relatorios", mostrar_titulo=False)

    st.markdown("---")

    with st.expander("📂 DADOS CARREGADOS PELO UTILIZADOR", expanded=False):
        exibir_sec_dados(ano_filtro, mostrar_titulo=False)