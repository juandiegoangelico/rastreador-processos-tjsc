#!/usr/bin/env python3
"""
Rastreador de Processos TJSC - Orquestrador Principal e Linha de Comando (CLI)
Monitoramento de processos em sessões de julgamento com foco em:
- Advogado Dativo (arbitramento/fixação de honorários)
- Defensoria Pública do Estado (DPE)
- Polo Desacompanhado (Sem Advogado Constituído)

Uso:
  python3 tracker.py
  python3 tracker.py --dias 7 --orgao criminal --filtro dativo,dpe,sem_advogado
  python3 tracker.py --inicio 01/09/2026 --fim 15/09/2026 --exportar html,csv
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

from config import (
    ORGAOS_EPROC,
    GRUPOS_ORGAOS,
    TIPO_DATIVO,
    TIPO_DPE,
    TIPO_SEM_ADVOGADO,
    TIPO_CONSTITUIDO,
)
from portal_tjsc import PortalTJSCScraper
from eproc_scraper import EprocScraper, SessaoJulgamento
from classifier import ProcessoJulgado
from exporter import Exporter


def formatar_data(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y")


def parse_argumentos():
    parser = argparse.ArgumentParser(
        description="Rastreador de Processos TJSC (Dativo, DPE e Sem Advogado)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  # Rastrear últimas sessões (últimos 7 dias) em câmaras criminais com foco em Dativo, DPE e Sem Advogado:
  python3 tracker.py --dias 7 --orgao criminal --filtro dativo,dpe,sem_advogado

  # Rastrear período específico em todos os órgãos e exportar em HTML e CSV:
  python3 tracker.py --inicio 01/09/2026 --fim 15/09/2026 --exportar html,csv

  # Apenas processos com Advogado Dativo:
  python3 tracker.py --filtro dativo
        """
    )

    parser.add_argument(
        "--inicio",
        type=str,
        default="",
        help="Data inicial no formato DD/MM/AAAA (ex: 01/09/2026)"
    )
    parser.add_argument(
        "--fim",
        type=str,
        default="",
        help="Data final no formato DD/MM/AAAA (ex: 15/09/2026)"
    )
    parser.add_argument(
        "--dias",
        type=int,
        default=7,
        help="Quantidade de dias anteriores a pesquisar a partir de hoje se não passar --inicio (padrão: 7)"
    )
    parser.add_argument(
        "--orgao",
        type=str,
        default="todos",
        help="Órgão ou grupo: todos, criminal, civil, publico, comercial ou código do órgão no eproc (padrão: todos)"
    )
    parser.add_argument(
        "--filtro",
        type=str,
        default="dativo,dpe,sem_advogado",
        help="Categorias desejadas separadas por vírgula: dativo, dpe, sem_advogado, todos (padrão: dativo,dpe,sem_advogado)"
    )
    parser.add_argument(
        "--max-atas",
        type=int,
        default=15,
        help="Limite de atas a baixar e processar para evitar sobrecarga (padrão: 15, use 0 para ilimitado)"
    )
    parser.add_argument(
        "--exportar",
        type=str,
        default="html,csv",
        help="Formatos de saída separados por vírgula: html, csv, json, todos (padrão: html,csv)"
    )
    parser.add_argument(
        "--saida",
        type=str,
        default="./relatorios",
        help="Diretório onde os relatórios gerados serão salvos (padrão: ./relatorios)"
    )
    parser.add_argument(
        "--sem-portal",
        action="store_true",
        help="Ignora a consulta complementar ao portal de cancelamentos do TJSC"
    )

    return parser.parse_args()


def resolver_periodo(inicio: str, fim: str, dias: int) -> tuple[str, str]:
    """Calcula ou valida o período de busca DD/MM/AAAA."""
    if inicio and fim:
        return inicio, fim

    hoje = datetime.now()
    if not fim:
        fim = formatar_data(hoje)
    if not inicio:
        dt_inicio = hoje - timedelta(days=dias)
        inicio = formatar_data(dt_inicio)

    return inicio, fim


def resolver_orgao_id(orgao_arg: str) -> str:
    """Traduz argumento de órgão para ID do Eproc ou vazio para todos."""
    limpo = orgao_arg.lower().strip()
    if limpo in ["todos", "all", ""]:
        return ""
    if limpo in ORGAOS_EPROC:
        return ORGAOS_EPROC[limpo]
    # Se passou número direto
    if limpo.isdigit():
        return limpo
    return ""


