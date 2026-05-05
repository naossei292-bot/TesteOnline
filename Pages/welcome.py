import streamlit as st
from datetime import datetime

def mostrar_welcome():
    """
    Página inicial de boas-vindas com tutorial personalizado por role
    """
    
    # Obter o role do utilizador logado
    role = st.session_state.get("role", "")
    
    # Mapeamento de roles para nomes amigáveis
    nomes_roles = {
        "admin": "Administrador",
        "gestor_BALANÇOS": "Gestor de Balanços",
        "gestor_qualidade": "Gestor de Qualidade",
        "gestor_questionarios": "Gestor de Questionários"
    }
    
    nome_amigavel = nomes_roles.get(role, "Utilizador")
    
    # Cabeçalho com boas-vindas
    st.title(f"👋 Bem-vindo, {nome_amigavel}!")
    
    # Mostrar data e hora atual
    st.caption(f"📅 {datetime.now().strftime('%d/%m/%Y às %H:%M')}")
    
    st.markdown("---")
    
    # Conteúdo personalizado por role
    if role == "admin":
        _tutorial_admin()
    elif role == "gestor_BALANCOS":
        _tutorial_gestor_balancos()
    elif role == "gestor_qualidade":
        _tutorial_gestor_qualidade()
    elif role == "gestor_questionarios":
        _tutorial_gestor_questionarios()
    else:
        _tutorial_default()
    
    # Rodapé com dicas gerais
    st.markdown("---")
    st.info("💡 **Dica:** Utilize o menu lateral para navegar entre as diferentes secções da aplicação.", icon="ℹ️")

def _tutorial_admin():
    """Tutorial para o Administrador"""
    
    st.markdown("""
    ## 🚀 Dashboard Administrativo
    
    Como administrador, tens acesso total a todas as funcionalidades do sistema.
    """
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 📌 O que podes fazer:
        
        1. **📚 Balanços e Relatórios**
           - Gerar balanços financeiros
           - Criar relatórios detalhados
           - Exportar documentos em lote
        
        2. **📋 Questionários**
           - Gerir questionários de satisfação
           - Analisar respostas
           - Exportar resultados
        
        3. **🎯 Gestão de Qualidade**
           - Acompanhar métricas de qualidade
           - Gerar dashboards de desempenho
        """)
    
    with col2:
        st.markdown("""
        ### 📌 O que podes fazer (cont.):
        
        4. **📚 Cursos**
           - Gerir catálogo de formações
           - Controlar inscrições
           - Acompanhar progresso
        
        5. **⚔️ Comparador Versus**
           - Comparar dados entre períodos
           - Análise de tendências
        
        6. **📊 Dashboards**
           - Visualização avançada de dados
           - KPIs em tempo real
        """)
    
    st.markdown("---")
    
    # Dicas rápidas
    with st.expander("🎯 **Dicas rápidas para Administrador**", expanded=False):
        st.markdown("""
        - ✅ **Gerir permissões**: Podes adicionar/remover acessos de outros utilizadores
        - ✅ **Backup de dados**: Recomenda-se fazer backup regular dos dados
        - ✅ **Monitorização**: Acompanha os logs de acesso na secção de administração
        - ✅ **Suporte**: Em caso de dúvidas, contacta o suporte técnico
        """)
    
    # Passos iniciais
    st.success("""
    ### 🎯 Próximos passos recomendados:
    
    1. **Verifica os dados** carregados no sistema
    2. **Configura as permissões** dos utilizadores
    3. **Explora os dashboards** para monitorizar KPIs
    4. **Gera relatórios** periódicos para análise
    """)

def _tutorial_gestor_balancos():
    """Tutorial para o Gestor de Balanços"""
    
    st.markdown("""
    ## 📊 Painel do Gestor de Balanços
    
    Esta página foi desenvolvida para te ajudar na gestão financeira e administrativa das formações.
    """)
    
    # Funcionalidades principais
    st.markdown("### 🎯 Funcionalidades disponíveis:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### 📚 Balanços e Relatórios
        
        **O que podes fazer:**
        - Carregar múltiplos ficheiros Excel/CSV
        - Gerar balanços automáticos
        - Criar relatórios financeiros
        - Exportar documentos em formato ZIP
        
        **Como utilizar:**
        1. Acede à página **"📚 Balanços e Relatórios"**
        2. Carrega os ficheiros necessários
        3. Seleciona o ano e o tipo de operação
        4. Clica em "EXECUTAR" para processar
        5. Descarrega os resultados
        """)
    
    with col2:
        st.markdown("""
        #### 📊 Dashboard - Ações
        
        **O que podes fazer:**
        - Visualizar métricas de desempenho
        - Analisar tendências
        - Monitorizar indicadores-chave
        
        **Como utilizar:**
        1. Acede à página **"📊 Dashboard - Ações"**
        2. Aplica os filtros desejados
        3. Explora os gráficos interativos
        4. Exporta dados para análise
        """)
    
    st.markdown("---")
    
    # Tutorial passo a passo
    with st.expander("📖 **Tutorial passo a passo - Gerar Balanços**", expanded=True):
        st.markdown("""
        ### Passo 1: Preparar os dados
        - Certifica-te que tens os ficheiros no formato correto (Excel/CSV)
        - Os ficheiros devem conter as colunas necessárias (Inscritos, Aptos, etc.)
        
        ### Passo 2: Carregar os ficheiros
        - Na página "Balanços e Relatórios", usa o botão "Carregar múltiplos ficheiros"
        - Podes carregar vários ficheiros de uma só vez
        
        ### Passo 3: Configurar a operação
        - Seleciona o ano pretendido
        - Escolhe o tipo de operação (balanços, relatórios ou ambos)
        
        ### Passo 4: Executar
        - Clica em "EXECUTAR" e aguarda o processamento
        - Os resultados serão guardados automaticamente
        
        ### Passo 5: Descarregar resultados
        - Os ficheiros gerados aparecerão nas secções "BALANÇOS" e "RELATÓRIOS"
        - Podes descarregar individualmente ou todos em ZIP
        """)
    
    # Dicas úteis
    st.info("""
    💡 **Dicas importantes:**
    - Os ficheiros carregados são guardados por ano para melhor organização
    - Podes apagar ficheiros antigos para libertar espaço
    - O sistema suporta ficheiros até 200MB
    - Recomenda-se verificar os dados antes de gerar relatórios
    """)
    
    # Ações rápidas
    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button("🚀 Ir para Balanços e Relatórios", use_container_width=True):
            st.session_state.pagina = "📚 Balanços e Relatórios"
            st.rerun()

