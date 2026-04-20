import streamlit as st
import pandas as pd
import numpy as np
import io

def converter_colunas_numericas(df: pd.DataFrame) -> pd.DataFrame:
    """Converte colunas relevantes para numérico (float)."""
    colunas_numericas = ["Inscritos", "Concluídos", "Avaliados", "Aprovados", "Planeado", "Valor da Ação", "Valor Total"]
    for col in colunas_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def calcular_valor_total(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula Valor Total = Valor da Ação * Inscritos, se aplicável."""
    df = df.copy()
    if "Valor da Ação" in df.columns and "Valor Total" in df.columns and "Inscritos" in df.columns:
        df["Valor da Ação"] = pd.to_numeric(df["Valor da Ação"], errors="coerce")
        df["Inscritos"] = pd.to_numeric(df["Inscritos"], errors="coerce")
        df["Valor Total"] = pd.to_numeric(df["Valor Total"], errors="coerce")
        mask = (df["Valor da Ação"].notna()) & (df["Valor Total"].isna())
        if mask.any():
            df.loc[mask, "Valor Total"] = df.loc[mask, "Valor da Ação"] * df.loc[mask, "Inscritos"]
    return df

def normalizar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica todas as normalizações: conversão numérica e cálculo do Valor Total."""
    df = converter_colunas_numericas(df)
    df = calcular_valor_total(df)
    return df

def mostrar_cursos():
    st.header("📚 Análise de Formações")

    # Inicializar contador para forçar recriação do data_editor
    if "editor_key_counter" not in st.session_state:
        st.session_state.editor_key_counter = 0

    # Limpar o parâmetro de refresh após o carregamento
    if "refresh_trigger" in st.query_params:
        # Remove o parâmetro para não ficar na URL
        del st.query_params["refresh_trigger"]

    todas_colunas_dados = [
        "Status", "Ação", "Data Inicial", "Data Final", "Centro",
        "Inscritos", "Concluídos", "Avaliados", "Aprovados", "Planeado",
        "Formador", "Valor da Ação", "Valor Total"
    ]

    if "colunas_selecionadas" not in st.session_state:
        st.session_state.colunas_selecionadas = todas_colunas_dados.copy()

    st.subheader("📋 Escolha as colunas que pretende visualizar/editar")
    colunas_escolhidas = st.multiselect(
        "Selecione as colunas (a coluna 'Apagar' é sempre mostrada):",
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

    # ---------- Carregar ficheiro ----------
    st.subheader("📤 Carregar dados a partir de ficheiro")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        modo_carga = st.radio("Modo de carregamento:", ["Substituir dados existentes", "Adicionar ao final"], horizontal=True, key="modo_carga_acoes")
    with col2:
        ficheiros_carga = st.file_uploader(
            "Carregar um ou mais ficheiros (Excel ou CSV)",
            type=None,
            accept_multiple_files=True,
            key="carga_acoes_upload"
        )
    with col3:
        try:
            with open("assets/amostra_formacoes.xlsx", "rb") as f:
                conteudo_exemplo = f.read()
            st.download_button(
                label="📥 Descarregar ficheiro exemplo (Excel)",
                data=conteudo_exemplo,
                file_name="amostra_formacoes.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except FileNotFoundError:
            st.error("⚠️ Ficheiro de exemplo não encontrado. Verifique o caminho 'assets/amostra_formacoes.xlsx'.")
    with col4:
        try:
            with open("assets/amostra_formacoes_vazio.xlsx", "rb") as f:
                conteudo_exemplo = f.read()
            st.download_button(
                label="📥 Descarregar ficheiro exemplo vazio (Excel)",
                data=conteudo_exemplo,
                file_name="amostra_formacoes_vazio.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except FileNotFoundError:
            st.error("⚠️ Ficheiro de exemplo não encontrado. Verifique o caminho 'assets/amostra_formacoes_vazio.xlsx'.")

    if ficheiros_carga:
        lista_dfs = []
        for ficheiro in ficheiros_carga:
            nome = ficheiro.name.lower()
            try:
                if nome.endswith('.csv'):
                    df_parcial = pd.read_csv(ficheiro)
                elif nome.endswith('.xlsx'):
                    df_parcial = pd.read_excel(ficheiro)
                else:
                    st.warning(f"Ficheiro ignorado (formato não suportado): {ficheiro.name}")
                    continue

                df_parcial.columns = df_parcial.columns.str.strip()
                mapeamento = {
                    'status': 'Status', 'acao': 'Ação',
                    'dataini': 'Data Inicial', 'datafim': 'Data Final',
                    'centro': 'Centro',
                    'inscritos': 'Inscritos', 'concluidos': 'Concluídos',
                    'avaliados': 'Avaliados', 'aprovados': 'Aprovados',
                    'planeado': 'Planeado', 'formador': 'Formador',
                    'valorAcao': 'Valor da Ação', 'valorTotal': 'Valor Total',
                }
                df_parcial.rename(columns={k: v for k, v in mapeamento.items() if k in df_parcial.columns}, inplace=True)

                for col in colunas_dados:
                    if col not in df_parcial.columns:
                        df_parcial[col] = None
                df_parcial = df_parcial[colunas_dados]
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
            # Incrementar contador para forçar recriação do data_editor
            st.session_state.editor_key_counter += 1
            st.success(f"✅ {len(lista_dfs)} ficheiro(s) carregado(s) – total de {len(df_novo)} linhas")
            st.rerun()

        st.markdown("---")
    st.subheader("✏️ Editar tabela de ações")

    # Botão para forçar atualização manual (recria o placeholder)
    col_upd1, col_upd2 = st.columns([1, 5])
    with col_upd1:
        if st.button("🔄 Atualizar Tabela", use_container_width=True, key="btn_refresh"):
            # Incrementa o parâmetro refresh na URL
            import time

            # Gera um timestamp único
            timestamp = int(time.time())
            st.query_params["refresh_trigger"] = str(timestamp)
            st.rerun()

    # ---------- Adicionar linhas vazias ----------
    st.subheader("➕ Adicionar múltiplas linhas")
    col_add1, col_add2 = st.columns([1, 2])
    with col_add1:
        num_linhas = st.number_input("Número de linhas a adicionar:", min_value=1, max_value=10000, value=5, step=1)
    with col_add2:
        if st.button("Adicionar linhas vazias"):
            novas_linhas = pd.DataFrame({col: [None] * num_linhas for col in colunas_dados})
            novas_linhas.insert(0, "Apagar", False)
            st.session_state.acoes_editaveis = pd.concat([st.session_state.acoes_editaveis, novas_linhas], ignore_index=True)
            st.session_state.editor_key_counter += 1
            st.rerun()

    # ---------- Tabela editável (com placeholder) ----------
    placeholder = st.empty()

    # Preparar DataFrame
    df_atual = st.session_state.acoes_editaveis.copy()
    if "Apagar" not in df_atual.columns:
        df_atual.insert(0, "Apagar", False)
    else:
        cols = df_atual.columns.tolist()
        if cols[0] != "Apagar":
            cols.remove("Apagar")
            cols.insert(0, "Apagar")
            df_atual = df_atual[cols]

    for col in colunas_dados:
        if col not in df_atual.columns:
            df_atual[col] = None
    df_atual = df_atual[["Apagar"] + colunas_dados]

    # Recriar o data_editor dentro do placeholder
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

    if not edited_df.equals(df_atual):
        df_normalizado = normalizar_dataframe(edited_df)
        st.session_state.acoes_editaveis = df_normalizado
        st.session_state.editor_key_counter += 1
        st.rerun()

    # ---------- Botões ----------
    st.markdown("---")
    col_bot1, col_bot2 = st.columns(2)

    with col_bot1:
        if st.button("🗑️ Limpar todos os dados", use_container_width=True):
            st.session_state.acoes_editaveis = pd.DataFrame(columns=colunas_com_apagar)
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

    # ---------- Exportar dados ----------
    st.markdown("---")
    st.subheader("📎 Exportar dados")

    # Botão de download direto (sem duplo clique)
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
    # ---------- Métricas resumo (FORA do with col_exp1) ----------
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
        total_conc = (
            df_metricas["Concluídos"].sum()
            if "Concluídos" in df_metricas.columns and pd.api.types.is_numeric_dtype(df_metricas["Concluídos"])
            else 0
        )
        taxa_conc = (total_conc / total_inscricoes * 100) if total_inscricoes > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Ações", total_acoes)
        col2.metric("Total de Inscrições", f"{total_inscricoes:,.0f}".replace(",", "."))
        col3.metric("Taxa de Conclusão Média", f"{taxa_conc:.1f}%")
    else:
        st.info("ℹ️ Tabela sem dados válidos. Adicione ou carregue dados.")

if __name__ == "__main__":
    mostrar_cursos()