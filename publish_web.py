#!/usr/bin/env python3
"""
Script auxiliar para atualizar o painel web público com o relatório mais recente.
"""

import glob
import json
import os
import subprocess
import sys


def obter_relatorio_mais_recente(relatorios_dir="./relatorios") -> str:
    arquivos = glob.glob(os.path.join(relatorios_dir, "tjsc_rastreabilidade_*.json"))
    if not arquivos:
        return ""
    arquivos.sort(key=os.path.getmtime, reverse=True)
    return arquivos[0]


def atualizar_web(json_path: str, web_dir="../rastreador-tjsc-web", push_git=True):
    if not os.path.exists(json_path):
        print(f"[ERRO] Arquivo não encontrado: {json_path}")
        return False

    os.makedirs(web_dir, exist_ok=True)
    with open(json_path, "r", encoding="utf-8") as f:
        data_full = json.load(f)

    # Copia data.json
    dest_data = os.path.join(web_dir, "data.json")
    with open(dest_data, "w", encoding="utf-8") as f:
        json.dump(data_full, f, ensure_ascii=False, indent=2)

    # Gera index.html a partir do exporter
    from classifier import ProcessoJulgado, Parte, Representante
    from exporter import Exporter

    processos = []
    for p in data_full.get("processos", []):
        partes = []
        for pt in p.get("partes", []):
            reps = [
                Representante(tipo=r.get("tipo", ""), nome=r.get("nome", ""), oab_ou_orgao=r.get("oab_ou_orgao", ""))
                for r in pt.get("representantes", [])
            ]
            partes.append(Parte(polo=pt.get("polo", ""), tipo=pt.get("tipo", ""), nome=pt.get("nome", ""), representantes=reps))

        proc = ProcessoJulgado(
            numero_processo=p.get("numero_processo", ""),
            classe_processual=p.get("classe_processual", ""),
            origem=p.get("origem", "SC"),
            seq_pauta=p.get("seq_pauta", ""),
            orgao_julgador=p.get("orgao_julgador", ""),
            data_sessao=p.get("data_sessao", ""),
            tipo_sessao=p.get("tipo_sessao", ""),
            partes=partes,
            decisao=p.get("decisao", ""),
            categorias=p.get("categorias", []),
            detalhes_classificacao=p.get("detalhes_classificacao", {}),
            link_processo=p.get("link_processo", "")
        )
        processos.append(proc)

    dest_html = os.path.join(web_dir, "index.html")
    Exporter.export_html(processos, dest_html, cancelamentos=data_full.get("cancelamentos_tjsc", []))
    print(f"✔ Dashboard web atualizado: {dest_html}")

    if push_git and os.path.exists(os.path.join(web_dir, ".git")):
        print("Enviando atualização para o GitHub Pages...")
        subprocess.run(["git", "add", "."], cwd=web_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Atualização automática de dados do TJSC"], cwd=web_dir, check=True)
        subprocess.run(["git", "push"], cwd=web_dir, check=True)
        print("✔ Publicado no GitHub Pages com sucesso!")

    return True


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else obter_relatorio_mais_recente()
    if not caminho:
        print("Nenhum relatório encontrado para publicar.")
        sys.exit(1)
    print(f"Publicando relatório: {caminho}")
    atualizar_web(caminho)
