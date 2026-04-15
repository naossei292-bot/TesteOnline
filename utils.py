import pandas as pd

def get_col(df, name):
    """Encontra o nome da coluna independentemente de maiúsculas/minúsculas"""
    if df is None:
        return None
    for col in df.columns:
        if str(col).strip().lower() == name.lower():
            return col
    return None

def aplicar_filtros(df):
    """Aplica filtros de centro ao DataFrame"""
    if df is None:
        return None
    temp_df = df.copy()
    if st.session_state.filtro_centro:
        col_c = get_col(temp_df, "Centro")
        if col_c:
            temp_df = temp_df[temp_df[col_c].isin(st.session_state.filtro_centro)]
    return temp_df