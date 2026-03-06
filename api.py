"""
API FastAPI para Upload de Dados e Integração Mobne
Compatível com Vercel Deployment
"""

from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
from pathlib import Path

from data_processor import DataProcessor

try:
    from mobne_api import (
        MobneAPIClient,
        sync_mobne_to_json,
        MOBNE_EMPRESAS,
        MOBNE_EMPRESA_ID,
        MOBNE_API_KEY,
        _cache_clear,
    )
    MOBNE_AVAILABLE = True
except ImportError:
    MobneAPIClient = None
    MOBNE_AVAILABLE = False

try:
    from analises import (
        carregar_configuracoes,
        salvar_configuracoes,
        obter_status_sincronizacao,
        sincronizacao_completa,
        analises_periodo,
    )
except ImportError:
    carregar_configuracoes = None
    salvar_configuracoes = None
    obter_status_sincronizacao = None
    sincronizacao_completa = None
    analises_periodo = None

# ============================================================
# APP
# ============================================================

app = FastAPI(title="DuBairro API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# SAÚDE
# ============================================================

@app.get("/api/health")
async def health_check():
    return JSONResponse({
        "status": "ok",
        "service": "dubairro-api",
        "version": "1.1.0",
        "mobne_available": MOBNE_AVAILABLE,
    })


# ============================================================
# UPLOAD
# ============================================================

@app.post("/api/upload")
async def upload_excel(file: UploadFile = File(...)):
    """
    Endpoint para upload de arquivo Excel/CSV.

    Formatos esperados:
    - vendas: Data, Categoria, Produto, Quantidade, Valor_Unitario, Vlr_Venda, Custo, Vlr_Lucro, Qtde_Documentos
    - produtos: Produto, Categoria, Custo_Medio, Preco, Estoque
    - simples: Data, Categoria, Produto, Faturamento
    """
    try:
        if not file.filename.lower().endswith((".xlsx", ".xls", ".csv")):
            return JSONResponse(
                {"error": "Apenas arquivos Excel (.xlsx, .xls) ou CSV são aceitos"},
                status_code=400,
            )

        try:
            if file.filename.lower().endswith(".csv"):
                df = pd.read_csv(file.file)
            else:
                df = pd.read_excel(file.file)
        except Exception as e:
            return JSONResponse({"error": f"Erro ao ler arquivo: {str(e)}"}, status_code=400)

        if df.empty:
            return JSONResponse({"error": "Arquivo vazio"}, status_code=400)

        processor = DataProcessor()
        format_type = processor.detect_format(df)

        if format_type == "desconhecido":
            return JSONResponse(
                {"error": "Formato de arquivo não reconhecido. Verifique as colunas."},
                status_code=400,
            )

        is_valid, validation_msg = processor.validate_data(df, format_type)
        if not is_valid:
            return JSONResponse({"error": validation_msg}, status_code=400)

        if format_type == "vendas":
            processed_df = processor.process_vendas(df)
            mes = int(processed_df["DATA"].dt.month.iloc[0])
            ano = int(processed_df["DATA"].dt.year.iloc[0])
        elif format_type == "produtos":
            processed_df = processor.process_produtos(df)
            mes = 1
            ano = 2026
        else:
            processed_df = df.copy()
            mes = 1
            ano = 2026

        data_dict = processor.aggregate_to_monthly(processed_df, mes, ano)
        success, filepath = processor.save_processed_data(data_dict)

        if not success:
            return JSONResponse({"error": filepath}, status_code=500)

        return JSONResponse({
            "status": "success",
            "message": f"Arquivo processado com sucesso: {format_type}",
            "format": format_type,
            "rows_processed": len(processed_df),
            "filepath": filepath,
            "mes": mes,
            "ano": ano,
        })

    except Exception as e:
        return JSONResponse({"error": f"Erro ao processar arquivo: {str(e)}"}, status_code=500)


# ============================================================
# MOBNE — STATUS
# ============================================================

@app.get("/api/mobne/status")
async def mobne_status():
    """Verifica status e configuração da integração Mobne"""
    api_key = os.getenv("MOBNE_API_KEY", "")
    empresas_info = {}

    if MOBNE_AVAILABLE:
        for eid, info in MOBNE_EMPRESAS.items():
            empresas_info[eid] = {
                "cnpj": info["cnpj"],
                "nome": info.get("nome", ""),
            }

    return JSONResponse({
        "status": "configured" if api_key else "not_configured",
        "has_api_key": bool(api_key),
        "mobne_available": MOBNE_AVAILABLE,
        "empresa_padrao": MOBNE_EMPRESA_ID,
        "empresas": empresas_info,
    })


# ============================================================
# MOBNE — SYNC
# ============================================================

@app.post("/api/mobne/sync")
async def sync_mobne(
    action: str = Query("all", description="produtos | clientes | vendas | all"),
    empresa_id: str = Query(None, description="ID da empresa (padrão: empresa principal)"),
    force: bool = Query(False, description="Ignorar cache e forçar nova busca"),
):
    """
    Sincroniza dados com API Mobne e salva em public/data/*.json

    - **all**: sincroniza tudo (produtos + clientes + vendas)
    - **produtos**: apenas produtos
    - **clientes**: apenas clientes
    - **vendas**: apenas vendas (últimos 30 dias)
    """
    if not MOBNE_AVAILABLE:
        return JSONResponse(
            {"error": "MobneAPIClient não disponível. Verifique as dependências."},
            status_code=503,
        )

    api_key = os.getenv("MOBNE_API_KEY", "")
    if not api_key:
        return JSONResponse(
            {"error": "MOBNE_API_KEY não configurado nas variáveis de ambiente"},
            status_code=400,
        )

    eid = str(empresa_id or MOBNE_EMPRESA_ID)

    try:
        if action == "all":
            results = sync_mobne_to_json(empresa_id=eid, force=force)
            total = sum(r.get("count", 0) for r in results.values() if r.get("ok"))
            return JSONResponse({
                "status": "success",
                "empresa_id": eid,
                "action": "all",
                "results": results,
                "total_items": total,
            })

        client = MobneAPIClient(empresa_id=eid)

        if action == "produtos":
            ok, data = client.fetch_produtos()
            label = "Produtos"
        elif action == "clientes":
            ok, data = client.fetch_clientes()
            label = "Clientes"
        elif action == "vendas":
            ok, data = client.fetch_vendas()
            label = "Vendas"
        else:
            return JSONResponse(
                {"error": f"Action '{action}' inválida. Use: all, produtos, clientes, vendas"},
                status_code=400,
            )

        if not ok:
            return JSONResponse(
                {"error": f"Falha ao buscar {label} do Mobne"},
                status_code=502,
            )

        return JSONResponse({
            "status": "success",
            "empresa_id": eid,
            "action": action,
            "label": label,
            "count": len(data),
        })

    except Exception as e:
        return JSONResponse(
            {"error": f"Erro ao sincronizar com Mobne: {str(e)}"},
            status_code=500,
        )


@app.delete("/api/mobne/cache")
async def clear_mobne_cache(empresa_id: str = Query(None)):
    """Limpa o cache em memória do cliente Mobne"""
    if not MOBNE_AVAILABLE:
        return JSONResponse({"error": "Mobne não disponível"}, status_code=503)
    prefix = str(empresa_id) if empresa_id else ""
    _cache_clear(prefix)
    return JSONResponse({"status": "ok", "message": f"Cache limpo (prefixo='{prefix}')"})


@app.get("/api/mobne/empresas")
async def listar_empresas():
    """Lista as empresas configuradas no sistema"""
    if not MOBNE_AVAILABLE:
        return JSONResponse({"error": "Mobne não disponível"}, status_code=503)
    return JSONResponse({
        "empresa_padrao": MOBNE_EMPRESA_ID,
        "empresas": {
            eid: {"cnpj": info["cnpj"], "nome": info.get("nome", "")}
            for eid, info in MOBNE_EMPRESAS.items()
        },
    })


# ============================================================
# DASHBOARD — STATUS DE SINCRONIZAÇÃO
# ============================================================

@app.get("/api/dashboard/status/sync")
async def dashboard_status_sync():
    """
    Retorna o status completo da sincronização de todos os dados

    Response:
    {
        "sincronizacao_completa": true/false,
        "todos_dados_sincronizados": true/false,
        "detalhes": {
            "produtos": {"ultima_sync": "...", "total": 123},
            "clientes": {...},
            "vendas": {...}
        }
    }
    """
    if not obter_status_sincronizacao:
        return JSONResponse({"error": "Módulo de análises não disponível"}, status_code=503)

    status = obter_status_sincronizacao()
    completo = sincronizacao_completa()

    return JSONResponse({
        "sincronizacao_completa": completo,
        "todos_dados_sincronizados": completo,
        "detalhes": {
            "produtos": status.get("produtos"),
            "clientes": status.get("clientes"),
            "vendas": status.get("vendas"),
        },
        "timestamp": status.get("timestamp"),
    })


# ============================================================
# DASHBOARD — ANÁLISES POR PERÍODO
# ============================================================

@app.get("/api/dashboard/analises/periodo")
async def dashboard_analises_periodo(
    mes: int = Query(None, ge=1, le=12, description="Mês (1-12)"),
    ano: int = Query(None, ge=2000, le=2100, description="Ano"),
):
    """
    Retorna análises completas para um período específico

    Query Parameters:
    - mes: 1-12 (obrigatório)
    - ano: 2000-2100 (obrigatório)

    Response inclui:
    - Métricas: total vendas, valor, ticket médio
    - Comparativo: vs. mês anterior (variação %)
    - Gráficos: vendas por dia, faturamento por dia
    - Financeiro: lucro bruto, lucro líquido, ponto de equilíbrio
    """
    if not analises_periodo:
        return JSONResponse({"error": "Módulo de análises não disponível"}, status_code=503)

    if mes is None or ano is None:
        return JSONResponse(
            {"error": "Parâmetros obrigatórios: mes (1-12) e ano"},
            status_code=400,
        )

    result = analises_periodo(mes, ano)

    if "error" in result:
        return JSONResponse(result, status_code=400)

    return JSONResponse(result)


# ============================================================
# DASHBOARD — CONFIGURAÇÕES
# ============================================================

@app.get("/api/dashboard/configuracoes")
async def get_configuracoes():
    """
    Retorna as configurações atuais do dashboard

    Response:
    {
        "custo_fixo_mensal": 16913.46,
        "margem_meta": 15.0,
        "faturamento_meta": 100000.0,
        "custos_detalhes": {...},
        "data_atualizacao": "..."
    }
    """
    if not carregar_configuracoes:
        return JSONResponse({"error": "Módulo de análises não disponível"}, status_code=503)

    config = carregar_configuracoes()
    return JSONResponse(config)


@app.post("/api/dashboard/configuracoes")
async def post_configuracoes(body: dict):
    """
    Atualiza as configurações do dashboard

    Body esperado:
    {
        "custo_fixo_mensal": 16913.46,
        "margem_meta": 15.0,
        "faturamento_meta": 100000.0,
        "custos_detalhes": {
            "aluguel": 0.0,
            "salarios": 0.0,
            "utilidades": 0.0,
            "manutencao": 0.0
        }
    }
    """
    if not salvar_configuracoes:
        return JSONResponse({"error": "Módulo de análises não disponível"}, status_code=503)

    if not body:
        return JSONResponse({"error": "Body vazio"}, status_code=400)

    # Validação básica
    if "custo_fixo_mensal" in body:
        if not isinstance(body["custo_fixo_mensal"], (int, float)):
            return JSONResponse({"error": "custo_fixo_mensal deve ser um número"}, status_code=400)

    if "margem_meta" in body:
        margem = body["margem_meta"]
        if not isinstance(margem, (int, float)) or not (0 <= margem <= 100):
            return JSONResponse(
                {"error": "margem_meta deve estar entre 0 e 100"},
                status_code=400,
            )

    # Salvar
    config = carregar_configuracoes()
    config.update(body)

    if salvar_configuracoes(config):
        return JSONResponse({
            "status": "success",
            "message": "Configurações atualizadas",
            "config": config,
        })
    else:
        return JSONResponse(
            {"error": "Erro ao salvar configurações"},
            status_code=500,
        )


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():
    return JSONResponse({
        "name": "DuBairro API",
        "version": "1.2.0",
        "status": "ok",
        "endpoints": {
            "health": "GET /api/health",
            "upload": "POST /api/upload",
            "mobne": {
                "status": "GET /api/mobne/status",
                "sync": "POST /api/mobne/sync?action=all|produtos|clientes|vendas",
                "cache": "DELETE /api/mobne/cache",
                "empresas": "GET /api/mobne/empresas",
            },
            "dashboard": {
                "status_sync": "GET /api/dashboard/status/sync",
                "analises_periodo": "GET /api/dashboard/analises/periodo?mes=1&ano=2026",
                "configuracoes_get": "GET /api/dashboard/configuracoes",
                "configuracoes_post": "POST /api/dashboard/configuracoes",
            },
        },
    })
