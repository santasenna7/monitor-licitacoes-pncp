import re
import time
from datetime import date, datetime, timedelta

import requests

BASE_URL_PROPOSTA = "https://pncp.gov.br/api/consulta/v1/contratacoes/proposta"
BASE_URL_PUBLICACAO = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"

MODALIDADES = {
    6: "Pregão - Eletrônico",
    4: "Concorrência - Eletrônica",
    8: "Dispensa de Licitação",
    9: "Inexigibilidade",
}

TODAS_MODALIDADES = {
    1: "Leilão - Eletrônico",
    2: "Diálogo Competitivo",
    3: "Concurso",
    4: "Concorrência - Eletrônica",
    5: "Concorrência - Presencial",
    6: "Pregão - Eletrônico",
    7: "Pregão - Presencial",
    8: "Dispensa de Licitação",
    9: "Inexigibilidade",
    10: "Manifestação de Interesse",
    11: "Pré-qualificação",
    12: "Credenciamento",
    13: "Leilão - Presencial",
}


def _get_com_retentativa(url: str, params: dict, tentativas: int = 5) -> dict:
    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            resp = requests.get(url, params=params, timeout=45)
            if resp.status_code == 204:
                return {"data": [], "totalPaginas": 0}
            if resp.status_code == 429:
                espera = min(30 * tentativa, 120)
                print(f"   [429] Rate limit atingido, aguardando {espera}s...")
                time.sleep(espera)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            ultimo_erro = e
            time.sleep(5 * tentativa)
    raise RuntimeError(f"Falha ao consultar PNCP ({params}): {ultimo_erro}")


def buscar_contratacoes_abertas(data_final: date = None, uf: str = None) -> list:
    if not data_final:
        data_final = date.today() + timedelta(days=60)
    data_final_str = data_final.strftime("%Y%m%d")

    resultados = []
    for cod_modalidade, nome_modalidade in MODALIDADES.items():
        pagina = 1
        while pagina <= 20:
            params = {
                "dataFinal": data_final_str,
                "codigoModalidadeContratacao": cod_modalidade,
                "pagina": pagina,
                "tamanhoPagina": 50,
            }
            if uf:
                params["uf"] = uf

            corpo = _get_com_retentativa(BASE_URL_PROPOSTA, params)
            itens = corpo.get("data", [])
            if not itens:
                break

            for item in itens:
                item["_modalidade"] = nome_modalidade
                resultados.append(item)

            total_paginas = corpo.get("totalPaginas", 1)
            if pagina >= total_paginas:
                break
            pagina += 1
            time.sleep(2)

    return resultados


def buscar_contratacoes_publicadas(data_inicial: date = None, data_final: date = None, uf: str = None) -> list:
    data_inicial = data_inicial or date.today() - timedelta(days=30)
    data_final = data_final or date.today() + timedelta(days=60)

    resultados = []
    for cod_modalidade, nome_modalidade in MODALIDADES.items():
        pagina = 1
        while True:
            params = {
                "dataInicial": data_inicial.strftime("%Y%m%d"),
                "dataFinal": data_final.strftime("%Y%m%d"),
                "codigoModalidadeContratacao": cod_modalidade,
                "pagina": pagina,
                "tamanhoPagina": 50,
            }
            if uf:
                params["uf"] = uf

            corpo = _get_com_retentativa(BASE_URL_PUBLICACAO, params)
            itens = corpo.get("data", [])
            if not itens:
                break

            for item in itens:
                item["_modalidade"] = nome_modalidade
                resultados.append(item)

            total_paginas = corpo.get("totalPaginas", 1)
            if pagina >= total_paginas:
                break
            pagina += 1
            time.sleep(2)

    return resultados


def filtrar_por_palavras_chave(contratacoes: list, palavras_chave: list, cnaes: list = None) -> list:
    if not palavras_chave:
        return []
    termos = [p.lower() for p in palavras_chave]
    cnae_codigos = [str(c) for c in (cnaes or []) if c]
    encontrados = []
    for c in contratacoes:
        objeto = (c.get("objetoCompra") or "").lower()
        numero_processo = str(c.get("numeroControlePNCP") or "")
        palavras_objeto = set(re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]{4,}", objeto))

        match_palavra = any(termo in objeto for termo in termos)
        match_cnae = False
        if cnae_codigos:
            for codigo in cnae_codigos:
                if codigo and codigo in objeto:
                    match_cnae = True
                    break
                if codigo and codigo in palavras_objeto:
                    match_cnae = True
                    break

        if match_palavra or match_cnae:
            encontrados.append(c)
    return encontrados


def link_pncp(contratacao: dict) -> str:
    cnpj = contratacao.get("orgaoEntidade", {}).get("cnpj", "")
    ano = contratacao.get("anoCompra", "")
    sequencial = contratacao.get("sequencialCompra", "")
    if cnpj and ano and sequencial:
        return f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{sequencial}"
    return "https://pncp.gov.br"


def dias_restantes(contratacao: dict) -> int | None:
    data_enc = contratacao.get("dataEncerramentoProposta")
    if not data_enc:
        return None
    try:
        if "T" in str(data_enc):
            dt = datetime.fromisoformat(str(data_enc).replace("Z", "+00:00")).date()
        else:
            dt = datetime.strptime(str(data_enc)[:10], "%Y-%m-%d").date()
        return (dt - date.today()).days
    except Exception:
        return None


def filtrar_por_prazo(contratacoes: list, dias_minimo: int) -> list:
    filtrados = []
    for c in contratacoes:
        dias = dias_restantes(c)
        if dias is None or dias >= dias_minimo:
            c["_dias_restantes"] = dias
            filtrados.append(c)
    return filtrados
