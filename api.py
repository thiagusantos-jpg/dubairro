"""
API FastAPI para Upload de Dados e Integração Mobne
Compatível com Vercel Deployment
"""

from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import sys
import os
from pathlib import Path

from data_processor import DataProcessor

try:
    from mobne_api import MobneAPIClient
except ImportError:
    MobneAPIClient = None

# Criar aplicação FastAPI
app = FastAPI(title="DuBairro API", version="1.0.0")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROTAS DE SAÚDE
# ============================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({"status": "ok", "service": "dubairro-api"})


# ============================================================
# ROTAS DE UPLOAD
# ============================================================

@app.post("/api/upload")
async def upload_excel(file: UploadFile = File(...)):
    """
    Endpoint para upload de arquivo Excel
    Detecta formato e processa dados

    Formatos esperados:
    - vendas: Data, Categoria, Produto, Quantidade, Valor_Unitario, Vlr_Venda, Custo, Vlr_Lucro, Qtde_Documentos
    - produtos: Produto, Categoria, Custo_Medio, Preco, Estoque
    - simples: Data, Categoria, Produto, Faturamento
    """
    try:
        # Validar extensão
        if not file.filename.lower().endswith(('.xlsx', '.xls', '.csv')):
            return JSONResponse(
                {"error": "Apenas arquivos Excel (.xlsx, .xls) ou CSV são aceitos"},
                status_code=400
            )

        # Ler arquivo
        try:
            if file.filename.lower().endswith('.csv'):
                df = pd.read_csv(file.file)
            else:
                df = pd.read_excel(file.file)
        except Exception as e:
            return JSONResponse(
                {"error": f"Erro ao ler arquivo: {str(e)}"},
                status_code=400
            )

        if df.empty:
            return JSONResponse(
                {"error": "Arquivo vazio"},
                status_code=400
            )

        # Inicializar processador
        processor = DataProcessor()

        # Detectar formato
        format_type = processor.detect_format(df)

        if format_type == 'desconhecido':
            return JSONResponse(
                {"error": "Formato de arquivo não reconhecido. Verifique as colunas."},
                status_code=400
            )

        # Validar dados
        is_valid, validation_msg = processor.validate_data(df, format_type)
        if not is_valid:
            return JSONResponse(
                {"error": validation_msg},
                status_code=400
            )

        # Processar dados conforme tipo
        if format_type == 'vendas':
            processed_df = processor.process_vendas(df)
            mes = int(processed_df['DATA'].dt.month.iloc[0])
            ano = int(processed_df['DATA'].dt.year.iloc[0])
        elif format_type == 'produtos':
            processed_df = processor.process_produtos(df)
            mes = 1
            ano = 2026
        else:  # simples
            processed_df = df.copy()
            mes = 1
            ano = 2026

        # Agregar dados mensais
        data_dict = processor.aggregate_to_monthly(processed_df, mes, ano)

        # Salvar dados processados
        success, filepath = processor.save_processed_data(data_dict)

        if not success:
            return JSONResponse(
                {"error": filepath},
                status_code=500
            )

        return JSONResponse({
            "status": "success",
            "message": f"Arquivo processado com sucesso: {format_type}",
            "format": format_type,
            "rows_processed": len(processed_df),
            "filepath": filepath,
            "mes": mes,
            "ano": ano
        }, status_code=200)

    except Exception as e:
        return JSONResponse(
            {"error": f"Erro ao processar arquivo: {str(e)}"},
            status_code=500
        )


# ============================================================
# ROTAS DE MOBNE
# ============================================================

@app.post("/api/mobne/sync")
async def sync_mobne(action: str = Query("produtos")):
    """
    Sincroniza dados com API Mobne

    Actions disponíveis:
    - produtos: Sincroniza produtos
    - clientes: Sincroniza clientes
    - vendas: Sincroniza vendas
    """
    if not MobneAPIClient:
        return JSONResponse(
            {"error": "MobneAPIClient não disponível. Verifique as dependências."},
            status_code=503
        )

    # Validar chave API e CNPJ
    api_key = os.getenv("MOBNE_API_KEY", "")
    cnpj = os.getenv("MOBNE_CNPJ", "")

    if not api_key or not cnpj:
        return JSONResponse(
            {"error": "MOBNE_API_KEY ou MOBNE_CNPJ não configurados"},
            status_code=400
        )

    try:
        client = MobneAPIClient(api_key=api_key, cnpj=cnpj)

        if action == "produtos":
            result = client.fetch_produtos()
            action_label = "Produtos"
        elif action == "clientes":
            result = client.fetch_clientes()
            action_label = "Clientes"
        elif action == "vendas":
            result = client.fetch_vendas()
            action_label = "Vendas"
        else:
            return JSONResponse(
                {"error": f"Action '{action}' não reconhecida. Use: produtos, clientes, vendas"},
                status_code=400
            )

        # Se resultado é DataFrame, converter para dict
        if hasattr(result, 'to_dict'):
            result = result.to_dict(orient='records')

        return JSONResponse({
            "status": "success",
            "action": action,
            "action_label": action_label,
            "count": len(result) if isinstance(result, (list, dict)) else 0,
            "message": f"{action_label} sincronizados com sucesso"
        })

    except Exception as e:
        return JSONResponse(
            {"error": f"Erro ao sincronizar com Mobne: {str(e)}"},
            status_code=500
        )


@app.get("/api/mobne/status")
async def mobne_status():
    """Verifica status da integração Mobne"""
    api_key = os.getenv("MOBNE_API_KEY", "")
    cnpj = os.getenv("MOBNE_CNPJ", "")

    return JSONResponse({
        "status": "configured" if api_key and cnpj else "not_configured",
        "has_api_key": bool(api_key),
        "has_cnpj": bool(cnpj),
        "client_available": MobneAPIClient is not None
    })


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
async def root():
    """Root endpoint - retorna informações da API"""
    return JSONResponse({
        "name": "DuBairro API",
        "version": "1.0.0",
        "status": "ok",
        "endpoints": {
            "health": "/api/health",
            "upload": "/api/upload",
            "mobne": "/api/mobne/sync",
            "mobne_status": "/api/mobne/status"
        }
    })
