import json
import os
import re
import time
import requests

BRASILAPI_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
RECEITAWS_URL = "https://www.receitaws.com.br/v1/cnpj/{cnpj}"

CAMINHO_CACHE = os.path.join(os.path.dirname(__file__), "..", "config", "cache_cnpj.json")

STOPWORDS = {
    "de", "da", "do", "das", "dos", "e", "em", "para", "com", "a", "o",
    "as", "os", "outros", "outras", "outro", "outra", "nao",
    "especificados", "especificadas", "atividades", "atividade",
    "geral", "gerais", "diversos", "diversas", "produtos", "servicos",
    "serviços", "comercio", "comercio", "varejista", "atacadista",
    "exceto", "inclusive", "por", "sem", "sobre", "entre", "quando",
}


def limpar_cnpj(cnpj: str) -> str:
    return re.sub(r"\D", "", cnpj)


def extrair_palavras_chave(descricao: str, min_len: int = 4) -> list:
    if not descricao:
        return []
    palavras = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", descricao.lower())
    return [p for p in palavras if len(p) >= min_len and p not in STOPWORDS]


def _carregar_cache() -> dict:
    if os.path.exists(CAMINHO_CACHE):
        with open(CAMINHO_CACHE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass
    return {}


def _salvar_cache(cache: dict) -> None:
    with open(CAMINHO_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _normalizar_resposta(dados: dict) -> dict:
    cnae_principal = {
        "codigo": dados.get("cnae_fiscal"),
        "descricao": dados.get("cnae_fiscal_descricao", ""),
    }
    cnaes_secundarios = [
        {"codigo": c.get("codigo"), "descricao": c.get("descricao", "")}
        for c in dados.get("cnaes_secundarios", []) or []
    ]

    palavras_chave = set(extrair_palavras_chave(cnae_principal["descricao"]))
    for c in cnaes_secundarios:
        palavras_chave.update(extrair_palavras_chave(c["descricao"]))

    return {
        "cnpj": dados.get("cnpj", ""),
        "razao_social": dados.get("razao_social", ""),
        "nome_fantasia": dados.get("nome_fantasia", ""),
        "uf": dados.get("uf", ""),
        "municipio": dados.get("municipio", ""),
        "cnae_principal": cnae_principal,
        "cnaes_secundarios": cnaes_secundarios,
        "palavras_chave": sorted(palavras_chave),
    }


def _buscar_brasilapi(cnpj_limpo: str, tentativas: int = 3) -> dict:
    url = BRASILAPI_URL.format(cnpj=cnpj_limpo)
    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 429:
                time.sleep(10 * tentativa)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            ultimo_erro = e
            time.sleep(3 * tentativa)
    raise RuntimeError(f"BrasilAPI falhou para {cnpj_limpo}: {ultimo_erro}")


def _buscar_receitaws(cnpj_limpo: str, tentativas: int = 2) -> dict:
    url = RECEITAWS_URL.format(cnpj=cnpj_limpo)
    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 429:
                time.sleep(10 * tentativa)
                continue
            if resp.status_code == 404:
                raise RuntimeError(f"CNPJ {cnpj_limpo} nao encontrado na ReceitaWS")
            resp.raise_for_status()
            dados = resp.json()
            if dados.get("status") == "ERROR":
                raise RuntimeError(f"ReceitaWS erro: {dados.get('message', '')}")
            return dados
        except requests.RequestException as e:
            ultimo_erro = e
            time.sleep(3 * tentativa)
    raise RuntimeError(f"ReceitaWS falhou para {cnpj_limpo}: {ultimo_erro}")


def consultar_cnpj(cnpj: str, tentativas: int = 3) -> dict:
    cnpj_limpo = limpar_cnpj(cnpj)

    cache = _carregar_cache()
    if cnpj_limpo in cache:
        print(f"   [CACHE] Dados do CNPJ {cnpj_limpo} carregados do cache.")
        return cache[cnpj_limpo]

    try:
        dados = _buscar_brasilapi(cnpj_limpo, tentativas)
        resultado = _normalizar_resposta(dados)
    except Exception:
        print(f"   [FALLBACK] BrasilAPI falhou, tentando ReceitaWS...")
        dados = _buscar_receitaws(cnpj_limpo)
        resultado = _normalizar_resposta(dados)

    resultado["cnpj"] = cnpj_limpo
    cache[cnpj_limpo] = resultado
    _salvar_cache(cache)
    return resultado
