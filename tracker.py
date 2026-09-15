#!/usr/bin/env python3
"""
Rastreador de Revisões Criminais do TJSC
Foco exclusivo: Processos em fase de Revisão Criminal sem advogado constituído.

Uso:
  python3 tracker.py
  python3 tracker.py --dias 30
  python3 tracker.py --inicio 01/08/2026 --fim 15/09/2026
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from typing import List

from config import (
    ORGAOS_REVISAO_CRIMINAL,
    STATUS_SEM_ADVOGADO,
    STATUS_DATIVO,
    STATUS_DPE,
    STATUS_CONSTITUIDO,
)
from portal_tjsc import PortalTJSCScraper
from eproc_scraper import EprocScraper, SessaoJulgamento
from classifier import RevisaoCriminal
from exporter import Exporter


def formatar_data(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y")


def parse_argumentos():
    parser = argparse.ArgumentParser(
        description="Rastreador de Revisões Criminais do TJSC (Sentenciados sem Advogado)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Rastrear revisões criminais dos últimos 30 dias:
  python3 tracker.py --dias 30

  # Rastrear período específico:
  python3 tracker.py --inicio 01/08/2026 --fim 15/09/2026

  # Rastrear incluindo processos com advogado constituído para comparação:
  python3 tracker.py --todos-status
        """
    )

    parser.add_argument("--inicio", type=str, default="", help="Data inicial DD/MM/AAAA")
    parser.add_argument("--fim", type=str, default="", help="Data final DD/MM/AAAA")
    parser.add_argument("--dias", type=int, default=30, help="Quantidade de dias anteriores a pesquisar (padrão: 30)")
    parser.add_argument(
        "--todos-status",
        action="store_true",
        help="Inclui todas as revisões criminais (inclusive as com advogado particular constituído)"
    )
    parser.add_argument("--saida", type=str, default="./relatorios", help="Diretório de saída (padrão: ./relatorios)")

    return parser.parse_args()


def resolver_periodo(inicio: str, fim: str, dias: int) -> tuple[str, str]:
    if inicio and fim:
        return inicio, fim
    hoje = datetime.now()
    if not fim:
        fim = formatar_data(hoje)
    if not inicio:
        dt_inicio = hoje - timedelta(days=dias)
        inicio = formatar_data(dt_inicio)
    return inicio, fim


