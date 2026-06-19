import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import unicodedata
import re
import unicodedata
from datetime import datetime, date
from io import BytesIO


# ------------------------------------------------------------
# Funções auxiliares
# ------------------------------------------------------------
def _norm_header(c):
    """Tira \n e espaços a mais dos cabeçalhos."""
    return re.sub(r'\s+', ' ', str(c).replace('\n', ' ')).strip()
 
def _base_name(c):
    """Nome base sem sufixo .1/.2 do pandas, sem acentos, minusculas."""
    base = re.sub(r'\.\d+$', '', str(c))
    base = _norm_header(base).lower()
    return unicodedata.normalize('NFKD', base).encode('ASCII', 'ignore').decode('ASCII')
 
 
def carregar_projecao_anual(uploaded_file, ano=None):
    """Le a projecao do ANO indicado (por defeito o atual) do ficheiro novo (PFE).
    Devolve (df_ld, df_vsp, info) com colunas: Centro, Codigo curso, Nº Acoes Previstas."""
    if ano is None:
        ano = datetime.now().year
 
    xl = pd.ExcelFile(uploaded_file)
    info = {'ano': ano, 'folhas_disponiveis': xl.sheet_names}
 
    def achar_folha(tipo):
        for s in xl.sheet_names:
            sl = s.lower()
            if str(ano) in sl and tipo.lower() in sl:
                return s
        return None
 
    folha_ld = achar_folha('LD')
    folha_vsp = achar_folha('VSP')
    info['folha_ld'] = folha_ld
    info['folha_vsp'] = folha_vsp
 
    def preparar(folha):
        if folha is None:
            return pd.DataFrame(columns=['Centro', 'Código curso', 'Nº Ações Previstas']), None
        df = pd.read_excel(uploaded_file, sheet_name=folha)
        df.columns = [_norm_header(c) for c in df.columns]
 
        if 'Centro' not in df.columns:
            for c in df.columns:
                if _base_name(c) in ('centro', 'centro de formacao'):
                    df = df.rename(columns={c: 'Centro'})
                    break
        if 'Código curso' not in df.columns:
            for c in df.columns:
                if 'codigo curso' in _base_name(c):
                    df = df.rename(columns={c: 'Código curso'})
                    break
 
        # No VSP ha DUAS colunas com este nome: usar a ULTIMA (bloco "Projecao {ano}")
        alvo = 'numero de acoes de formacao a desenvolver do curso'
        candidatas = [c for c in df.columns if _base_name(c) == alvo]
        col_acoes = candidatas[-1] if candidatas else None
 
        if 'Centro' not in df.columns:
            df['Centro'] = ''
        if 'Código curso' not in df.columns:
            df['Código curso'] = ''
 
        df['Centro'] = df['Centro'].fillna('').astype(str).str.strip()
        df['Código curso'] = df['Código curso'].fillna('').astype(str).str.strip()
        df['Nº Ações Previstas'] = pd.to_numeric(df[col_acoes], errors='coerce').fillna(0) if col_acoes else 0
        df = df[df['Código curso'] != '']
 
        out = df.groupby(['Centro', 'Código curso'], as_index=False)['Nº Ações Previstas'].sum()
        return out, col_acoes
 
    df_ld, col_ld = preparar(folha_ld)
    df_vsp, col_vsp = preparar(folha_vsp)
    info['coluna_usada_ld'] = col_ld
    info['coluna_usada_vsp'] = col_vsp
    return df_ld, df_vsp, info
 
 
def combinar_projecao(df_ld, df_vsp):
    """Junta LD + VSP: Centro, Codigo curso, Nº Acoes LD, Nº Acoes VSP, Nº Acoes Previstas."""
    a = df_ld.rename(columns={'Nº Ações Previstas': 'Nº Ações LD'})
    b = df_vsp.rename(columns={'Nº Ações Previstas': 'Nº Ações VSP'})
    comb = pd.merge(a, b, on=['Centro', 'Código curso'], how='outer')
    comb['Nº Ações LD'] = comb['Nº Ações LD'].fillna(0)
    comb['Nº Ações VSP'] = comb['Nº Ações VSP'].fillna(0)
    comb['Nº Ações Previstas'] = comb['Nº Ações LD'] + comb['Nº Ações VSP']
    return comb

def get_col(df, pattern):
    """Retorna a primeira coluna cujo nome contenha o pattern (case-insensitive)."""
    pattern = pattern.lower()
    for col in df.columns:
        if pattern in col.lower():
            return col
    return None

def aplicar_filtros(df):
    """Aplica os filtros globais da sidebar (centro, datas, etc.) se existirem."""
    if df is None or df.empty:
        return df
    if hasattr(st.session_state, 'filtro_centro') and st.session_state.filtro_centro:
        if 'Centro' in df.columns:
            df = df[df['Centro'].isin(st.session_state.filtro_centro)]
    return df

def normalizar_centro(nome):
    if pd.isna(nome):
        return "DESCONHECIDO"
    nome = str(nome).strip().upper()
    mapeamento = {
        'GAIA': 'GAIA', 'GALA': 'GAIA', 'VILA NOVA DE GAIA': 'GAIA',
        'PORTO': 'PORTO',
        'LISBOA': 'LISBOA',
        'AMADORA': 'AMADORA',
        'ALVERCA': 'ALVERCA',
        'BRAGA': 'BRAGA',
        'COIMBRA': 'COIMBRA',
        'FARO': 'FARO',
        'FUNCHAL': 'FUNCHAL', 'MADEIRA': 'FUNCHAL',
        'S.J.MADEIRA': 'S.J.MADEIRA', 'SAO JOAO DA MADEIRA': 'S.J.MADEIRA',
        'VISEU': 'VISEU',
    }
    for chave, valor in mapeamento.items():
        if chave in nome:
            return valor
    return nome

ORDEM_MESES = {
    'janeiro': 1, 'fevereiro': 2, 'março': 3, 'marco': 3, 'abril': 4,
    'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8, 'setembro': 9,
    'outubro': 10, 'novembro': 11, 'dezembro': 12,
}

def ordenar_meses(valores):
    return sorted(
        valores,
        key=lambda m: (ORDEM_MESES.get(str(m).strip().lower(), 99), str(m).strip().lower())
    )

