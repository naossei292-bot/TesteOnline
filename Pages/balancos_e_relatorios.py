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

from balancos.geradores import gerar_formacao_centros, gerar_acoes_bl

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
    pasta_ano = os.path.join(PASTA_DADOS, str(ano))
    if not os.path.exists(pasta_ano):
        return []
    return listar_ficheiros(pasta_ano, extensoes=["*.*"])

def aplicar_filtros(ficheiros, tipo_filtro, ano_filtro, pesquisa):
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
        if f["ano"] != ano_filtro:
            continue
        if pesquisa and pesquisa.lower() not in f["nome"].lower():
            continue
        resultados.append(f)
    return resultados

# ======================== FUNÇÕES DE EXIBIÇÃO ========================
def exibir_sec_ficheiros(titulo, ficheiros, chave_prefix, mostrar_titulo=True):
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
        if st.button(f"📦 Descarregar tudo (ZIP)", key=f"zip_{chave_prefix}", use_container_width=True):
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
        if st.button(f"🔥 Apagar todos", key=f"del_all_{chave_prefix}", use_container_width=True):
            for f in ficheiros:
                try:
                    os.remove(f["caminho"])
                except Exception as e:
                    st.error(f"Erro ao apagar {f['nome']}: {e}")
            st.rerun()

    st.markdown("---")

    for f in ficheiros:
        col_a, col_b, col_c = st.columns([4, 1, 1])
        with col_a:
            if f["extensao"] == ".docx":
                icon = "📘"
            elif f["extensao"] in [".xlsx", ".xls"]:
                icon = "📊"
            else:
                icon = "📄"
            st.write(f"**{icon} {f['nome']}**")
            st.caption(f"{f['tamanho_kb']} KB · Modificado: {f['modificado'].strftime('%d/%m/%Y %H:%M')} · Ano: {f['ano']}")
        with col_b:
            with open(f["caminho"], "rb") as file:
                st.download_button(
                    "📥 Download",
                    data=file,
                    file_name=f["nome"],
                    key=f"down_{chave_prefix}_{f['nome']}",
                    use_container_width=True
                )
        with col_c:
            if st.button("🗑️ Apagar", key=f"del_{chave_prefix}_{f['nome']}", use_container_width=True):
                os.remove(f["caminho"])
                st.rerun()

def _exibir_card_dados(f):
    col_a, col_b, col_c, col_d = st.columns([3, 1, 1, 1])
    with col_a:
        icon = "📊" if f["extensao"] in [".xlsx", ".xls", ".csv"] else "📄"
        st.write(f"**{icon} {f['nome']}**")
        st.caption(f"{f['tamanho_kb']} KB · {f['modificado'].strftime('%d/%m/%Y %H:%M')}")
    with col_b:
        with open(f["caminho"], "rb") as file:
            st.download_button("📥", data=file, file_name=f["nome"], key=f"down_dados_{f['nome']}", use_container_width=True)
    with col_c:
        if f["extensao"] in [".xlsx", ".xls", ".csv"]:
            if st.button("👁️ Pré‑ver", key=f"view_dados_{f['nome']}", use_container_width=True):
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
        if st.button("🗑️", key=f"del_dados_{f['nome']}", use_container_width=True):
            os.remove(f["caminho"])
            st.rerun()

def exibir_sec_dados(ano, mostrar_titulo=True):
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
        if st.button(f"📦 Descarregar todos os dados de {ano} (ZIP)", key="zip_dados_all", use_container_width=True):
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
        if st.button(f"🔥 Apagar todos os ficheiros de {ano}", key="del_dados_all", use_container_width=True):
            for f in ficheiros:
                try:
                    os.remove(f["caminho"])
                except Exception as e:
                    st.error(f"Erro ao apagar {f['nome']}: {e}")
            st.rerun()
    
    st.markdown("---")
    
    for f in ficheiros:
        _exibir_card_dados(f)

