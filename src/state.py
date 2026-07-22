import json
import os

CAMINHO_PADRAO = os.path.join(os.path.dirname(__file__), "..", "state.json")


def carregar_estado(caminho: str = CAMINHO_PADRAO) -> dict:
    if not os.path.exists(caminho):
        return {"notificados": []}
    with open(caminho, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"notificados": []}


def salvar_estado(estado: dict, caminho: str = CAMINHO_PADRAO) -> None:
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def id_contratacao(contratacao: dict) -> str:
    return contratacao.get("numeroControlePNCP") or (
        f"{contratacao.get('orgaoEntidade', {}).get('cnpj', '')}-"
        f"{contratacao.get('anoCompra', '')}-"
        f"{contratacao.get('sequencialCompra', '')}"
    )
