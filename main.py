import sys
import time
import json
import os

from src.cnpj_lookup import consultar_cnpj
from src.pncp_search import buscar_contratacoes_abertas, filtrar_por_palavras_chave, link_pncp
from src.telegram_alert import enviar_telegram, formatar_alerta
from src.state import carregar_estado, salvar_estado, id_contratacao

CAMINHO_EMPRESAS = os.path.join(os.path.dirname(__file__), "config", "empresas.json")


def carregar_empresas() -> list:
    with open(CAMINHO_EMPRESAS, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    empresas = carregar_empresas()
    if not empresas:
        print("Nenhuma empresa cadastrada em config/empresas.json")
        return 0

    ufs_todas = set()
    for e in empresas:
        ufs_todas.update(e.get("ufs_interesse", []))

    print(f"[1/4] Buscando contratacoes abertas no PNCP...")
    if ufs_todas:
        todas_contratacoes = []
        for uf in ufs_todas:
            print(f"   -> Buscando licitacoes em {uf}...")
            todas_contratacoes.extend(buscar_contratacoes_abertas(uf=uf))
    else:
        todas_contratacoes = buscar_contratacoes_abertas()
    print(f"   -> {len(todas_contratacoes)} contratacoes com propostas em aberto encontradas.")

    estado = carregar_estado()
    notificados = set(estado.get("notificados", []))
    novos_alertas = 0

    for empresa_cfg in empresas:
        cnpj = empresa_cfg["cnpj"]
        nome_cfg = empresa_cfg.get("nome", cnpj)
        print(f"\n[2/4] Consultando CNAE do CNPJ {cnpj} ({nome_cfg})...")

        try:
            dados_empresa = consultar_cnpj(cnpj)
        except Exception as e:
            print(f"   [ERRO] Nao foi possivel consultar o CNPJ {cnpj}: {e}")
            continue

        palavras = set(dados_empresa["palavras_chave"])
        palavras.update(empresa_cfg.get("palavras_chave_extra", []))
        razao_social = dados_empresa["razao_social"] or nome_cfg

        print(f"   -> Razao social: {razao_social}")
        print(f"   -> CNAE principal: {dados_empresa['cnae_principal']['descricao']}")
        print(f"   -> {len(palavras)} palavras-chave geradas para busca.")

        print(f"[3/4] Cruzando com o objeto das licitacoes...")
        candidatos = todas_contratacoes
        uf_interesse = empresa_cfg.get("ufs_interesse") or []
        if uf_interesse:
            candidatos = [
                c for c in candidatos
                if c.get("unidadeOrgao", {}).get("ufSigla") in uf_interesse
            ]

        cidade_interesse = (empresa_cfg.get("cidade") or "").upper().strip()
        if cidade_interesse:
            candidatos = [
                c for c in candidatos
                if cidade_interesse in (c.get("unidadeOrgao", {}).get("municipioNome") or "").upper()
                or cidade_interesse in (c.get("objetoCompra") or "").upper()
                or cidade_interesse in (c.get("orgaoEntidade", {}).get("razaoSocial") or "").upper()
            ]

        cnae_codigo = dados_empresa["cnae_principal"].get("codigo", "")
        cnaes_sec_codigos = [c.get("codigo", "") for c in dados_empresa["cnaes_secundarios"]]
        todos_cnaes = [cnae_codigo] + cnaes_sec_codigos

        encontrados = filtrar_por_palavras_chave(candidatos, list(palavras), todos_cnaes)
        print(f"   -> {len(encontrados)} licitacoes compatíveis.")

        print(f"[4/4] Enviando alertas de licitacoes novas...")
        for contratacao in encontrados:
            cid = id_contratacao(contratacao)
            chave = f"{cnpj}:{cid}"
            if chave in notificados:
                continue

            link = link_pncp(contratacao)
            mensagem = formatar_alerta(razao_social, contratacao, link)
            enviado = enviar_telegram(mensagem)
            if enviado:
                novos_alertas += 1
            notificados.add(chave)
            time.sleep(0.5)

    estado["notificados"] = sorted(notificados)
    salvar_estado(estado)

    print(f"\nConcluido. {novos_alertas} novo(s) alerta(s) enviado(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
