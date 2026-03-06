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
# ROOT
# ============================================================

@app.get("/")
async def root():
    return JSONResponse({
        "name": "DuBairro API",
        "version": "1.1.0",
        "status": "ok",
        "endpoints": {
            "health": "GET /api/health",
            "upload": "POST /api/upload",
            "mobne_status": "GET /api/mobne/status",
            "mobne_sync": "POST /api/mobne/sync?action=all|produtos|clientes|vendas&empresa_id=218&force=false",
            "mobne_cache": "DELETE /api/mobne/cache",
            "mobne_empresas": "GET /api/mobne/empresas",
        },
    })
