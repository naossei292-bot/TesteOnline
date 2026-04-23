import streamlit as st
import pandas as pd
import numpy as np
import io
import re

def converter_colunas_numericas(df: pd.DataFrame) -> pd.DataFrame:
    """Converte colunas relevantes para numérico (float)."""
    colunas_numericas = [
        "Inscritos", "Aptos", "Inaptos", "Desistentes", "Devedores",
        "Taxa de Satisfação M01", "Taxa de Satisfação M02", "Taxa de Satisfação M03",
        "Taxa de Satisfação M04", "Taxa de Satisfação M05", "Taxa de Satisfação M06",
        "Taxa de Satisfação M07", "Taxa de Satisfação M08", "Taxa de Satisfação M09",
        "Taxa de Satisfação M10", "Taxa de Satisfação M11", "Taxa de Satisfação M12",
        "Taxa de satisfação Final", "Valor total a receber", "Valor Total Recebido",
        "Avaliação formador"
    ]
    for col in colunas_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def normalizar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica normalizações: conversão numérica."""
    df = converter_colunas_numericas(df)
    return df

def obter_max_mes_satisfacao(df: pd.DataFrame) -> int:
    if df.empty:
        return 2
    padrao = re.compile(r"Taxa de Satisfação M(\d{2})")
    max_mes = 2
    for col in df.columns:
        match = padrao.match(col)
        if match:
            mes = int(match.group(1))
            if df[col].notna().any():
                if mes > max_mes:
                    max_mes = mes
    return max_mes

def atualizar_colunas_satisfacao():
    if 'acoes_editaveis' not in st.session_state or st.session_state.acoes_editaveis.empty:
        max_mes = 2
    else:
        df_temp = st.session_state.acoes_editaveis.drop(columns=["Apagar"], errors="ignore")
        max_mes = obter_max_mes_satisfacao(df_temp)

    colunas_satisfacao = [f"Taxa de Satisfação M{i:02d}" for i in range(1, max_mes + 1)]

    atuais = st.session_state.get("colunas_selecionadas", [])
    outras_colunas = [col for col in atuais if not col.startswith("Taxa de Satisfação M")]
    novas_selecionadas = outras_colunas + [col for col in colunas_satisfacao if col not in outras_colunas]
    todas_opcoes = [
        "Status", "Ação", "Data Inicial", "Data Final", "Centro",
        "Inscritos", "Aptos", "Inaptos", "Desistentes", "Devedores",
        "Taxa de Satisfação M01", "Taxa de Satisfação M02", "Taxa de Satisfação M03",
        "Taxa de Satisfação M04", "Taxa de Satisfação M05", "Taxa de Satisfação M06",
        "Taxa de Satisfação M07", "Taxa de Satisfação M08", "Taxa de Satisfação M09",
        "Taxa de Satisfação M10", "Taxa de Satisfação M11", "Taxa de Satisfação M12",
        "Taxa de satisfação Final", "Nacionalidades(Portugueses/Estrangeiros)",
        "Valor total a receber", "Valor Total Recebido", "Formador", "Avaliação formador"
    ]
    novas_selecionadas = [col for col in todas_opcoes if col in novas_selecionadas]

    if set(novas_selecionadas) != set(st.session_state.colunas_selecionadas):
        st.session_state.colunas_selecionadas = novas_selecionadas
        return True
    return False

# NOVO: garante TODAS as colunas no dataframe (M03-M12 incluídas), preenchendo
# com None as que não existirem. Resolve o problema das colunas a saltar.
def garantir_todas_colunas(df: pd.DataFrame, todas_colunas: list) -> pd.DataFrame:
    for col in todas_colunas:
        if col not in df.columns:
            df[col] = None
    if "Apagar" not in df.columns:
        df.insert(0, "Apagar", False)
    cols_ordenadas = ["Apagar"] + [c for c in todas_colunas if c in df.columns]
    return df[cols_ordenadas]

# NOVO: comparação robusta que trata None e NaN como equivalentes.
# O .equals() original falhava porque garantir_todas_colunas preenche com None,
# mas o data_editor devolve NaN — logo a comparação era sempre diferente → loop infinito.
def dfs_diferentes(df1: pd.DataFrame, df2: pd.DataFrame) -> bool:
    if df1.shape != df2.shape:
        return True
    try:
        return not df1.fillna("__NA__").astype(str).equals(
            df2.fillna("__NA__").astype(str)
        )
    except Exception:
        return True

def mostrar_cursos():
    st.header("📚 Análise de Formações")

    # Inicializa contadores de chave dinâmica (para uploader e editor)
    if "uploader_key_cursos" not in st.session_state:
        st.session_state.uploader_key_cursos = 0
    if "editor_key_counter" not in st.session_state:
        st.session_state.editor_key_counter = 0

    if "refresh_trigger" in st.query_params:
        del st.query_params["refresh_trigger"]

    todas_colunas_dados = [
        "Status", "Ação", "Data Inicial", "Data Final", "Centro",
        "Inscritos", "Aptos", "Inaptos", "Desistentes", "Devedores",
        "Taxa de Satisfação M01", "Taxa de Satisfação M02", "Taxa de Satisfação M03",
        "Taxa de Satisfação M04", "Taxa de Satisfação M05", "Taxa de Satisfação M06",
        "Taxa de Satisfação M07", "Taxa de Satisfação M08", "Taxa de Satisfação M09",
        "Taxa de Satisfação M10", "Taxa de Satisfação M11", "Taxa de Satisfação M12",
        "Taxa de satisfação Final", "Nacionalidades(Portugueses/Estrangeiros)",
        "Valor total a receber", "Valor Total Recebido", "Formador", "Avaliação formador"
    ]

    if "colunas_selecionadas" not in st.session_state:
        st.session_state.colunas_selecionadas = [
            col for col in todas_colunas_dados
            if (not col.startswith("Taxa de Satisfação M") or col in ["Taxa de Satisfação M01", "Taxa de Satisfação M02"])
            and col != "Nacionalidades(Portugueses/Estrangeiros)"
        ]

    st.subheader("📋 Escolha as colunas que pretende visualizar/editar")
    colunas_escolhidas = st.multiselect(
        "Selecione as colunas (a coluna 'Apagar!' é sempre mostrada):",
        options=todas_colunas_dados,
        default=st.session_state.colunas_selecionadas,
        key="seletor_colunas"
    )

    if set(colunas_escolhidas) != set(st.session_state.colunas_selecionadas):
        st.session_state.colunas_selecionadas = colunas_escolhidas
        if 'acoes_editaveis' in st.session_state and not st.session_state.acoes_editaveis.empty:
            df_atual = st.session_state.acoes_editaveis
            if "Apagar" in df_atual.columns:
                apagar = df_atual["Apagar"]
                outras = {col: df_atual[col] for col in st.session_state.colunas_selecionadas if col in df_atual.columns}
                novo_df = pd.DataFrame(outras)
                novo_df.insert(0, "Apagar", apagar)
                st.session_state.acoes_editaveis = normalizar_dataframe(novo_df)
            else:
                st.session_state.acoes_editaveis = pd.DataFrame(columns=["Apagar"] + st.session_state.colunas_selecionadas)
        st.rerun()

    colunas_dados = st.session_state.colunas_selecionadas
    colunas_com_apagar = ["Apagar"] + colunas_dados

    if 'acoes_editaveis' not in st.session_state:
        st.session_state.acoes_editaveis = pd.DataFrame(columns=colunas_com_apagar)
    else:
        st.session_state.acoes_editaveis = normalizar_dataframe(st.session_state.acoes_editaveis)

    # ---------- Carregar ficheiro (com chave dinâmica) ----------
    st.subheader("📤 Carregar dados a partir de ficheiro")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        modo_carga = st.radio(
            "Modo de carregamento:",
            ["Substituir dados existentes", "Adicionar ao final"],
            horizontal=True,
            key="modo_carga_acoes"
        )
    with col2:
        # CHAVE DINÂMICA – igual à lógica dos questionários
        ficheiros_carga = st.file_uploader(
            "Carregar um ou mais ficheiros (Excel ou CSV)",
            type=None,
            accept_multiple_files=True,
            key=f"carga_acoes_upload_{st.session_state.uploader_key_cursos}",
        )
    with col3:
        try:
            with open("assets/Modelo_Acoes_Preenchido.xlsx", "rb") as f:
                conteudo_exemplo = f.read()
            st.download_button(
                label="📥 Descarregar ficheiro exemplo preenchido (Excel)",
                data=conteudo_exemplo,
                file_name="Modelo_Acoes_Preenchido.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except FileNotFoundError:
            st.error("⚠️ Ficheiro de exemplo preenchido não encontrado. Verifique o caminho 'assets/Modelo_Acoes_Preenchido.xlsx'.")

    with col4:
        try:
            with open("assets/Modelo_Acoes.xlsx", "rb") as f:
                conteudo_exemplo = f.read()
            st.download_button(
                label="📥 Descarregar ficheiro exemplo vazio (Excel)",
                data=conteudo_exemplo,
                file_name="Modelo_Acoes.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except FileNotFoundError:
            st.error("⚠️ Ficheiro de exemplo vazio não encontrado. Verifique o caminho 'assets/Modelo_Acoes.xlsx'.")

    if ficheiros_carga:
        lista_dfs = []
        for ficheiro in ficheiros_carga:
            nome = ficheiro.name.lower()
            try:
                if nome.endswith('.csv'):
                    df_parcial = pd.read_csv(ficheiro)
                    df_parcial.columns = df_parcial.columns.str.strip()
                elif nome.endswith('.xlsx'):
                    df_parcial = pd.read_excel(ficheiro, header=1)
                    df_parcial.columns = df_parcial.columns.str.strip()

                    if 'Portugueses' in df_parcial.columns and 'Estrangeiros' in df_parcial.columns:
                        df_parcial['Nacionalidades(Portugueses/Estrangeiros)'] = (
                            df_parcial['Portugueses'].fillna('').astype(str).str.strip()
                            + '/'
                            + df_parcial['Estrangeiros'].fillna('').astype(str).str.strip()
                        )
                        df_parcial.drop(columns=['Portugueses', 'Estrangeiros'], inplace=True)

                    for col in ['Ação', 'Status', 'Centro', 'Formador']:
                        if col in df_parcial.columns:
                            df_parcial[col] = df_parcial[col].astype(str).str.strip()
                            df_parcial[col] = df_parcial[col].replace('nan', None)
                else:
                    st.warning(f"Ficheiro ignorado (formato não suportado): {ficheiro.name}")
                    continue

                # Mapeamento de colunas (mantido igual)
                mapeamento = {
                    'status': 'Status', 'acao': 'Ação',
                    'dataini': 'Data Inicial', 'datafim': 'Data Final',
                    'centro': 'Centro',
                    'inscritos': 'Inscritos', 'aptos': 'Aptos',
                    'inaptos': 'Inaptos', 'desistentes': 'Desistentes',
                    'devedores': 'Devedores',
                    'taxa_satisfacao_m01': 'Taxa de Satisfação M01',
                    'taxa_satisfacao_m02': 'Taxa de Satisfação M02',
                    'taxa_satisfacao_m03': 'Taxa de Satisfação M03',
                    'taxa_satisfacao_m04': 'Taxa de Satisfação M04',
                    'taxa_satisfacao_m05': 'Taxa de Satisfação M05',
                    'taxa_satisfacao_m06': 'Taxa de Satisfação M06',
                    'taxa_satisfacao_m07': 'Taxa de Satisfação M07',
                    'taxa_satisfacao_m08': 'Taxa de Satisfação M08',
                    'taxa_satisfacao_m09': 'Taxa de Satisfação M09',
                    'taxa_satisfacao_m10': 'Taxa de Satisfação M10',
                    'taxa_satisfacao_m11': 'Taxa de Satisfação M11',
                    'taxa_satisfacao_m12': 'Taxa de Satisfação M12',
                    'taxa_final': 'Taxa de satisfação Final',
                    'nacionalidades': 'Nacionalidades(Portugueses/Estrangeiros)',
                    'valor_total_receber': 'Valor total a receber',
                    'valor_total_recebido': 'Valor Total Recebido',
                    'formador': 'Formador',
                    'avaliacao_formador': 'Avaliação formador'
                }
                df_parcial.rename(columns={k: v for k, v in mapeamento.items() if k in df_parcial.columns}, inplace=True)

                for col in todas_colunas_dados:
                    if col not in df_parcial.columns:
                        df_parcial[col] = None
                df_parcial = df_parcial[todas_colunas_dados]
                df_parcial.insert(0, "Apagar", False)
                df_parcial = normalizar_dataframe(df_parcial)
                lista_dfs.append(df_parcial)
            except Exception as e:
                st.error(f"Erro ao ler {ficheiro.name}: {e}")

        if lista_dfs:
            df_novo = pd.concat(lista_dfs, ignore_index=True)
            if modo_carga == "Substituir dados existentes":
                st.session_state.acoes_editaveis = df_novo
            else:
                st.session_state.acoes_editaveis = pd.concat(
                    [st.session_state.acoes_editaveis, df_novo], ignore_index=True
                )
            # Incrementa as chaves dinâmicas para limpar o uploader e forçar rerender do editor
            st.session_state.uploader_key_cursos += 1
            st.session_state.editor_key_counter += 1
            st.success(f"✅ {len(lista_dfs)} ficheiro(s) carregado(s) – total de {len(df_novo)} linhas")
            st.rerun()

        st.markdown("---")

    st.subheader("➕ Adicionar múltiplas linhas")
    col_add1, col_add2 = st.columns([1, 2])
    with col_add1:
        num_linhas = st.number_input("Número de linhas a adicionar:", min_value=1, max_value=10000, value=5, step=1)
    with col_add2:
        if st.button("Adicionar linhas vazias"):
            novas_linhas = pd.DataFrame({col: [None] * num_linhas for col in todas_colunas_dados})
            novas_linhas.insert(0, "Apagar", False)
            st.session_state.acoes_editaveis = pd.concat([st.session_state.acoes_editaveis, novas_linhas], ignore_index=True)
            st.session_state.editor_key_counter += 1
            st.rerun()

    placeholder = st.empty()
    df_atual = garantir_todas_colunas(
        st.session_state.acoes_editaveis.copy(),
        todas_colunas_dados
    )
    df_atual = normalizar_dataframe(df_atual)

    with placeholder.container():
        edited_df = st.data_editor(
            df_atual,
            use_container_width=True,
            num_rows="dynamic",
            height=400,
            key=f"acoes_editor_{st.session_state.editor_key_counter}",
            column_config={
                "Apagar": st.column_config.CheckboxColumn("Apagar", default=False)
            }
        )

    if dfs_diferentes(edited_df, df_atual):
        df_completo = st.session_state.acoes_editaveis.copy()
        for col in edited_df.columns:
            if col != "Apagar":
                df_completo[col] = edited_df[col].values
        if "Apagar" in edited_df.columns:
            df_completo["Apagar"] = edited_df["Apagar"].values
        df_normalizado = normalizar_dataframe(df_completo)
        st.session_state.acoes_editaveis = df_normalizado
        st.session_state.editor_key_counter += 1
        st.rerun()

    st.markdown("---")
    col_bot1, col_bot2 = st.columns(2)

    with col_bot1:
        if st.button("🗑️ Limpar todos os dados", use_container_width=True):
            st.session_state.acoes_editaveis = pd.DataFrame(columns=colunas_com_apagar)
            st.session_state.colunas_selecionadas = [
                col for col in todas_colunas_dados
                if not col.startswith("Taxa de Satisfação M") or col in ["Taxa de Satisfação M01", "Taxa de Satisfação M02"]
            ]
            st.session_state.editor_key_counter += 1
            st.rerun()

    with col_bot2:
        if st.button("✖️ Apagar selecionados", use_container_width=True):
            df = st.session_state.acoes_editaveis.copy()
            if "Apagar" in df.columns:
                linhas_apagar = df[df["Apagar"] == True].index.tolist()
                if linhas_apagar:
                    df.drop(index=linhas_apagar, inplace=True)
                    df.reset_index(drop=True, inplace=True)
                    df["Apagar"] = False
                    st.session_state.acoes_editaveis = normalizar_dataframe(df)
                    st.session_state.editor_key_counter += 1
                    st.rerun()
                else:
                    st.warning("Nenhuma linha marcada para apagar.")
            else:
                st.warning("Coluna 'Apagar' não encontrada.")

    st.markdown("---")
    st.subheader("📎 Exportar dados")

    df_export = st.session_state.acoes_editaveis.drop(columns=["Apagar"], errors="ignore")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name="Cursos")
    output.seek(0)

    st.download_button(
        label="📥 Descarregar dados em Excel",
        data=output,
        file_name="cursos_exportados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key="download_cursos_excel"
    )

    df_metricas = st.session_state.acoes_editaveis.drop(columns=["Apagar"], errors="ignore").copy()
    df_metricas = converter_colunas_numericas(df_metricas)

    if "Ação" in df_metricas.columns:
        df_metricas["Ação"] = df_metricas["Ação"].replace({"": None, "None": None, "nan": None, "NaN": None})
        df_metricas = df_metricas.dropna(subset=["Ação"])
        df_metricas = df_metricas[df_metricas["Ação"].astype(str).str.strip() != ""]

    if not df_metricas.empty:
        st.markdown("---")
        st.subheader("📊 Resumo Geral")

        total_acoes = df_metricas["Ação"].nunique() if "Ação" in df_metricas.columns else 0
        total_inscricoes = (
            df_metricas["Inscritos"].sum()
            if "Inscritos" in df_metricas.columns and pd.api.types.is_numeric_dtype(df_metricas["Inscritos"])
            else 0
        )
        total_aptos = (
            df_metricas["Aptos"].sum()
            if "Aptos" in df_metricas.columns and pd.api.types.is_numeric_dtype(df_metricas["Aptos"])
            else 0
        )
        taxa_aprovacao = (total_aptos / total_inscricoes * 100) if total_inscricoes > 0 else 0
        media_satisfacao = (
            df_metricas["Taxa de satisfação Final"].mean()
            if "Taxa de satisfação Final" in df_metricas.columns and pd.api.types.is_numeric_dtype(df_metricas["Taxa de satisfação Final"])
            else 0
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de Ações", total_acoes)
        col2.metric("Total de Inscrições", f"{total_inscricoes:,.0f}".replace(",", "."))
        col3.metric("Taxa de Aprovação (Aptos)", f"{taxa_aprovacao:.1f}%")
        col4.metric("Satisfação Final Média", f"{media_satisfacao:.1f}%")
    else:
        st.info("ℹ️ Tabela sem dados válidos. Adicione ou carregue dados.")

if __name__ == "__main__":
    mostrar_cursos()