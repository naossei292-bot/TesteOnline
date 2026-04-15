import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.data_utils import get_col, aplicar_filtros

st.set_page_config(page_title="Gestão de Qualidade", layout="wide")

def mostrar_qualidade():
    """Função principal da página de qualidade"""
st.header("🎯 Scorecard de Qualidade Pedagógica")

df_c_filt = aplicar_filtros(st.session_state.cursos_df)
df_q_filt = aplicar_filtros(st.session_state.quest_df)

# Inicializar objetivos
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

has_cursos = df_c_filt is not None and not df_c_filt.empty
has_quest = df_q_filt is not None and not df_q_filt.empty

if has_cursos or has_quest:
    
    # Cálculo dos KPIs
    if has_quest:
        media_sat = df_q_filt["Media"].mean()
        META_SAT = st.session_state.obj_satisfacao
    else:
        media_sat = 0
        META_SAT = st.session_state.obj_satisfacao
    
    if has_cursos:
        c_insc = get_col(df_c_filt, "inscritos")
        c_conc = get_col(df_c_filt, "concluidos")
        t_conc = (df_c_filt[c_conc].sum() / df_c_filt[c_insc].sum() * 100) if c_insc and c_conc else 0
        META_CONC = st.session_state.obj_conclusao
        
        c_aval = get_col(df_c_filt, "avaliados")
        c_aprov = get_col(df_c_filt, "aprovados")
        t_aprov = (df_c_filt[c_aprov].sum() / df_c_filt[c_aval].sum() * 100) if c_aval and c_aprov else 0
        META_APROV = st.session_state.obj_aprovacao
        
        c_planeado = get_col(df_c_filt, "planeado")
        if c_planeado and c_conc:
            t_plano = (df_c_filt[c_conc].sum() / df_c_filt[c_planeado].sum() * 100)
        else:
            t_plano = None
        META_PLANO = st.session_state.obj_plano
    else:
        t_conc = t_aprov = 0
        t_plano = None
        META_CONC = META_APROV = META_PLANO = 0
    
    if has_quest:
        df_formador = df_q_filt[df_q_filt["Respondente"].str.contains("Formador", na=False)]
        media_formador = df_formador["Media"].mean() if not df_formador.empty else None
        META_FORMADOR = st.session_state.obj_formador
    else:
        media_formador = None
        META_FORMADOR = st.session_state.obj_formador
    
    # CSS
    st.markdown("""
    <style>
    .kpi-card {
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 10px;
        transition: all 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    .kpi-title {
        font-size: 14px;
        color: #666;
        margin-bottom: 5px;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 5px;
    }
    .kpi-meta {
        font-size: 12px;
        color: #888;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.subheader("📊 KPIs Essenciais")
    
    # Exibição dos KPIs
    col1, col2, col3 = st.columns(3)
    
    with col1:
        delta_sat = media_sat - META_SAT
        delta_color = "▲" if delta_sat >= 0 else "▼"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">🎓 Satisfação dos Formandos</div>
            <div class="kpi-value">{media_sat:.2f} / 5</div>
            <div class="kpi-meta">Objetivo: ≥ {META_SAT} | {delta_color} {abs(delta_sat):.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        delta_conc = t_conc - META_CONC
        delta_color = "▲" if delta_conc >= 0 else "▼"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">✅ Taxa de Conclusão</div>
            <div class="kpi-value">{t_conc:.1f}%</div>
            <div class="kpi-meta">Objetivo: ≥ {META_CONC}% | {delta_color} {abs(delta_conc):.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        delta_aprov = t_aprov - META_APROV
        delta_color = "▲" if delta_aprov >= 0 else "▼"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">📝 Taxa de Aprovação</div>
            <div class="kpi-value">{t_aprov:.1f}%</div>
            <div class="kpi-meta">Objetivo: ≥ {META_APROV}% | {delta_color} {abs(delta_aprov):.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    col4, col5, col6 = st.columns(3)
    
    with col4:
        if t_plano is not None:
            delta_plano = t_plano - META_PLANO
            delta_color = "▲" if delta_plano >= 0 else "▼"
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">📅 Cumprimento do Plano</div>
                <div class="kpi-value">{t_plano:.1f}%</div>
                <div class="kpi-meta">Objetivo: ≥ {META_PLANO}% | {delta_color} {abs(delta_plano):.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">📅 Cumprimento do Plano</div>
                <div class="kpi-value">N/D</div>
                <div class="kpi-meta">⚠️ Adicione coluna "Planeado"</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col5:
        if media_formador is not None:
            delta_form = media_formador - META_FORMADOR
            delta_color = "▲" if delta_form >= 0 else "▼"
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">👨‍🏫 Avaliação dos Formadores</div>
                <div class="kpi-value">{media_formador:.2f} / 5</div>
                <div class="kpi-meta">Objetivo: ≥ {META_FORMADOR} | {delta_color} {abs(delta_form):.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">👨‍🏫 Avaliação dos Formadores</div>
                <div class="kpi-value">N/D</div>
                <div class="kpi-meta">⚠️ Sem dados disponíveis</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Visualizações adicionais
    if has_quest:
        st.markdown("---")
        col_rad, col_bar = st.columns(2)

        with col_rad:
            st.subheader("Equilíbrio de Qualidade (Radar)")
            cat_stats = df_q_filt.groupby("Categoria")["Media"].mean().reset_index()
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=cat_stats["Media"], 
                theta=cat_stats["Categoria"], 
                fill='toself', 
                name='Média'
            ))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False)
            st.plotly_chart(fig_radar, use_container_width=True)

        with col_bar:
            st.subheader("Presencial vs. À Distância")
            mod_comp = df_q_filt.groupby(["Categoria", "Modalidade"])["Media"].mean().reset_index()
            fig_mod = px.bar(
                mod_comp, 
                x="Categoria", 
                y="Media", 
                color="Modalidade", 
                barmode="group", 
                range_y=[0,5]
            )
            st.plotly_chart(fig_mod, use_container_width=True)

else:
    st.warning("⚠️ Carregue ficheiros de Cursos e/ou Questionários na barra lateral para visualizar os KPIs.")

if __name__ == "__main__":
    mostrar_qualidade()    