"""
Dashboard de Gestão Estratégica - Mercado duBairro
Versão 1.2 - Integração Full API

Página Principal / Home
"""

import streamlit as st
from datetime import datetime
import json
from pathlib import Path

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="Mercado duBairro - Dashboard",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CSS CUSTOMIZADO
# ============================================================

st.markdown("""
<style>
    .main-header {
        font-size: 3em;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 10px;
    }
    .subtitle {
        font-size: 1.2em;
        color: #666;
        margin-bottom: 30px;
    }
    .card-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 20px;
        margin: 20px 0;
    }
    .card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .card.success {
        background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
        color: #333;
    }
    .card.warning {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        color: #333;
    }
    .card.info {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        color: #333;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-header">🏪 Mercado duBairro</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">Dashboard de Gestão Estratégica — v1.2 API Integrada</div>',
    unsafe_allow_html=True
)

st.markdown("---")

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.image("https://via.placeholder.com/200x100?text=Logo+Mercado", use_column_width=True)

    st.markdown("### 📱 Navegação")
    st.markdown("""
    Use o menu à esquerda para navegar entre as diferentes seções:

    - **📊 Status de Sincronização** — Veja o status dos dados da API
    - **📈 Análises por Período** — Explore dados por mês e ano
    - **⚙️ Configurações** — Custos, metas e parâmetros
    """)

    st.markdown("---")

    st.markdown("### ℹ️ Informações")
    st.markdown(f"""
    **Última atualização:**
    {datetime.now().strftime('%d/%m/%Y às %H:%M')}

    **Versão:** 1.2
    **Ambiente:** Production
    """)


# ============================================================
# STATUS RÁPIDO
# ============================================================

st.markdown("## 🚀 Status Geral do Sistema")

col1, col2, col3, col4 = st.columns(4)

# Carregar status de sincronização
def carregar_status_arquivo(caminho: Path) -> dict:
    """Carrega informações de sincronização de um arquivo JSON"""
    if not caminho.exists():
        return None
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "ultima_sync": data.get("ultima_sync", "Nunca"),
            "total": data.get("total", 0),
        }
    except:
        return None


data_dir = Path("public/data")

status_produtos = carregar_status_arquivo(data_dir / "produtos.json")
status_clientes = carregar_status_arquivo(data_dir / "clientes.json")
status_vendas = carregar_status_arquivo(data_dir / "vendas_mobne.json")

with col1:
    st.metric(
        "📦 Produtos",
        status_produtos["total"] if status_produtos else "—",
        help="Produtos sincronizados da API Mobne"
    )
    if status_produtos:
        st.caption(f"Última sync: {status_produtos['ultima_sync'][:10]}")

with col2:
    st.metric(
        "👥 Clientes",
        status_clientes["total"] if status_clientes else "—",
        help="Clientes sincronizados da API Mobne"
    )
    if status_clientes:
        st.caption(f"Última sync: {status_clientes['ultima_sync'][:10]}")

with col3:
    st.metric(
        "💳 Vendas",
        status_vendas["total"] if status_vendas else "—",
        help="Vendas sincronizadas da API Mobne"
    )
    if status_vendas:
        st.caption(f"Última sync: {status_vendas['ultima_sync'][:10]}")

with col4:
    # Carregar configurações
    config_file = Path("public/data/configuracoes.json")
    if config_file.exists():
        try:
            with open(config_file) as f:
                config = json.load(f)
            st.metric(
                "⚙️ Configurações",
                "✅ Configurado",
                help="Sistema de custo e metas"
            )
        except:
            st.metric("⚙️ Configurações", "⚠️ Erro")
    else:
        st.metric(
            "⚙️ Configurações",
            "⏳ Pendente",
            help="Configure os custos e metas"
        )


# ============================================================
# SEÇÃO PRINCIPAL
# ============================================================

st.markdown("---")
st.markdown("## 📊 O que é este Dashboard?")

st.markdown("""
Este é um **Dashboard de Gestão Estratégica** para o Mercado duBairro que responde a três
perguntas fundamentais sobre o seu negócio:

### ❓ As 3 Perguntas Essenciais

1. **O que aconteceu?** 📊
   Dados e métricas dos últimos períodos

2. **Por que aconteceu?** 🔍
   Análise de causas e fatores que impactaram

3. **O que fazer?** 💡
   Recomendações e ações para otimizar
""")

st.markdown("---")

st.markdown("## 🎯 Prioridades de Negócio")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 💰 Inteligência de Preços
    - Monitorar se os preços estão corretos
    - Detectar erosão de margem
    - Identificar oportunidades de aumento

    ### 🗂️ Mapa de Lucratividade
    - Produtos que geram lucro real
    - Identificar "peso morto"
    - Decisões de reposição
    """)

with col2:
    st.markdown("""
    ### 📈 Diagnóstico de Faturamento
    - Entender variações de vendas
    - Análise de preço, volume e fluxo
    - Heatmap por dia da semana

    ### 🚨 Monitoramento de Ruptura
    - Detectar falta de produtos
    - Produtos de alto giro sem venda
    - Alertas de reposição
    """)

st.markdown("---")

st.markdown("## 🔄 Fluxo de Dados")

st.markdown("""
```
API Mobne (REALTIME)
       ↓
   [Sync Service]
       ↓
   public/data/*.json
       ↓
   [Dashboard]
       ↓
   [Análises & Recomendações]
```
""")

st.info("""
**Dados Sincronizados:**
- ✅ Produtos (Cadastro e Preços)
- ✅ Clientes (Cadastro)
- ✅ Vendas (Histórico de Pedidos)
- ✅ Análises (Cálculos derivados)
""")

st.markdown("---")

st.markdown("## 🚀 Como Começar")

st.markdown("""
### 1️⃣ Sincronizar Dados
Acesse **📊 Status de Sincronização** e clique em "Sincronizar Tudo"

### 2️⃣ Configurar Parâmetros
Vá para **⚙️ Configurações** e defina:
- Custo Fixo Mensal
- Meta de Margem
- Meta de Faturamento

### 3️⃣ Explorar Dados
Em **📈 Análises por Período**, selecione um mês e explore os dados

### 4️⃣ Tomar Decisões
Use as análises e recomendações para otimizar o negócio
""")

st.markdown("---")

st.markdown("## 📞 Suporte")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 📧 Email
    [suporte@dubairro.local]
    """)

with col2:
    st.markdown("""
    ### 📱 WhatsApp
    Abrir ticket
    """)

with col3:
    st.markdown("""
    ### 🔧 Status da API
    [Verificar Status](/api/health)
    """)

st.markdown("---")

st.caption(f"© 2026 Mercado duBairro — v1.2 | Dashboard Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
