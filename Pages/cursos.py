import streamlit as st
import pandas as pd
import numpy as np
import io
import re

# ------------------- Funções auxiliares -------------------
def converter_colunas_numericas(df: pd.DataFrame) -> pd.DataFrame:
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
    return converter_colunas_numericas(df)

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

def dfs_diferentes(df1: pd.DataFrame, df2: pd.DataFrame) -> bool:
    if df1.shape != df2.shape:
        return True
    try:
        return not df1.fillna("__NA__").astype(str).equals(
            df2.fillna("__NA__").astype(str)
        )
    except Exception:
        return True

def garantir_todas_colunas(df: pd.DataFrame, todas_colunas: list, incluir_apagar=True) -> pd.DataFrame:
    for col in todas_colunas:
        if col not in df.columns:
            df[col] = None
    if incluir_apagar and "Apagar" not in df.columns:
        df.insert(0, "Apagar", False)
    cols_ordenadas = ["Apagar"] + [c for c in todas_colunas if c in df.columns] if incluir_apagar else todas_colunas
    return df[cols_ordenadas]

# ------------------- Funções para formandos e cálculos -------------------
def calcular_colunas_formandos(df_formandos: pd.DataFrame) -> pd.DataFrame:
    """Calcula Valor_curso_final e Total_a_pagar com base nas outras colunas."""
    if df_formandos.empty:
        return df_formandos
    # Converte para numérico
    for col in ["Valor_curso", "Desconto", "Total_ja_pago"]:
        if col in df_formandos.columns:
            df_formandos[col] = pd.to_numeric(df_formandos[col], errors="coerce").fillna(0)
    if "Valor_curso" in df_formandos.columns and "Desconto" in df_formandos.columns:
        df_formandos["Valor_curso_final"] = df_formandos["Valor_curso"] - df_formandos["Desconto"]
    if "Valor_curso_final" in df_formandos.columns and "Total_ja_pago" in df_formandos.columns:
        df_formandos["Total_a_pagar"] = df_formandos["Valor_curso_final"] - df_formandos["Total_ja_pago"]
    return df_formandos

def recalcular_cursos_a_partir_formandos(df_cursos: pd.DataFrame, df_formandos: pd.DataFrame) -> pd.DataFrame:
    """Atualiza as colunas Devedores, Valor total a receber, Valor Total Recebido em df_cursos."""
    # Garantia de que ambos são DataFrames, nunca None
    if df_cursos is None:
        df_cursos = pd.DataFrame()
    if df_formandos is None:
        df_formandos = pd.DataFrame()

    if df_cursos.empty:
        # Se não há cursos, retorna vazio
        return df_cursos

    # Garante que as três colunas existem
    for col in ["Devedores", "Valor total a receber", "Valor Total Recebido"]:
        if col not in df_cursos.columns:
            df_cursos[col] = 0

    if df_formandos.empty or "Ação" not in df_formandos.columns:
        # Sem formandos, zera tudo
        df_cursos["Devedores"] = 0
        df_cursos["Valor total a receber"] = 0
        df_cursos["Valor Total Recebido"] = 0
        return df_cursos

    # Prepara df_formandos com cálculos
    df_form = calcular_colunas_formandos(df_formandos.copy())

    # Agrupa por Ação
    agg = df_form.groupby("Ação").agg(
        Devedores=("Total_a_pagar", lambda x: (x > 0).sum()),
        Valor_total_a_receber=("Valor_curso_final", "sum"),
        Valor_Total_Recebido=("Total_ja_pago", "sum")
    ).reset_index()

    # Renomeia para corresponder às colunas do df_cursos
    agg.rename(columns={
        "Valor_total_a_receber": "Valor total a receber",
        "Valor_Total_Recebido": "Valor Total Recebido"
    }, inplace=True)

    # Faz merge e atualiza df_cursos
    df_cursos = df_cursos.merge(agg, on="Ação", how="left", suffixes=("", "_calc"))
    for col in ["Devedores", "Valor total a receber", "Valor Total Recebido"]:
        col_calc = f"{col}_calc"
        if col_calc in df_cursos.columns:
            df_cursos[col] = df_cursos[col_calc].fillna(0)
            df_cursos.drop(columns=[col_calc], inplace=True)
        else:
            df_cursos[col] = df_cursos[col].fillna(0)

    return df_cursos