def _tutorial_gestor_qualidade():
    """Tutorial para o Gestor de Qualidade"""
    
    st.markdown("""
    ## 🎯 Painel do Gestor de Qualidade
    
    Esta página foi desenvolvida para monitorizar e garantir a qualidade das formações.
    """)
    
    # Funcionalidades principais
    st.markdown("### 🎯 Funcionalidades disponíveis:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### 🎯 Gestão de Qualidade
        
        **O que podes fazer:**
        - Analisar métricas de satisfação
        - Monitorizar indicadores de qualidade
        - Identificar áreas de melhoria
        
        **Como utilizar:**
        1. Acede à página **"🎯 Gestão de Qualidade"**
        2. Explora os KPIs e gráficos
        3. Aplica filtros para análises específicas
        4. Identifica tendências e padrões
        """)
    
    with col2:
        st.markdown("""
        #### 📚 Cursos
        
        **O que podes fazer:**
        - Gerir catálogo de formações
        - Analisar desempenho por curso
        - Monitorizar taxas de conclusão
        
        **Como utilizar:**
        1. Acede à página **"📚 Cursos"**
        2. Visualiza todos os cursos disponíveis
        3. Analisa métricas por curso
        4. Exporta dados para relatórios
        """)
    
    st.markdown("---")
    
    # KPIs importantes
    st.markdown("### 📊 Indicadores-Chave a Monitorizar:")
    
    kpi_cols = st.columns(3)
    with kpi_cols[0]:
        st.metric("🎯 Satisfação Média", "> 4.0", "Objetivo", delta_color="normal")
    with kpi_cols[1]:
        st.metric("✅ Taxa de Aprovação", "> 85%", "Meta", delta_color="normal")
    with kpi_cols[2]:
        st.metric("📈 Participação", "> 70%", "Alvo", delta_color="normal")
    
    st.markdown("---")
    
    # Tutorial
    with st.expander("📖 **Como monitorizar a qualidade das formações**", expanded=True):
        st.markdown("""
        ### 1. Análise de Satisfação
        - Acede ao **Dashboard - Ações** para ver a satisfação por centro
        - Identifica cursos com baixa satisfação
        - Gera relatórios detalhados para análise profunda
        
        ### 2. Monitorização de Indicadores
        - Acompanha a taxa de aprovação por centro
        - Verifica a evolução mensal dos indicadores
        - Compara desempenho entre diferentes períodos
        
        ### 3. Identificação de Oportunidades
        - Localiza cursos com maior potencial de melhoria
        - Analisa feedback dos participantes
        - Propõe ações corretivas baseadas em dados
        
        ### 4. Geração de Relatórios
        - Exporta dashboards para apresentações
        - Cria relatórios periódicos de qualidade
        - Compartilha insights com a equipa
        """)
    
    # Dicas
    st.warning("""
    ⚠️ **Atenção aos pontos críticos:**
    - Cursos com satisfação < 3.0 merecem atenção prioritária
    - Centros com baixa taxa de aprovação devem ser analisados
    - Ações com muitos inaptos/desistentes requerem revisão
    """)
    
    # Ações rápidas
    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("🎯 Ir para Gestão de Qualidade", use_container_width=True):
            st.session_state.pagina = "🎯 Gestão de Qualidade"
            st.rerun()
    
    with col_btn2:
        if st.button("📊 Ver Dashboard de Ações", use_container_width=True):
            st.session_state.pagina = "📊 Dashboard - Ações"
            st.rerun()

def _tutorial_gestor_questionarios():
    """Tutorial para o Gestor de Questionários"""
    
    st.markdown("""
    ## 📋 Painel do Gestor de Questionários
    
    Esta página foi desenvolvida para gerir e analisar questionários de satisfação.
    """)
    
    # Funcionalidades principais
    st.markdown("### 🎯 Funcionalidades disponíveis:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### 📋 Questionários
        
        **O que podes fazer:**
        - Carregar questionários preenchidos
        - Analisar respostas individualmente
        - Editar e corrigir dados
        - Exportar resultados
        
        **Como utilizar:**
        1. Acede à página **"📋 Questionários"**
        2. Carrega o ficheiro Excel com os dados
        3. Edita as respostas se necessário
        4. Guarda as alterações
        """)
    
    with col2:
        st.markdown("""
        #### 📊 Dashboard - Questionários
        
        **O que podes fazer:**
        - Visualizar análises estatísticas
        - Identificar tendências de satisfação
        - Comparar resultados por período
        - Exportar dashboards
        
        **Como utilizar:**
        1. Acede à página **"📊 Dashboard - Questionários"**
        2. Aplica filtros (centro, período, etc.)
        3. Explora os gráficos interativos
        4. Identifica padrões e insights
        """)
    
    st.markdown("---")
    
    # Tutorial detalhado
    with st.expander("📖 **Tutorial: Como gerir questionários**", expanded=True):
        st.markdown("""
        ### Passo 1: Preparar os dados
        - Os questionários devem estar em formato Excel
        - As colunas devem incluir: Respondente, Centro, Ação, Perguntas, etc.
        
        ### Passo 2: Carregar questionários
        - Na página "Questionários", usa o uploader de ficheiros
        - Podes carregar múltiplos ficheiros
        - O sistema vai consolidar os dados automaticamente
        
        ### Passo 3: Editar dados
        - Após carregar, podes editar diretamente na tabela
        - Corrige erros ou ajusta respostas
        - As alterações são guardadas automaticamente
        
        ### Passo 4: Analisar resultados
        - Acede ao "Dashboard - Questionários"
        - Aplica filtros para análises específicas
        - Explora os diferentes gráficos e métricas
        
        ### Passo 5: Exportar
        - Podes exportar os dados editados
        - Descarrega dashboards para apresentações
        - Gera relatórios personalizados
        """)
    
    # Dicas
    st.info("""
    💡 **Dicas para melhor gestão:**
    - Mantém os ficheiros organizados por data/período
    - Verifica sempre a consistência dos dados carregados
    - Utiliza os dashboards para identificar tendências
    - Exporta relatórios regularmente para documentação
    """)
    
    # Métricas importantes
    st.markdown("### 📊 Métricas a acompanhar:")
    
    met_cols = st.columns(3)
    with met_cols[0]:
        st.metric("Taxa de Resposta", "> 60%", "Objetivo")
    with met_cols[1]:
        st.metric("Satisfação Média", "> 4.0", "Meta")
    with met_cols[2]:
        st.metric("Participação", "> 500", "Respostas/mês")
    
    # Ações rápidas
    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("📋 Gerir Questionários", use_container_width=True):
            st.session_state.pagina = "📋 Questionários"
            st.rerun()
    
    with col_btn2:
        if st.button("📊 Ver Dashboard", use_container_width=True):
            st.session_state.pagina = "📊 Dashboard - Questionários"
            st.rerun()

def _tutorial_default():
    """Tutorial padrão (fallback)"""
    
    st.markdown("""
    ## 👋 Bem-vindo ao Sistema de Gestão
    
    ### 📌 Como começar:
    
    1. **Explore o menu lateral** para aceder às diferentes funcionalidades
    2. **Consulte os tutoriais** específicos para o teu perfil
    3. **Contacte o administrador** se tiver dúvidas
    
    ### 🎯 Funcionalidades disponíveis:
    
    Dependendo do teu perfil de acesso, tens disponíveis diferentes módulos:
    - 📚 **Balanços e Relatórios** (Gestão financeira)
    - 📋 **Questionários** (Análise de satisfação)
    - 🎯 **Gestão de Qualidade** (Monitorização de métricas)
    - 📚 **Cursos** (Gestão de formações)
    - 📊 **Dashboards** (Visualização de dados)
    
    Para mais informações, contacta o administrador do sistema.
    """)
    
    st.info("ℹ️ O teu perfil de acesso pode limitar algumas funcionalidades. Se precisares de mais permissões, contacta o administrador.", icon="🔒")


if __name__ == "__main__":
    mostrar_welcome()