def mostrar_gerador_documentos():
    """Uploader autónomo: recebe o Execução Física, gera os documentos
    derivados (Centros agora; Ações BL futuramente) e oferece para download.
    NÃO grava em dados/ — o utilizador saca, verifica e só depois carrega
    no uploader principal dos balanços."""
    st.markdown("### 🧩 Gerador de documentos a partir do Execução Física")
    st.caption(
        "Carrega o **Modelo Execução Fisica.xlsx** e gera o Formação Centros "
        "automaticamente. Descarrega, confere, e só depois usa no gerador de balanços."
    )

    exec_file = st.file_uploader(
        "Modelo Execução Fisica.xlsx",
        type=["xlsx", "xls"],
        accept_multiple_files=False,
        key="upload_gerador_exec",
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📊 Gerar Modelo Formação Centros", use_container_width=True,
                     key="btn_gerar_centros", disabled=(exec_file is None)):
            try:
                df_exec = pd.read_excel(exec_file)
                dados, avisos = gerar_formacao_centros(df_exec)

                for aviso in avisos:
                    st.warning(f"⚠️ {aviso}")

                st.success("✅ Modelo Formação Centros gerado!")
                st.download_button(
                    "📥 Descarregar Modelo Formacao Centros.xlsx",
                    data=dados,
                    file_name="Modelo Formacao Centros.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_centros_gerado",
                    use_container_width=True,
                )
            except (FileNotFoundError, ValueError) as e:
                st.warning(f"⚠️ {e}")
            except Exception:
                st.error(f"Erro inesperado:\n\n{traceback.format_exc()}")

    with col2:
        if st.button("🔗 Gerar Modelo Ações BL", use_container_width=True,
                     key="btn_gerar_acoesbl", disabled=(exec_file is None)):
            try:
                df_exec = pd.read_excel(exec_file)
                dados, avisos = gerar_acoes_bl(df_exec)

                for aviso in avisos:
                    st.info(f"ℹ️ {aviso}")

                st.success("✅ Modelo Ações BL gerado!")
                st.download_button(
                    "📥 Descarregar Modelo Ações BL.xlsx",
                    data=dados,
                    file_name="Modelo Ações BL.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_acoesbl_gerado",
                    use_container_width=True,
                )
            except (FileNotFoundError, ValueError) as e:
                st.warning(f"⚠️ {e}")
            except Exception:
                st.error(f"Erro inesperado:\n\n{traceback.format_exc()}")

def mostrar_gerador_documentos():
    """Uploader autónomo: recebe o Execução Física, gera os documentos
    derivados (Centros agora; Ações BL futuramente) e oferece para download.
    NÃO grava em dados/ — o utilizador saca, verifica e só depois carrega
    no uploader principal dos balanços."""
    st.markdown("### 🧩 Gerador de documentos a partir do Execução Física")
    st.caption(
        "Carrega o **Modelo Execução Fisica.xlsx** e gera o Formação Centros "
        "automaticamente. Descarrega, confere, e só depois usa no gerador de balanços."
    )

    exec_file = st.file_uploader(
        "Modelo Execução Fisica.xlsx",
        type=["xlsx", "xls"],
        accept_multiple_files=False,
        key="upload_gerador_exec",
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📊 Gerar Modelo Formação Centros", use_container_width=True,
                     key="btn_gerar_centros", disabled=(exec_file is None)):
            try:
                df_exec = pd.read_excel(exec_file)
                dados, avisos = gerar_formacao_centros(df_exec)

                for aviso in avisos:
                    st.warning(f"⚠️ {aviso}")

                st.success("✅ Modelo Formação Centros gerado!")
                st.download_button(
                    "📥 Descarregar Modelo Formacao Centros.xlsx",
                    data=dados,
                    file_name="Modelo Formacao Centros.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_centros_gerado",
                    use_container_width=True,
                )
            except (FileNotFoundError, ValueError) as e:
                st.warning(f"⚠️ {e}")
            except Exception:
                st.error(f"Erro inesperado:\n\n{traceback.format_exc()}")

    with col2:
        if st.button("🔗 Gerar Modelo Ações BL", use_container_width=True,
                     key="btn_gerar_acoesbl", disabled=(exec_file is None)):
            try:
                df_exec = pd.read_excel(exec_file)
                dados, avisos = gerar_acoes_bl(df_exec)

                for aviso in avisos:
                    st.info(f"ℹ️ {aviso}")

                st.success("✅ Modelo Ações BL gerado!")
                st.download_button(
                    "📥 Descarregar Modelo Ações BL.xlsx",
                    data=dados,
                    file_name="Modelo Ações BL.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_acoesbl_gerado",
                    use_container_width=True,
                )
            except (FileNotFoundError, ValueError) as e:
                st.warning(f"⚠️ {e}")
            except Exception:
                st.error(f"Erro inesperado:\n\n{traceback.format_exc()}")

