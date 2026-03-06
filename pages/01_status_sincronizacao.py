"""
Página de Status de Sincronização
Mostra o estado da sincronização com a API Mobne e permite sincronizar dados
"""

import streamlit as st
import json
from pathlib import Path
from datetime import datetime
import requests

st.set_page_config(
    page_title="Status de Sincronização | Mercado duBairro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Status de Sincronização de Dados")
st.markdown("Acompanhe o status da sincronização com a API Mobne")

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

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
            "status": "✅ OK" if data.get("total", 0) > 0 else "⚠️ Vazio",
        }
    except:
        return None


def chamar_sync_api(action: str = "all") -> dict:
    """Chama o endpoint de sincronização da API"""
    try:
        response = requests.post(
            "http://localhost:8000/api/mobne/sync",
            params={"action": action, "force": True},
            timeout=60,
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Status {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# SIDEBAR - CONTROLES
# ============================================================

with st.sidebar:
    st.header("⚙️ Controles de Sincronização")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Sincronizar Tudo", use_container_width=True):
            with st.spinner("Sincronizando dados... Isso pode levar alguns minutos..."):
                result = chamar_sync_api("all")
            if "error" in result:
                st.error(f"Erro na sincronização: {result['error']}")
            else:
                st.success("✅ Sincronização concluída com sucesso!")
                st.rerun()

    with col2:
        if st.button("🗑️ Limpar Cache", use_container_width=True):
            try:
                requests.delete("http://localhost:8000/api/mobne/cache")
                st.success("Cache limpo!")
            except:
                st.info("Não foi possível limpar o cache")

    st.markdown("---")
    st.markdown("### Sincronizar por Entidade")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📦 Produtos", use_container_width=True):
            with st.spinner("Sincronizando produtos..."):
                result = chamar_sync_api("produtos")
            st.success(f"✅ {result.get('count', 0)} produtos sincronizados")

    with col2:
        if st.button("👥 Clientes", use_container_width=True):
            with st.spinner("Sincronizando clientes..."):
                result = chamar_sync_api("clientes")
            st.success(f"✅ {result.get('count', 0)} clientes sincronizados")

    with col3:
        if st.button("💳 Vendas", use_container_width=True):
            with st.spinner("Sincronizando vendas..."):
                result = chamar_sync_api("vendas")
            st.success(f"✅ {result.get('count', 0)} vendas sincronizadas")


# ============================================================
# CONTEÚDO PRINCIPAL
# ============================================================

data_dir = Path("public/data")

# Cards de Status
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### 📦 Produtos")
    status = carregar_status_arquivo(data_dir / "produtos.json")
    if status:
        st.metric("Total", status["total"])
        st.markdown(f"**Última sync:** {status['ultima_sync']}")
        st.markdown(status["status"])
    else:
        st.warning("Sem dados")

with col2:
    st.markdown("### 👥 Clientes")
    status = carregar_status_arquivo(data_dir / "clientes.json")
    if status:
        st.metric("Total", status["total"])
        st.markdown(f"**Última sync:** {status['ultima_sync']}")
        st.markdown(status["status"])
    else:
        st.warning("Sem dados")

with col3:
    st.markdown("### 💳 Vendas")
    status = carregar_status_arquivo(data_dir / "vendas_mobne.json")
    if status:
        st.metric("Total", status["total"])
        st.markdown(f"**Última sync:** {status['ultima_sync']}")
        st.markdown(status["status"])
    else:
        st.warning("Sem dados")

with col4:
    st.markdown("### 🔗 Integração Mobne")
    try:
        response = requests.get("http://localhost:8000/api/mobne/status")
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "configured":
                st.success("✅ Configurada")
                empresas = data.get("empresas", {})
                for eid, info in empresas.items():
                    st.caption(f"Empresa {eid}: {info.get('cnpj')}")
            else:
                st.error("❌ Não configurada")
        else:
            st.error("Erro ao verificar")
    except:
        st.error("API indisponível")

# ============================================================
# DETALHES
# ============================================================

st.markdown("---")
st.markdown("## 📋 Detalhes da Sincronização")

tabs = st.tabs(["Produtos", "Clientes", "Vendas", "Timeline"])

with tabs[0]:
    status = carregar_status_arquivo(data_dir / "produtos.json")
    if status:
        st.success(f"✅ {status['total']} produtos sincronizados")
        st.info(f"Última sincronização: {status['ultima_sync']}")

        with st.expander("Ver primeiros 5 produtos"):
            try:
                with open(data_dir / "produtos.json") as f:
                    data = json.load(f)
                    produtos = data.get("produtos", [])[:5]
                    for p in produtos:
                        st.json({
                            "ID": p.get("ProdutoId"),
                            "Descrição": p.get("Descricao"),
                            "Status": p.get("Status"),
                        })
            except:
                st.error("Erro ao carregar dados")
    else:
        st.warning("Nenhum dado sincronizado. Execute a sincronização primeiro.")

with tabs[1]:
    status = carregar_status_arquivo(data_dir / "clientes.json")
    if status:
        st.success(f"✅ {status['total']} clientes sincronizados")
        st.info(f"Última sincronização: {status['ultima_sync']}")
    else:
        st.warning("Nenhum dado sincronizado. Execute a sincronização primeiro.")

with tabs[2]:
    status = carregar_status_arquivo(data_dir / "vendas_mobne.json")
    if status:
        st.success(f"✅ {status['total']} vendas sincronizadas")
        st.info(f"Última sincronização: {status['ultima_sync']}")
        try:
            with open(data_dir / "vendas_mobne.json") as f:
                data = json.load(f)
                periodo = data.get("periodo", {})
                st.info(f"Período: {periodo.get('inicio')} a {periodo.get('fim')}")
        except:
            pass
    else:
        st.warning("Nenhum dado sincronizado. Execute a sincronização primeiro.")

with tabs[3]:
    st.markdown("### 🕐 Timeline de Sincronizações")
    st.info("Funcionalidade em desenvolvimento")
    st.caption("Mostrará histórico de todas as sincronizações realizadas")

st.markdown("---")
st.caption("Última atualização: " + datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