def exportar_excel(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return output.getvalue()

# ------------------- Função principal -------------------
def mostrar_cursos():
    st.header("📚 Análise de Formações")

    # ---------- Inicializações seguras ----------
    todas_colunas_cursos = [
        "Status", "Ação", "Data Inicial", "Data Final", "Centro",
        "Inscritos", "Aptos", "Inaptos", "Desistentes", "Devedores",
        "Taxa de Satisfação M01", "Taxa de Satisfação M02", "Taxa de Satisfação M03",
        "Taxa de Satisfação M04", "Taxa de Satisfação M05", "Taxa de Satisfação M06",
        "Taxa de Satisfação M07", "Taxa de Satisfação M08", "Taxa de Satisfação M09",
        "Taxa de Satisfação M10", "Taxa de Satisfação M11", "Taxa de Satisfação M12",
        "Taxa de satisfação Final", "Nacionalidades(Portugueses/Estrangeiros)",
        "Valor total a receber", "Valor Total Recebido", "Formador", "Avaliação formador"
    ]

    todas_colunas_formandos = [
        "Ação", "Data_inicial", "Data_final", "Nome", "Formando",
        "Valor_curso", "Desconto", "Valor_curso_final", "Total_ja_pago", "Total_a_pagar"
    ]

    # Garante que as variáveis no session_state sejam sempre DataFrames, não None
    if "cursos_df" not in st.session_state or st.session_state.cursos_df is None:
        st.session_state.cursos_df = pd.DataFrame(columns=["Apagar"] + todas_colunas_cursos)
    if "formandos_df" not in st.session_state or st.session_state.formandos_df is None:
        st.session_state.formandos_df = pd.DataFrame(columns=["Apagar"] + todas_colunas_formandos)

    # Inicializa contadores
    for key in ["cursos_uploader_counter", "formandos_uploader_counter", "cursos_editor_key", "formandos_editor_key"]:
        if key not in st.session_state:
            st.session_state[key] = 0

    # Colunas selecionadas
    if "colunas_cursos" not in st.session_state:
        st.session_state.colunas_cursos = [col for col in todas_colunas_cursos
                                           if not col.startswith("Taxa de Satisfação M") or col in ["Taxa de Satisfação M01", "Taxa de Satisfação M02"]]
    if "colunas_formandos" not in st.session_state:
        st.session_state.colunas_formandos = todas_colunas_formandos.copy()

    # Recalcula cursos sempre que necessário (garante consistência)
    st.session_state.cursos_df = recalcular_cursos_a_partir_formandos(
        st.session_state.cursos_df, st.session_state.formandos_df
    )

    # ---------- Abas ----------
    tab_cursos, tab_formandos = st.tabs(["📋 Cursos (Ações)", "👥 Formandos (Alunos)"])

    # ========== ABA CURSOS ==========
    with tab_cursos:
        # Seletor de colunas
        colunas_escolhidas_cursos = st.multiselect(
            "Selecione as colunas para visualizar/editar (exceto as três calculadas, que são automáticas):",
            options=todas_colunas_cursos,
            default=st.session_state.colunas_cursos,
            key="seletor_cursos"
        )
        if set(colunas_escolhidas_cursos) != set(st.session_state.colunas_cursos):
            st.session_state.colunas_cursos = colunas_escolhidas_cursos
            st.rerun()

        # Editor de cursos
        df_cursos_para_editar = garantir_todas_colunas(
            st.session_state.cursos_df.copy(),
            st.session_state.colunas_cursos,
            incluir_apagar=True
        )

        edited_cursos = st.data_editor(
            df_cursos_para_editar,
            use_container_width=True,
            num_rows="dynamic",
            height=400,
            key=f"cursos_editor_{st.session_state.cursos_editor_key}",
            column_config={"Apagar": st.column_config.CheckboxColumn("Apagar", default=False)}
        )

        if dfs_diferentes(edited_cursos, df_cursos_para_editar):
            # Atualiza apenas as colunas editáveis (exceto as calculadas)
            df_atual = st.session_state.cursos_df.copy()
            for col in edited_cursos.columns:
                if col not in ["Devedores", "Valor total a receber", "Valor Total Recebido", "Apagar"]:
                    df_atual[col] = edited_cursos[col].values
            if "Apagar" in edited_cursos.columns:
                df_atual["Apagar"] = edited_cursos["Apagar"].values
            st.session_state.cursos_df = normalizar_dataframe(df_atual)
            # Recalcula (garante que as calculadas fiquem corretas)
            st.session_state.cursos_df = recalcular_cursos_a_partir_formandos(
                st.session_state.cursos_df, st.session_state.formandos_df
            )
            st.session_state.cursos_editor_key += 1
            st.rerun()

        # Botões para cursos
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🗑️ Limpar todos os cursos", use_container_width=True):
                st.session_state.cursos_df = pd.DataFrame(columns=["Apagar"] + todas_colunas_cursos)
                st.session_state.cursos_editor_key += 1
                st.rerun()
        with col2:
            if st.button("✖️ Apagar selecionados (cursos)", use_container_width=True):
                df = st.session_state.cursos_df.copy()
                if "Apagar" in df.columns:
                    linhas_apagar = df[df["Apagar"] == True].index.tolist()
                    if linhas_apagar:
                        df.drop(index=linhas_apagar, inplace=True)
                        df.reset_index(drop=True, inplace=True)
                        df["Apagar"] = False
                        st.session_state.cursos_df = normalizar_dataframe(df)
                        st.session_state.cursos_editor_key += 1
                        st.rerun()
                    else:
                        st.warning("Nenhuma linha marcada para apagar.")
        with col3:
            # Exportar cursos
            df_export_cursos = st.session_state.cursos_df.drop(columns=["Apagar"], errors="ignore")
            st.download_button(
                label="📥 Exportar cursos",
                data=exportar_excel(df_export_cursos),
                file_name="cursos_exportados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        # Upload de cursos (opcional para manter a funcionalidade)
        with st.expander("📤 Carregar dados de cursos (Excel/CSV)"):
            modo_carga_cursos = st.radio("Modo:", ["Substituir", "Adicionar"], horizontal=True, key="modo_carga_cursos")
            ficheiros_cursos = st.file_uploader(
                "Carregar ficheiros",
                type=None, accept_multiple_files=True,
                key=f"cursos_upload_{st.session_state.cursos_uploader_counter}"
            )
            if ficheiros_cursos:
                lista_dfs = []
                for f in ficheiros_cursos:
                    try:
                        if f.name.lower().endswith('.csv'):
                            df_parcial = pd.read_csv(f)
                        else:
                            df_parcial = pd.read_excel(f, header=1)
                        df_parcial.columns = df_parcial.columns.str.strip()
                        # Mapeamento básico (pode adaptar)
                        for col in todas_colunas_cursos:
                            if col not in df_parcial.columns:
                                df_parcial[col] = None
                        df_parcial = df_parcial[todas_colunas_cursos]
                        df_parcial.insert(0, "Apagar", False)
                        lista_dfs.append(df_parcial)
                    except Exception as e:
                        st.error(f"Erro em {f.name}: {e}")
                if lista_dfs:
                    df_novo = pd.concat(lista_dfs, ignore_index=True)
                    if modo_carga_cursos == "Substituir":
                        st.session_state.cursos_df = df_novo
                    else:
                        st.session_state.cursos_df = pd.concat([st.session_state.cursos_df, df_novo], ignore_index=True)
                    st.session_state.cursos_df = recalcular_cursos_a_partir_formandos(
                        st.session_state.cursos_df, st.session_state.formandos_df
                    )
                    st.session_state.cursos_uploader_counter += 1
                    st.session_state.cursos_editor_key += 1
                    st.rerun()

    # ========== ABA FORMANDOS ==========
    with tab_formandos:
        st.subheader("👥 Dados dos Formandos (alunos por ação)")

        # Seletor de colunas
        colunas_escolhidas_formandos = st.multiselect(
            "Selecione as colunas para os formandos:",
            options=todas_colunas_formandos,
            default=st.session_state.colunas_formandos,
            key="seletor_formandos"
        )
        if set(colunas_escolhidas_formandos) != set(st.session_state.colunas_formandos):
            st.session_state.colunas_formandos = colunas_escolhidas_formandos
            st.rerun()

        # Upload de formandos
        with st.expander("📤 Carregar dados de formandos (Excel/CSV)"):
            modo_carga_form = st.radio("Modo:", ["Substituir", "Adicionar"], horizontal=True, key="modo_carga_formandos")
            ficheiros_form = st.file_uploader(
                "Carregar ficheiros",
                type=None, accept_multiple_files=True,
                key=f"formandos_upload_{st.session_state.formandos_uploader_counter}"
            )
            if ficheiros_form:
                lista_dfs_form = []
                for f in ficheiros_form:
                    try:
                        if f.name.lower().endswith('.csv'):
                            df_parcial = pd.read_csv(f)
                        else:
                            df_parcial = pd.read_excel(f, header=0)
                        df_parcial.columns = df_parcial.columns.str.strip()
                        for col in todas_colunas_formandos:
                            if col not in df_parcial.columns:
                                df_parcial[col] = None
                        df_parcial = df_parcial[todas_colunas_formandos]
                        df_parcial.insert(0, "Apagar", False)
                        lista_dfs_form.append(df_parcial)
                    except Exception as e:
                        st.error(f"Erro em {f.name}: {e}")
                if lista_dfs_form:
                    df_novo_form = pd.concat(lista_dfs_form, ignore_index=True)
                    if modo_carga_form == "Substituir":
                        st.session_state.formandos_df = df_novo_form
                    else:
                        st.session_state.formandos_df = pd.concat([st.session_state.formandos_df, df_novo_form], ignore_index=True)
                    st.session_state.formandos_df = calcular_colunas_formandos(st.session_state.formandos_df)
                    st.session_state.cursos_df = recalcular_cursos_a_partir_formandos(
                        st.session_state.cursos_df, st.session_state.formandos_df
                    )
                    st.session_state.formandos_uploader_counter += 1
                    st.session_state.formandos_editor_key += 1
                    st.rerun()

        # Adicionar linhas vazias
        col_add1, col_add2 = st.columns([1, 2])
        with col_add1:
            num_linhas_form = st.number_input("Nº linhas a adicionar:", min_value=1, value=5, step=1)
        with col_add2:
            if st.button("➕ Adicionar linhas vazias (formandos)"):
                novas_linhas = pd.DataFrame({col: [None] * num_linhas_form for col in todas_colunas_formandos})
                novas_linhas.insert(0, "Apagar", False)
                st.session_state.formandos_df = pd.concat([st.session_state.formandos_df, novas_linhas], ignore_index=True)
                st.session_state.formandos_df = calcular_colunas_formandos(st.session_state.formandos_df)
                st.session_state.cursos_df = recalcular_cursos_a_partir_formandos(
                    st.session_state.cursos_df, st.session_state.formandos_df
                )
                st.session_state.formandos_editor_key += 1
                st.rerun()

        # Editor de formandos
        df_formandos_para_editar = garantir_todas_colunas(
            st.session_state.formandos_df.copy(),
            st.session_state.colunas_formandos,
            incluir_apagar=True
        )
        edited_formandos = st.data_editor(
            df_formandos_para_editar,
            use_container_width=True,
            num_rows="dynamic",
            height=400,
            key=f"formandos_editor_{st.session_state.formandos_editor_key}",
            column_config={"Apagar": st.column_config.CheckboxColumn("Apagar", default=False)}
        )

        if dfs_diferentes(edited_formandos, df_formandos_para_editar):
            df_atual_form = st.session_state.formandos_df.copy()
            for col in edited_formandos.columns:
                if col != "Apagar":
                    df_atual_form[col] = edited_formandos[col].values
            if "Apagar" in edited_formandos.columns:
                df_atual_form["Apagar"] = edited_formandos["Apagar"].values
            df_atual_form = calcular_colunas_formandos(df_atual_form)
            st.session_state.formandos_df = df_atual_form
            st.session_state.cursos_df = recalcular_cursos_a_partir_formandos(
                st.session_state.cursos_df, st.session_state.formandos_df
            )
            st.session_state.formandos_editor_key += 1
            st.rerun()

        # Botões para formandos
        colb1, colb2, colb3 = st.columns(3)
        with colb1:
            if st.button("🗑️ Limpar todos os formandos"):
                st.session_state.formandos_df = pd.DataFrame(columns=["Apagar"] + todas_colunas_formandos)
                st.session_state.cursos_df = recalcular_cursos_a_partir_formandos(
                    st.session_state.cursos_df, st.session_state.formandos_df
                )
                st.session_state.formandos_editor_key += 1
                st.rerun()
        with colb2:
            if st.button("✖️ Apagar selecionados (formandos)"):
                df = st.session_state.formandos_df.copy()
                if "Apagar" in df.columns:
                    linhas_apagar = df[df["Apagar"] == True].index.tolist()
                    if linhas_apagar:
                        df.drop(index=linhas_apagar, inplace=True)
                        df.reset_index(drop=True, inplace=True)
                        df["Apagar"] = False
                        st.session_state.formandos_df = calcular_colunas_formandos(df)
                        st.session_state.cursos_df = recalcular_cursos_a_partir_formandos(
                            st.session_state.cursos_df, st.session_state.formandos_df
                        )
                        st.session_state.formandos_editor_key += 1
                        st.rerun()
                    else:
                        st.warning("Nenhum formando marcado para apagar.")
        with colb3:
            df_export_form = st.session_state.formandos_df.drop(columns=["Apagar"], errors="ignore")
            st.download_button(
                label="📥 Exportar formandos",
                data=exportar_excel(df_export_form),
                file_name="formandos_exportados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

if __name__ == "__main__":
    mostrar_cursos()