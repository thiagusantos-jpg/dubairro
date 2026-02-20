"""
Módulo de Integração com ERP Mobne
Sincroniza dados entre Mercado duBairro e ERP Mobne via API REST
"""

import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
from functools import wraps
import os

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações da API Mobne
MOBNE_API_BASE_URL = os.getenv("MOBNE_API_URL", "https://apiexternal.mobne.com.br")
MOBNE_API_TIMEOUT = 30  # segundos
MOBNE_API_KEY = os.getenv("MOBNE_API_KEY", "")
MOBNE_CNPJ = os.getenv("MOBNE_CNPJ", "")


class MobneAPIClient:
    """Cliente para comunicação com API Mobne"""

    def __init__(self, api_key: str = None, cnpj: str = None, base_url: str = None):
        """
        Inicializa o cliente da API Mobne

        Args:
            api_key: Chave de autenticação da API
            cnpj: CNPJ da empresa no Mobne
            base_url: URL base da API (padrão: https://apiexternal.mobne.com.br)
        """
        self.api_key = api_key or MOBNE_API_KEY
        self.cnpj = cnpj or MOBNE_CNPJ
        self.base_url = base_url or MOBNE_API_BASE_URL
        self.session = requests.Session()
        self._setup_headers()
        self.last_sync = None

    def _setup_headers(self) -> None:
        """Configura headers de autenticação"""
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-CNPJ": self.cnpj,
            "User-Agent": "Mercado-duBairro/1.0"
        })

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Tuple[bool, Dict]:
        """
        Realiza requisição HTTP com tratamento de erro

        Args:
            method: GET, POST, PUT, DELETE
            endpoint: Endpoint da API (sem base URL)
            **kwargs: Argumentos adicionais para requests

        Returns:
            Tupla (sucesso, resposta/erro)
        """
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault("timeout", MOBNE_API_TIMEOUT)

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.ConnectionError:
            msg = f"Erro de conexão com Mobne API: {url}"
            logger.error(msg)
            return False, {"error": msg}
        except requests.exceptions.Timeout:
            msg = f"Timeout na requisição para Mobne API"
            logger.error(msg)
            return False, {"error": msg}
        except requests.exceptions.HTTPError as e:
            msg = f"Erro HTTP {response.status_code}: {response.text}"
            logger.error(msg)
            return False, {"error": msg}
        except Exception as e:
            msg = f"Erro ao comunicar com Mobne API: {str(e)}"
            logger.error(msg)
            return False, {"error": msg}

    def verify_connection(self) -> Tuple[bool, str]:
        """
        Verifica se a conexão com a API está funcionando

        Returns:
            Tupla (sucesso, mensagem)
        """
        success, response = self._make_request("GET", "/api/v1/health")

        if success:
            return True, "✅ Conectado com sucesso ao Mobne"
        else:
            return False, f"❌ Erro ao conectar: {response.get('error')}"

    def fetch_produtos(self, limit: int = 1000, offset: int = 0) -> Tuple[bool, List[Dict]]:
        """
        Busca lista de produtos do Mobne

        Args:
            limit: Quantidade de produtos por página
            offset: Offset para paginação

        Returns:
            Tupla (sucesso, lista de produtos)
        """
        success, response = self._make_request(
            "GET",
            f"/api/v1/produtos?limit={limit}&offset={offset}"
        )

        if success:
            products = response.get("data", [])
            logger.info(f"Buscados {len(products)} produtos do Mobne")
            return True, products
        else:
            return False, []

    def fetch_clientes(self, limit: int = 1000, offset: int = 0) -> Tuple[bool, List[Dict]]:
        """
        Busca lista de clientes do Mobne

        Args:
            limit: Quantidade de clientes por página
            offset: Offset para paginação

        Returns:
            Tupla (sucesso, lista de clientes)
        """
        success, response = self._make_request(
            "GET",
            f"/api/v1/clientes?limit={limit}&offset={offset}"
        )

        if success:
            clients = response.get("data", [])
            logger.info(f"Buscados {len(clients)} clientes do Mobne")
            return True, clients
        else:
            return False, []

    def fetch_vendas(
        self,
        data_inicio: datetime = None,
        data_fim: datetime = None,
        limit: int = 1000,
        offset: int = 0
    ) -> Tuple[bool, List[Dict]]:
        """
        Busca vendas do Mobne dentro de um período

        Args:
            data_inicio: Data de início (padrão: últimos 30 dias)
            data_fim: Data de fim (padrão: hoje)
            limit: Quantidade por página
            offset: Offset para paginação

        Returns:
            Tupla (sucesso, lista de vendas)
        """
        if data_fim is None:
            data_fim = datetime.now()
        if data_inicio is None:
            data_inicio = data_fim - timedelta(days=30)

        params = {
            "data_inicio": data_inicio.strftime("%Y-%m-%d"),
            "data_fim": data_fim.strftime("%Y-%m-%d"),
            "limit": limit,
            "offset": offset
        }

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        success, response = self._make_request("GET", f"/api/v1/vendas?{query_string}")

        if success:
            vendas = response.get("data", [])
            logger.info(f"Buscadas {len(vendas)} vendas do Mobne")
            return True, vendas
        else:
            return False, []

    def send_venda(self, venda_data: Dict) -> Tuple[bool, str]:
        """
        Envia dados de venda para o Mobne

        Args:
            venda_data: Dicionário com dados da venda

        Returns:
            Tupla (sucesso, ID da venda ou mensagem de erro)
        """
        required_fields = ['data', 'cliente_id', 'produtos', 'valor_total']
        missing = [f for f in required_fields if f not in venda_data]

        if missing:
            msg = f"Campos obrigatórios faltando: {', '.join(missing)}"
            logger.error(msg)
            return False, msg

        success, response = self._make_request(
            "POST",
            "/api/v1/vendas",
            json=venda_data
        )

        if success:
            venda_id = response.get("id")
            logger.info(f"Venda {venda_id} enviada para Mobne com sucesso")
            return True, venda_id
        else:
            return False, response.get("error", "Erro desconhecido")

    def sync_produtos_para_dataframe(self) -> Tuple[bool, pd.DataFrame]:
        """
        Sincroniza produtos do Mobne e retorna como DataFrame

        Returns:
            Tupla (sucesso, DataFrame com produtos)
        """
        success, products = self.fetch_produtos()

        if not success:
            return False, pd.DataFrame()

        try:
            df = pd.DataFrame(products)
            df['DATA_SYNC'] = datetime.now()
            self.last_sync = datetime.now()
            logger.info(f"Sincronizados {len(df)} produtos do Mobne")
            return True, df
        except Exception as e:
            logger.error(f"Erro ao processar produtos: {str(e)}")
            return False, pd.DataFrame()

    def sync_clientes_para_dataframe(self) -> Tuple[bool, pd.DataFrame]:
        """
        Sincroniza clientes do Mobne e retorna como DataFrame

        Returns:
            Tupla (sucesso, DataFrame com clientes)
        """
        success, clients = self.fetch_clientes()

        if not success:
            return False, pd.DataFrame()

        try:
            df = pd.DataFrame(clients)
            df['DATA_SYNC'] = datetime.now()
            self.last_sync = datetime.now()
            logger.info(f"Sincronizados {len(df)} clientes do Mobne")
            return True, df
        except Exception as e:
            logger.error(f"Erro ao processar clientes: {str(e)}")
            return False, pd.DataFrame()

    def sync_vendas_para_dataframe(
        self,
        data_inicio: datetime = None,
        data_fim: datetime = None
    ) -> Tuple[bool, pd.DataFrame]:
        """
        Sincroniza vendas do Mobne e retorna como DataFrame

        Returns:
            Tupla (sucesso, DataFrame com vendas)
        """
        success, vendas = self.fetch_vendas(data_inicio, data_fim)

        if not success:
            return False, pd.DataFrame()

        try:
            df = pd.DataFrame(vendas)
            df['DATA_SYNC'] = datetime.now()
            self.last_sync = datetime.now()
            logger.info(f"Sincronizadas {len(df)} vendas do Mobne")
            return True, df
        except Exception as e:
            logger.error(f"Erro ao processar vendas: {str(e)}")
            return False, pd.DataFrame()