# ========================= FUNÇÃO PRINCIPAL =========================
def mostrar_relatorios():
    st.title("📁 Sistema de Gestão de Ficheiros")

    with st.expander("🧩 Gerar documentos automaticamente", expanded=False):
        mostrar_gerador_documentos()
        
    # ======================== LAYOUT PRINCIPAL COM COLUNAS ========================
    col_config, col_upload, col_limpar = st.columns(3)
    
    # Coluna de Configurações
    with col_config:
        st.markdown("### ⚙️ Configurações")
        ano_exec = st.number_input("Ano", min_value=2000, max_value=2030, step=1, value=2025, key="ano_exec")
        operacao = st.selectbox(
            "Operação",
            ["Gerar balanços e relatórios (completo)", "Apenas balanços", "Apenas relatórios"],
            key="operacao"
        )
        
        st.markdown("---")
        st.markdown("### 📁 Descarregar modelos")
        caminho_modelos = os.path.join(BALANCOS_DIR, "Modelos")
        if os.path.exists(caminho_modelos) and os.path.isdir(caminho_modelos):
            if st.button("⬇️ Descarregar pasta 'Modelos' (ZIP)", key="download_modelos_btn", use_container_width=True):
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(caminho_modelos):
                        for file in files:
                            file_path = os.path.join(root, file)
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
            st.info("Pasta 'Modelos' não encontrada.", icon="⚠️")
    
    # Coluna de Upload de Ficheiros
    with col_upload:
        st.markdown("### 📥 Carregar múltiplos ficheiros")
        
        ficheiros_carregados = st.file_uploader(
            "Selecione um ou mais ficheiros (Excel/CSV)",
            type=["xlsx", "xls", "csv"],
            accept_multiple_files=True,
            key="upload_files"
        )
        
        if st.button("🚀 EXECUTAR", type="primary", use_container_width=True):
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
                            avisos = gerar_balancos(ano_exec)
                            for aviso in (avisos or []):
                                st.warning(f"⚠️ {aviso}")
                            st.success(f"Balanços gerados para {ano_exec}!")
                        st.rerun()
                    except FileNotFoundError as e:
                        st.warning(f"⚠️ {e}")          # falta de ficheiro → mensagem limpa, não traceback
                    except Exception:
                        st.error(f"Erro inesperado:\n\n{traceback.format_exc()}")

    # Coluna de Limpeza Global
    with col_limpar:
        st.markdown("### 🗑️ Limpeza Global")
        
        if "confirmar_eliminar_global" not in st.session_state:
            st.session_state.confirmar_eliminar_global = False
        
        if not st.session_state.confirmar_eliminar_global:
            if st.button("🗑️ ELIMINAR TUDO", key="btn_eliminar_global", use_container_width=True):
                st.session_state.confirmar_eliminar_global = True
                st.rerun()
        else:
            st.warning("⚠️ Irreversível!")
            col_sim, col_nao = st.columns(2)
            with col_sim:
                if st.button("✅ SIM", key="conf_sim_global", use_container_width=True):
                    eliminados = 0
                    erros = []
                    
                    for f in listar_ficheiros(PASTA_BALANCO, extensoes=["*.docx"]):
                        try:
                            os.remove(f["caminho"])
                            eliminados += 1
                        except Exception as e:
                            erros.append(f"Balanço {f['nome']}: {e}")
                    
                    for f in listar_ficheiros(PASTA_RELATORIOS, extensoes=["*.xlsx", "*.xls"]):
                        try:
                            os.remove(f["caminho"])
                            eliminados += 1
                        except Exception as e:
                            erros.append(f"Relatório {f['nome']}: {e}")
                    
                    if os.path.exists(PASTA_DADOS):
                        for ano_dir in os.listdir(PASTA_DADOS):
                            ano_path = os.path.join(PASTA_DADOS, ano_dir)
                            if os.path.isdir(ano_path):
                                for f in listar_ficheiros(ano_path, extensoes=["*.*"]):
                                    try:
                                        os.remove(f["caminho"])
                                        eliminados += 1
                                    except Exception as e:
                                        erros.append(f"Dados {f['nome']}: {e}")
                                try:
                                    if not os.listdir(ano_path):
                                        os.rmdir(ano_path)
                                except:
                                    pass
                    
                    st.session_state.confirmar_eliminar_global = False
                    
                    if eliminados > 0:
                        st.success(f"✅ {eliminados} ficheiro(s) eliminado(s)!")
                    if erros:
                        st.error("⚠️ Erros:\n" + "\n".join(erros[:5]))
                    st.rerun()
            with col_nao:
                if st.button("❌ NÃO", key="conf_nao_global", use_container_width=True):
                    st.session_state.confirmar_eliminar_global = False
                    st.rerun()

    # --- CARREGAR E FILTRAR FICHEIROS ---
    balancos_raw = listar_ficheiros(PASTA_BALANCO, extensoes=["*.docx"])
    relatorios_raw = listar_ficheiros(PASTA_RELATORIOS, extensoes=["*.xlsx", "*.xls"])

    total_ficheiros_existentes = len(balancos_raw) + len(relatorios_raw)
    
    # --- SÓ MOSTRAR FILTROS SE HOUVER FICHEIROS ---
    if total_ficheiros_existentes > 0:
        st.markdown("---")
        st.subheader("🔍 Filtros rápidos")
        
        col_f1, col_f2, col_f3 = st.columns(3)

        with col_f1:
            tipo_filtro = st.multiselect(
                "Tipo de ficheiro",
                ["Excel", "Word", "Balanços", "Relatórios", "Moodle"],
                key="tipo_filtro"
            )
        with col_f2:
            anos_disponiveis = set()
            for pasta in [PASTA_BALANCO, PASTA_RELATORIOS]:
                if os.path.exists(pasta):
                    for f in glob(os.path.join(pasta, "**", "*.*"), recursive=True):
                        ano = extrair_ano_do_caminho(f, pasta)
                        if ano != "Desconhecido":
                            anos_disponiveis.add(ano)
                    for root, dirs, files in os.walk(pasta):
                        if files:
                            for d in dirs:
                                if d.isdigit() and len(d) == 4:
                                    anos_disponiveis.add(d)
            
            if os.path.exists(PASTA_DADOS):
                for item in os.listdir(PASTA_DADOS):
                    ano_path = os.path.join(PASTA_DADOS, item)
                    if os.path.isdir(ano_path) and item.isdigit() and len(item) == 4:
                        tem_ficheiros = any(
                            os.path.isfile(os.path.join(ano_path, f)) 
                            for f in os.listdir(ano_path)
                        )
                        if tem_ficheiros:
                            anos_disponiveis.add(item)
            
            anos_ordenados = sorted(anos_disponiveis)
            
            if not anos_ordenados:
                st.info("ℹ️ Ainda não há ficheiros gerados.")
                ano_filtro = None
            else:
                ano_filtro = st.selectbox("Filtrar por Ano", anos_ordenados, key="ano_filtro")
        with col_f3:
            pesquisa = st.text_input("Pesquisar por nome", placeholder="digite parte do nome...", key="pesquisa")
        
        balancos_filtrados = aplicar_filtros(balancos_raw, tipo_filtro, ano_filtro, pesquisa)
        relatorios_filtrados = aplicar_filtros(relatorios_raw, tipo_filtro, ano_filtro, pesquisa)
        
        total_ficheiros = len(balancos_filtrados) + len(relatorios_filtrados)
        if total_ficheiros > 0:
            if st.button(f"📦 Descarregar TUDO ({total_ficheiros} ficheiros)", type="primary", use_container_width=True, key="download_tudo"):
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for f in balancos_filtrados:
                        zipf.write(f["caminho"], arcname=os.path.join("Balanços", f["nome"]))
                    for f in relatorios_filtrados:
                        zipf.write(f["caminho"], arcname=os.path.join("Relatórios", f["nome"]))
                zip_buffer.seek(0)
                st.download_button(
                    label="✅ Clique para descarregar ZIP",
                    data=zip_buffer,
                    file_name=f"Balancos_Relatorios_{ano_filtro}.zip",
                    key="down_tudo_zip",
                    use_container_width=True
                )
    else:
        st.markdown("---")
        st.info("📭 **Nenhum balanço ou relatório encontrado.** Carregue ficheiros e execute uma operação para gerar resultados.", icon="ℹ️")
        balancos_filtrados = []
        relatorios_filtrados = []
        ano_filtro = None

    # ======================== EXIBIR SECÇÕES COM EXPANSORES (SÓ SE HOUVER DADOS) ========================
    
    if balancos_filtrados:
        st.markdown("---")
        with st.expander("📄 BALANÇOS", expanded=False):
            exibir_sec_ficheiros("", balancos_filtrados, "balancos", mostrar_titulo=False)

    if relatorios_filtrados:
        st.markdown("---")
        with st.expander("📊 RELATÓRIOS EXCEL", expanded=False):
            exibir_sec_ficheiros("", relatorios_filtrados, "relatorios", mostrar_titulo=False)

    ano_para_dados = ano_filtro if ano_filtro else str(ano_exec)
    dados_raw = listar_ficheiros_dados(ano_para_dados)
    if dados_raw:
        st.markdown("---")
        with st.expander("📂 DADOS CARREGADOS PELO UTILIZADOR", expanded=False):
            exibir_sec_dados(ano_para_dados, mostrar_titulo=False)