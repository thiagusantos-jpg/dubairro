"""
MERCADO duBAIRRO — Dashboard de Gestão v2.0
Streamlit App com 6 páginas de análise estratégica

MELHORIAS v2.0:
- Logo do Mercado DuBairro na sidebar
- Tooltips explicativos em TODOS os gráficos
- Clareza temporal: badges de período + comparação mês a mês
- Página 6 nova: Visão Futurista (cenários e projeções)
- Simulador "E se?" na sidebar (custo fixo ajustável)
- Tolerância visual nos KPIs (±2% = neutro/amarelo)
- Código seguro contra dados faltantes (safe_div)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from pathlib import Path

# ============================================================
# CONFIGURAÇÃO GERAL
# ============================================================
st.set_page_config(
    page_title="Gestão | Mercado duBairro",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUSTO_FIXO_DEFAULT = 16913.46
META_LIQUIDA = 0.15

COLORS = {
    'yellow': '#FFC107', 'dark': '#2D2D2D', 'gray': '#666666',
    'green': '#27AE60', 'red': '#E74C3C', 'blue': '#2E86C1',
    'light_gray': '#F5F5F5', 'orange': '#F39C12',
    'green_dark': '#1E8449', 'green_light': '#82E0AA',
    'yellow_light': '#F9E79F', 'red_light': '#F5B7B1',
}

# ============================================================
# CSS CUSTOMIZADO
# ============================================================
st.markdown("""
<style>
    .stApp { background-color: #FAFAFA; }
    [data-testid="stSidebar"] { background-color: #2D2D2D; }
    [data-testid="stSidebar"] * { color: #FFFFFF !important; }
    [data-testid="stSidebar"] .stRadio label { color: #FFFFFF !important; font-size: 14px; }
    .kpi-card {
        background: white; border-radius: 12px; padding: 20px 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-left: 4px solid #FFC107; margin-bottom: 8px;
    }
    .kpi-title { font-size: 13px; color: #666; margin-bottom: 4px; font-weight: 500; }
    .kpi-value { font-size: 28px; font-weight: 700; color: #2D2D2D; line-height: 1.2; }
    .kpi-subtitle { font-size: 11px; color: #999; margin-top: 4px; }
    .kpi-positive { color: #27AE60; }
    .kpi-negative { color: #E74C3C; }
    .kpi-neutral { color: #F39C12; }
    .story-box {
        background: #FFF9E6; border-left: 3px solid #FFC107;
        padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 8px 0 16px 0; font-size: 13px; color: #555;
    }
    .section-header {
        font-size: 18px; font-weight: 600; color: #2D2D2D;
        border-bottom: 2px solid #FFC107; padding-bottom: 6px; margin: 24px 0 12px 0;
    }
    .periodo-badge {
        background: #FFC107; color: #2D2D2D; padding: 4px 12px;
        border-radius: 20px; font-size: 12px; font-weight: 600; display: inline-block; margin-bottom: 8px;
    }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    [data-testid="stMetricDelta"] { font-size: 14px; }
</style>
""", unsafe_allow_html=True)

MESES_NOMES = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
               'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
MESES_LABELS = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

# ============================================================
# CARREGAMENTO DE DADOS
# ============================================================
@st.cache_data
def load_data():
    file_path = "Base_PowerBI.xlsx"
    data = {}
    data['vendas_mensais'] = pd.read_excel(file_path, sheet_name='fato_vendas_mensais')
    data['vendas_diarias'] = pd.read_excel(file_path, sheet_name='fato_vendas_diarias')
    data['produtos'] = pd.read_excel(file_path, sheet_name='dim_produtos')
    data['calendario'] = pd.read_excel(file_path, sheet_name='dim_calendario')
    data['yoy'] = pd.read_excel(file_path, sheet_name='comparativo_yoy')
    data['erosao'] = pd.read_excel(file_path, sheet_name='alertas_erosao_margem')
    return data

# ============================================================
# HELPERS
# ============================================================
def get_custo_fixo():
    return st.session_state.get('custo_fixo', CUSTO_FIXO_DEFAULT)

def get_mes_ref(yoy):
    yoy_mes = yoy[yoy['Receita_2026'] > 0]
    if not yoy_mes.empty:
        return yoy_mes.iloc[-1]['Mes'], int(yoy_mes.iloc[-1]['Mes_Num'])
    return "Janeiro", 1

def safe_div(a, b, default=0):
    try:
        return a / b if b != 0 else default
    except:
        return default

def delta_color(v, tol=2.0):
    if abs(v) <= tol: return "kpi-neutral"
    return "kpi-positive" if v > 0 else "kpi-negative"

def delta_arrow(v, tol=2.0):
    if abs(v) <= tol: return "●"
    return "▲" if v > 0 else "▼"

def render_kpi_card(title, value, subtitle="", color_class=""):
    sub_html = f'<div class="kpi-subtitle {color_class}">{subtitle}</div>' if subtitle else ''
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">{title}</div><div class="kpi-value">{value}</div>{sub_html}</div>', unsafe_allow_html=True)

def render_story(text):
    st.markdown(f'<div class="story-box">💡 {text}</div>', unsafe_allow_html=True)

def render_section(text):
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)

def render_periodo_badge(mes_nome, ano):
    st.markdown(f'<span class="periodo-badge">📅 Analisando: {mes_nome}/{ano}</span>', unsafe_allow_html=True)

def render_tooltip(title, what, how, why, example=""):
    with st.expander(f"💡 Como interpretar: {title}"):
        st.markdown(f"**O que mostra:** {what}\n\n**Como ler:** {how}\n\n**Por que importa:** {why}")
        if example:
            st.markdown(f"**Exemplo prático:** {example}")


# ============================================================
# PÁGINA 1: RESUMO EXECUTIVO
# ============================================================
def page_resumo_executivo(data):
    st.markdown("## 📊 Resumo Executivo")
    st.markdown("*Como foi o mês? Estamos melhor ou pior que antes?*")
    CUSTO_FIXO = get_custo_fixo()
    vm = data['vendas_mensais']; yoy = data['yoy']; produtos = data['produtos']
    mes_nome, mes_num = get_mes_ref(yoy)
    render_periodo_badge(mes_nome, 2026)
    st.markdown("---")

    fat = vm['Vlr_Venda'].sum(); lb = vm['Vlr_Lucro'].sum(); ll = lb - CUSTO_FIXO
    mb = safe_div(lb, fat) * 100; mr = safe_div(ll, fat) * 100
    pe = safe_div(CUSTO_FIXO, mb / 100) if mb > 0 else 0
    folga = (safe_div(fat, pe) - 1) * 100 if pe > 0 else 0
    cupons = vm['Qtde_Documentos'].sum(); tm = safe_div(fat, cupons)
    skus = len(produtos)

    vr = vl = vc = vt = 0.0; c25 = r25 = t25 = 0.0
    yoy_mes = yoy[yoy['Receita_2026'] > 0]
    if not yoy_mes.empty:
        row = yoy_mes.iloc[-1]
        vr = row.get('Var_Receita_Pct', 0) or 0; vl = row.get('Var_Lucro_Pct', 0) or 0
        c25 = row.get('Cupons_2025', 0) or 0; r25 = row.get('Receita_2025', 0) or 0
        t25 = safe_div(r25, c25); vc = safe_div(cupons - c25, c25) * 100; vt = safe_div(tm - t25, t25) * 100

    c1, c2, c3, c4 = st.columns(4)
    with c1: render_kpi_card("Faturamento do Mês", f"R$ {fat:,.2f}", f"{delta_arrow(vr)} {vr:+.1f}% vs {mes_nome}/25", delta_color(vr))
    with c2: render_kpi_card("Lucro Líquido", f"R$ {ll:,.2f}", f"Bruto: R$ {lb:,.2f} − Fixo: R$ {CUSTO_FIXO:,.2f}")
    with c3:
        status = "✅ Saudável" if mr > 20 else ("⚠️ Atenção" if mr > 15 else "🔴 Crítico")
        render_kpi_card("Margem Real", f"{mr:.1f}%", f"Meta: 15% | {status}")
    with c4: render_kpi_card("Ponto de Equilíbrio", f"R$ {pe:,.0f}", f"Folga de {folga:.0f}%", "kpi-positive" if folga > 50 else "kpi-negative")

    c5, c6, c7, c8 = st.columns(4)
    with c5: render_kpi_card("Nº de Cupons (Clientes)", f"{cupons:,.0f}", f"{delta_arrow(vc)} {vc:+.1f}% vs {mes_nome}/25", delta_color(vc))
    with c6: render_kpi_card("Ticket Médio", f"R$ {tm:.2f}", f"{delta_arrow(vt)} {vt:+.1f}% vs {mes_nome}/25", delta_color(vt))
    with c7:
        ca = len(produtos[produtos['Curva'] == 'A']) if 'Curva' in produtos.columns else 0
        render_kpi_card("SKUs Ativos", f"{skus:,}", f"Curva A: {ca} produtos")
    with c8: render_kpi_card("Variação YoY Lucro", f"{vl:+.1f}%", f"{delta_arrow(vl)} {vl:+.1f}% vs {mes_nome}/25", delta_color(vl))

    render_tooltip("KPIs do Resumo Executivo",
        "Os 8 indicadores-chave do mês, comparados com o mesmo mês do ano anterior.",
        "Setas verdes (▲) = melhoria, vermelhas (▼) = piora, laranja (●) = estável (variação menor que ±2%).",
        "Permite em 5 segundos entender a saúde geral do mercado.",
        f"Faturamento de {mes_nome}/26: R$ {fat:,.0f}. Em {mes_nome}/25: R$ {r25:,.0f}. Variação de {vr:+.1f}%.")

    if vr != 0:
        ef = "mais eficientes — vendemos menos, mas lucramos mais por real vendido" if abs(vl) < abs(vr) else "com desafios de margem"
        render_story(f"Em {mes_nome}/26, o faturamento variou {vr:+.1f}% vs {mes_nome}/25, mas o lucro variou {vl:+.1f}%. Estamos {ef}. O fluxo de clientes variou {vc:+.0f}% e o ticket médio variou {vt:+.0f}%.")

    st.markdown("---")
    col_left, col_right = st.columns([3, 2])

    with col_left:
        render_section(f"Evolução Mensal — 2025 vs 2026 (mês a mês)")
        chart_data = []
        for _, r in yoy.iterrows():
            if r['Receita_2025'] > 0: chart_data.append({'Mês': r['Mes'], 'Receita': r['Receita_2025'], 'Lucro': r['Lucro_2025'], 'Ano': '2025'})
            if r['Receita_2026'] > 0: chart_data.append({'Mês': r['Mes'], 'Receita': r['Receita_2026'], 'Lucro': r['Lucro_2026'], 'Ano': '2026'})
        if chart_data:
            dc = pd.DataFrame(chart_data); fig = make_subplots(specs=[[{"secondary_y": True}]])
            d25 = dc[dc['Ano'] == '2025']; d26 = dc[dc['Ano'] == '2026']
            fig.add_trace(go.Bar(x=d25['Mês'], y=d25['Receita'], name='Fat. 2025', marker_color='#D5DBDB', text=[f"R${v/1000:.0f}k" for v in d25['Receita']], textposition='outside', textfont_size=9))
            if not d26.empty: fig.add_trace(go.Bar(x=d26['Mês'], y=d26['Receita'], name='Fat. 2026', marker_color=COLORS['yellow'], text=[f"R${v/1000:.0f}k" for v in d26['Receita']], textposition='outside', textfont_size=9))
            fig.add_trace(go.Scatter(x=d25['Mês'], y=d25['Lucro'], name='Lucro 2025', line=dict(color=COLORS['green'], width=2, dash='dot'), mode='lines+markers'), secondary_y=True)
            if not d26.empty: fig.add_trace(go.Scatter(x=d26['Mês'], y=d26['Lucro'], name='Lucro 2026', line=dict(color=COLORS['green_dark'], width=3), mode='lines+markers'), secondary_y=True)
            fig.update_layout(barmode='group', height=380, margin=dict(l=20,r=20,t=30,b=20), legend=dict(orientation="h",y=-0.15), plot_bgcolor='white', yaxis_title="Faturamento (R$)")
            fig.update_yaxes(title_text="Lucro (R$)", secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)
        render_tooltip("Evolução Mensal 2025 vs 2026", "Barras cinzas = 2025. Barras amarelas = 2026. Linhas = lucro.", "Compare cada mês lado a lado.", "Identifica tendências de crescimento ou queda.", f"Se {mes_nome}/26 (amarelo) está menor que {mes_nome}/25 (cinza), o faturamento caiu.")

    with col_right:
        render_section(f"Participação por Categoria ({mes_nome}/26)")
        vms = vm.sort_values('Vlr_Venda', ascending=False)
        def mc(md):
            if md > 55: return COLORS['green_dark']
            elif md > 40: return COLORS['green']
            elif md > 30: return COLORS['orange']
            else: return COLORS['red']
        vms['Color'] = vms['Markdown_Pct'].apply(mc)
        fig_tree = go.Figure(go.Treemap(labels=vms['Categoria'], parents=['']*len(vms), values=vms['Vlr_Venda'], texttemplate="<b>%{label}</b><br>R$%{value:,.0f}", marker=dict(colors=vms['Color']), hovertemplate="<b>%{label}</b><br>R$%{value:,.2f}<extra></extra>"))
        fig_tree.update_layout(height=380, margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig_tree, use_container_width=True)
        st.caption("🟢 Margem > 55%  |  🟡 40-55%  |  🟠 30-40%  |  🔴 < 30%")
        render_tooltip("Treemap por Categoria", "Tamanho = faturamento. Cor = margem.", "Blocos grandes + verdes = categorias fortes.", "Mostra de onde vem o dinheiro e se é lucrativo.")

    render_section(f"Top 10 Produtos por Lucro — {mes_nome}/26")
    top10 = produtos.nlargest(10, 'Lucro_Total'); top10['Custo'] = top10['Receita_Total'] - top10['Lucro_Total']
    fig_top = go.Figure()
    fig_top.add_trace(go.Bar(y=top10['Produto'], x=top10['Custo'], name='Custo', orientation='h', marker_color='#D5DBDB'))
    fig_top.add_trace(go.Bar(y=top10['Produto'], x=top10['Lucro_Total'], name='Lucro', orientation='h', marker_color=COLORS['green'], text=[f"R$ {v:,.0f}" for v in top10['Lucro_Total']], textposition='outside', textfont_size=10))
    fig_top.update_layout(barmode='stack', height=350, margin=dict(l=10,r=80,t=10,b=10), legend=dict(orientation="h",y=-0.1), plot_bgcolor='white', yaxis=dict(autorange="reversed"), xaxis_title="R$")
    st.plotly_chart(fig_top, use_container_width=True)
    lt = top10['Lucro_Total'].sum(); ltot = produtos['Lucro_Total'].sum(); pct = safe_div(lt, ltot) * 100
    render_tooltip("Top 10 por Lucro", "Os 10 produtos mais lucrativos. Cinza = custo, verde = lucro.", "Quanto mais verde, melhor a margem.", "Proteger estoque e preço desses produtos a todo custo.", f"Juntos representam {pct:.0f}% do lucro total.")
    render_story(f"Os 10 produtos mais lucrativos representam {pct:.0f}% do lucro. {top10.iloc[0]['Produto']} lidera com R$ {top10.iloc[0]['Lucro_Total']:,.0f}.")


# ============================================================
# PÁGINA 2: INTELIGÊNCIA DE PREÇOS
# ============================================================
def page_inteligencia_precos(data):
    st.markdown("## 💰 Inteligência de Preços")
    st.markdown("*Onde estou deixando dinheiro na mesa?*")
    mes_nome, _ = get_mes_ref(data['yoy']); render_periodo_badge(mes_nome, 2026); st.markdown("---")
    vm = data['vendas_mensais']; erosao = data['erosao']; produtos = data['produtos']
    tv = vm['Vlr_Venda'].sum()
    mdm = safe_div((vm['Vlr_Venda'] * vm['Markdown_Pct'] / 100).sum(), tv) * 100
    cs = erosao[erosao['Alerta'].str.contains('SUBIU', na=False)]
    cc = erosao[erosao['Alerta'].str.contains('CAIU', na=False)]
    ca = produtos[produtos['Curva'] == 'A']; mb = ca[ca['Margem_Media'] < 35]
    oport = mb['Receita_Total'].sum() * 0.05

    c1, c2, c3 = st.columns(3)
    with c1: render_kpi_card("Markdown Médio Ponderado", f"{mdm:.1f}%", f"De cada R$1 vendido, R$ {mdm/100:.2f} é margem")
    with c2: render_kpi_card("Produtos com Custo Subindo", f"{len(cs)}", "Curva A com erosão detectada", "kpi-negative")
    with c3: render_kpi_card("Oportunidade Estimada", f"R$ {oport:,.0f}/mês", f"{len(mb)} produtos com margem < 35%", "kpi-neutral")
    render_tooltip("KPIs de Preços", "Markdown = margem bruta. Erosão = custo subiu sem reajuste.", "Markdown alto = saudável. Custo subindo = alerta.", "Proteger a margem é proteger o lucro.", f"{len(cs)} produtos precisam de reajuste.")
    render_story(f"Margem média: {mdm:.1f}%. {len(cs)} produtos Curva A com custo subindo — reajustar para evitar erosão.")
    st.markdown("---")

    cl, cr = st.columns([3, 2])
    with cl:
        render_section(f"Duelo de Produtos ({mes_nome}/26)")
        cap = ca[ca['Receita_Total'] > 50].copy()
        fig = px.scatter(cap, x='Receita_Total', y='Margem_Media', size='Lucro_Total', color='Classificacao', hover_name='Produto',
            hover_data={'Receita_Total':':.2f','Lucro_Total':':.2f','Margem_Media':':.1f','Dias_Vendidos':True},
            color_discrete_map={'⭐ Estrela':COLORS['green'],'💰 Gerador de Caixa':COLORS['yellow'],'🔍 Oportunidade':COLORS['blue'],'⚠️ Peso Morto':COLORS['red']}, size_max=30)
        ar = cap['Receita_Total'].mean()
        fig.add_hline(y=mdm, line_dash="dash", line_color="#999", annotation_text=f"Margem: {mdm:.0f}%")
        fig.add_vline(x=ar, line_dash="dash", line_color="#999", annotation_text=f"Receita: R${ar:.0f}")
        fig.update_layout(height=450, plot_bgcolor='white', margin=dict(l=20,r=20,t=30,b=20), xaxis_title="Faturamento (R$)", yaxis_title="Margem (%)", legend=dict(orientation="h",y=-0.15))
        st.plotly_chart(fig, use_container_width=True)
        render_tooltip("Scatter Plot de Preços", "Cada bolha = produto Curva A. X = faturamento. Y = margem. Tamanho = lucro.", "Superior direito = melhor. Inferior direito = vende mas não lucra.", "Identifica onde reajustar preço.", "Produto com alto faturamento e margem 15% precisa de reajuste.")

    with cr:
        render_section(f"Ranking Margem por Categoria ({mes_nome}/26)")
        crk = vm[['Categoria','Vlr_Venda','Vlr_Lucro','Markdown_Pct']].copy()
        crk = crk.sort_values('Markdown_Pct', ascending=False)
        crk['Status'] = crk['Markdown_Pct'].apply(lambda x: '🟢' if x > 55 else ('🟡' if x > 40 else '🔴'))
        crk['Fat.'] = crk['Vlr_Venda'].apply(lambda x: f"R$ {x:,.0f}")
        crk['Markdown'] = crk['Markdown_Pct'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(crk[['Status','Categoria','Fat.','Markdown']].reset_index(drop=True), use_container_width=True, height=420, hide_index=True)
        render_tooltip("Ranking por Categoria", "24 categorias ordenadas por margem. 🟢>55% 🟡40-55% 🔴<40%.", "Categorias 🔴 com alto faturamento são as mais urgentes.", "Renegociar fornecedores ou reajustar preços.")

    render_section(f"🚨 Alerta de Erosão — Curva A ({mes_nome}/26)")
    st.markdown("*Produtos onde o custo de reposição mudou significativamente.*")
    t1, t2 = st.tabs(["🔴 Custo Subiu", "🟢 Custo Caiu"])
    with t1:
        if not cs.empty:
            df = cs[['Produto','Vlr_Venda','Margem_Pct','Markdown_Pct','Markdown_Ult_Entrada','Erosao_Margem']].copy()
            df.columns = ['Produto','Faturamento','Margem %','Markdown Atual','Markdown Ult. Entrada','Erosão (pts)']
            st.dataframe(df.sort_values('Erosão (pts)', ascending=False).reset_index(drop=True), use_container_width=True, hide_index=True)
            render_story(f"{len(cs)} produtos com custo subindo. Reajustar preço para proteger margem futura.")
        else: st.success("Nenhum produto com custo subindo!")
    with t2:
        if not cc.empty:
            df = cc[['Produto','Vlr_Venda','Margem_Pct','Markdown_Pct','Markdown_Ult_Entrada','Erosao_Margem']].copy()
            df.columns = ['Produto','Faturamento','Margem %','Markdown Atual','Markdown Ult. Entrada','Erosão (pts)']
            st.dataframe(df.sort_values('Erosão (pts)').reset_index(drop=True), use_container_width=True, hide_index=True)
            render_story(f"{len(cc)} produtos com custo caindo. Mantenha preço para aumentar margem!")
        else: st.info("Nenhum produto com custo caindo.")
    render_tooltip("Erosão de Margem", "Compara markdown atual vs última entrada. Diferença = tendência do custo.", "Positivo = custo subiu (ruim). Negativo = custo caiu (bom).", "Alerta antecipado do que VAI acontecer com a margem.", "Açúcar com markdown 53% atual e 40% última entrada = custo subiu, margem vai cair.")


# ============================================================
# PÁGINA 3: MAPA DE PRODUTOS
# ============================================================
def page_mapa_produtos(data):
    st.markdown("## 🗺️ Mapa de Produtos — Matriz de Rentabilidade")
    st.markdown("*Quais produtos são estrelas e quais são peso morto?*")
    mes_nome, _ = get_mes_ref(data['yoy']); render_periodo_badge(mes_nome, 2026); st.markdown("---")
    p = data['produtos']
    est = p[p['Classificacao'].str.contains('Estrela')]; ger = p[p['Classificacao'].str.contains('Gerador')]
    opo = p[p['Classificacao'].str.contains('Oportunidade')]; pm = p[p['Classificacao'].str.contains('Peso Morto')]
    lt = p['Lucro_Total'].sum(); ps = p.sort_values('Lucro_Total', ascending=False)
    ps['LA'] = ps['Lucro_Total'].cumsum(); n80 = (ps['LA'] <= lt * 0.8).sum() + 1

    c1, c2, c3, c4 = st.columns(4)
    with c1: render_kpi_card("⭐ Estrelas", f"{len(est)}", f"R$ {est['Lucro_Total'].sum():,.0f} lucro")
    with c2: render_kpi_card("💰 Geradores", f"{len(ger)}", f"R$ {ger['Lucro_Total'].sum():,.0f} lucro")
    with c3: render_kpi_card("🔍 Oportunidades", f"{len(opo)}", f"R$ {opo['Lucro_Total'].sum():,.0f} lucro")
    with c4: render_kpi_card("⚠️ Peso Morto", f"{len(pm)}", f"R$ {pm['Lucro_Total'].sum():,.0f} lucro")
    render_tooltip("Matriz 2×2", "Giro × Margem. ⭐Alto/Alto 💰Alto/Baixo 🔍Baixo/Alto ⚠️Baixo/Baixo.", "⭐Proteger 💰Renegociar 🔍Dar visibilidade ⚠️Avaliar remoção.", "Permite priorizar decisões sobre cada grupo.", f"Apenas {n80} de {len(p):,} produtos geram 80% do lucro.")
    render_story(f"Apenas {n80} produtos (de {len(p):,}) geram 80% do lucro. As {len(est)} Estrelas são intocáveis.")
    st.markdown("---")

    render_section(f"Matriz de Rentabilidade ({mes_nome}/26)")
    pp = p[p['Receita_Total'] > 20].copy()
    fig = px.scatter(pp, x='Giro', y='Margem_Media', size='Receita_Total', color='Classificacao', hover_name='Produto',
        hover_data={'Receita_Total':':.2f','Lucro_Total':':.2f','Dias_Vendidos':True,'Curva':True},
        color_discrete_map={'⭐ Estrela':COLORS['green'],'💰 Gerador de Caixa':COLORS['yellow'],'🔍 Oportunidade':COLORS['blue'],'⚠️ Peso Morto':'#CCCCCC'}, size_max=35)
    fig.add_hline(y=50, line_dash="dash", line_color="#999", annotation_text="Margem 50%")
    fig.add_vline(x=0.6, line_dash="dash", line_color="#999", annotation_text="Giro 60%")
    fig.add_annotation(x=0.85,y=85,text="⭐ ESTRELAS",showarrow=False,font=dict(size=12,color=COLORS['green']))
    fig.add_annotation(x=0.85,y=15,text="💰 GERADORES",showarrow=False,font=dict(size=12,color=COLORS['orange']))
    fig.add_annotation(x=0.15,y=85,text="🔍 OPORTUNIDADES",showarrow=False,font=dict(size=12,color=COLORS['blue']))
    fig.add_annotation(x=0.15,y=15,text="⚠️ PESO MORTO",showarrow=False,font=dict(size=12,color=COLORS['red']))
    fig.update_layout(height=500, plot_bgcolor='white', margin=dict(l=20,r=20,t=30,b=20), xaxis_title="Giro (% dias com venda)", yaxis_title="Margem (%)", xaxis=dict(range=[-0.05,1.05], tickformat='.0%'), legend=dict(orientation="h",y=-0.12))
    st.plotly_chart(fig, use_container_width=True)
    render_tooltip("Scatter Plot Giro vs Margem", "Cada bolha = produto. X = giro. Y = margem. Tamanho = faturamento.", "Superior direito = ⭐. Inferior direito = 💰. Passe o mouse para ver detalhes.", "Ferramenta principal para decisões de mix.")

    cl, cr = st.columns(2)
    with cl:
        render_section("⭐ Estrelas")
        if not est.empty:
            df = est[['Produto','Dias_Vendidos','Margem_Media','Receita_Total','Lucro_Total']].copy()
            df.columns = ['Produto','Dias','Margem %','Receita','Lucro']
            st.dataframe(df.sort_values('Lucro', ascending=False).reset_index(drop=True), use_container_width=True, hide_index=True)
        render_section("🔍 Oportunidades (Top 15)")
        ot = opo.nlargest(15, 'Lucro_Total')
        if not ot.empty:
            df = ot[['Produto','Dias_Vendidos','Margem_Media','Receita_Total','Lucro_Total']].copy()
            df.columns = ['Produto','Dias','Margem %','Receita','Lucro']
            st.dataframe(df.reset_index(drop=True), use_container_width=True, hide_index=True)
    with cr:
        render_section("💰 Geradores de Caixa")
        if not ger.empty:
            df = ger[['Produto','Dias_Vendidos','Margem_Media','Receita_Total','Lucro_Total']].copy()
            df.columns = ['Produto','Dias','Margem %','Receita','Lucro']
            st.dataframe(df.sort_values('Receita', ascending=False).reset_index(drop=True), use_container_width=True, hide_index=True)
        render_section("⚠️ Peso Morto (Top 15)")
        pmt = pm.nlargest(15, 'Receita_Total')
        if not pmt.empty:
            df = pmt[['Produto','Dias_Vendidos','Margem_Media','Receita_Total','Lucro_Total']].copy()
            df.columns = ['Produto','Dias','Margem %','Receita','Lucro']
            st.dataframe(df.reset_index(drop=True), use_container_width=True, hide_index=True)

# ============================================================
# PÁGINA 4: DIAGNÓSTICO DE FATURAMENTO
# ============================================================
def page_diagnostico(data):
    st.markdown("## 🔍 Diagnóstico de Faturamento")
    st.markdown("*Menos clientes, menos gasto, ou mix mudou?*")
    yoy = data['yoy']; mes_nome, _ = get_mes_ref(yoy); render_periodo_badge(mes_nome, 2026); st.markdown("---")
    vm = data['vendas_mensais']; vd = data['vendas_diarias']
    fat = vm['Vlr_Venda'].sum(); cup = vm['Qtde_Documentos'].sum(); tk = safe_div(fat, cup)
    yoy_mes = yoy[yoy['Receita_2026'] > 0]
    c25 = t25 = vc = vt = r25 = 0.0
    if not yoy_mes.empty:
        r = yoy_mes.iloc[-1]; c25 = r.get('Cupons_2025',0) or 0; r25 = r.get('Receita_2025',0) or 0
        t25 = safe_div(r25, c25); vc = safe_div(cup - c25, c25)*100; vt = safe_div(tk - t25, t25)*100

    c1, c2, c3, c4 = st.columns(4)
    with c1: render_kpi_card("FATURAMENTO =", f"R$ {fat:,.0f}", "Cupons × Ticket Médio")
    with c2: render_kpi_card("Nº Cupons", f"{cup:,.0f}", f"{delta_arrow(vc)} {vc:+.0f}% vs {mes_nome}/25", delta_color(vc))
    with c3: render_kpi_card("× Ticket Médio", f"R$ {tk:.2f}", f"{delta_arrow(vt)} {vt:+.0f}% vs {mes_nome}/25", delta_color(vt))
    with c4:
        if r25 > 0 and c25 > 0:
            ic = (cup - c25)*t25; it = (tk - t25)*cup
            render_kpi_card("Diagnóstico", "Fluxo ↓" if abs(ic) > abs(it) else "Ticket ↓", f"Cupons: R$ {ic:+,.0f} | Ticket: R$ {it:+,.0f}")
        else: render_kpi_card("Diagnóstico", "—", "Sem dados YoY")
    render_tooltip("Decomposição do Faturamento", "FAT = Cupons × Ticket. Se caiu, ou veio menos gente ou gastou menos.", "'Fluxo ↓' = problema de atração. 'Ticket ↓' = problema de gasto por cliente.", "Fluxo → marketing/fachada. Ticket → cross-selling/mix.", f"{mes_nome}/26: {cup:,.0f} × R$ {tk:.2f}. {mes_nome}/25: {c25:,.0f} × R$ {t25:.2f}.")
    render_story(f"Faturamento = {cup:,.0f} cupons × R$ {tk:.2f}. Fluxo variou {vc:+.0f}% e ticket variou {vt:+.0f}% vs {mes_nome}/25.")
    st.markdown("---")

    cl, cr = st.columns(2)
    with cl:
        render_section(f"Contribuição por Categoria ({mes_nome}/26)")
        vw = vm[['Categoria','Vlr_Venda','Vlr_Lucro']].sort_values('Vlr_Venda', ascending=False).head(12)
        fig = go.Figure(go.Bar(x=vw['Categoria'], y=vw['Vlr_Venda'], marker_color=[COLORS['green'] if l>0 else COLORS['red'] for l in vw['Vlr_Lucro']], text=[f"R${v:,.0f}" for v in vw['Vlr_Venda']], textposition='outside', textfont_size=9))
        fig.update_layout(height=380, plot_bgcolor='white', margin=dict(l=10,r=10,t=10,b=80), xaxis_tickangle=-45, yaxis_title="Faturamento (R$)")
        st.plotly_chart(fig, use_container_width=True)
        render_tooltip("Contribuição por Categoria", "Top 12 categorias. Verde = lucro positivo.", "Barras mais altas = mais faturamento.", "Identifica motores do faturamento.")

    with cr:
        render_section(f"Heatmap por Dia ({mes_nome}/26)")
        vc = vd.copy(); vc['Data'] = pd.to_datetime(vc['Data']); vc['Dia_Semana'] = vc['Data'].dt.day_name()
        dm = {'Monday':'Segunda','Tuesday':'Terça','Wednesday':'Quarta','Thursday':'Quinta','Friday':'Sexta','Saturday':'Sábado','Sunday':'Domingo'}
        vc['DSP'] = vc['Dia_Semana'].map(dm); do = ['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo']
        ds = vc.groupby([vc['Data'].dt.isocalendar().week.rename('Sem'),'DSP'])['Vlr_Venda'].sum().reset_index()
        hp = ds.pivot(index='Sem', columns='DSP', values='Vlr_Venda').fillna(0)
        hp = hp.reindex(columns=[d for d in do if d in hp.columns])
        fig = px.imshow(hp.values, x=hp.columns, y=[f"Sem {int(s)}" for s in hp.index], color_continuous_scale='YlOrRd', labels=dict(x="Dia",y="Semana",color="Fat."), text_auto='.0f')
        fig.update_layout(height=380, margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig, use_container_width=True)
        render_tooltip("Heatmap Semanal", f"Faturamento de cada dia de {mes_nome}/26.", "Cores quentes = dias fortes. Frias = fracos.", "Identifica padrões semanais e dias atípicos.")

    render_section(f"Faturamento Médio por Dia ({mes_nome}/26)")
    da = vc.groupby('DSP').agg(FT=('Vlr_Venda','sum'), D=('Data','nunique')).reset_index()
    da['FM'] = da['FT'] / da['D']
    da['DSP'] = pd.Categorical(da['DSP'], categories=do, ordered=True); da = da.sort_values('DSP')
    fig = go.Figure(go.Bar(x=da['DSP'], y=da['FM'], marker_color=[COLORS['yellow'] if d!='Domingo' else COLORS['red'] for d in da['DSP']], text=[f"R$ {v:,.0f}" for v in da['FM']], textposition='outside'))
    fig.update_layout(height=280, plot_bgcolor='white', margin=dict(l=10,r=10,t=10,b=10), yaxis_title="Fat. Médio (R$)")
    st.plotly_chart(fig, use_container_width=True)
    bd = da.loc[da['FM'].idxmax(),'DSP'] if not da.empty else "N/A"; wd = da.loc[da['FM'].idxmin(),'DSP'] if not da.empty else "N/A"
    render_tooltip("Faturamento por Dia da Semana", f"Média diária em {mes_nome}/26. Domingo em vermelho.", "Barras altas = dias fortes. Use para planejar estoque.", "Promoções nos dias fracos, reforço nos fortes.")
    render_story(f"{bd} é o mais forte, {wd} o mais fraco. Promoções para {wd}, reforço de estoque para {bd}.")

# ============================================================
# PÁGINA 5: SAZONALIDADE
# ============================================================
def page_sazonalidade(data):
    st.markdown("## 📈 Sazonalidade e Tendências")
    st.markdown("*Padrão de 2025 para planejar 2026*"); st.markdown("---")
    yoy = data['yoy']; p = data['produtos']
    fa25 = yoy['Receita_2025'].sum(); fmm25 = safe_div(fa25, 12); la25 = yoy['Lucro_2025'].sum()
    m26 = yoy[yoy['Receita_2026'] > 0]; fa26 = m26['Receita_2026'].sum()

    c1, c2, c3, c4 = st.columns(4)
    with c1: render_kpi_card("Faturamento 2025 (Completo)", f"R$ {fa25:,.0f}", f"Média: R$ {fmm25:,.0f}/mês")
    with c2: render_kpi_card("Lucro 2025 (Completo)", f"R$ {la25:,.0f}", f"Margem: {safe_div(la25,fa25)*100:.1f}%")
    with c3: render_kpi_card("Acumulado 2026", f"R$ {fa26:,.0f}", f"{len(m26)} mês(es)")
    with c4:
        j25 = yoy[yoy['Mes_Num']==1]['Receita_2025'].values; j25 = j25[0] if len(j25)>0 else 0
        f25 = yoy[yoy['Mes_Num']==2]['Receita_2025'].values; f25 = f25[0] if len(f25)>0 else 0
        j26 = yoy[yoy['Mes_Num']==1]['Receita_2026'].values; j26 = j26[0] if len(j26)>0 else 0
        if j25>0 and f25>0 and j26>0:
            sf = f25/j25; pf = j26*sf
            render_kpi_card("Projeção Fev/26", f"R$ {pf:,.0f}", f"Fev/25 foi {(sf-1)*100:+.1f}% vs Jan/25")
        else: render_kpi_card("Projeção Fev/26", "—", "Dados insuficientes")
    render_tooltip("KPIs Sazonalidade", "2025 completo (referência) + 2026 parcial + projeção.", "Projeção usa padrão sazonal: se Fev/25 foi X% vs Jan/25, aplica sobre Jan/26.", "Planejar compras, estoque e caixa.")
    st.markdown("---")

    cl, cr = st.columns([3, 2])
    with cl:
        render_section("Sazonalidade — 2025 (Completo) vs 2026 (Parcial)")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=MESES_LABELS, y=yoy['Receita_2025'], name='2025 (completo)', mode='lines+markers+text', line=dict(color='#AAA',width=2), marker=dict(size=8), text=[f"R${v/1000:.0f}k" for v in yoy['Receita_2025']], textposition='top center', textfont_size=9))
        r26 = yoy['Receita_2026'].tolist(); ml26 = [MESES_LABELS[i] for i,v in enumerate(r26) if v>0]; rv26 = [v for v in r26 if v>0]
        if rv26: fig.add_trace(go.Scatter(x=ml26, y=rv26, name='2026 (real)', mode='lines+markers+text', line=dict(color=COLORS['yellow'],width=3), marker=dict(size=12,symbol='diamond'), text=[f"R${v/1000:.0f}k" for v in rv26], textposition='bottom center', textfont_size=10))
        fig.add_hline(y=fmm25, line_dash="dot", line_color="#CCC", annotation_text=f"Média 2025: R${fmm25/1000:.0f}k")
        fig.update_layout(height=400, plot_bgcolor='white', margin=dict(l=20,r=20,t=30,b=20), yaxis_title="Faturamento (R$)", legend=dict(orientation="h",y=-0.1))
        st.plotly_chart(fig, use_container_width=True)
        render_tooltip("Sazonalidade 2025 vs 2026", "Cinza = 2025. Losangos amarelos = 2026 real. Linha pontilhada = média 2025.", "Compare o losango de 2026 com o ponto do MESMO mês de 2025.", "2025 mostra o padrão. Se Março/25 foi pico, espere algo similar em 2026.")

    with cr:
        render_section("Índice de Sazonalidade — 2025")
        ys = yoy.copy(); ys['Idx'] = ys['Receita_2025'].apply(lambda x: safe_div(x, fmm25))
        fig = go.Figure(go.Bar(x=MESES_LABELS, y=ys['Idx'], marker_color=[COLORS['green'] if v>1 else COLORS['red'] for v in ys['Idx']], text=[f"{v:.2f}" for v in ys['Idx']], textposition='outside', textfont_size=10))
        fig.add_hline(y=1, line_dash="solid", line_color="#999", line_width=2)
        fig.update_layout(height=400, plot_bgcolor='white', margin=dict(l=20,r=20,t=30,b=20), yaxis_title="Índice (1.00 = média)")
        st.plotly_chart(fig, use_container_width=True)
        render_tooltip("Índice de Sazonalidade", "Cada barra = faturamento do mês ÷ média anual de 2025. 1.00 = exatamente na média.", "Verde (>1.00) = mês forte. Vermelho (<1.00) = mês fraco. Ex: 1.15 = 15% acima da média.", "Prever meses fortes e fracos de 2026.", f"Média 2025: R$ {fmm25:,.0f}. Índice 1.20 = ~R$ {fmm25*1.2:,.0f}.")

    render_section("Mix de Produtos — 2025 (Completo)")
    sp = yoy[['Mes','SKUs_2025']].copy(); sp = sp[sp['SKUs_2025']>0]
    if not sp.empty:
        fig = go.Figure(go.Scatter(x=sp['Mes'], y=sp['SKUs_2025'], mode='lines+markers+text', line=dict(color=COLORS['blue'],width=2), marker=dict(size=10), text=sp['SKUs_2025'].astype(int).astype(str), textposition='top center'))
        fig.update_layout(height=280, plot_bgcolor='white', margin=dict(l=20,r=20,t=30,b=20), yaxis_title="Nº SKUs")
        st.plotly_chart(fig, use_container_width=True)
        p1=sp.iloc[0]['SKUs_2025']; u1=sp.iloc[-1]['SKUs_2025']
        render_tooltip("Evolução do Mix", f"SKUs vendidos por mês em 2025.", "Linha descendo = menos variedade.", "Menos produtos = menos motivos para o cliente.", f"De {int(p1)} para {int(u1)} ({int(u1-p1)}).")
        render_story(f"Mix encolheu de {int(p1)} para {int(u1)} SKUs em 2025 ({int(u1-p1)}).")

    render_section("Tendência — 12 Meses Móveis")
    ra = yoy['Receita_2025'].tolist()
    for _, r in yoy.iterrows():
        if r['Receita_2026'] > 0: ra.append(r['Receita_2026'])
    if len(ra) >= 12:
        rol = []; lbl = []
        for i in range(11, len(ra)):
            rol.append(sum(ra[max(0,i-11):i+1]))
            lbl.append((MESES_LABELS[i]+'/25') if i < 12 else (MESES_LABELS[i-12]+'/26'))
        fig = go.Figure(go.Scatter(x=lbl, y=rol, mode='lines+markers', line=dict(color=COLORS['blue'],width=3), fill='tozeroy', fillcolor='rgba(46,134,193,0.1)'))
        fig.update_layout(height=280, plot_bgcolor='white', margin=dict(l=20,r=20,t=30,b=20), yaxis_title="Fat. Acum. 12m (R$)")
        st.plotly_chart(fig, use_container_width=True)
        render_tooltip("12 Meses Móveis", "Soma dos últimos 12 meses em cada ponto. Elimina sazonalidade.", "Subindo = negócio crescendo. Descendo = encolhendo.", "Melhor indicador de tendência real.")
        if len(rol)>1:
            tp = safe_div(rol[-1]-rol[0], rol[0])*100
            render_story(f"Faturamento 12m: R$ {rol[-1]:,.0f}. Tendência {'subindo' if tp>0 else 'caindo'} ({tp:+.1f}%).")


# ============================================================
# PÁGINA 6: VISÃO FUTURISTA (NOVA!)
# ============================================================
def page_visao_futurista(data):
    st.markdown("## 🔮 Visão Futurista — Cenários e Projeções")
    st.markdown("*Baseado nos dados, o que esperar e como se preparar?*"); st.markdown("---")
    CUSTO_FIXO = get_custo_fixo(); yoy = data['yoy']; vm = data['vendas_mensais']; produtos = data['produtos']
    mes_nome, mes_num = get_mes_ref(yoy)
    fat = vm['Vlr_Venda'].sum(); lb = vm['Vlr_Lucro'].sum(); mg = safe_div(lb, fat) * 100
    fmm25 = safe_div(yoy['Receita_2025'].sum(), 12)

    # Índices de sazonalidade e fator de ajuste
    idx_saz = {}
    for _, r in yoy.iterrows():
        if fmm25 > 0 and r['Receita_2025'] > 0:
            idx_saz[int(r['Mes_Num'])] = r['Receita_2025'] / fmm25
    md = yoy[yoy['Receita_2026'] > 0]
    fa = 1.0
    if not md.empty:
        r26 = md['Receita_2026'].sum(); r25eq = md['Receita_2025'].sum()
        if r25eq > 0: fa = r26 / r25eq

    # Projeções
    proj = []
    for m in range(1, 13):
        r25v = yoy[yoy['Mes_Num']==m]['Receita_2025'].values; r25 = r25v[0] if len(r25v)>0 else 0
        r26v = yoy[yoy['Mes_Num']==m]['Receita_2026'].values; r26 = r26v[0] if len(r26v)>0 else 0
        proj.append({'Mes': MESES_NOMES[m], 'Num': m, 'Lbl': MESES_LABELS[m-1], 'R25': r25, 'R26': r26, 'Proj': r25*fa if r25>0 else 0, 'Tipo': 'Real' if r26>0 else 'Projeção'})
    dp = pd.DataFrame(proj)

    render_section("📊 Projeção de Faturamento — 2026 Completo")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dp['Lbl'], y=dp['R25'], name='2025 (ref)', mode='lines+markers', line=dict(color='#CCC',width=2,dash='dot'), marker=dict(size=6)))
    dr = dp[dp['R26']>0]
    if not dr.empty: fig.add_trace(go.Bar(x=dr['Lbl'], y=dr['R26'], name='2026 (real)', marker_color=COLORS['yellow'], text=[f"R${v/1000:.0f}k" for v in dr['R26']], textposition='outside'))
    df = dp[(dp['R26']==0) & (dp['Proj']>0)]
    if not df.empty: fig.add_trace(go.Bar(x=df['Lbl'], y=df['Proj'], name='2026 (projeção)', marker_color='rgba(255,193,7,0.4)', text=[f"R${v/1000:.0f}k" for v in df['Proj']], textposition='outside', marker_line=dict(color=COLORS['yellow'],width=2)))
    fig.update_layout(height=400, plot_bgcolor='white', margin=dict(l=20,r=20,t=30,b=20), legend=dict(orientation="h",y=-0.1), yaxis_title="Faturamento (R$)", barmode='overlay')
    st.plotly_chart(fig, use_container_width=True)
    render_tooltip("Projeção 2026", "Amarelo sólido = real. Amarelo transparente = projeção sazonal. Cinza = 2025.", f"Fator de ajuste: {fa:.2f} (2026 está a {(fa-1)*100:+.1f}% de 2025).", "Antecipar faturamento para planejar compras e caixa.")
    st.markdown("---")

    # Cenários próximo mês
    pm = mes_num + 1 if mes_num < 12 else 1; pmn = MESES_NOMES[pm]
    ppj = dp[dp['Num']==pm]['Proj'].values; ppj = ppj[0] if len(ppj)>0 else fat
    cp = ppj*0.85; cr_ = ppj; co = ppj*1.15

    render_section(f"🎯 Cenários para {pmn}/26")
    c1, c2, c3 = st.columns(3)
    with c1:
        lp = cp*(mg/100)-CUSTO_FIXO
        render_kpi_card("😟 Pessimista (-15%)", f"R$ {cp:,.0f}", f"Lucro: R$ {lp:,.0f}", "kpi-negative" if lp<0 else "kpi-neutral")
    with c2:
        lr = cr_*(mg/100)-CUSTO_FIXO
        render_kpi_card("📊 Realista", f"R$ {cr_:,.0f}", f"Lucro: R$ {lr:,.0f}", "kpi-positive")
    with c3:
        lo = co*(mg/100)-CUSTO_FIXO
        render_kpi_card("🚀 Otimista (+15%)", f"R$ {co:,.0f}", f"Lucro: R$ {lo:,.0f}", "kpi-positive")
    render_tooltip(f"Cenários {pmn}", f"3 cenários baseados na projeção sazonal: pessimista, realista, otimista.", "Se o pessimista já dá lucro, o negócio está seguro.", "Planejar caixa e definir metas realistas.")
    st.markdown("---")

    # Velocímetro
    render_section(f"🏎️ Velocímetro — {mes_nome}/26 vs Metas")
    mm = safe_div(CUSTO_FIXO, mg/100) if mg > 0 else 0; mi = mm * 1.5
    fig = go.Figure(go.Indicator(mode="gauge+number+delta", value=fat,
        number={'prefix':"R$ ",'valueformat':',.0f'}, delta={'reference':mi,'prefix':"R$ ",'valueformat':',.0f'},
        title={'text':f"Faturamento {mes_nome}/26"},
        gauge={'axis':{'range':[0,mi*1.5],'tickformat':',.0f','tickprefix':'R$ '},
            'bar':{'color':COLORS['yellow']},
            'steps':[{'range':[0,mm],'color':'#FADBD8'},{'range':[mm,mi],'color':'#F9E79F'},{'range':[mi,mi*1.5],'color':'#D5F5E3'}],
            'threshold':{'line':{'color':COLORS['red'],'width':4},'thickness':0.75,'value':mm}}))
    fig.update_layout(height=300, margin=dict(l=20,r=20,t=60,b=20))
    st.plotly_chart(fig, use_container_width=True)
    render_tooltip("Velocímetro", f"Vermelho = prejuízo (<R$ {mm:,.0f}). Amarelo = acima do break-even. Verde = meta ideal.", f"Break-even: R$ {mm:,.0f}. Meta ideal: R$ {mi:,.0f}.", "Quanto mais para a direita (verde), mais saudável.")
    st.markdown("---")

    # Sazonalidade por categoria top 5
    render_section("📦 Top 5 Categorias — Performance e Tendência")
    vmtop = vm.nlargest(5, 'Vlr_Venda')
    cols = st.columns(5)
    for i, (_, row) in enumerate(vmtop.iterrows()):
        with cols[i]:
            idx = idx_saz.get(pm, 1.0)
            emoji = "🔥" if idx>1.1 else ("❄️" if idx<0.9 else "➡️")
            st.markdown(f"**{row['Categoria']}**")
            st.markdown(f"Fat: R$ {row['Vlr_Venda']:,.0f}")
            st.markdown(f"Margem: {row['Markdown_Pct']:.0f}%")
            st.markdown(f"{emoji} {pmn}: índice {idx:.2f}")
    render_tooltip("Top 5 Categorias", "As 5 maiores categorias + tendência sazonal do próximo mês.", "🔥 = mês forte (>1.10). ❄️ = fraco (<0.90). ➡️ = normal.", "Reforçar estoque das 🔥 e promover as ❄️.")
    st.markdown("---")

    # Plano de ação
    render_section(f"📋 Direcionamento Estratégico — {pmn}/26")
    est = produtos[produtos['Classificacao'].str.contains('Estrela')]
    pmo = produtos[produtos['Classificacao'].str.contains('Peso Morto')]
    erosao = data['erosao']; cs = erosao[erosao['Alerta'].str.contains('SUBIU', na=False)]

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"### ✅ O que FAZER em {pmn}")
        acoes = []
        if len(cs)>0: acoes.append(f"🔴 **Reajustar preços** de {len(cs)} produtos com custo subindo")
        if not est.empty:
            tops = est.nlargest(3,'Lucro_Total')['Produto'].tolist()
            acoes.append(f"⭐ **Garantir estoque** dos top Estrelas: {', '.join(tops[:3])}")
        idx_pm = idx_saz.get(pm, 1.0)
        if idx_pm > 1.05: acoes.append(f"📈 **Reforçar compras** — {pmn} é forte (índice {idx_pm:.2f})")
        elif idx_pm < 0.95: acoes.append(f"📢 **Planejar promoções** — {pmn} é fraco (índice {idx_pm:.2f})")
        acoes.append(f"🎯 **Meta faturamento**: R$ {cr_:,.0f}")
        acoes.append(f"💰 **Meta lucro líquido**: R$ {lr:,.0f}")
        for a in acoes: st.markdown(f"- {a}")
    with c2:
        st.markdown("### ⚠️ O que MONITORAR")
        yoy_m = yoy[yoy['Receita_2026']>0]
        c25_ref = yoy_m.iloc[-1]['Cupons_2025'] if not yoy_m.empty else 1
        cup_atual = vm['Qtde_Documentos'].sum()
        vc_ref = safe_div(cup_atual-c25_ref, c25_ref)*100
        st.markdown(f"- 👥 **Fluxo de clientes**: variou {vc_ref:+.0f}% vs ano anterior")
        st.markdown(f"- 📊 **Margem real**: manter acima de 15% (atual: {mg:.1f}%)")
        st.markdown(f"- 🏷️ **Erosão**: {len(cs)} produtos precisam reajuste")
        if len(pmo)>50: st.markdown(f"- 🗑️ **Peso Morto**: {len(pmo)} produtos a avaliar")
    render_tooltip("Plano de Ação", "Gerado automaticamente com base nos dados e projeções.", "Ações priorizadas por impacto: margem → estoque → sazonalidade.", "Revise com os sócios no início de cada mês.")


# ============================================================
# SIDEBAR E NAVEGAÇÃO
# ============================================================
def main():
    with st.sidebar:
        logo_path = Path("logo_dubairro.png")
        if logo_path.exists():
            st.image(str(logo_path), use_container_width=True)
        else:
            st.markdown("### 🏪 Mercado duBairro")
        st.markdown("**Painel dos Sócios**")
        st.markdown("---")

        pagina = st.radio("Navegação", [
            "📊 Resumo Executivo", "💰 Inteligência de Preços", "🗺️ Mapa de Produtos",
            "🔍 Diagnóstico de Faturamento", "📈 Sazonalidade e Tendências", "🔮 Visão Futurista",
        ], label_visibility="collapsed")

        st.markdown("---")
        st.markdown("##### 🎛️ Simulador")
        custo_fixo_input = st.number_input("Custo Fixo Mensal (R$)", value=CUSTO_FIXO_DEFAULT, step=500.0, format="%.2f",
            help="Ajuste para simular cenários. Ex: 'E se o aluguel aumentar 10%?'")
        st.session_state['custo_fixo'] = custo_fixo_input
        if custo_fixo_input != CUSTO_FIXO_DEFAULT:
            st.caption(f"⚡ Simulando com R$ {custo_fixo_input:,.2f}")

        st.markdown("---")
        st.markdown("##### ⚙️ Informações")
        st.markdown(f"**Custo Fixo:** R$ {custo_fixo_input:,.2f}")
        st.markdown(f"**Meta Líquida:** {META_LIQUIDA*100:.0f}%")
        st.markdown("---")
        st.caption("Mercado duBairro © 2026")
        st.caption("Dashboard de Gestão v2.0")

    try:
        data = load_data()
    except FileNotFoundError:
        st.error("⚠️ Arquivo **Base_PowerBI.xlsx** não encontrado!")
        st.stop()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        st.stop()

    if "Resumo" in pagina: page_resumo_executivo(data)
    elif "Preços" in pagina: page_inteligencia_precos(data)
    elif "Mapa" in pagina: page_mapa_produtos(data)
    elif "Diagnóstico" in pagina: page_diagnostico(data)
    elif "Sazonalidade" in pagina: page_sazonalidade(data)
    elif "Futurista" in pagina: page_visao_futurista(data)

if __name__ == "__main__":
    main()
