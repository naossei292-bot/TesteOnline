import streamlit as st
import sys
import os
from glob import glob

# Adiciona o caminho da pasta 'balancos' para importar os módulos das Partes
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BALANCOS_DIR = os.path.join(BASE_DIR, 'balancos')
sys.path.insert(0, BALANCOS_DIR)

sys.path.insert(0, BALANCOS_DIR)
from balancos.main import gerar_balancos

def mostrar():
    st.write("DEBUG: Entrei na função mostrar")   # linha adicionada        
    st.title("📑 Balanços e Relatórios")
    
    # Verificação de login (assumindo que st.session_state.logado existe)
    if not st.session_state.get("logado", False):
        st.warning("Faça login para aceder a esta área.")
        return

    # Interface
    ano = st.number_input("Ano", min_value=2000, max_value=2030, step=1, value=2024)
    if st.button("Gerar relatórios e balanços (completo)"):
        with st.spinner("A processar..."):
            try:
                resultado = gerar_balancos(ano)
                st.success(f"Balanços gerados para {ano}!")
                # Opcional: guardar o ano na sessão
                st.session_state['ultimo_ano'] = ano
            except Exception as e:
                st.error(f"Erro: {e}")
    
    # Listar ficheiros da pasta balancos/balanco/
    pasta_balanco = os.path.join(BALANCOS_DIR, "balanco")
    if os.path.exists(pasta_balanco):
        ficheiros = glob(os.path.join(pasta_balanco, "*.*"))
        if ficheiros:
            st.subheader("Balanços disponíveis")
            for f in ficheiros:
                nome = os.path.basename(f)
                with open(f, "rb") as file:
                    st.download_button(f"📄 {nome}", data=file, file_name=nome)
        else:
            st.info("Nenhum balanço encontrado.")
    else:
        st.info("A pasta de balanços ainda não existe. Gere um relatório para criá-la.")