# ------------------------------------------------------------
# Página principal de Qualidade
# ------------------------------------------------------------
def mostrar_qualidade():
    st.header("🎯 Scorecard de Qualidade Pedagógica")

    # ------------------------------------------------------------
    # NOVO: Área de upload da Projeção 2026 (fora do expander)
    # ------------------------------------------------------------
    st.markdown("---")
    st.subheader("📁 Upload da Projeção 2026 (LD + VSP)")

    col_upload, col_download = st.columns([3, 1])

    with col_upload:
        uploaded_file = st.file_uploader(
            "Carregue o ficheiro 'Modelo_Previsões_Anuais.xlsx' para calcular o cumprimento do plano",
            type=["xlsx", "xls"],
            key="upload_projecao_plano_global"
        )

    with col_download:
        # Botão de download do modelo
        try:
            with open("assets/Modelo_Previsões_Anuais.xlsx", "rb") as f:
                modelo_conteudo = f.read()
            st.download_button(
                label="📥 Baixar Modelo",
                data=modelo_conteudo,
                file_name="Modelo_Previsões_Anuais.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="download_modelo_previsoes"
            )
        except FileNotFoundError:
            st.error("⚠️ Modelo não encontrado: assets/Modelo_Previsões_Anuais.xlsx")
        except Exception as e:
            st.error(f"Erro ao carregar modelo: {e}")

    # Processar o ficheiro se foi carregado
    if uploaded_file is not None:
            try:
                ano_atual = datetime.now().year
                df_ld, df_vsp, info_proj = carregar_projecao_anual(uploaded_file, ano=ano_atual)
    
                if info_proj['folha_ld'] is None and info_proj['folha_vsp'] is None:
                    st.error(
                        f"⚠️ Nao encontrei folhas para o ano {ano_atual}. "
                        f"Folhas no ficheiro: {info_proj['folhas_disponiveis']}"
                    )
                    st.session_state.projecao_uploaded = False
                else:
                    st.session_state.df_projecao_ld = df_ld
                    st.session_state.df_projecao_vsp = df_vsp
                    st.session_state.info_projecao = info_proj
                    st.session_state.projecao_uploaded = True
    
                    st.success(
                        f"✅ Projecao {ano_atual} carregada "
                        f"(LD: '{info_proj['folha_ld']}' | VSP: '{info_proj['folha_vsp']}')"
                    )
                    with st.expander("🔎 Verificacao da leitura", expanded=False):
                        st.write(f"**Ano usado:** {info_proj['ano']}")
                        st.write(f"**Coluna LD usada:** {info_proj['coluna_usada_ld']}")
                        st.write(f"**Coluna VSP usada:** {info_proj['coluna_usada_vsp']}")
                        st.write(f"**Total acoes LD:** {df_ld['Nº Ações Previstas'].sum():.0f}")
                        st.write(f"**Total acoes VSP:** {df_vsp['Nº Ações Previstas'].sum():.0f}")
                        st.write(f"**Total GLOBAL previstas:** "
                                 f"{df_ld['Nº Ações Previstas'].sum() + df_vsp['Nº Ações Previstas'].sum():.0f}")
            except Exception as e:
                st.error(f"Erro ao carregar o ficheiro: {e}")
                st.session_state.projecao_uploaded = False
    
    elif st.session_state.get("projecao_uploaded", False):
        st.success("✅ Ficheiro ja carregado. Use o botao 'Ver detalhes' abaixo para ver os resultados.")

    # ----- Dados dos Cursos (NOVA ESTRUTURA: usa st.session_state.acoes_df) -----
    df_cursos_raw = st.session_state.get("acoes_df", None)   # <--- ALTERADO
    if df_cursos_raw is not None and not df_cursos_raw.empty:
        if "Apagar" in df_cursos_raw.columns:
            df_cursos_raw = df_cursos_raw.drop(columns=["Apagar"])
        # Conversões de tipo
        for col in ["Inscritos", "Aptos", "Inaptos", "Desistentes",
                    "Taxa de satisfação Final", "Avaliação formador",
                    "Valor total a receber", "Valor Total Recebido"]:
            if col in df_cursos_raw.columns:
                df_cursos_raw[col] = pd.to_numeric(df_cursos_raw[col], errors="coerce")
        # A coluna "Devedores" pode chamar-se "Devedor" na nova estrutura
        if "Devedor" in df_cursos_raw.columns:
            df_cursos_raw["Devedores"] = df_cursos_raw["Devedor"]   # compatibilidade
        for col in ["Data Inicial", "Data Final"]:
            if col in df_cursos_raw.columns:
                df_cursos_raw[col] = pd.to_datetime(df_cursos_raw[col], errors="coerce", dayfirst=True)
    else:
        df_cursos_raw = None

    # ----- Dados dos Questionários (inalterado) -----
    df_quest_raw = st.session_state.get("quest_editaveis", None)

    # Aplicar filtros (centro, datas, etc.)
    df_cursos = aplicar_filtros(df_cursos_raw) if df_cursos_raw is not None else None
    df_quest = aplicar_filtros(df_quest_raw) if df_quest_raw is not None else None

    has_cursos = df_cursos is not None and not df_cursos.empty
    has_quest = df_quest is not None and not df_quest.empty

    # Inicializar objectivos (metas) no session_state (inalterado)
    if 'obj_satisfacao' not in st.session_state:
        st.session_state.obj_satisfacao = 4.2
    if 'obj_conclusao' not in st.session_state:
        st.session_state.obj_conclusao = 85.0
    if 'obj_aprovacao' not in st.session_state:
        st.session_state.obj_aprovacao = 80.0
    if 'obj_plano' not in st.session_state:
        st.session_state.obj_plano = 95.0
    if 'obj_formador' not in st.session_state:
        st.session_state.obj_formador = 4.3
    if 'obj_substituicao' not in st.session_state:
        st.session_state.obj_substituicao = 10.0
    if 'obj_multiformador' not in st.session_state:
        st.session_state.obj_multiformador = 20.0
    if 'obj_reclamacao_curso' not in st.session_state:
        st.session_state.obj_reclamacao_curso = 5.0
    if 'obj_tmrp' not in st.session_state:
        st.session_state.obj_tmrp = 48.0
    if 'obj_acoes_implementadas' not in st.session_state:
        st.session_state.obj_acoes_implementadas = 80.0
    if 'obj_recorrencia' not in st.session_state:
        st.session_state.obj_recorrencia = 10.0
    if 'obj_conformidade' not in st.session_state:
        st.session_state.obj_conformidade = 100.0

    # Expander para editar as metas (inalterado)
    with st.expander("⚙️ Definir Objetivos (Metas) dos KPI's", expanded=False):
        st.markdown("Ajuste os valores desejados para cada indicador:")
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.obj_satisfacao = st.number_input(
                "🎓 Satisfação dos Formandos (máx 5)", min_value=0.0, max_value=5.0, step=0.1,
                value=st.session_state.obj_satisfacao, key="edit_sat"
            )
            st.session_state.obj_conclusao = st.number_input(
                "✅ Taxa de Conclusão (%)", min_value=0.0, max_value=100.0, step=1.0,
                value=st.session_state.obj_conclusao, key="edit_conc"
            )
            st.session_state.obj_aprovacao = st.number_input(
                "📝 Taxa de Aprovação (%)", min_value=0.0, max_value=100.0, step=1.0,
                value=st.session_state.obj_aprovacao, key="edit_aprov"
            )
            st.session_state.obj_plano = st.number_input(
                "📅 Cumprimento do Plano (%)", min_value=0.0, max_value=100.0, step=1.0,
                value=st.session_state.obj_plano, key="edit_plano"
            )
            st.session_state.obj_formador = st.number_input(
                "👨‍🏫 Avaliação dos Formadores (máx 5)", min_value=0.0, max_value=5.0, step=0.1,
                value=st.session_state.obj_formador, key="edit_form"
            )
        with col2:
            st.session_state.obj_substituicao = st.number_input(
                "🔄 Taxa de Substituição de Formadores (%) - máximo", min_value=0.0, max_value=100.0, step=1.0,
                value=st.session_state.obj_substituicao, key="edit_subst"
            )
            st.session_state.obj_multiformador = st.number_input(
                "👥 Ações com mais de um Formador (%) - mínimo", min_value=0.0, max_value=100.0, step=1.0,
                value=st.session_state.obj_multiformador, key="edit_mult"
            )
            st.session_state.obj_reclamacao_curso = st.number_input(
                "📢 Taxa de Reclamações por Curso (%) - máximo", min_value=0.0, max_value=100.0, step=0.5,
                value=st.session_state.obj_reclamacao_curso, key="edit_recl"
            )
            st.session_state.obj_tmrp = st.number_input(
                "⏱️ TMRP (horas) - máximo", min_value=0.0, max_value=200.0, step=1.0,
                value=st.session_state.obj_tmrp, key="edit_tmrp"
            )
            st.session_state.obj_acoes_implementadas = st.number_input(
                "✅ Ações de Melhoria Implementadas (%) - mínimo", min_value=0.0, max_value=100.0, step=1.0,
                value=st.session_state.obj_acoes_implementadas, key="edit_acoes"
            )
            st.session_state.obj_recorrencia = st.number_input(
                "⚠️ Recorrência de Problemas (%) - máximo", min_value=0.0, max_value=100.0, step=1.0,
                value=st.session_state.obj_recorrencia, key="edit_rec"
            )
            st.session_state.obj_conformidade = st.number_input(
                "📄 Conformidade Documental (%) - mínimo", min_value=0.0, max_value=100.0, step=1.0,
                value=st.session_state.obj_conformidade, key="edit_conf"
            )
        st.info("💡 As alterações são aplicadas imediatamente. Os objetivos são guardados durante a sessão.")

    # ------------------------------------------------------------
    # Cálculo dos KPIs principais (com as novas fórmulas)
    # ------------------------------------------------------------
    if has_cursos:
        total_inscritos = df_cursos["Inscritos"].sum() if "Inscritos" in df_cursos.columns else 0
        total_aptos = df_cursos["Aptos"].sum() if "Aptos" in df_cursos.columns else 0
        total_inaptos = df_cursos["Inaptos"].sum() if "Inaptos" in df_cursos.columns else 0
        
        # Taxa de Conclusão = ((Aptos + Inaptos) / Inscritos) * 100
        total_aptos_inaptos = total_aptos + total_inaptos
        taxa_conclusao = (total_aptos_inaptos / total_inscritos * 100) if total_inscritos > 0 else 0

        # Taxa de Aprovação = (Aptos / (Aptos + Inaptos)) * 100
        taxa_aprovacao = (total_aptos / total_aptos_inaptos * 100) if total_aptos_inaptos > 0 else 0

        # Cumprimento do Plano = (Finalizados / Previstas) * 100
        if "Status" in df_cursos.columns:
            status_norm = df_cursos["Status"].astype(str).str.strip().str.lower()
            total_finalizadas = (status_norm == "finalizado").sum()
            total_previstas = (status_norm == "prevista").sum()
            cumprimento_plano = (total_finalizadas / total_previstas * 100) if total_previstas > 0 else 0
        else:
            cumprimento_plano = None

        # ➕ ADICIONAR ESTAS LINHAS A SEGUIR:
        # Se já existe o cálculo real (LD+VSP), usar esse valor no card
        if st.session_state.get("cumprimento_plano_calculado") is not None:
            cumprimento_plano = st.session_state.cumprimento_plano_calculado

        # Satisfação dos formandos (média da Taxa de satisfação Final)
        if "Taxa de satisfação Final" in df_cursos.columns:
            media_satisfacao_cursos = df_cursos["Taxa de satisfação Final"].mean()
        else:
            media_satisfacao_cursos = None

        # Avaliação dos formadores
        if "Avaliação formador" in df_cursos.columns:
            media_avaliacao_formador = df_cursos["Avaliação formador"].mean()
        else:
            media_avaliacao_formador = None
    else:
        total_inscritos = total_aptos = total_inaptos = 0
        taxa_conclusao = taxa_aprovacao = 0
        cumprimento_plano = None
        media_satisfacao_cursos = None
        media_avaliacao_formador = None

    # Se existirem questionários, usar a média da coluna "Média" (prioridade para satisfação)
    if has_quest and "Média" in df_quest.columns:
        media_satisfacao = df_quest["Média"].mean()
        if "Respondente" in df_quest.columns:
            df_formador_quest = df_quest[df_quest["Respondente"].str.contains("Formador", na=False)]
            media_formador_quest = df_formador_quest["Média"].mean() if not df_formador_quest.empty else None
        else:
            media_formador_quest = None
    else:
        media_satisfacao = media_satisfacao_cursos
        media_formador_quest = media_avaliacao_formador

    satisfacao_valor = media_satisfacao if media_satisfacao is not None else 0
    avaliacao_formador_valor = media_formador_quest if media_formador_quest is not None else 0

    # ------------------------------------------------------------
    # CSS personalizado para os cards (inalterado)
    # ------------------------------------------------------------
    st.markdown("""
    <style>
    .kpi-card {
        background-color: var(--secondary-background-color);
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 10px;
        transition: all 0.2s ease;
        border: 1px solid var(--border-color);
        height: 100%;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    .kpi-title {
        font-size: 14px;
        color: var(--text-color);
        opacity: 0.7;
        margin-bottom: 5px;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 5px;
        color: var(--text-color);
    }
    .kpi-meta {
        font-size: 12px;
        color: var(--text-color);
        opacity: 0.6;
    }
    </style>
    """, unsafe_allow_html=True)

    st.subheader("📊 KPI's Essenciais")

    # Estado para controlar qual detalhe está aberto (None = nenhum)
    if 'detalhe_ativo' not in st.session_state:
        st.session_state.detalhe_ativo = None

    def set_detalhe(kpi):
        if st.session_state.detalhe_ativo == kpi:
            st.session_state.detalhe_ativo = None
        else:
            st.session_state.detalhe_ativo = kpi

    col1, col2, col3 = st.columns(3)
    col4, col5 = st.columns(2)

    with col1:
        delta_sat = satisfacao_valor - st.session_state.obj_satisfacao
        delta_color = "▲" if delta_sat >= 0 else "▼"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">🎓 Satisfação dos Formandos</div>
            <div class="kpi-value">{satisfacao_valor:.2f} / 5</div>
            <div class="kpi-meta">Objetivo: ≥ {st.session_state.obj_satisfacao} | {delta_color} {abs(delta_sat):.2f}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔍 Ver detalhes", key="btn_sat", use_container_width=True):
            set_detalhe('sat')

    with col2:
        delta_conc = taxa_conclusao - st.session_state.obj_conclusao
        delta_color = "▲" if delta_conc >= 0 else "▼"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">✅ Taxa de Conclusão</div>
            <div class="kpi-value">{taxa_conclusao:.1f}%</div>
            <div class="kpi-meta">Objetivo: ≥ {st.session_state.obj_conclusao}% | {delta_color} {abs(delta_conc):.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔍 Ver detalhes", key="btn_conc", use_container_width=True):
            set_detalhe('conc')

    with col3:
        delta_aprov = taxa_aprovacao - st.session_state.obj_aprovacao
        delta_color = "▲" if delta_aprov >= 0 else "▼"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">📝 Taxa de Aprovação</div>
            <div class="kpi-value">{taxa_aprovacao:.1f}%</div>
            <div class="kpi-meta">Objetivo: ≥ {st.session_state.obj_aprovacao:.0f}% | {delta_color} {abs(delta_aprov):.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔍 Ver detalhes", key="btn_aprov", use_container_width=True):
            set_detalhe('aprov')

    with col4:
        if cumprimento_plano is not None:
            delta_plano = cumprimento_plano - st.session_state.obj_plano
            delta_color = "▲" if delta_plano >= 0 else "▼"
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">📅 Cumprimento do Plano</div>
                <div class="kpi-value">{cumprimento_plano:.1f}%</div>
                <div class="kpi-meta">Objetivo: ≥ {st.session_state.obj_plano}% | {delta_color} {abs(delta_plano):.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">📅 Cumprimento do Plano</div>
                <div class="kpi-value">N/D</div>
                <div class="kpi-meta">⚠️ Coluna "Status" sem 'Prevista'/'Finalizado'</div>
            </div>
            """, unsafe_allow_html=True)

        if st.button("🔍 Ver detalhes", key="btn_plano", use_container_width=True):
            set_detalhe('plano')

    with col5:
        if avaliacao_formador_valor > 0:
            delta_avf = avaliacao_formador_valor - st.session_state.obj_formador
            delta_color = "▲" if delta_avf >= 0 else "▼"
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">👨‍🏫 Avaliação dos Formadores</div>
                <div class="kpi-value">{avaliacao_formador_valor:.2f} / 5</div>
                <div class="kpi-meta">Objetivo: ≥ {st.session_state.obj_formador} | {delta_color} {abs(delta_avf):.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">👨‍🏫 Avaliação dos Formadores</div>
                <div class="kpi-value">N/D</div>
                <div class="kpi-meta">⚠️ Sem dados</div>
            </div>
            """, unsafe_allow_html=True)
        if st.button("🔍 Ver detalhes", key="btn_avf", use_container_width=True):
            set_detalhe('avf')

    #NOVO: calcular cumprimento do plano em background sempre que o ficheiro está disponível
    if st.session_state.get("projecao_uploaded") and has_cursos:
        try:
            df_ld_bg = st.session_state.get("df_projecao_ld")
            df_vsp_bg = st.session_state.get("df_projecao_vsp")

            if df_ld_bg is not None and df_vsp_bg is not None:
                df_comb_bg = combinar_projecao(df_ld_bg, df_vsp_bg)
                total_previstas_bg = df_comb_bg['Nº Ações Previstas'].sum()

                if "Status" in df_cursos.columns and "Ação" in df_cursos.columns:
                    codigos_bg = set(df_comb_bg['Código curso'].astype(str).str.strip().unique())
                    df_tmp = df_cursos.copy()
                    df_tmp['Status'] = df_tmp['Status'].astype(str).str.strip().str.lower()
                    df_fin = df_tmp[df_tmp['Status'].str.contains('finaliz|conclu', na=False, regex=True)]

                    if not df_fin.empty:
                        def extrair_cod_bg(s):
                            s = str(s).strip()
                            if s in codigos_bg:
                                return s
                            for c in sorted(codigos_bg, key=len, reverse=True):
                                if s.startswith(c):
                                    return c
                            return s
                        df_fin = df_fin.copy()
                        df_fin['Código curso'] = df_fin['Ação'].apply(extrair_cod_bg)
                        acoes_unicas_bg = df_fin.drop_duplicates(subset=['Ação'])
                        acoes_com_match_bg = acoes_unicas_bg[acoes_unicas_bg['Código curso'].isin(codigos_bg)]
                        total_fin_bg = len(acoes_com_match_bg)
                    else:
                        total_fin_bg = 0

                    cumpr_bg = (total_fin_bg / total_previstas_bg * 100) if total_previstas_bg > 0 else 0
                    st.session_state.cumprimento_plano_calculado = cumpr_bg
                    cumprimento_plano = cumpr_bg
        except Exception:
            pass

    # ---------- ÁREAS DE DETALHE (mantidas inalteradas, mas com referência ao novo df_cursos) ----------
    if st.session_state.detalhe_ativo == 'plano':
        with st.expander("📊 Detalhe do Cumprimento do Plano", expanded=True):
            planos_previstos_total = 0
            planos_finalizados = 0
            cumprimento_calculado = 0
            df_combinado = None

            df_ld_det = st.session_state.get("df_projecao_ld")
            df_vsp_det = st.session_state.get("df_projecao_vsp")

            if df_ld_det is not None and df_vsp_det is not None:
                try:
                    info_proj = st.session_state.get("info_projecao", {})
                    st.success(
                        f"✅ Projecao {info_proj.get('ano', '')} em uso "
                        f"(LD: '{info_proj.get('folha_ld')}' | VSP: '{info_proj.get('folha_vsp')}')"
                    )

                    df_combinado = combinar_projecao(df_ld_det, df_vsp_det)
                    df_combinado['Centro_Norm'] = df_combinado['Centro'].apply(normalizar_centro)
                    planos_previstos_total = df_combinado['Nº Ações Previstas'].sum()

                    # ---- CALCULAR ACOES FINALIZADAS (logica original, intacta) ----
                    if has_cursos and "Status" in df_cursos.columns and "Ação" in df_cursos.columns:
                        df_cursos_temp = df_cursos.copy()
                        df_cursos_temp['Status'] = df_cursos_temp['Status'].astype(str).str.strip().str.lower()
                        codigos_combinado = set(df_combinado['Código curso'].astype(str).str.strip().unique())

                        def extrair_codigo(acao_str):
                            acao_str = str(acao_str).strip()
                            if acao_str in codigos_combinado:
                                return acao_str
                            for codigo in sorted(codigos_combinado, key=len, reverse=True):
                                if acao_str.startswith(codigo):
                                    return codigo
                            return acao_str

                        df_cursos_temp['Código curso'] = df_cursos_temp['Ação'].apply(extrair_codigo)
                        df_finalizadas = df_cursos_temp[
                            df_cursos_temp['Status'].str.contains('finaliz|conclu', na=False, regex=True)
                        ].copy()

                        if not df_finalizadas.empty:
                            acoes_unicas = df_finalizadas.drop_duplicates(subset=['Ação'])[['Ação', 'Código curso', 'Centro']].copy()
                            acoes_unicas['Centro_Norm'] = acoes_unicas['Centro'].apply(normalizar_centro)
                            st.write(f"**Total de acoes unicas finalizadas:** {len(acoes_unicas)}")
                            codigos_projecao = set(df_combinado['Código curso'].unique())
                            acoes_unicas['Tem_Match'] = acoes_unicas['Código curso'].isin(codigos_projecao)
                            acoes_com_match = acoes_unicas[acoes_unicas['Tem_Match']].copy()
                            acoes_sem_match = acoes_unicas[~acoes_unicas['Tem_Match']].copy()
                            st.write(f"**COM match:** {len(acoes_com_match)} | **SEM match:** {len(acoes_sem_match)}")
                            if not acoes_sem_match.empty:
                                st.warning(f"⚠️ {len(acoes_sem_match)} acoes SEM match na projecao:")
                                st.dataframe(acoes_sem_match[['Ação', 'Código curso', 'Centro']].head(20))
                            finalizadas_por_centro_curso = (
                                acoes_com_match
                                .drop_duplicates(subset=['Ação'])
                                .groupby(['Centro_Norm', 'Código curso'], as_index=False)
                                .size()
                                .rename(columns={'size': 'Nº Finalizadas'})
                            )
                            st.write(f"**Total apos groupby:** {finalizadas_por_centro_curso['Nº Finalizadas'].sum()}")
                        else:
                            finalizadas_por_centro_curso = pd.DataFrame(columns=['Centro_Norm', 'Código curso', 'Nº Finalizadas'])
                            st.warning("⚠️ Nenhuma acao finalizada encontrada!")

                        if 'Nº Finalizadas' in df_combinado.columns:
                            df_combinado = df_combinado.drop(columns=['Nº Finalizadas'])
                        df_combinado = df_combinado.merge(
                            finalizadas_por_centro_curso, on=['Centro_Norm', 'Código curso'], how='left'
                        )
                        df_combinado['Nº Finalizadas'] = df_combinado['Nº Finalizadas'].fillna(0).astype(int)
                        df_combinado['% Cumprimento'] = (
                            df_combinado['Nº Finalizadas'] / df_combinado['Nº Ações Previstas'] * 100
                        ).fillna(0).clip(upper=100)
                        planos_finalizados = int(finalizadas_por_centro_curso['Nº Finalizadas'].sum())
                        cumprimento_calculado = (planos_finalizados / planos_previstos_total * 100) if planos_previstos_total > 0 else 0
                        st.session_state.cumprimento_plano_calculado = cumprimento_calculado
                    else:
                        st.warning("⚠️ Nao foi possivel calcular acoes finalizadas: faltam dados de cursos")

                    # ---- MOSTRAR RESULTADOS ----
                    st.markdown("---")
                    st.subheader("📊 Resultados do Calculo (LD + VSP Combinado)")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("📋 Acoes Previstas (LD)", f"{df_combinado['Nº Ações LD'].sum():.0f}")
                    with col2:
                        st.metric("📋 Acoes Previstas (VSP)", f"{df_combinado['Nº Ações VSP'].sum():.0f}")
                    with col3:
                        st.metric("📋 Total Previstas", f"{planos_previstos_total:.0f}")
                    with col4:
                        st.metric("✅ Acoes Finalizadas", f"{planos_finalizados:.0f}")

                    col5, col6 = st.columns(2)
                    with col5:
                        delta = cumprimento_calculado - st.session_state.obj_plano
                        delta_color = "🟢" if delta >= 0 else "🔴"
                        st.metric("📊 Cumprimento do Plano", f"{cumprimento_calculado:.1f}%",
                                  delta=f"{delta_color} {delta:.1f}%")
                    with col6:
                        st.progress(min(cumprimento_calculado / 100, 1.0))

                    if df_combinado is not None and not df_combinado.empty:
                        with st.expander("📋 Ver detalhes da Projecao Combinada", expanded=True):
                            colunas_para_mostrar = ['Centro', 'Código curso', 'Nº Ações LD', 'Nº Ações VSP',
                                                    'Nº Ações Previstas', 'Nº Finalizadas', '% Cumprimento']
                            colunas_existentes = [c for c in colunas_para_mostrar if c in df_combinado.columns]
                            df_show = df_combinado[colunas_existentes].copy()
                            if '% Cumprimento' in df_show.columns:
                                df_show = df_show.sort_values('% Cumprimento', ascending=False)

                                def highlight_cumprimento(val):
                                    if val >= 100:
                                        return 'background-color: #d4edda; color: #155724;'
                                    elif val >= 50:
                                        return 'background-color: #fff3cd; color: #856404;'
                                    else:
                                        return 'background-color: #f8d7da; color: #721c24;'
                                styled_df = df_show.style.map(highlight_cumprimento, subset=['% Cumprimento'])
                                st.dataframe(styled_df, use_container_width=True)
                            else:
                                st.dataframe(df_show, use_container_width=True)

                            # ===== Snapshot para reforecast (1º sem -> 2º sem) =====
                            data_snapshot = st.date_input(
                                "Data do retrato (corte do 1º semestre)",
                                value=date.today(),
                                key="data_snapshot_reforecast"
                            )

                            df_export = df_combinado[
                                ['Centro', 'Código curso', 'Nº Ações Previstas', 'Nº Finalizadas']
                            ].rename(columns={
                                'Nº Ações Previstas': 'Previstas',
                                'Nº Finalizadas': 'Finalizadas',
                            }).copy()
                            df_export['Data Retrato'] = data_snapshot.strftime("%Y-%m-%d")

                            buffer = BytesIO()
                            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                                df_export.to_excel(writer, index=False, sheet_name="Snapshot 1Sem")
                            buffer.seek(0)

                            st.download_button(
                                label="📥 Exportar snapshot para reforecast",
                                data=buffer,
                                file_name=f"reforecast_{data_snapshot.strftime('%Y-%m-%d')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                            )
                            # ========================================================

                            col_f1, col_f2 = st.columns(2)
                            with col_f1:
                                centros_sel = st.multiselect("Centro", options=sorted(df_show['Centro'].unique()), key="proj_centro")
                            with col_f2:
                                cursos_sel = st.multiselect("Curso", options=sorted(df_show['Código curso'].unique()), key="proj_curso")
                            df_filt = df_show.copy()
                            if centros_sel:
                                df_filt = df_filt[df_filt['Centro'].isin(centros_sel)]
                            if cursos_sel:
                                df_filt = df_filt[df_filt['Código curso'].isin(cursos_sel)]
                            if centros_sel or cursos_sel:
                                st.dataframe(df_filt, use_container_width=True)
                                tp = df_filt['Nº Ações Previstas'].sum()
                                tf = df_filt['Nº Finalizadas'].sum() if 'Nº Finalizadas' in df_filt.columns else 0
                                tx = (tf / tp * 100) if tp > 0 else 0
                                st.caption(f"📊 Filtrado: {tp:.0f} previstas, {tf:.0f} finalizadas, taxa: {tx:.1f}%")

                except Exception as e:
                    st.error(f"Erro ao processar dados: {e}")
                    import traceback
                    st.code(traceback.format_exc())
            else:
                st.info("⬆️ Carregue o ficheiro da projecao do ano atual para ver os detalhes.")
                if has_cursos and "Status" in df_cursos.columns:
                    status_tmp = df_cursos['Status'].astype(str).str.strip().str.lower()
                    fin_fb = status_tmp.str.contains('finaliz|conclu', regex=True).sum()
                    prev_fb = (status_tmp == 'prevista').sum()
                    cumpr_fb = (fin_fb / prev_fb * 100) if prev_fb > 0 else 0
                    st.info(f"📊 Metodo alternativo (sem ficheiro): {cumpr_fb:.1f}%")

            # --- RESUMO FINAL ---
            st.markdown("---")
            st.subheader("📊 Resumo do KPI - Cumprimento do Plano")
            finalizadas_show = st.session_state.get("planos_finalizados_calculado", planos_finalizados)
            previstas_show = st.session_state.get("planos_previstos_calculado", planos_previstos_total)
            cumprimento_show = st.session_state.get("cumprimento_plano_calculado", cumprimento_calculado)
            col_sum1, col_sum2 = st.columns(2)
            with col_sum1:
                st.metric("Acoes Finalizadas (Real)", f"{finalizadas_show:.0f}")
            with col_sum2:
                st.metric("Acoes Previstas (Projecao)", f"{previstas_show:.0f}")
            st.progress(min(cumprimento_show / 100, 1.0))
            st.caption(f"📈 Cumprimento: {cumprimento_show:.1f}% (Meta: {st.session_state.obj_plano:.0f}%)")
            st.session_state.planos_finalizados_calculado = planos_finalizados
            st.session_state.planos_previstos_calculado = planos_previstos_total

    if st.session_state.detalhe_ativo == 'avf':
        with st.expander("📊 Detalhe da Avaliação dos Formadores", expanded=True):
            if has_quest and "Média" in df_quest.columns and "Respondente" in df_quest.columns:
                df_avf = df_quest[df_quest['Respondente'].str.contains("Formador", na=False)][['Ação', 'Centro', 'Categoria', 'Média']].copy()
                if not df_avf.empty:
                    df_avf['Média'] = pd.to_numeric(df_avf['Média'], errors='coerce')
                    meta_avf = st.session_state.obj_formador
                    def highlight_by_goal(val, meta):
                        if pd.notna(val):
                            if val < meta:
                                return 'background-color: #fce8ea; border-left: 4px solid #dc3545;'
                            else:
                                return 'background-color: #d4edda; border-left: 4px solid #28a745;'
                        return ''
                    styled_avf = df_avf.style.map(lambda x: highlight_by_goal(x, meta_avf), subset=['Média'])
                    st.dataframe(styled_avf, use_container_width=True)
                    st.markdown("**Filtros:**")
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        centros = st.multiselect("Centro", options=sorted(df_avf['Centro'].unique()), key="avf_centro_quest")
                    with col_f2:
                        categorias = st.multiselect("Categoria", options=sorted(df_avf['Categoria'].unique()), key="avf_cat")
                    df_filt = df_avf.copy()
                    if centros:
                        df_filt = df_filt[df_filt['Centro'].isin(centros)]
                    if categorias:
                        df_filt = df_filt[df_filt['Categoria'].isin(categorias)]
                    styled_filt = df_filt.style.map(lambda x: highlight_by_goal(x, meta_avf), subset=['Média'])
                    st.dataframe(styled_filt, use_container_width=True)
                    st.caption(f"Média global: {df_filt['Média'].mean():.2f} | Total respostas: {len(df_filt)}")
                else:
                    st.info("Nenhuma avaliação de formador encontrada nos questionários.")
            elif has_cursos and "Avaliação formador" in df_cursos.columns:
                df_avf_cursos = df_cursos[['Ação', 'Centro', 'Formador', 'Avaliação formador']].dropna(subset=['Avaliação formador'])
                df_avf_cursos['Avaliação formador'] = pd.to_numeric(df_avf_cursos['Avaliação formador'], errors='coerce')
                df_avf_cursos = df_avf_cursos.dropna(subset=['Avaliação formador'])
                meta_avf = st.session_state.obj_formador
                def highlight_by_goal(val, meta):
                    if pd.notna(val):
                        if val < meta:
                            return 'background-color: #fce8ea; border-left: 4px solid #dc3545;'
                        else:
                            return 'background-color: #d4edda; border-left: 4px solid #28a745;'
                    return ''
                styled_cursos = df_avf_cursos.style.map(lambda x: highlight_by_goal(x, meta_avf), subset=['Avaliação formador'])
                st.dataframe(styled_cursos, use_container_width=True)
                st.markdown("**Filtros:**")
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    centros = st.multiselect("Centro", options=sorted(df_avf_cursos['Centro'].unique()), key="avf_cursos_centro")
                with col_f2:
                    acoes = st.multiselect("Ação", options=sorted(df_avf_cursos['Ação'].unique()), key="avf_cursos_acao")
                with col_f3:
                    formadores = st.multiselect("Formador", options=sorted(df_avf_cursos['Formador'].unique()), key="avf_cursos_formador")
                df_filt_cursos = df_avf_cursos.copy()
                if centros:
                    df_filt_cursos = df_filt_cursos[df_filt_cursos['Centro'].isin(centros)]
                if acoes:
                    df_filt_cursos = df_filt_cursos[df_filt_cursos['Ação'].isin(acoes)]
                if formadores:
                    df_filt_cursos = df_filt_cursos[df_filt_cursos['Formador'].isin(formadores)]
                styled_filt_cursos = df_filt_cursos.style.map(lambda x: highlight_by_goal(x, meta_avf), subset=['Avaliação formador'])
                st.dataframe(styled_filt_cursos, use_container_width=True)
                st.caption(f"Média: {df_filt_cursos['Avaliação formador'].mean():.2f} | Total registos: {len(df_filt_cursos)}")
            else:
                st.warning("Sem dados de avaliação de formadores.")

    # ------------------------------------------------------------
    # KPI 4 – Ações com mais de um formador (compatível com nova estrutura)
    # ------------------------------------------------------------
    if has_cursos and "Formador" in df_cursos.columns:
        def contar_formadores(valor):
            if pd.isna(valor):
                return 0
            valor_str = str(valor)
            for sep in [',', ';', '/', ' e ']:
                if sep in valor_str:
                    return len([n.strip() for n in re.split(r'[,;/]| e ', valor_str) if n.strip()])
            return 1 if valor_str.strip() else 0

        df_cursos['num_formadores'] = df_cursos['Formador'].apply(contar_formadores)
        total_acoes = len(df_cursos)
        acoes_multiformador = (df_cursos['num_formadores'] > 1).sum()
        perc_multiformador = (acoes_multiformador / total_acoes * 100) if total_acoes > 0 else 0
        meta_multiformador = st.session_state.obj_multiformador
        delta_multiformador = perc_multiformador - meta_multiformador
        delta_color = "▲" if delta_multiformador >= 0 else "▼"

        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">👥 Ações com mais de um Formador</div>
            <div class="kpi-value">{acoes_multiformador} / {total_acoes}</div>
            <div class="kpi-meta">{perc_multiformador:.1f}% das ações | Meta: ≥ {meta_multiformador}% | {delta_color} {abs(delta_multiformador):.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Carregue um ficheiro de cursos com a coluna 'Formador' para ver ações com múltiplos formadores.")

    # ------------------------------------------------------------
    # KPI 5 – Taxa de Substituição de Formadores (com edição)
    # ------------------------------------------------------------
    st.markdown("---")
    st.subheader("👥 Substituição de Formadores")

    if has_cursos and "Formador" in df_cursos.columns and "Ação" in df_cursos.columns:
        def normalizar_string(texto):
            if pd.isna(texto):
                return ""
            texto = str(texto).strip().lower()
            texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
            return texto

        # Guardar snapshot original na primeira execução
        if "formadores_originais" not in st.session_state:
            originais = df_cursos[["Ação", "Formador"]].copy()
            originais["Formador_Norm"] = originais["Formador"].apply(normalizar_string)
            st.session_state.formadores_originais = originais
            st.session_state.formadores_originais_exibicao = df_cursos[["Ação", "Formador"]].copy()

        # Preparar DataFrame para edição
        df_edit_formadores = df_cursos[["Ação", "Formador"]].copy()
        df_edit_formadores.columns = ["ID Ação", "Formador Atual"]

        # 🔧 CORREÇÃO: converter colunas para string (evita erro de tipo float vs TextColumn)
        df_edit_formadores["Formador Atual"] = df_edit_formadores["Formador Atual"].astype(str)

        original_map = st.session_state.formadores_originais_exibicao.set_index("Ação")["Formador"].to_dict()
        df_edit_formadores["Formador Original"] = df_edit_formadores["ID Ação"].map(original_map)
        df_edit_formadores["Formador Original"] = df_edit_formadores["Formador Original"].astype(str)

        df_edit_formadores = df_edit_formadores[["ID Ação", "Formador Original", "Formador Atual"]]

        st.info("✏️ Edite o campo 'Formador Atual' para simular uma substituição. O KPI será atualizado automaticamente.")

        edited_formadores = st.data_editor(
            df_edit_formadores,
            use_container_width=True,
            column_config={
                "ID Ação": st.column_config.TextColumn("ID Ação", disabled=True),
                "Formador Original": st.column_config.TextColumn("Formador Original", disabled=True),
                "Formador Atual": st.column_config.TextColumn("Formador Atual"),
            },
            key="formadores_editor"
        )

        col_btn1, col_btn2 = st.columns([1, 5])
        with col_btn1:
            if st.button("💾 Guardar alterações de formadores", key="save_formadores"):
                for idx, row in edited_formadores.iterrows():
                    acao = row["ID Ação"]
                    novo_formador = row["Formador Atual"]
                    mask = df_cursos["Ação"] == acao
                    if mask.any():
                        df_cursos.loc[mask, "Formador"] = novo_formador
                st.session_state.acoes_df = df_cursos   # guarda no state atualizado
                st.success("✅ Formadores atualizados! A página vai recarregar.")
                st.rerun()

        # Calcular substituições usando normalização
        original_norm_map = st.session_state.formadores_originais.set_index("Ação")["Formador_Norm"].to_dict()
        substituicoes = 0
        total = len(edited_formadores)
        for idx, row in edited_formadores.iterrows():
            acao = row["ID Ação"]
            atual = row["Formador Atual"]
            atual_norm = normalizar_string(atual)
            original_norm = original_norm_map.get(acao, "")
            if atual_norm != original_norm:
                substituicoes += 1

        taxa_substituicao = (substituicoes / total * 100) if total > 0 else 0
        meta_subst = st.session_state.obj_substituicao
        delta_subst = taxa_substituicao - meta_subst
        delta_str = f"▲ {delta_subst:.1f}%" if delta_subst > 0 else f"▼ {abs(delta_subst):.1f}%"

        col_kpi1, col_kpi2 = st.columns(2)
        with col_kpi1:
            st.metric(
                label="🔄 Taxa de Substituição de Formadores",
                value=f"{taxa_substituicao:.1f}%",
                delta=delta_str,
                help=f"Percentagem de cursos onde o formador atual é diferente do original. Objetivo: ≤ {meta_subst}%"
            )
        with col_kpi2:
            st.metric(
                label="📊 Cursos com substituição",
                value=f"{substituicoes} / {total}",
                help="Número de cursos onde o formador foi trocado"
            )

        if st.button("🔄 Redefinir formadores originais (basear nos atuais)"):
            novos_originais = df_cursos[["Ação", "Formador"]].copy()
            novos_originais["Formador_Norm"] = novos_originais["Formador"].apply(normalizar_string)
            st.session_state.formadores_originais = novos_originais
            st.session_state.formadores_originais_exibicao = df_cursos[["Ação", "Formador"]].copy()
            st.success("Base de comparação redefinida. A taxa de substituição voltará a 0%.")
            st.rerun()
    else:
        st.info("Carregue um ficheiro de cursos com as colunas 'Ação' e 'Formador' para calcular a taxa de substituição.")

    # ------------------------------------------------------------
    # KPI 6 e 7 – Incidentes Operacionais e TMRP (inalterado)
    # ------------------------------------------------------------
    st.markdown("---")
    st.subheader("⚠️ Incidentes Operacionais e Resolução")

    if "incidentes_df" not in st.session_state:
        st.session_state.incidentes_df = None
    if "incidentes_filename" not in st.session_state:
        st.session_state.incidentes_filename = None

    if st.session_state.incidentes_df is not None:
        st.success(f"📁 Ficheiro carregado: **{st.session_state.incidentes_filename}**")
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("🔄 Carregar novo ficheiro", key="reset_incidentes"):
                st.session_state.incidentes_df = None
                st.session_state.incidentes_filename = None
                st.rerun()
        df_inc = st.session_state.incidentes_df.copy()
    else:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            modo_carga_inc = st.radio("Modo:", ["Substituir", "Adicionar"], horizontal=True, key="modo_carga_inc")
        with c2:
            incidente_file = st.file_uploader(
                "Carregar ficheiro de Incidentes (Excel)",
                type=["xlsx", "xls"], key="incidentes_upload"
            )
        with c3:
            try:
                with open("assets/Incidentes.xlsx", "rb") as f:
                    conteudo_inc = f.read()
                st.download_button(
                    label="📥 Exemplo Incidentes (Excel)",
                    data=conteudo_inc,
                    file_name="Incidentes.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except FileNotFoundError:
                st.error("⚠️ Ficheiro de exemplo não encontrado: assets/Incidentes.xlsx")
        if incidente_file is not None:
            try:
                df_inc = pd.read_excel(incidente_file)
                df_inc.columns = df_inc.columns.str.strip()
                required = ['Ação', 'Centro', 'Descrição', 'Status', 'Data_Abertura']
                missing = [c for c in required if c not in df_inc.columns]
                if missing:
                    st.error(f"Colunas obrigatórias em falta: {missing}")
                    df_inc = None
                else:
                    st.session_state.incidentes_df = df_inc.copy()
                    st.session_state.incidentes_filename = incidente_file.name
                    st.rerun()
            except Exception as e:
                st.error(f"Erro ao processar ficheiro: {e}")
                df_inc = None
        else:
            df_inc = None

    if df_inc is not None:
        try:
            df_inc['Data_Abertura'] = pd.to_datetime(df_inc['Data_Abertura'], errors='coerce')
            if 'Data_Resolução' in df_inc.columns:
                df_inc['Data_Resolução'] = pd.to_datetime(df_inc['Data_Resolução'], errors='coerce')
            else:
                df_inc['Data_Resolução'] = pd.NaT

            status_map = {
                'aberto': 'Aberto',
                'em resolução': 'Em resolução',
                'resolvido': 'Resolvido',
                'aprovado': 'Resolvido',
                '': 'Aberto',
                None: 'Aberto'
            }
            df_inc['Status'] = df_inc['Status'].astype(str).str.lower().map(status_map).fillna('Desconhecido')

            mask_resolvido = (df_inc['Status'] == 'Resolvido') & df_inc['Data_Abertura'].notna() & df_inc['Data_Resolução'].notna()
            df_inc['TMRP_horas'] = None
            df_inc.loc[mask_resolvido, 'TMRP_horas'] = (
                (df_inc.loc[mask_resolvido, 'Data_Resolução'] - df_inc.loc[mask_resolvido, 'Data_Abertura'])
                .dt.total_seconds() / 3600
            )

            if hasattr(st.session_state, 'filtro_centro') and st.session_state.filtro_centro and 'Centro' in df_inc.columns:
                df_inc = df_inc[df_inc['Centro'].isin(st.session_state.filtro_centro)]

            if not df_inc.empty:
                total_incidentes = len(df_inc)
                st.metric("📌 Nº Total de Incidentes Operacionais", total_incidentes)

                if not df_inc['Data_Abertura'].isna().all():
                    df_inc['AnoMes'] = df_inc['Data_Abertura'].dt.to_period('M')
                    incidentes_mensal = df_inc.groupby('AnoMes').size().reset_index(name='Quantidade')
                    incidentes_mensal['AnoMes'] = incidentes_mensal['AnoMes'].astype(str)
                    fig_mensal = px.line(
                        incidentes_mensal, x='AnoMes', y='Quantidade', markers=True,
                        title="Evolução Mensal do Número de Incidentes (abertura)",
                        labels={'AnoMes': 'Mês', 'Quantidade': 'Nº Incidentes'}
                    )
                    st.plotly_chart(fig_mensal, use_container_width=True)
                else:
                    st.info("Sem datas de abertura válidas para evolução mensal.")

                df_resolvidos = df_inc[df_inc['Status'] == 'Resolvido']
                tmrp_medio = df_resolvidos['TMRP_horas'].mean() if not df_resolvidos.empty else None
                meta_tmrp = st.session_state.obj_tmrp
                if tmrp_medio is not None:
                    delta_tmrp = tmrp_medio - meta_tmrp
                    delta_str = f"▲ {delta_tmrp:.0f}h" if delta_tmrp > 0 else f"▼ {abs(delta_tmrp):.0f}h"
                    st.metric(
                        label="⏱️ Tempo Médio de Resolução (TMRP)",
                        value=f"{tmrp_medio:.1f} h",
                        delta=delta_str,
                        help="Média do tempo entre abertura e resolução (apenas incidentes resolvidos). Objetivo: ≤ 48h"
                    )
                else:
                    st.metric(label="⏱️ Tempo Médio de Resolução (TMRP)", value="Sem incidentes resolvidos")

                st.subheader("📊 Distribuição por Estado")
                status_counts = df_inc['Status'].value_counts().reindex(['Aberto', 'Em resolução', 'Resolvido'], fill_value=0)
                col_s1, col_s2, col_s3 = st.columns(3)
                with col_s1:
                    st.metric("🟡 Aberto", status_counts.get('Aberto', 0))
                with col_s2:
                    st.metric("🟠 Em resolução", status_counts.get('Em resolução', 0))
                with col_s3:
                    st.metric("🟢 Resolvido", status_counts.get('Resolvido', 0))

                fig_status = px.bar(
                    x=status_counts.index, y=status_counts.values,
                    labels={'x': 'Estado', 'y': 'Nº Incidentes'},
                    title="Incidentes por Estado", text_auto=True,
                    color=status_counts.index,
                    color_discrete_map={'Aberto':'orange', 'Em resolução':'gold', 'Resolvido':'green'}
                )
                st.plotly_chart(fig_status, use_container_width=True)

                if 'Centro' in df_inc.columns:
                    st.subheader("🏢 Desempenho por Centro")
                    centro_status = df_inc.groupby(['Centro', 'Status']).size().unstack(fill_value=0)
                    for estado in ['Aberto', 'Em resolução', 'Resolvido']:
                        if estado not in centro_status.columns:
                            centro_status[estado] = 0

                    df_resolvidos_centro = df_resolvidos.copy()
                    if not df_resolvidos_centro.empty:
                        df_resolvidos_centro['Dentro_meta'] = df_resolvidos_centro['TMRP_horas'] <= 48
                        dentro_meta = df_resolvidos_centro[df_resolvidos_centro['Dentro_meta']].groupby('Centro').size()
                        fora_meta = df_resolvidos_centro[~df_resolvidos_centro['Dentro_meta']].groupby('Centro').size()
                    else:
                        dentro_meta = pd.Series(dtype=int)
                        fora_meta = pd.Series(dtype=int)

                    tmrp_centro = df_resolvidos.groupby('Centro')['TMRP_horas'].mean().round(1)
                    centros = centro_status.index
                    centro_resumo = pd.DataFrame(index=centros)
                    centro_resumo['Aberto'] = centro_status['Aberto']
                    centro_resumo['Em resolução'] = centro_status['Em resolução']
                    centro_resumo['Resolvido'] = centro_status['Resolvido']
                    centro_resumo['Resolvidos dentro da meta (≤48h)'] = dentro_meta.reindex(centros, fill_value=0)
                    centro_resumo['Resolvidos fora da meta (>48h)'] = fora_meta.reindex(centros, fill_value=0)
                    centro_resumo['TMRP médio (h)'] = tmrp_centro.reindex(centros)
                    centro_resumo = centro_resumo.sort_index()
                    st.dataframe(centro_resumo, use_container_width=True)

                st.subheader("📋 Lista detalhada de Incidentes")
                df_display = df_inc.copy()
                df_display['Tempo (horas)'] = df_display['TMRP_horas'].apply(lambda x: f"{x:.1f} h" if pd.notna(x) else "-")
                df_display['Data Abertura'] = df_display['Data_Abertura'].dt.strftime('%d/%m/%Y')
                df_display['Data Resolução'] = df_display['Data_Resolução'].dt.strftime('%d/%m/%Y')
                cols_show = ['Ação', 'Centro', 'Descrição', 'Status', 'Data Abertura', 'Data Resolução', 'Tempo (horas)']
                df_filtravel = df_display[cols_show].copy()
                st.markdown("**Filtros:**")
                col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                with col_f1:
                    acoes = st.multiselect("Ação", options=sorted(df_filtravel['Ação'].unique()), key="filt_acao")
                with col_f2:
                    centros = st.multiselect("Centro", options=sorted(df_filtravel['Centro'].unique()), key="filt_centro")
                with col_f3:
                    estados = st.multiselect("Estado", options=sorted(df_filtravel['Status'].unique()), key="filt_status")
                with col_f4:
                    busca_desc = st.text_input("🔍 Buscar na Descrição", placeholder="Palavra-chave", key="filt_desc")
                df_filtrado = df_filtravel.copy()
                if acoes:
                    df_filtrado = df_filtrado[df_filtrado['Ação'].isin(acoes)]
                if centros:
                    df_filtrado = df_filtrado[df_filtrado['Centro'].isin(centros)]
                if estados:
                    df_filtrado = df_filtrado[df_filtrado['Status'].isin(estados)]
                if busca_desc:
                    df_filtrado = df_filtrado[df_filtrado['Descrição'].str.contains(busca_desc, case=False, na=False)]
                st.dataframe(df_filtrado, use_container_width=True, height=400)
                st.caption(f"📌 Mostrando {len(df_filtrado)} de {len(df_filtravel)} incidentes.")
                with st.expander("⚠️ Incidentes resolvidos com TMRP > 48h (fora da meta)"):
                    if not df_resolvidos.empty:
                        fora_meta = df_resolvidos[df_resolvidos['TMRP_horas'] > meta_tmrp]
                        if not fora_meta.empty:
                            st.dataframe(fora_meta[['Ação', 'Centro', 'Descrição', 'Data_Abertura', 'Data_Resolução', 'TMRP_horas']],
                                         use_container_width=True)
                        else:
                            st.success("✅ Nenhum incidente resolvido ultrapassou as 48h.")
                    else:
                        st.info("Sem incidentes resolvidos para análise.")
            else:
                st.info("Nenhum incidente após aplicação dos filtros.")
        except Exception as e:
            st.error(f"Erro ao processar incidentes: {e}")
    else:
        st.info("⬆️ Carregue um ficheiro Excel com os dados de incidentes (colunas: Ação, Centro, Descrição, Status, Data_Abertura, Data_Resolução opcional) para visualizar os KPIs 6 e 7.")

    # ------------------------------------------------------------
    # KPI 8 – Taxa de Reclamações (nova estrutura)
    # ------------------------------------------------------------
    st.markdown("---")
    st.subheader("📢 Taxa de Reclamações")

    if "reclamacoes_df" not in st.session_state:
        st.session_state.reclamacoes_df = None
    if "reclamacoes_filename" not in st.session_state:
        st.session_state.reclamacoes_filename = None

    if st.session_state.reclamacoes_df is not None:
        st.success(f"📁 Ficheiro de reclamações carregado: **{st.session_state.reclamacoes_filename}**")
        col_reset1, _ = st.columns([1, 5])
        with col_reset1:
            if st.button("🔄 Trocar ficheiro de reclamações", key="reset_recl"):
                st.session_state.reclamacoes_df = None
                st.session_state.reclamacoes_filename = None
                st.rerun()
        df_recl = st.session_state.reclamacoes_df.copy()
    else:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            modo_carga_recl = st.radio("Modo:", ["Substituir", "Adicionar"], horizontal=True, key="modo_carga_recl")
        with c2:
            recl_file = st.file_uploader("Carregar ficheiro de Reclamações (Excel)", type=["xlsx", "xls"], key="reclamacoes_upload")
        with c3:
            try:
                with open("assets/reclamações.xlsx", "rb") as f:
                    conteudo_recl = f.read()
                st.download_button(label="📥 Exemplo Reclamações (Excel)", data=conteudo_recl,
                                file_name="reclamacoes.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True)
            except FileNotFoundError:
                st.error("⚠️ Ficheiro de exemplo não encontrado: assets/reclamacoes.xlsx")
        if recl_file is not None:
            try:
                # Lê o Excel usando a segunda linha como cabeçalho
                df_recl = pd.read_excel(recl_file, header=0)
                # Normaliza nomes das colunas (minúsculas, sem espaços)
                df_recl.columns = df_recl.columns.str.strip().str.lower()

                # Colunas obrigatórias
                required = ['data', 'centro', 'devolução', 'curso', 'motivo']
                missing = [c for c in required if c not in df_recl.columns]
                if missing:
                    st.error(f"Colunas obrigatórias em falta: {missing}")
                    st.info(f"Colunas encontradas: {list(df_recl.columns)}")
                    df_recl = None
                else:
                    # Renomeia 'curso' e 'centro' para nomes internos
                    df_recl.rename(columns={
                        'curso': 'Ação',
                        'centro': 'Centro'
                    }, inplace=True)
                    
                    # A coluna 'data' será mantida como string (sem conversão)
                    df_recl['data'] = df_recl['data'].astype(str)
                    
                    # ---- NOVA LÓGICA: derivar Status e Valor Devolvido a partir de 'devolução' e 'valor' ----
                    # Normalizar a coluna 'devolução' (minúsculas, sem espaços)
                    df_recl['devolucao_norm'] = df_recl['devolução'].astype(str).str.strip().str.lower()
                    
                    # Definir condição de aceitação: "sim", "s", "yes", "true", "1" são considerados verdadeiros
                    cond_aceite = df_recl['devolucao_norm'].isin(['sim', 's', 'yes', 'true', '1'])
                    
                    # Status: "Aceite" se cond_aceite verdadeiro, caso contrário "Não Aceite"
                    df_recl['Status'] = df_recl['devolucao_norm'].apply(lambda x: 'Aceite' if x in ['sim','s','yes','true','1'] else 'Não Aceite')
                    
                    # Valor Devolvido: se cond_aceite, pegar no valor da coluna 'valor' (se existir e for numérico); senão 0
                    if 'valor' in df_recl.columns:
                        # Limpar e converter valor
                        df_recl['valor_clean'] = (
                            df_recl['valor']
                            .astype(str)
                            .str.replace('€', '', regex=False)
                            .str.replace(',', '.', regex=False)
                            .str.strip()
                        )
                        df_recl['valor_clean'] = pd.to_numeric(df_recl['valor_clean'], errors='coerce').fillna(0)
                    else:
                        df_recl['valor_clean'] = 0
                        st.info("Nota: coluna 'valor' não encontrada. Serão atribuídos 0 a todos os valores devolvidos.")
                    
                    # Atribuir Valor Devolvido conforme aceitação
                    df_recl['Valor Devolvido'] = 0.0
                    df_recl.loc[cond_aceite, 'Valor Devolvido'] = df_recl.loc[cond_aceite, 'valor_clean']
                    
                    # ---- Devoluções Negadas (não aceites, mas com valor pedido) ----
                    df_recl['Valor_Nao_Aceite'] = 0.0
                    cond_nao_aceite = ~cond_aceite   # todas as que não foram aceites
                    # Só interessa se existir um valor (diferente de zero e não nulo) na coluna 'valor_clean'
                    df_recl.loc[cond_nao_aceite & (df_recl['valor_clean'] > 0), 'Valor_Nao_Aceite'] = df_recl.loc[cond_nao_aceite & (df_recl['valor_clean'] > 0), 'valor_clean']

                    # Remover colunas auxiliares
                    df_recl.drop(columns=['devolucao_norm', 'valor_clean'], inplace=True, errors='ignore')
                    
                    # Opcional: se existir coluna 'valor' original, renomear para 'Valor_Reclamado' (apenas para referência)
                    if 'valor' in df_recl.columns:
                        df_recl.rename(columns={'valor': 'Valor_Reclamado'}, inplace=True)
                    # ------------------------------------------------------------
                    
                    st.session_state.reclamacoes_df = df_recl.copy()
                    st.session_state.reclamacoes_filename = recl_file.name
                    st.rerun()
            except Exception as e:
                st.error(f"Erro ao processar reclamações: {e}")
                df_recl = None
        else:
            df_recl = None

    if df_recl is not None and has_cursos:
        # ------------------------------
        # FILTROS ESPECÍFICOS PARA RECLAMAÇÕES
        # ------------------------------
        with st.expander("🔍 Filtrar reclamações", expanded=False):
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            
            with col_f1:
                centros_opcoes = sorted(df_recl['Centro'].dropna().unique())
                centros_sel = st.multiselect("Centro", options=centros_opcoes, default=centros_opcoes, key="filtro_recl_centro")
            
            with col_f2:
                meses_opcoes = ordenar_meses(df_recl['data'].dropna().unique())
                meses_sel = st.multiselect("Mês", options=meses_opcoes, default=meses_opcoes, key="filtro_recl_mes")
            
            with col_f3:
                cursos_opcoes = sorted(df_recl['Ação'].dropna().unique())
                cursos_sel = st.multiselect("Curso", options=cursos_opcoes, default=cursos_opcoes, key="filtro_recl_curso")
            
            with col_f4:
                status_opcoes = ['Aceite', 'Não Aceite']
                status_sel = st.multiselect("Status", options=status_opcoes, default=status_opcoes, key="filtro_recl_status")
            
            busca_motivo = st.text_input("🔍 Buscar no motivo", placeholder="Palavra-chave", key="filtro_recl_motivo")
        
        # Aplicar filtros
        df_filtrado = df_recl.copy()
        if centros_sel:
            df_filtrado = df_filtrado[df_filtrado['Centro'].isin(centros_sel)]
        if meses_sel:
            df_filtrado = df_filtrado[df_filtrado['data'].isin(meses_sel)]
        if cursos_sel:
            df_filtrado = df_filtrado[df_filtrado['Ação'].isin(cursos_sel)]
        if status_sel:
            df_filtrado = df_filtrado[df_filtrado['Status'].isin(status_sel)]
        if busca_motivo:
            df_filtrado = df_filtrado[df_filtrado['motivo'].str.contains(busca_motivo, case=False, na=False)]
        
        # Cálculo dos KPIs com os dados filtrados
        total_reclamacoes = len(df_filtrado)
        total_cursos_realizados = df_cursos['Ação'].nunique() if 'Ação' in df_cursos.columns else 0
        taxa_reclamacoes_curso = (total_reclamacoes / total_cursos_realizados * 100) if total_cursos_realizados > 0 else 0
        
        total_devolvido = df_filtrado['Valor Devolvido'].sum()
        total_negado = df_filtrado['Valor_Nao_Aceite'].sum()
        meta_reclamacao = st.session_state.obj_reclamacao_curso
        delta_recl = taxa_reclamacoes_curso - meta_reclamacao
        delta_color = "▲" if delta_recl > 0 else "▼"
        
        col_recl11, col_recl2, col_recl3, col_recl4 = st.columns(4)
        with col_recl11:
            st.metric("📊 Taxa de Reclamações por Curso", f"{taxa_reclamacoes_curso:.1f}%",
                      delta=f"{delta_color} {abs(delta_recl):.1f}%",
                      help=f"Objetivo: ≤ {meta_reclamacao}% | {total_reclamacoes} reclamações em {total_cursos_realizados} cursos")
        with col_recl2:
            st.metric("💰 Total Devolvido", f"{total_devolvido:,.2f} €".replace(',', ' '))
        with col_recl3:
            st.metric("❌ Total de Devoluções Negadas", f"{total_negado:,.2f} €".replace(',', ' '))
        with col_recl4:
            st.metric("📋 Nº Reclamações", total_reclamacoes)
        
        # Lista detalhada (filtrada)
        with st.expander("📋 Lista completa de Reclamações", expanded=False):
            df_show = df_filtrado[['data', 'Centro', 'Ação', 'motivo', 'Valor Devolvido', 'Valor_Nao_Aceite', 'Status']].copy()
            df_show.rename(columns={
                'data': 'Mês',
                'Valor Devolvido': 'Devolvido (Aceite)',
                'Valor_Nao_Aceite': 'Valor Não Aceite'
            }, inplace=True)
            st.dataframe(df_show, use_container_width=True)
            st.caption(f"📌 Mostrando {len(df_show)} de {len(df_recl)} reclamações (filtradas).")
    else:
        if not has_cursos:
            st.warning("Carregue o ficheiro de Cursos (com a coluna 'Ação') para calcular a taxa de reclamações.")
        else:
            st.info("⬆️ Carregue um ficheiro Excel com as colunas: data, centro, devolução, curso, motivo (e opcional valor).")


    # ------------------------------------------------------------
    # KPI 9 – Ações de Melhoria Implementadas e Recorrência (inalterado)
    # ------------------------------------------------------------
    st.markdown("---")
    st.subheader("🔧 Ações de Melhoria e Recorrência")

    if "acoes_df" not in st.session_state:
        st.session_state.acoes_df = None
    if "acoes_filename" not in st.session_state:
        st.session_state.acoes_filename = None

    if st.session_state.acoes_df is not None:
        st.success(f"📁 Ficheiro de Ações de Melhoria carregado: **{st.session_state.acoes_filename}**")
        col_reset, _ = st.columns([1, 5])
        with col_reset:
            if st.button("🔄 Trocar ficheiro de ações", key="reset_acoes"):
                st.session_state.acoes_df = None
                st.session_state.acoes_filename = None
                st.rerun()
        df_acoes = st.session_state.acoes_df.copy()
    else:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            modo_carga_acoes = st.radio("Modo:", ["Substituir", "Adicionar"], horizontal=True, key="modo_carga_acoes")
        with c2:
            acoes_file = st.file_uploader("Carregar ficheiro de Ações de Melhoria (Excel)", type=["xlsx", "xls"], key="acoes_upload")
        with c3:
            try:
                with open("assets/acoes_melhoria.xlsx", "rb") as f:
                    conteudo_acoes = f.read()
                st.download_button(label="📥 Exemplo Ações de Melhoria (Excel)", data=conteudo_acoes,
                                   file_name="acoes_melhoria.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)
            except FileNotFoundError:
                st.error("⚠️ Ficheiro de exemplo não encontrado: assets/acoes_melhoria.xlsx")
        if acoes_file is not None:
            try:
                df_acoes = pd.read_excel(acoes_file)
                df_acoes.columns = df_acoes.columns.str.strip()
                st.session_state.acoes_df = df_acoes.copy()
                st.session_state.acoes_filename = acoes_file.name
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao processar ficheiro de ações: {e}")
                df_acoes = None
        else:
            df_acoes = None

    if df_acoes is not None:
        if hasattr(st.session_state, 'filtro_centro') and st.session_state.filtro_centro and 'Centro' in df_acoes.columns:
            df_acoes = df_acoes[df_acoes['Centro'].isin(st.session_state.filtro_centro)]

        if not df_acoes.empty:
            total_acoes_melhoria = len(df_acoes)
            if 'Implementada' in df_acoes.columns:
                if df_acoes['Implementada'].dtype == 'object':
                    implementadas = (df_acoes['Implementada'].str.lower() == 'sim').sum()
                else:
                    implementadas = (df_acoes['Implementada'] == 1).sum()
            else:
                implementadas = 0

            if 'Problema_Recorreu' in df_acoes.columns:
                if df_acoes['Problema_Recorreu'].dtype == 'object':
                    recorrencias = (df_acoes['Problema_Recorreu'].str.lower() == 'sim').sum()
                else:
                    recorrencias = (df_acoes['Problema_Recorreu'] == 1).sum()
            else:
                recorrencias = 0

            perc_implementadas = (implementadas / total_acoes_melhoria) * 100 if total_acoes_melhoria > 0 else 0
            perc_recorrencia = (recorrencias / total_acoes_melhoria) * 100 if total_acoes_melhoria > 0 else 0
            meta_implementadas = st.session_state.obj_acoes_implementadas
            meta_recorrencia = st.session_state.obj_recorrencia

            col_acoes1, col_acoes2 = st.columns(2)
            with col_acoes1:
                delta_imp = perc_implementadas - meta_implementadas
                delta_imp_str = f"▲ {delta_imp:.1f}%" if delta_imp >= 0 else f"▼ {abs(delta_imp):.1f}%"
                st.metric(label="✅ Ações de Melhoria Implementadas", value=f"{perc_implementadas:.1f}%",
                          delta=delta_imp_str, help=f"Objetivo: ≥ {meta_implementadas}%")
            with col_acoes2:
                delta_rec = perc_recorrencia - meta_recorrencia
                delta_rec_str = f"▲ {delta_rec:.1f}%" if delta_rec > 0 else f"▼ {abs(delta_rec):.1f}%"
                st.metric(label="⚠️ Recorrência de Problemas", value=f"{perc_recorrencia:.1f}%",
                          delta=delta_rec_str, help=f"Objetivo: ≤ {meta_recorrencia}%")

            if 'Data_Implementacao' in df_acoes.columns:
                df_acoes['Data_Implementacao'] = pd.to_datetime(df_acoes['Data_Implementacao'], errors='coerce')
                df_acoes['Mes'] = df_acoes['Data_Implementacao'].dt.to_period('M').astype(str)
                acoes_por_mes = df_acoes.groupby('Mes').size().reset_index(name='Quantidade')
                if not acoes_por_mes.empty:
                    fig_acoes = px.bar(acoes_por_mes, x='Mes', y='Quantidade', title="Ações de Melhoria por Mês")
                    st.plotly_chart(fig_acoes, use_container_width=True)

            with st.expander("📋 Lista de Ações de Melhoria"):
                st.dataframe(df_acoes, use_container_width=True)
        else:
            st.info("Nenhuma ação de melhoria após aplicação dos filtros.")
    else:
        st.info("⬆️ Carregue um ficheiro Excel com as Ações de Melhoria para visualizar o KPI 9.")

    # ------------------------------------------------------------
    # KPI 10 – Conformidade Documental (DGERT/PSP) (inalterado)
    # ------------------------------------------------------------
    st.markdown("---")
    st.subheader("📄 Conformidade Documental (DGERT/PSP)")

    if "conformidade_df" not in st.session_state:
        st.session_state.conformidade_df = None
    if "conformidade_filename" not in st.session_state:
        st.session_state.conformidade_filename = None

    def is_conforme(valor):
        if pd.isna(valor):
            return False
        valor_str = str(valor).lower()
        valor_str = unicodedata.normalize('NFKD', valor_str).encode('ASCII', 'ignore').decode('ASCII')
        return valor_str in ['sim', 's', '1', 'true']

    if st.session_state.conformidade_df is not None:
        st.success(f"📁 Ficheiro de Conformidade Documental carregado: **{st.session_state.conformidade_filename}**")
        col_reset, _ = st.columns([1, 5])
        with col_reset:
            if st.button("🔄 Trocar ficheiro de conformidade", key="reset_conf"):
                st.session_state.conformidade_df = None
                st.session_state.conformidade_filename = None
                st.rerun()
        df_conf = st.session_state.conformidade_df.copy()
    else:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            modo_carga_conf = st.radio("Modo:", ["Substituir", "Adicionar"], horizontal=True, key="modo_carga_conf")
        with c2:
            conf_file = st.file_uploader("Carregar ficheiro de Conformidade Documental (Excel)", type=["xlsx", "xls"], key="conformidade_upload")
        with c3:
            try:
                with open("assets/conformidade_documental.xlsx", "rb") as f:
                    conteudo_conf = f.read()
                st.download_button(label="📥 Exemplo Conformidade (Excel)", data=conteudo_conf,
                                   file_name="conformidade_documental.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)
            except FileNotFoundError:
                st.error("⚠️ Ficheiro de exemplo não encontrado: assets/conformidade_documental.xlsx")
        if conf_file is not None:
            try:
                df_conf = pd.read_excel(conf_file)
                df_conf.columns = df_conf.columns.str.strip()
                st.session_state.conformidade_df = df_conf.copy()
                st.session_state.conformidade_filename = conf_file.name
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao processar ficheiro de conformidade: {e}")
                df_conf = None
        else:
            df_conf = None

    if df_conf is not None:
        if hasattr(st.session_state, 'filtro_centro') and st.session_state.filtro_centro and 'Centro' in df_conf.columns:
            df_conf = df_conf[df_conf['Centro'].isin(st.session_state.filtro_centro)]

        if not df_conf.empty:
            total_docs = len(df_conf)
            conformes = df_conf['Conforme'].apply(is_conforme).sum()
            taxa_conformidade = (conformes / total_docs) * 100 if total_docs > 0 else 0
            meta_conformidade = st.session_state.obj_conformidade
            delta_conf = taxa_conformidade - meta_conformidade
            delta_conf_str = f"▲ {delta_conf:.1f}%" if delta_conf >= 0 else f"▼ {abs(delta_conf):.1f}%"

            st.metric(label="📑 Taxa de Conformidade Documental", value=f"{taxa_conformidade:.1f}%",
                      delta=delta_conf_str, help="Objetivo: 100% (crítico para DGERT/PSP)")

            if taxa_conformidade < 100:
                nao_conformes = df_conf[~df_conf['Conforme'].apply(is_conforme)]
                st.warning(f"⚠️ Atenção: {len(nao_conformes)} documento(s) não conforme(s). Ação corretiva necessária.")
                with st.expander("📋 Documentos não conformes"):
                    st.dataframe(nao_conformes, use_container_width=True)
            else:
                st.success("✅ Todos os documentos estão em conformidade. Parabéns!")

            if 'Curso' in df_conf.columns:
                conf_por_curso = df_conf.groupby('Curso').apply(
                    lambda g: (g['Conforme'].apply(is_conforme).sum() / len(g)) * 100
                ).reset_index(name='Taxa_Conformidade_%')
                fig_conf = px.bar(conf_por_curso, x='Curso', y='Taxa_Conformidade_%',
                                  title="Conformidade Documental por Curso", range_y=[0, 100])
                fig_conf.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="Meta 100%")
                st.plotly_chart(fig_conf, use_container_width=True)

            with st.expander("📋 Lista completa de documentos"):
                st.dataframe(df_conf, use_container_width=True)
        else:
            st.info("Nenhum dado de conformidade após aplicação dos filtros.")
    else:
        st.info("⬆️ Carregue um ficheiro Excel com os dados de Conformidade Documental para visualizar o KPI 10.")

    # ------------------------------------------------------------
    # Visualizações adicionais (se existirem questionários)
    # ------------------------------------------------------------
    if has_quest:
        st.markdown("---")
        col_rad, col_bar = st.columns(2)

        with col_rad:
            st.subheader("Equilíbrio de Qualidade (Radar)")
            if "Categoria" in df_quest.columns and "Média" in df_quest.columns:
                cat_stats = df_quest.groupby("Categoria")["Média"].mean().reset_index()
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(r=cat_stats["Média"], theta=cat_stats["Categoria"],
                                                    fill='toself', name='Média'))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False)
                st.plotly_chart(fig_radar, use_container_width=True)
            else:
                st.info("Colunas 'Categoria' e/ou 'Média' não encontradas nos questionários.")

        with col_bar:
            st.subheader("Presencial vs. À Distância")
            if "Categoria" in df_quest.columns and "Modalidade" in df_quest.columns and "Média" in df_quest.columns:
                mod_comp = df_quest.groupby(["Categoria", "Modalidade"])["Média"].mean().reset_index()
                fig_mod = px.bar(mod_comp, x="Categoria", y="Média", color="Modalidade", barmode="group", range_y=[0, 5])
                st.plotly_chart(fig_mod, use_container_width=True)
            else:
                st.info("Colunas necessárias (Categoria, Modalidade, Média) não encontradas.")

    else:
        if not has_cursos:
            st.warning("⚠️ Carregue ficheiros de Cursos e/ou Questionários na barra lateral para visualizar os KPIs.")

if __name__ == "__main__":
    mostrar_qualidade()