def main():
    args = parse_argumentos()
    data_inicio, data_termino = resolver_periodo(args.inicio, args.fim, args.dias)
    id_orgao = resolver_orgao_id(args.orgao)

    print("=" * 70)
    print("      RASTREADOR DE PROCESSOS JUDICIAIS - TJSC (EPROC / PORTAL)")
    print("=" * 70)
    print(f"Período: {data_inicio} até {data_termino}")
    print(f"Filtro de Órgão: {args.orgao.upper()}")
    print(f"Filtro de Representação: {args.filtro.upper()}")
    print("-" * 70)

    # 1. Consulta ao Portal Institucional TJSC (Cancelamentos e Transferências)
    cancelamentos_info = []
    if not args.sem_portal:
        print("[1/3] Verificando avisos de cancelamentos no Portal do TJSC...")
        portal_scraper = PortalTJSCScraper()
        dados_portal = portal_scraper.obter_dados_completos()
        cancelamentos_info = dados_portal.get("cancelamentos", [])
        tot_canc = len(cancelamentos_info)
        tot_fis = dados_portal.get("total_sessoes_fisicas", 0)
        print(f"  -> {tot_canc} cancelamento(s)/alteração(ões) ativa(s) encontrada(s).")
        print(f"  -> {tot_fis} sessão(ões) física(s) no calendário oficial.")
        for c in cancelamentos_info:
            print(f"     ⚠️ {c.get('orgao_julgador')} ({c.get('sessao_original')}): {c.get('descricao_alteracao')}")

    # 2. Consulta ao Eproc 2G
    print(f"\n[2/3] Consultando sessões no Eproc 2G ({data_inicio} a {data_termino})...")
    eproc_scraper = EprocScraper()
    sessoes = eproc_scraper.buscar_sessoes(
        data_inicio=data_inicio,
        data_termino=data_termino,
        id_orgao=id_orgao
    )
    print(f"  -> Total de sessões listadas no período: {len(sessoes)}")

    # Filtra por grupo de órgãos se especificado
    orgao_arg_lower = args.orgao.lower().strip()
    if orgao_arg_lower in GRUPOS_ORGAOS:
        # filtra pelo nome do orgao ou câmara
        if orgao_arg_lower == "criminal":
            sessoes = [s for s in sessoes if "criminal" in s.orgao_julgador.lower()]
        elif orgao_arg_lower == "civil":
            sessoes = [s for s in sessoes if "civil" in s.orgao_julgador.lower()]
        elif orgao_arg_lower == "publico":
            sessoes = [s for s in sessoes if "público" in s.orgao_julgador.lower() or "publico" in s.orgao_julgador.lower()]
        elif orgao_arg_lower == "comercial":
            sessoes = [s for s in sessoes if "comercial" in s.orgao_julgador.lower()]
        print(f"  -> Sessões pertencentes ao grupo '{orgao_arg_lower}': {len(sessoes)}")

    sessoes_com_ata = [s for s in sessoes if s.possui_ata]
    print(f"  -> Sessões com Ata de Julgamento concluída: {len(sessoes_com_ata)}")

    # 3. Processamento das Atas
    max_atas = args.max_atas if args.max_atas > 0 else len(sessoes_com_ata)
    sessoes_para_processar = sessoes_com_ata[:max_atas]

    print(f"\n[3/3] Baixando e analisando {len(sessoes_para_processar)} atas de julgamento...")
    todos_processos: List[ProcessoJulgado] = []

    for idx, sessao in enumerate(sessoes_para_processar, 1):
        print(f"  [{idx}/{len(sessoes_para_processar)}] {sessao.orgao_julgador} ({sessao.periodo_data})... ", end="", flush=True)
        procs = eproc_scraper.carregar_processos_da_ata(sessao)
        todos_processos.extend(procs)
        print(f"{len(procs)} processos analisados.")

    # 4. Filtragem por categorias
    filtros_selecionados = [f.strip().upper() for f in args.filtro.split(",")]
    processos_filtrados: List[ProcessoJulgado] = []

    for p in todos_processos:
        if "TODOS" in filtros_selecionados:
            processos_filtrados.append(p)
        else:
            corresponde = False
            for f in filtros_selecionados:
                if f == "DATIVO" and TIPO_DATIVO in p.categorias:
                    corresponde = True
                elif f in ["DPE", "DEFENSORIA"] and TIPO_DPE in p.categorias:
                    corresponde = True
                elif f in ["SEM_ADVOGADO", "SEM_ADV", "REVEL"] and TIPO_SEM_ADVOGADO in p.categorias:
                    corresponde = True
                elif f == "CONSTITUIDO" and TIPO_CONSTITUIDO in p.categorias:
                    corresponde = True
            if corresponde:
                processos_filtrados.append(p)

    # 5. Apresentação dos Resultados
    tot_dativo = sum(1 for p in todos_processos if TIPO_DATIVO in p.categorias)
    tot_dpe = sum(1 for p in todos_processos if TIPO_DPE in p.categorias)
    tot_sem = sum(1 for p in todos_processos if TIPO_SEM_ADVOGADO in p.categorias)

    print("\n" + "=" * 70)
    print("                    ESTATÍSTICAS CONSOLIDADAS")
    print("=" * 70)
    print(f"Total de Processos Julgados nas Atas Analisadas: {len(todos_processos)}")
    print(f"  🟣 Com Advogado Dativo (honorários fixados):   {tot_dativo}")
    print(f"  🟢 Com Defensoria Pública (DPE):              {tot_dpe}")
    print(f"  🔴 Sem Advogado Constituído / Réu Desassistido: {tot_sem}")
    print(f"Total de Processos Selecionados para Relatório: {len(processos_filtrados)}")
    print("=" * 70)

    # Mostra até 5 destaques
    if processos_filtrados:
        print("\nExemplos de processos identificados:")
        for p in processos_filtrados[:5]:
            cats = " | ".join(p.categorias)
            print(f"\n  • Processo: {p.numero_processo} ({p.classe_processual})")
            print(f"    Câmara: {p.orgao_julgador} | Sessão: {p.data_sessao}")
            print(f"    Status: [{cats}]")
            if TIPO_DATIVO in p.categorias:
                m = p.detalhes_classificacao.get("motivos_dativo", [{}])[0]
                trecho = m.get("trecho") or m.get("detalhe", "")
                print(f"    Arbitramento Dativo: \"{trecho}\"")
            if TIPO_DPE in p.categorias:
                d = p.detalhes_classificacao.get("defensores_dpe", [{}])[0]
                print(f"    Defensoria: {d.get('representante')} representando {d.get('parte')}")
            if TIPO_SEM_ADVOGADO in p.categorias:
                s = p.detalhes_classificacao.get("partes_sem_advogado", [{}])[0]
                print(f"    Parte Desacompanhada: {s.get('tipo')} - {s.get('nome')}")

    # 6. Exportação
    os.makedirs(args.saida, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefixo = os.path.join(args.saida, f"tjsc_rastreabilidade_{timestamp}")

    formatos = [f.strip().lower() for f in args.exportar.split(",")]
    arquivos_gerados = []

    if "csv" in formatos or "todos" in formatos:
        csv_file = f"{prefixo}.csv"
        Exporter.export_csv(processos_filtrados, csv_file)
        arquivos_gerados.append(("CSV (Planilha Excel)", csv_file))

    if "json" in formatos or "todos" in formatos:
        json_file = f"{prefixo}.json"
        Exporter.export_json(processos_filtrados, json_file, cancelamentos=cancelamentos_info)
        arquivos_gerados.append(("JSON Estruturado", json_file))

    if "html" in formatos or "todos" in formatos:
        html_file = f"{prefixo}.html"
        Exporter.export_html(processos_filtrados, html_file, cancelamentos=cancelamentos_info)
        arquivos_gerados.append(("Relatório Visual Interativo (HTML)", html_file))

    print("\n" + "=" * 70)
    print("                    ARQUIVOS EXPORTADOS")
    print("=" * 70)
    for desc, path in arquivos_gerados:
        print(f"  ✔ {desc}: {os.path.abspath(path)}")
    print("=" * 70)

    # Mostra comando para abrir HTML se foi gerado
    html_gerado = next((p for d, p in arquivos_gerados if "HTML" in d), None)
    if html_gerado:
        print(f"\n💡 Dica: Para abrir o relatório visual no navegador, execute:")
        print(f"   open \"{os.path.abspath(html_gerado)}\"")
    print()


if __name__ == "__main__":
    main()