class MobneIntegration:
    """Gerenciador de integração com Mobne para uso em Streamlit"""

    def __init__(self):
        """Inicializa a integração"""
        self.client = None
        self._initialize_session_state()

    def _initialize_session_state(self):
        """Inicializa variáveis de sessão do Streamlit"""
        if 'mobne_client' not in st.session_state:
            st.session_state.mobne_client = None
        if 'mobne_connected' not in st.session_state:
            st.session_state.mobne_connected = False
        if 'mobne_api_key' not in st.session_state:
            st.session_state.mobne_api_key = ""
        if 'mobne_cnpj' not in st.session_state:
            st.session_state.mobne_cnpj = ""

    def connect(self, api_key: str, cnpj: str) -> Tuple[bool, str]:
        """
        Conecta à API Mobne

        Args:
            api_key: Chave de autenticação
            cnpj: CNPJ da empresa

        Returns:
            Tupla (sucesso, mensagem)
        """
        try:
            self.client = MobneAPIClient(api_key=api_key, cnpj=cnpj)
            success, message = self.client.verify_connection()

            if success:
                st.session_state.mobne_client = self.client
                st.session_state.mobne_connected = True
                st.session_state.mobne_api_key = api_key
                st.session_state.mobne_cnpj = cnpj
                return True, message
            else:
                return False, message
        except Exception as e:
            return False, f"Erro ao conectar: {str(e)}"

    def disconnect(self):
        """Desconecta da API Mobne"""
        st.session_state.mobne_client = None
        st.session_state.mobne_connected = False
        st.session_state.mobne_api_key = ""
        st.session_state.mobne_cnpj = ""

    def is_connected(self) -> bool:
        """Verifica se está conectado"""
        return st.session_state.get('mobne_connected', False)

    def get_client(self) -> Optional[MobneAPIClient]:
        """Retorna o cliente da API"""
        return st.session_state.get('mobne_client')

    @staticmethod
    def require_mobne_connection(func):
        """Decorator que requer conexão com Mobne"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            integration = MobneIntegration()
            if not integration.is_connected():
                st.error("❌ Não conectado ao Mobne. Configure a integração primeiro!")
                return None
            return func(*args, **kwargs)
        return wrapper


# Funções utilitárias para o Streamlit
def setup_mobne_connection_ui():
    """Cria interface para configurar conexão com Mobne"""
    st.markdown("### 🔌 Configurar Conexão Mobne")

    with st.form("mobne_connection_form"):
        api_key = st.text_input("🔑 Chave de API Mobne", type="password")
        cnpj = st.text_input("📊 CNPJ da Empresa", placeholder="00.000.000/0000-00")
        submit = st.form_submit_button("Conectar ao Mobne")

        if submit:
            if not api_key or not cnpj:
                st.error("❌ Preencha todos os campos!")
            else:
                with st.spinner("Conectando ao Mobne..."):
                    integration = MobneIntegration()
                    success, message = integration.connect(api_key, cnpj)

                    if success:
                        st.success(message)
                        st.session_state.mobne_configured = True
                    else:
                        st.error(message)


def display_mobne_status():
    """Exibe status da conexão Mobne"""
    integration = MobneIntegration()

    if integration.is_connected():
        st.success(f"✅ Conectado ao Mobne - CNPJ: {st.session_state.mobne_cnpj}")
        if st.button("🔌 Desconectar do Mobne"):
            integration.disconnect()
            st.rerun()
    else:
        st.info("⚠️ Não conectado ao Mobne")
