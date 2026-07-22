import os
import time
from datetime import datetime

import requests

API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def enviar_telegram(mensagem: str, token: str = None, chat_id: str = None) -> bool:
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("[AVISO] TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID nao configurados.")
        return False

    url = API_URL.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": mensagem,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    for tentativa in range(3):
        resp = requests.post(url, data=payload, timeout=15)
        if resp.ok:
            return True
        if resp.status_code == 429:
            retry_after = resp.json().get("parameters", {}).get("retry_after", 30)
            print(f"[429] Telegram rate limit, aguardando {retry_after}s...")
            time.sleep(retry_after + 1)
            continue
        print("[ERRO] Falha ao enviar Telegram:", resp.status_code, resp.text)
        return False
    print("[ERRO] Telegram: 3 tentativas falharam.")
    return False


def formatar_status(lista_empresas: list, novos: int) -> str:
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    empresas_texto = "\n".join(f"  - {e}" for e in lista_empresas)
    if novos > 0:
        resultado = f"{novos} nova(s) licitacao(oes) encontrada(s) e alerta(s) enviado(s)."
    else:
        resultado = "Nenhuma licitacao nova encontrada nesta busca."
    return (
        f"<b>Monitor de Licitacoes - Status</b>\n"
        f"Hora: {agora}\n"
        f"Empresas monitoradas:\n{empresas_texto}\n"
        f"Resultado: {resultado}"
    )


def formatar_alerta(empresa: str, contratacao: dict, link: str, cidade_empresa: str = "") -> str:
    orgao = contratacao.get("orgaoEntidade", {}).get("razaoSocial", "Orgao nao informado")
    modalidade = contratacao.get("_modalidade", "")
    objeto = (contratacao.get("objetoCompra") or "").strip()
    if len(objeto) > 400:
        objeto = objeto[:400] + "..."
    encerramento = contratacao.get("dataEncerramentoProposta", "N/A")
    valor = contratacao.get("valorTotalEstimado")
    valor_fmt = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if valor else "nao informado"
    uf = contratacao.get("unidadeOrgao", {}).get("ufSigla", "")
    municipio = contratacao.get("unidadeOrgao", {}).get("municipioNome", "")
    local = f"{municipio}/{uf}" if municipio else uf

    tag_local = ""
    if cidade_empresa and municipio and cidade_empresa.upper() in municipio.upper():
        tag_local = " LOCAL"

    dias = contratacao.get("_dias_restantes")
    dias_texto = f"{dias} dias restantes" if dias is not None else "prazo nao informado"

    return (
        f"<b>Nova licitacao encontrada{tag_local}</b>\n"
        f"Empresa monitorada: {empresa}\n"
        f"Local: {local}\n"
        f"Modalidade: {modalidade}\n"
        f"Orgao: {orgao}\n"
        f"Objeto: {objeto}\n"
        f"Valor estimado: {valor_fmt}\n"
        f"Prazo: {encerramento} ({dias_texto})\n"
        f"{link}"
    )
