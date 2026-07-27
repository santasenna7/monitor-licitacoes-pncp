import csv
import json
import os
from datetime import datetime

PASTA_DATA = os.path.join(os.path.dirname(__file__), "..", "data")
ARQUIVO_CSV = os.path.join(PASTA_DATA, "licitacoes.csv")
ARQUIVO_JSON = os.path.join(PASTA_DATA, "licitacoes.json")
ARQUIVO_RESUMO = os.path.join(PASTA_DATA, "resumo_empresa.csv")

CAMPOS_CSV = [
    "data_execucao",
    "fonte",
    "empresa",
    "numero_pncp",
    "modalidade",
    "orgao",
    "objeto",
    "valor_estimado",
    "data_encerramento",
    "dias_restantes",
    "municipio",
    "uf",
    "link",
]


def _garantir_pasta():
    os.makedirs(PASTA_DATA, exist_ok=True)


def _extrair_dados(contratacao: dict, empresa: str, fonte: str, link: str) -> dict:
    orgao = contratacao.get("orgaoEntidade", {}).get("razaoSocial", "")
    valor = contratacao.get("valorTotalEstimado")
    uf = contratacao.get("unidadeOrgao", {}).get("ufSigla", "")
    municipio = contratacao.get("unidadeOrgao", {}).get("municipioNome", "")
    return {
        "data_execucao": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "fonte": fonte,
        "empresa": empresa,
        "numero_pncp": contratacao.get("numeroControlePNCP", ""),
        "modalidade": contratacao.get("_modalidade", ""),
        "orgao": orgao,
        "objeto": (contratacao.get("objetoCompra") or "").strip(),
        "valor_estimado": valor if valor else "",
        "data_encerramento": (contratacao.get("dataEncerramentoProposta") or "")[:10],
        "dias_restantes": contratacao.get("_dias_restantes", ""),
        "municipio": municipio,
        "uf": uf,
        "link": link,
    }


def exportar_licitacoes(lista: list, empresa: str, fonte: str = "empresa"):
    if not lista:
        return
    _garantir_pasta()
    registros = []
    for c in lista:
        from src.pncp_search import link_pncp
        link = link_pncp(c)
        registros.append(_extrair_dados(c, empresa, fonte, link))

    existente = []
    if os.path.exists(ARQUIVO_CSV):
        with open(ARQUIVO_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existente = list(reader)

    ids_existentes = {
        (r.get("numero_pncp"), r.get("empresa")) for r in existente
    }

    novos = 0
    for reg in registros:
        chave = (reg["numero_pncp"], reg["empresa"])
        if chave not in ids_existentes:
            existente.append(reg)
            ids_existentes.add(chave)
            novos += 1

    with open(ARQUIVO_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS_CSV)
        writer.writeheader()
        writer.writerows(existente)

    with open(ARQUIVO_JSON, "w", encoding="utf-8") as f:
        json.dump(existente, f, ensure_ascii=False, indent=2)

    print(f"   [DATA] {novos} novo(s) registro(s) salvo(s) em data/ ({len(existente)} total no CSV).")


def exportar_resumo(empresas_stats: list):
    if not empresas_stats:
        return
    _garantir_pasta()
    with open(ARQUIVO_RESUMO, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["data_execucao", "empresa", "cnpj", "licitacoes_encontradas", "alertas_enviados"])
        writer.writeheader()
        writer.writerows(empresas_stats)
    print(f"   [DATA] Resumo por empresa salvo em data/resumo_empresa.csv.")
