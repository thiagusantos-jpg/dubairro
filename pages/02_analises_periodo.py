"""
Página de Análises com Seletor de Período
Permite filtrar e analisar dados por mês e ano
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timedelta
from calendar import monthrange

st.set_page_config(
    page_title="Análises por Período | Mercado duBairro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📈 Análises por Período")
st.markdown("Selecione o período e explore os dados da API Mobne")

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def gerar_meses_disponiveis():
    """Gera lista de meses/anos disponíveis (últimos 24 meses)"""
    meses = []
    data_atual = datetime.now()

    for i in range(24):
        data = data_atual - timedelta(days=30*i)
        meses.append((data.month, data.year))

    return sorted(set(meses), reverse=True)


def carregar_vendas():
    """Carrega dados de vendas do JSON"""
    try:
        caminho = Path("public/data/vendas_mobne.json")
        if caminho.exists():
            with open(caminho) as f:
                data = json.load(f)
            return data.get("vendas", [])
    except:
        pass
    return []


def carregar_produtos():
    """Carrega dados de produtos do JSON"""
    try:
        caminho = Path("public/data/produtos.json")
        if caminho.exists():
            with open(caminho) as f:
                data = json.load(f)
            return data.get("produtos", [])
    except:
        pass
    return []


def filtrar_vendas_por_periodo(vendas: list, mes: int, ano: int) -> list:
    """Filtra vendas por mês e ano"""
    filtradas = []

    for venda in vendas:
        data_str = venda.get("DtaEmissao", "")
        if data_str:
            try:
                data = datetime.fromisoformat(data_str.replace("Z", "+00:00"))
                if data.month == mes and data.year == ano:
                    filtradas.append(venda)
            except:
                pass

    return filtradas


def calcular_metricas(vendas: list) -> dict:
    """Calcula métricas para o período"""
    if not vendas:
        return {
            "total_vendas": 0,
            "valor_total": 0.0,
            "ticket_medio": 0.0,
            "items": 0,
        }

    total_vendas = len(vendas)
    valor_total = sum(v.get("Valor", 0) for v in vendas if isinstance(v.get("Valor"), (int, float)))
    items = sum(len(v.get("PedidoItens", [])) for v in vendas)
    ticket_medio = valor_total / total_vendas if total_vendas > 0 else 0

    return {
        "total_vendas": total_vendas,
        "valor_total": valor_total,
        "ticket_medio": ticket_medio,
        "items": items,
    }


# ============================================================
# SIDEBAR - SELETORES DE PERÍODO
# ============================================================

with st.sidebar:
    st.header("🗓️ Período de Análise")

    meses_disponiveis = gerar_meses_disponiveis()

    # Seletores
    mes_selecionado = st.selectbox(
        "Mês",
        options=[m[0] for m in meses_disponiveis],
        format_func=lambda x: ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                               "Jul", "Ago", "Set", "Out", "Nov", "Dez"][x - 1]
    )

    ano_selecionado = st.selectbox(
        "Ano",
        options=sorted(set(m[1] for m in meses_disponiveis), reverse=True)
    )

    st.markdown("---")

    # Opções rápidas
    st.markdown("### ⚡ Atalhos")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Mês Atual", use_container_width=True):
            mes_selecionado = datetime.now().month
            ano_selecionado = datetime.now().year
            st.rerun()

    with col2:
        if st.button("Mês Anterior", use_container_width=True):
            data_anterior = datetime.now() - timedelta(days=30)
            mes_selecionado = data_anterior.month
            ano_selecionado = data_anterior.year
            st.rerun()

    st.markdown("---")

    # Info do período
    nome_mes = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][mes_selecionado - 1]

    st.info(f"📅 **Período Selecionado:**\n\n{nome_mes} de {ano_selecionado}")


# ============================================================
# CONTEÚDO PRINCIPAL
# ============================================================

# Carregar dados
vendas_todas = carregar_vendas()
produtos_todos = carregar_produtos()

# Filtrar por período
vendas_filtradas = filtrar_vendas_por_periodo(vendas_todas, mes_selecionado, ano_selecionado)

# Calcular métricas
metricas = calcular_metricas(vendas_filtradas)

# ============================================================
# CARDS DE MÉTRICAS
# ============================================================

st.markdown("## 📊 Resumo do Período")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total de Vendas",
        metricas["total_vendas"],
        delta="cupons",
        help="Número total de pedidos de venda"
    )

with col2:
    st.metric(
        "Valor Total",
        f"R$ {metricas['valor_total']:,.2f}",
        help="Faturamento total do período"
    )

with col3:
    st.metric(
        "Ticket Médio",
        f"R$ {metricas['ticket_medio']:,.2f}",
        help="Valor médio por venda"
    )

with col4:
    st.metric(
        "Items Vendidos",
        metricas["items"],
        help="Total de itens vendidos"
    )


# ============================================================
# ABAS DE ANÁLISE
# ============================================================

tabs = st.tabs(["Visão Geral", "Produtos", "Detalhes de Vendas", "Comparativo"])

with tabs[0]:
    st.markdown("### 📈 Visão Geral do Período")

    if vendas_filtradas:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🏪 Número de Vendas por Dia")

            vendas_por_dia = {}
            for venda in vendas_filtradas:
                data_str = venda.get("DtaEmissao", "")
                if data_str:
                    try:
                        data = datetime.fromisoformat(data_str.replace("Z", "+00:00"))
                        dia = data.strftime("%d/%m")
                        vendas_por_dia[dia] = vendas_por_dia.get(dia, 0) + 1
                    except:
                        pass

            if vendas_por_dia:
                df_dias = pd.DataFrame(list(vendas_por_dia.items()), columns=["Dia", "Vendas"])
                st.bar_chart(df_dias.set_index("Dia"))
            else:
                st.info("Sem dados para este período")

        with col2:
            st.markdown("#### 💰 Faturamento por Dia")

            faturamento_por_dia = {}
            for venda in vendas_filtradas:
                data_str = venda.get("DtaEmissao", "")
                valor = venda.get("Valor", 0) or 0
                if data_str:
                    try:
                        data = datetime.fromisoformat(data_str.replace("Z", "+00:00"))
                        dia = data.strftime("%d/%m")
                        faturamento_por_dia[dia] = faturamento_por_dia.get(dia, 0) + valor
                    except:
                        pass

            if faturamento_por_dia:
                df_fatura = pd.DataFrame(list(faturamento_por_dia.items()), columns=["Dia", "Faturamento"])
                st.line_chart(df_fatura.set_index("Dia"))
            else:
                st.info("Sem dados para este período")
    else:
        st.warning("Nenhuma venda encontrada para este período")
        st.info("Verifique se os dados foram sincronizados em 'Status de Sincronização'")

with tabs[1]:
    st.markdown("### 📦 Análise de Produtos")

    if produtos_todos:
        st.info(f"Total de {len(produtos_todos)} produtos cadastrados")

        # Tabela de produtos
        cols = ["ProdutoId", "Descricao", "Status", "Finalidade", "CategoriaId"]
        produtos_df = pd.DataFrame([
            {col: p.get(col, "") for col in cols}
            for p in produtos_todos[:20]
        ])

        st.dataframe(produtos_df, use_container_width=True)

        if len(produtos_todos) > 20:
            st.caption(f"Mostrando 20 de {len(produtos_todos)} produtos")
    else:
        st.warning("Nenhum produto sincronizado")

with tabs[2]:
    st.markdown("### 📋 Detalhes de Vendas")

    if vendas_filtradas:
        # Tabela simplificada de vendas
        vendas_resumo = []
        for v in vendas_filtradas[:50]:
            vendas_resumo.append({
                "ID": v.get("PedidoVendaId"),
                "Data": v.get("DtaEmissao", "").split("T")[0] if "DtaEmissao" in v else "",
                "Cliente": v.get("PessoaId"),
                "Valor": f"R$ {v.get('Valor', 0):,.2f}" if "Valor" in v else "N/A",
                "Situação": v.get("Situacao"),
            })

        df_vendas = pd.DataFrame(vendas_resumo)
        st.dataframe(df_vendas, use_container_width=True)

        if len(vendas_filtradas) > 50:
            st.caption(f"Mostrando 50 de {len(vendas_filtradas)} vendas")
    else:
        st.warning("Nenhuma venda neste período")

with tabs[3]:
    st.markdown("### 📊 Comparativo com Período Anterior")

    if mes_selecionado == 1:
        mes_anterior = 12
        ano_anterior = ano_selecionado - 1
    else:
        mes_anterior = mes_selecionado - 1
        ano_anterior = ano_selecionado

    vendas_anterior = filtrar_vendas_por_periodo(vendas_todas, mes_anterior, ano_anterior)
    metricas_anterior = calcular_metricas(vendas_anterior)

    nome_mes_anterior = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                         "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][mes_anterior - 1]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"#### 📊 Mês Atual ({datetime.now().strftime('%B')})")
        st.metric("Vendas", metricas["total_vendas"])
        st.metric("Faturamento", f"R$ {metricas['valor_total']:,.2f}")

    with col2:
        st.markdown(f"#### 📊 Período Anterior ({nome_mes_anterior} {ano_anterior})")
        st.metric("Vendas", metricas_anterior["total_vendas"])
        st.metric("Faturamento", f"R$ {metricas_anterior['valor_total']:,.2f}")

    # Variação
    if metricas_anterior["total_vendas"] > 0:
        var_vendas = ((metricas["total_vendas"] - metricas_anterior["total_vendas"])
                      / metricas_anterior["total_vendas"] * 100)
    else:
        var_vendas = 0

    if metricas_anterior["valor_total"] > 0:
        var_fatura = ((metricas["valor_total"] - metricas_anterior["valor_total"])
                      / metricas_anterior["valor_total"] * 100)
    else:
        var_fatura = 0

    st.markdown("---")
    st.markdown("#### 📈 Variação (%)")

    col1, col2 = st.columns(2)
    with col1:
        cor_vendas = "🟢" if var_vendas >= 0 else "🔴"
        st.markdown(f"{cor_vendas} **Vendas:** {var_vendas:+.1f}%")

    with col2:
        cor_fatura = "🟢" if var_fatura >= 0 else "🔴"
        st.markdown(f"{cor_fatura} **Faturamento:** {var_fatura:+.1f}%")

st.markdown("---")
st.caption(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
