"""
Página de Configurações
Manage fixed costs, meta, and business parameters
"""

import streamlit as st
import json
from pathlib import Path
from datetime import datetime

st.set_page_config(
    page_title="Configurações | Mercado duBairro",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("⚙️ Configurações do Dashboard")
st.markdown("Configure os parâmetros financeiros e metas do negócio")

# ============================================================
# ARQUIVO DE CONFIGURAÇÕES
# ============================================================

CONFIG_FILE = Path("public/data/configuracoes.json")


def carregar_configuracoes() -> dict:
    """Carrega configurações salvas"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass

    # Padrão
    return {
        "custo_fixo_mensal": 16913.46,
        "margem_meta": 15.0,
        "data_atualizacao": datetime.now().isoformat(),
    }


def salvar_configuracoes(config: dict):
    """Salva configurações em arquivo JSON"""
    config["data_atualizacao"] = datetime.now().isoformat()
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# ============================================================
# CARREGAR CONFIGURAÇÕES
# ============================================================

config = carregar_configuracoes()

# ============================================================
# ABAS
# ============================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "💰 Custos Fixos",
    "🎯 Metas",
    "📊 Visualização",
    "📝 Histórico"
])

# ============================================================
# TAB 1: CUSTOS FIXOS
# ============================================================

with tab1:
    st.markdown("## 💰 Custos Fixos Mensais")
    st.markdown("Configure os custos que a empresa tem mensalmente, independente do faturamento")

    # Divisão em colunas para melhor visualização
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🏢 Custo Fixo Mensal Total")

        custo_fixo_atual = config.get("custo_fixo_mensal", 16913.46)

        novo_custo = st.number_input(
            "Custo Fixo Mensal (R$)",
            min_value=0.0,
            step=100.0,
            value=custo_fixo_atual,
            help="Exemplo: Aluguel, Energia, Salários Fixos, etc.",
            key="custo_fixo_input"
        )

        st.info(f"""
        **Custo Fixo Atual:** R$ {custo_fixo_atual:,.2f}

        Este é o valor mínimo que o mercado precisa faturar para não ter prejuízo.

        Exemplo de itens:
        - 💧 Aluguel
        - 💡 Energia e Água
        - 👔 Salários Fixos
        - 📦 Manutenção e Equipamentos
        """)

    with col2:
        st.markdown("### 📋 Detalhamento (Opcional)")

        st.markdown("*Você pode detalhar os componentes do custo fixo abaixo:*")

        # Permitir adicionar custos detalhados
        custos_detalhes = config.get("custos_detalhes", {})

        col_a, col_b = st.columns(2)

        with col_a:
            aluguel = st.number_input(
                "Aluguel (R$)",
                min_value=0.0,
                step=100.0,
                value=custos_detalhes.get("aluguel", 0.0),
                key="aluguel_input"
            )

            salarios = st.number_input(
                "Salários Fixos (R$)",
                min_value=0.0,
                step=100.0,
                value=custos_detalhes.get("salarios", 0.0),
                key="salarios_input"
            )

        with col_b:
            utilidades = st.number_input(
                "Utilidades (Energia, Água, etc) (R$)",
                min_value=0.0,
                step=100.0,
                value=custos_detalhes.get("utilidades", 0.0),
                key="utilidades_input"
            )

            manutencao = st.number_input(
                "Manutenção (R$)",
                min_value=0.0,
                step=100.0,
                value=custos_detalhes.get("manutencao", 0.0),
                key="manutencao_input"
            )

        # Atualizar custo fixo com o total dos detalhes
        custo_calculado = aluguel + salarios + utilidades + manutencao

        st.markdown("---")
        st.markdown(f"### Total Calculado: R$ {custo_calculado:,.2f}")

        if custo_calculado > 0:
            if abs(custo_calculado - novo_custo) > 0.01:
                st.warning("⚠️ O total dos detalhes não corresponde ao custo fixo total acima")

        # Atualizar configuração
        config["custos_detalhes"] = {
            "aluguel": aluguel,
            "salarios": salarios,
            "utilidades": utilidades,
            "manutencao": manutencao,
        }

        if custo_calculado > 0:
            novo_custo = custo_calculado

    # ============================================================
    # SALVAR CUSTOS
    # ============================================================

    st.markdown("---")

    if st.button("💾 Salvar Configurações de Custo", use_container_width=True, type="primary"):
        config["custo_fixo_mensal"] = novo_custo
        salvar_configuracoes(config)
        st.success(f"✅ Custo fixo atualizado para R$ {novo_custo:,.2f}")
        st.rerun()


# ============================================================
# TAB 2: METAS
# ============================================================

with tab2:
    st.markdown("## 🎯 Metas e Objetivos")
    st.markdown("Defina as metas de margem, faturamento e outros indicadores")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Margem de Lucro")

        margem_meta_atual = config.get("margem_meta", 15.0)

        nova_margem = st.slider(
            "Meta de Margem Líquida (%)",
            min_value=0.0,
            max_value=50.0,
            step=0.5,
            value=margem_meta_atual,
            help="Percentual de lucro esperado sobre as vendas",
            key="margem_slider"
        )

        st.info(f"""
        **Meta Atual:** {nova_margem:.1f}%

        Exemplo: Se vender R$ 100, qual lucro mínimo esperado?
        - Meta 15% = R$ 15 de lucro em R$ 100 de venda
        - Meta 20% = R$ 20 de lucro em R$ 100 de venda

        **Benchmark do Varejo:** 12-18% é considerado bom
        """)

    with col2:
        st.markdown("### Meta de Faturamento")

        faturamento_meta = st.number_input(
            "Meta de Faturamento Mensal (R$)",
            min_value=0.0,
            step=1000.0,
            value=config.get("faturamento_meta", 100000.0),
            help="Quanto você precisa faturar por mês para atingir os objetivos",
            key="faturamento_meta_input"
        )

        # Calcular ponto de equilíbrio
        custo_fixo = config.get("custo_fixo_mensal", 16913.46)
        margem_decimal = nova_margem / 100
        ponto_equilibrio = custo_fixo / (1 - (1 - margem_decimal))

        st.warning(f"""
        **Ponto de Equilíbrio:** R$ {ponto_equilibrio:,.2f}

        Você precisa faturar este valor para cobrir os custos fixos
        e atingir a margem desejada.
        """)

    st.markdown("---")

    if st.button("💾 Salvar Metas", use_container_width=True, type="primary"):
        config["margem_meta"] = nova_margem
        config["faturamento_meta"] = faturamento_meta
        salvar_configuracoes(config)
        st.success(f"✅ Metas atualizadas: Margem {nova_margem:.1f}% | Faturamento R$ {faturamento_meta:,.2f}")
        st.rerun()


# ============================================================
# TAB 3: VISUALIZAÇÃO
# ============================================================

with tab3:
    st.markdown("## 📊 Resumo das Configurações Atuais")

    custo_fixo = config.get("custo_fixo_mensal", 16913.46)
    margem_meta = config.get("margem_meta", 15.0)
    faturamento_meta = config.get("faturamento_meta", 100000.0)

    # Cards informativos
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "💰 Custo Fixo Mensal",
            f"R$ {custo_fixo:,.2f}",
            help="Gastos fixos que não variam"
        )

    with col2:
        st.metric(
            "🎯 Meta de Margem",
            f"{margem_meta:.1f}%",
            help="Percentual de lucro esperado"
        )

    with col3:
        st.metric(
            "📈 Meta de Faturamento",
            f"R$ {faturamento_meta:,.2f}",
            help="Faturamento mínimo mensal"
        )

    st.markdown("---")

    st.markdown("### 📊 Cálculos Derivados")

    col1, col2 = st.columns(2)

    with col1:
        # Ponto de equilíbrio
        margem_decimal = margem_meta / 100
        ponto_eq = custo_fixo / (1 - (1 - margem_decimal))
        st.markdown(f"""
        **Ponto de Equilíbrio**

        R$ {ponto_eq:,.2f}

        *Faturamento necessário para não ter prejuízo*
        """)

        # Lucro esperado
        lucro_esperado = faturamento_meta * margem_decimal
        st.markdown(f"""
        **Lucro Esperado (com meta de faturamento)**

        R$ {lucro_esperado:,.2f}

        *Se atingir a meta de faturamento*
        """)

    with col2:
        # Detalhamento de custos
        custos = config.get("custos_detalhes", {})
        if custos and any(custos.values()):
            st.markdown("**Detalhamento de Custos Fixos**")
            for item, valor in custos.items():
                if valor > 0:
                    st.caption(f"• {item.replace('_', ' ').title()}: R$ {valor:,.2f}")
        else:
            st.info("Defina o detalhamento de custos na aba anterior")

        # Aviso de atualização
        data_att = config.get("data_atualizacao", "")
        if data_att:
            try:
                data_obj = datetime.fromisoformat(data_att)
                st.caption(f"Última atualização: {data_obj.strftime('%d/%m/%Y às %H:%M')}")
            except:
                st.caption("Data de atualização desconhecida")


# ============================================================
# TAB 4: HISTÓRICO
# ============================================================

with tab4:
    st.markdown("## 📝 Histórico de Alterações")
    st.info("Funcionalidade em desenvolvimento")

    st.markdown("""
    Aqui você verá:
    - 📅 Data e hora de cada alteração
    - 📊 Valores anteriores e novos
    - 👤 Quem fez a alteração (quando integrado com autenticação)
    - 📈 Gráfico de evolução das metas ao longo do tempo
    """)

    # Simulação de histórico
    st.markdown("---")
    st.markdown("### Alterações Recentes")

    historico = [
        {
            "data": config.get("data_atualizacao", ""),
            "tipo": "Configuração",
            "descricao": f"Custo fixo atualizado para R$ {config.get('custo_fixo_mensal', 16913.46):,.2f}",
        }
    ]

    for h in historico:
        if h["data"]:
            try:
                data_obj = datetime.fromisoformat(h["data"])
                st.caption(f"📅 {data_obj.strftime('%d/%m/%Y às %H:%M')}")
                st.markdown(f"**{h['tipo']}:** {h['descricao']}")
            except:
                pass
