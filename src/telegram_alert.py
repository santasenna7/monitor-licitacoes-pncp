import os
import requests

API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def enviar_telegram(mensagem: str, token: str = None, chat_id: str = None) -> bool:
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("[AVISO] TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID nao configurados. "
              "Mensagem nao enviada, exibindo no log:\n", mensagem)
        return False

    url = API_URL.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": mensagem,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    resp = requests.post(url, data=payload, timeout=15)
    if not resp.ok:
        print("[ERRO] Falha ao enviar Telegram:", resp.status_code, resp.text)
        return False
    return True


def formatar_alerta(empresa: str, contratacao: dict, link: str) -> str:
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

    return (
        f"<b>Nova licitacao encontrada</b>\n"
        f"Empresa monitorada: {empresa}\n"
        f"Local: {local}\n"
        f"Modalidade: {modalidade}\n"
        f"Orgao: {orgao}\n"
        f"Objeto: {objeto}\n"
        f"Valor estimado: {valor_fmt}\n"
        f"Encerramento das propostas: {encerramento}\n"
        f"{link}"
    )