def main():
    args = parse_argumentos()
    data_inicio, data_termino = resolver_periodo(args.inicio, args.fim, args.dias)

    print("=" * 72)
    print("       RASTREADOR DE REVISÕES CRIMINAIS - TJSC (EPROC)")
    print("=" * 72)
    print(f"Período de Análise: {data_inicio} até {data_termino}")
    print(f"Foco: Revisões Criminais sem Advogado Constituído (de próprio punho / jus postulandi)")
    print("-" * 72)

    # 1. Consulta ao Portal TJSC (Cancelamentos)
    print("[1/3] Verificando avisos regimentais e cancelamentos no Portal do TJSC...")
    portal_scraper = PortalTJSCScraper()
    dados_portal = portal_scraper.obter_dados_completos()
    cancelamentos = dados_portal.get("cancelamentos", [])
    print(f"  -> {len(cancelamentos)} alteração(ões)/cancelamento(s) ativa(s).")

    # 2. Busca de Sessões no 1º Grupo, 2º Grupo e Seção Criminal
    print(f"\n[2/3] Localizando sessões nos Grupos de Direito Criminal do TJSC...")
    eproc_scraper = EprocScraper()
    todas_sessoes: List[SessaoJulgamento] = []

    for nome_orgao, id_orgao in ORGAOS_REVISAO_CRIMINAL.items():
        sessoes = eproc_scraper.buscar_sessoes(
            data_inicio=data_inicio,
            data_termino=data_termino,
            id_orgao=id_orgao
        )
        sessoes_com_ata = [s for s in sessoes if s.possui_ata]
        print(f"  -> {nome_orgao}: {len(sessoes)} sessão(ões) ({len(sessoes_com_ata)} com Ata disponível)")
        todas_sessoes.extend(sessoes_com_ata)

    # 3. Download e Extração das Revisões Criminais
    print(f"\n[3/3] Extraindo processos de Revisão Criminal das {len(todas_sessoes)} atas colegiadas...")
    todas_revisoes: List[RevisaoCriminal] = []

    for idx, sessao in enumerate(todas_sessoes, 1):
        print(f"  [{idx}/{len(todas_sessoes)}] {sessao.orgao_julgador} ({sessao.periodo_data})... ", end="", flush=True)
        revs = eproc_scraper.carregar_revisoes_criminais_da_ata(sessao)
        todas_revisoes.extend(revs)
        print(f"{len(revs)} revisões criminais encontradas.")

    # 4. Filtragem
    if args.todos_status:
        selecionadas = todas_revisoes
    else:
        # Pega as que NÃO tem advogado constituído (inclui sem advogado, dativo nomeado e DPE)
        selecionadas = [
            r for r in todas_revisoes
            if r.status_defesa in [STATUS_SEM_ADVOGADO, STATUS_DATIVO, STATUS_DPE]
        ]

    # Estatísticas
    tot_sem = sum(1 for r in todas_revisoes if r.status_defesa == STATUS_SEM_ADVOGADO)
    tot_dat = sum(1 for r in todas_revisoes if r.status_defesa == STATUS_DATIVO)
    tot_dpe = sum(1 for r in todas_revisoes if r.status_defesa == STATUS_DPE)
    tot_const = sum(1 for r in todas_revisoes if r.status_defesa == STATUS_CONSTITUIDO)

    print("\n" + "=" * 72)
    print("                    ESTATÍSTICAS DE REVISÕES CRIMINAIS")
    print("=" * 72)
    print(f"Total de Revisões Criminais Identificadas:     {len(todas_revisoes)}")
    print(f"  🔴 Sem Advogado Constituído (de próprio punho): {tot_sem}")
    print(f"  🟣 Dativo Nomeado pelo Tribunal:               {tot_dat}")
    print(f"  🟢 Defensoria Pública (DPE):                   {tot_dpe}")
    print(f"  ⚪ Advogado Particular Constituído:             {tot_const}")
    print(f"Total Selecionado para o Relatório:            {len(selecionadas)}")
    print("=" * 72)

    # Exemplos
    if selecionadas:
        print("\nExemplos de sentenciados sem advogado constituído:")
        for r in selecionadas[:6]:
            print(f"\n  • Processo: {r.numero_processo} ({r.classe_processual})")
            print(f"    Sentenciado (Requerente): {r.nome_sentenciado}")
            print(f"    Origem: {r.comarca_origem} | Câmara: {r.orgao_julgador}")
            print(f"    Defesa: [{r.status_defesa}] -> {r.detalhes_defesa.get('justificativa')}")
            if r.decisao:
                print(f"    Decisão: \"{r.decisao[:180]}...\"")

    # 5. Exportação
    os.makedirs(args.saida, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefixo = os.path.join(args.saida, f"revisoes_criminais_tjsc_{timestamp}")

    csv_file = f"{prefixo}.csv"
    json_file = f"{prefixo}.json"
    html_file = f"{prefixo}.html"

    Exporter.export_csv(selecionadas, csv_file)
    Exporter.export_json(selecionadas, json_file, cancelamentos=cancelamentos)
    Exporter.export_html(selecionadas, html_file, cancelamentos=cancelamentos)

    print("\n" + "=" * 72)
    print("                         ARQUIVOS GERADOS")
    print("=" * 72)
    print(f"  ✔ Planilha CSV (Excel):      {os.path.abspath(csv_file)}")
    print(f"  ✔ Arquivo JSON Estruturado:  {os.path.abspath(json_file)}")
    print(f"  ✔ Relatório Local HTML:      {os.path.abspath(html_file)}")
    print(f"  ✔ Dashboard GitHub Pages:    {os.path.abspath('./docs/index.html')}")
    print("=" * 72)
    print("\nPara sincronizar a página pública com o GitHub Pages:")
    print("  git add docs/ . && git commit -m 'Atualização de Revisões Criminais' && git push\n")


if __name__ == "__main__":
    main()
