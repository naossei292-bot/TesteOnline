import streamlit as st
import hmac

def verificar_autenticacao():
    """Verifica se o utilizador está autenticado com a palavra-passe dos Secrets"""
    
    # Se já está autenticado nesta sessão, continua
    if st.session_state.get("autenticado", False):
        return True
    
    # Título da página de login
    st.title("🔒 Acesso Restrito")
    st.markdown("### Esta aplicação é privada")
    st.markdown("Introduza a palavra-passe para continuar.")
    
    # Campo para a password
    password_input = st.text_input(
        "Palavra-passe:",
        type="password",
        key="login_password"
    )
    
    # Botão para submeter
    if st.button("🔓 Entrar", use_container_width=True):
        # Busca a password correta dos Secrets
        try:
            password_correta = st.secrets["password"]
        except KeyError:
            st.error("⚠️ Erro de configuração: Password não definida nos Secrets")
            st.info("Contacte o administrador da aplicação.")
            return False
        
        # Compara as passwords de forma segura
        if hmac.compare_digest(password_input, password_correta):
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("❌ Palavra-passe incorreta!")
            return False
    
    return False

def mostrar_logout():
    """Mostra botão de logout"""
    col_logout1, col_logout2 = st.columns([6, 1])
    with col_logout2:
        if st.button("🚪 Sair", help="Terminar sessão"):
            st.session_state.clear()
            st.rerun()