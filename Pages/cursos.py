import streamlit as st
import pandas as pd

def mostrar_cursos():
    st.header("📚 Análise de Formações")

    # Todas as colunas de dados possíveis (exclui "Apagar")
    todas_colunas_dados = [
        "Status", "Ação", "Data Inicial", "Data Final", "Centro",
        "Inscritos", "Concluídos", "Avaliados", "Aprovados", "Planeado",
        "Formador", "Valor da Ação", "Valor Total"
    ]

    # --- Seletor de colunas (mantido no session_state) ---
    if "colunas_selecionadas" not in st.session_state:
        st.session_state.colunas_selecionadas = todas_colunas_dados.copy()  # por padrão, todas

    # Mostrar o multiselect na interface
    st.subheader("📋 Escolha as colunas que pretende visualizar/editar")
    colunas_escolhidas = st.multiselect(
        "Selecione as colunas (a coluna 'Apagar' é sempre mostrada):",
        options=todas_colunas_dados,
        default=st.session_state.colunas_selecionadas,
        key="seletor_colunas"
    )

    # Se o utilizador alterou a seleção, atualizar o estado e ajustar a tabela
    if set(colunas_escolhidas) != set(st.session_state.colunas_selecionadas):
        st.session_state.colunas_selecionadas = colunas_escolhidas
        # Reestruturar a tabela existente para conter apenas as colunas selecionadas
        if 'acoes_editaveis' in st.session_state and not st.session_state.acoes_editaveis.empty:
            df_atual = st.session_state.acoes_editaveis
            # Preservar a coluna "Apagar" (primeira)
            if "Apagar" in df_atual.columns:
                apagar = df_atual["Apagar"]
                outras = {col: df_atual[col] for col in st.session_state.colunas_selecionadas if col in df_atual.columns}
                # Criar novo DataFrame com as colunas selecionadas + Apagar
                novo_df = pd.DataFrame(outras)
                novo_df.insert(0, "Apagar", apagar)
                st.session_state.acoes_editaveis = novo_df
            else:
                st.session_state.acoes_editaveis = pd.DataFrame(columns=["Apagar"] + st.session_state.colunas_selecionadas)
        st.rerun()

    # A partir daqui, usamos st.session_state.colunas_selecionadas
    colunas_dados = st.session_state.colunas_selecionadas
    colunas_com_apagar = ["Apagar"] + colunas_dados

    # Inicializar dados no session_state
    if 'acoes_editaveis' not in st.session_state:
        st.session_state.acoes_editaveis = pd.DataFrame(columns=colunas_com_apagar)

    # ---------- Carregar ficheiro (apenas colunas selecionadas) ----------
    st.subheader("📤 Carregar dados a partir de ficheiro")
    col1, col2 = st.columns(2)
    with col1:
        modo_carga = st.radio("Modo de carregamento:", ["Substituir dados existentes", "Adicionar ao final"], horizontal=True, key="modo_carga_acoes")
    with col2:
        ficheiro_carga = st.file_uploader("Carregar Excel ou CSV", type=None, key="carga_acoes_upload")

    if ficheiro_carga is not None:
        try:
            nome_ficheiro = ficheiro_carga.name.lower()
            if nome_ficheiro.endswith('.csv'):
                df_novo = pd.read_csv(ficheiro_carga)
            elif nome_ficheiro.endswith('.xlsx'):
                df_novo = pd.read_excel(ficheiro_carga)
            else:
                st.error("Formato não suportado. Carregue um ficheiro .csv ou .xlsx")
                st.stop()

            df_novo.columns = df_novo.columns.str.strip()
            mapeamento = {
                'status': 'Status', 'acao': 'Ação',
                'dataini': 'Data Inicial', 'datafim': 'Data Final',
                'centro': 'Centro',
                'inscritos': 'Inscritos', 'concluidos': 'Concluídos',
                'avaliados': 'Avaliados', 'aprovados': 'Aprovados',
                'planeado': 'Planeado', 'formador': 'Formador',
                'valorAcao': 'Valor da Ação', 'valorTotal': 'Valor Total',
            }
            df_novo.rename(columns={k: v for k, v in mapeamento.items() if k in df_novo.columns}, inplace=True)
            # Manter apenas as colunas que estão selecionadas e existem no ficheiro
            colunas_importar = [c for c in colunas_dados if c in df_novo.columns]
            df_novo = df_novo[colunas_importar]
            # Adicionar colunas selecionadas que estejam em falta (com None)
            for col in colunas_dados:
                if col not in df_novo.columns:
                    df_novo[col] = None
            df_novo = df_novo[colunas_dados]  # reordena
            df_novo.insert(0, "Apagar", False)

            if modo_carga == "Substituir dados existentes":
                st.session_state.acoes_editaveis = df_novo
            else:
                st.session_state.acoes_editaveis = pd.concat([st.session_state.acoes_editaveis, df_novo], ignore_index=True)
            st.success(f"✅ Dados carregados com sucesso! ({len(df_novo)} linhas)")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao ler o ficheiro: {e}")

    st.markdown("---")
    st.subheader("✏️ Editar tabela de ações")

    # ---------- Adicionar linhas vazias (apenas colunas selecionadas) ----------
    st.subheader("➕ Adicionar múltiplas linhas")
    col_add1, col_add2 = st.columns([1, 2])
    with col_add1:
        num_linhas = st.number_input("Número de linhas a adicionar:", min_value=1, max_value=1000, value=5, step=1)
    with col_add2:
        if st.button("Adicionar linhas vazias"):
            novas_linhas = pd.DataFrame(
                {col: [None] * num_linhas for col in colunas_dados}
            )
            novas_linhas.insert(0, "Apagar", False)
            st.session_state.acoes_editaveis = pd.concat([st.session_state.acoes_editaveis, novas_linhas], ignore_index=True)
            st.rerun()

    # ---------- Tabela editável ----------
    df_atual = st.session_state.acoes_editaveis.copy()
    # Garantir que a coluna "Apagar" existe e é a primeira
    if "Apagar" not in df_atual.columns:
        df_atual.insert(0, "Apagar", False)
    else:
        cols = df_atual.columns.tolist()
        if cols[0] != "Apagar":
            cols.remove("Apagar")
            cols.insert(0, "Apagar")
            df_atual = df_atual[cols]

    # Se houver colunas selecionadas que não estão no DataFrame (ex: adicionadas depois), adicioná‑las
    for col in colunas_dados:
        if col not in df_atual.columns:
            df_atual[col] = None
    df_atual = df_atual[["Apagar"] + colunas_dados]  # reordena

    edited_df = st.data_editor(
        df_atual,
        use_container_width=True,
        num_rows="dynamic",
        height=400,
        key="acoes_editor",
        column_config={
            "Apagar": st.column_config.CheckboxColumn("Apagar", default=False)
        }
    )

    if not edited_df.equals(df_atual):
        st.session_state.acoes_editaveis = edited_df
        st.rerun()

    # ---------- Botões ----------
    st.markdown("---")
    col_bot1, col_bot2 = st.columns(2)

    with col_bot1:
        if st.button("🗑️ Limpar todos os dados", use_container_width=True):
            st.session_state.acoes_editaveis = pd.DataFrame(columns=colunas_com_apagar)
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
                    st.session_state.acoes_editaveis = df
                    st.rerun()
                else:
                    st.warning("Nenhuma linha marcada para apagar.")
            else:
                st.warning("Coluna 'Apagar' não encontrada.")

    # ---------- Métricas resumo (apenas com as colunas selecionadas) ----------
    df_metricas = st.session_state.acoes_editaveis.drop(columns=["Apagar"], errors="ignore").copy()

    # Filtro robusto: elimina linhas sem "Ação" (se "Ação" estiver selecionada)
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