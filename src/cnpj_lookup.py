import re
import time
import requests

BRASILAPI_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"

STOPWORDS = {
    "de", "da", "do", "das", "dos", "e", "em", "para", "com", "a", "o",
    "as", "os", "outros", "outras", "outro", "outra", "não", "nao",
    "especificados", "especificadas", "atividades", "atividade",
    "geral", "gerais", "diversos", "diversas", "produtos", "servicos",
    "serviços", "comercio", "comércio", "varejista", "atacadista",
    "exceto", "inclusive", "por", "sem", "sobre", "entre", "quando",
}


def limpar_cnpj(cnpj: str) -> str:
    return re.sub(r"\D", "", cnpj)


def extrair_palavras_chave(descricao: str, min_len: int = 4) -> list:
    if not descricao:
        return []
    palavras = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", descricao.lower())
    return [p for p in palavras if len(p) >= min_len and p not in STOPWORDS]


def consultar_cnpj(cnpj: str, tentativas: int = 3) -> dict:
    cnpj_limpo = limpar_cnpj(cnpj)
    url = BRASILAPI_URL.format(cnpj=cnpj_limpo)

    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 429:
                time.sleep(3 * tentativa)
                continue
            resp.raise_for_status()
            dados = resp.json()
            break
        except requests.RequestException as e:
            ultimo_erro = e
            time.sleep(2 * tentativa)
    else:
        raise RuntimeError(f"Falha ao consultar CNPJ {cnpj_limpo}: {ultimo_erro}")

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
        "cnpj": cnpj_limpo,
        "razao_social": dados.get("razao_social", ""),
        "nome_fantasia": dados.get("nome_fantasia", ""),
        "uf": dados.get("uf", ""),
        "municipio": dados.get("municipio", ""),
        "cnae_principal": cnae_principal,
        "cnaes_secundarios": cnaes_secundarios,
        "palavras_chave": sorted(palavras_chave),
    }
