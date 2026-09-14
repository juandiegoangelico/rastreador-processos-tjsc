"""
Módulo de Exportação e Relatórios.
Gera saídas em:
- CSV (compatível com Excel com codificação utf-8-sig)
- JSON estruturado
- Relatório HTML visual interativo (autossuficiente, com busca e filtros)
"""

import csv
import json
import os
from typing import List, Dict, Any
from classifier import ProcessoJulgado, TIPO_DATIVO, TIPO_DPE, TIPO_SEM_ADVOGADO


class Exporter:
    @staticmethod
    def export_csv(processos: List[ProcessoJulgado], filepath: str) -> str:
        """Gera arquivo CSV com os processos rastreados."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow([
                "Numero_Processo",
                "Classe_Processual",
                "Orgao_Julgador",
                "Data_Sessao",
                "Tipo_Sessao",
                "Categorias",
                "Partes",
                "Representantes",
                "Detalhes_Classificacao",
                "Decisao_Dispositivo",
                "Link_Eproc"
            ])

            for p in processos:
                partes_txt = " | ".join([f"{parte.tipo}: {parte.nome}" for parte in p.partes])
                reps_txt = []
                for parte in p.partes:
                    for r in parte.representantes:
                        reps_txt.append(f"{r.tipo}: {r.nome}")
                reps_str = " | ".join(reps_txt) if reps_txt else "Sem representante cadastrado"

                detalhes_arr = []
                if TIPO_DATIVO in p.categorias:
                    motivos = p.detalhes_classificacao.get("motivos_dativo", [])
                    trechos = [m.get("trecho") or m.get("detalhe", "") for m in motivos]
                    detalhes_arr.append("Dativo: " + "; ".join(trechos[:2]))
                if TIPO_DPE in p.categorias:
                    dpes = [f"{d.get('representante')} ({d.get('parte')})" for d in p.detalhes_classificacao.get("defensores_dpe", [])]
                    detalhes_arr.append("DPE: " + "; ".join(dpes))
                if TIPO_SEM_ADVOGADO in p.categorias:
                    sem = [f"{s.get('tipo')} {s.get('nome')}" for s in p.detalhes_classificacao.get("partes_sem_advogado", [])]
                    detalhes_arr.append("Sem Advogado: " + "; ".join(sem))

                writer.writerow([
                    p.numero_processo,
                    p.classe_processual,
                    p.orgao_julgador,
                    p.data_sessao,
                    p.tipo_sessao,
                    ", ".join(p.categorias),
                    partes_txt,
                    reps_str,
                    " // ".join(detalhes_arr),
                    p.decisao[:300] + ("..." if len(p.decisao) > 300 else ""),
                    p.link_processo
                ])

        return filepath

    @staticmethod
    def export_json(processos: List[ProcessoJulgado], filepath: str, cancelamentos: List[Dict[str, Any]] = None) -> str:
        """Gera arquivo JSON estruturado contendo processos e dados complementares."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        dados = {
            "total_processos": len(processos),
            "estatisticas": {
                "dativo": sum(1 for p in processos if TIPO_DATIVO in p.categorias),
                "dpe": sum(1 for p in processos if TIPO_DPE in p.categorias),
                "sem_advogado": sum(1 for p in processos if TIPO_SEM_ADVOGADO in p.categorias),
            },
            "cancelamentos_tjsc": cancelamentos or [],
            "processos": [
                {
                    "numero_processo": p.numero_processo,
                    "classe_processual": p.classe_processual,
                    "origem": p.origem,
                    "seq_pauta": p.seq_pauta,
                    "orgao_julgador": p.orgao_julgador,
                    "data_sessao": p.data_sessao,
                    "tipo_sessao": p.tipo_sessao,
                    "categorias": p.categorias,
                    "detalhes_classificacao": p.detalhes_classificacao,
                    "partes": [
                        {
                            "polo": pt.polo,
                            "tipo": pt.tipo,
                            "nome": pt.nome,
                            "representantes": [
                                {"tipo": r.tipo, "nome": r.nome, "oab_ou_orgao": r.oab_ou_orgao}
                                for r in pt.representantes
                            ]
                        }
                        for pt in p.partes
                    ],
                    "decisao": p.decisao,
                    "link_processo": p.link_processo
                }
                for p in processos
            ]
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        return filepath

    @staticmethod
    def export_html(processos: List[ProcessoJulgado], filepath: str, cancelamentos: List[Dict[str, Any]] = None) -> str:
        """Gera relatório HTML moderno, interativo e autossuficiente."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        tot_dativo = sum(1 for p in processos if TIPO_DATIVO in p.categorias)
        tot_dpe = sum(1 for p in processos if TIPO_DPE in p.categorias)
        tot_sem_adv = sum(1 for p in processos if TIPO_SEM_ADVOGADO in p.categorias)
        tot_total = len(processos)

        # Converte lista para JSON seguro embutido
        dados_json = json.dumps([
            {
                "num": p.numero_processo,
                "classe": p.classe_processual,
                "orgao": p.orgao_julgador,
                "data": p.data_sessao,
                "tipo": p.tipo_sessao,
                "categorias": p.categorias,
                "detalhes": p.detalhes_classificacao,
                "partes": [
                    {
                        "polo": pt.polo,
                        "tipo": pt.tipo,
                        "nome": pt.nome,
                        "reps": [f"{r.tipo}: {r.nome}" for r in pt.representantes]
                    }
                    for pt in p.partes
                ],
                "decisao": p.decisao,
                "link": p.link_processo
            }
            for p in processos
        ], ensure_ascii=False)

        cancelamentos_html = ""
        if cancelamentos:
            cancelamentos_html = "<div class='alerts-box'><h3>⚠️ Alterações e Cancelamentos Informados no Portal TJSC</h3><ul>"
            for c in cancelamentos:
                cancelamentos_html += f"<li><strong>{c.get('orgao_julgador')}</strong> ({c.get('sessao_original')}): {c.get('descricao_alteracao')}</li>"
            cancelamentos_html += "</ul></div>"

        html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rastreabilidade de Processos - TJSC (Dativo / DPE / Sem Advogado)</title>
    <style>
        :root {{
            --bg-color: #0f172a;
            --surface-color: #1e293b;
            --surface-hover: #334155;
            --primary: #38bdf8;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --badge-dativo: #a855f7;
            --badge-dpe: #10b981;
            --badge-sem: #ef4444;
            --badge-const: #64748b;
            --border-color: #334155;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            padding: 24px;
            line-height: 1.5;
        }}
        header {{
            margin-bottom: 24px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 16px;
        }}
        h1 {{ font-size: 1.8rem; font-weight: 700; color: #fff; }}
        p.subtitle {{ color: var(--text-muted); font-size: 0.95rem; margin-top: 4px; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .stat-card {{
            background: var(--surface-color);
            padding: 16px;
            border-radius: 10px;
            border: 1px solid var(--border-color);
        }}
        .stat-card .label {{ font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; }}
        .stat-card .value {{ font-size: 1.9rem; font-weight: 700; margin-top: 4px; }}
        .val-total {{ color: var(--primary); }}
        .val-dativo {{ color: var(--badge-dativo); }}
        .val-dpe {{ color: var(--badge-dpe); }}
        .val-sem {{ color: var(--badge-sem); }}
        .alerts-box {{
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid var(--badge-sem);
            padding: 14px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 0.9rem;
        }}
        .alerts-box h3 {{ color: #fca5a5; margin-bottom: 8px; font-size: 1rem; }}
        .controls {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 18px;
            align-items: center;
        }}
        .search-input {{
            flex: 1;
            min-width: 280px;
            padding: 10px 14px;
            border-radius: 8px;
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            color: #fff;
            font-size: 0.95rem;
        }}
        .filter-btn {{
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            padding: 8px 14px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.2s;
        }}
        .filter-btn.active {{
            background: var(--primary);
            color: #0f172a;
            font-weight: 600;
            border-color: var(--primary);
        }}
        .table-wrapper {{
            background: var(--surface-color);
            border-radius: 10px;
            border: 1px solid var(--border-color);
            overflow-x: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
            text-align: left;
        }}
        th {{
            background: #162032;
            color: var(--text-muted);
            padding: 12px 14px;
            font-weight: 600;
            border-bottom: 1px solid var(--border-color);
        }}
        td {{
            padding: 12px 14px;
            border-bottom: 1px solid var(--border-color);
            vertical-align: top;
        }}
        tr:hover {{ background: rgba(255,255,255,0.02); }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            margin-right: 4px;
            margin-bottom: 4px;
            text-transform: uppercase;
        }}
        .badge-dativo {{ background: rgba(168, 85, 247, 0.2); color: #d8b4fe; border: 1px solid var(--badge-dativo); }}
        .badge-dpe {{ background: rgba(16, 185, 129, 0.2); color: #6ee7b7; border: 1px solid var(--badge-dpe); }}
        .badge-sem {{ background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid var(--badge-sem); }}
        .badge-const {{ background: rgba(100, 116, 139, 0.2); color: #cbd5e1; }}
        .proc-link {{
            color: var(--primary);
            text-decoration: none;
            font-weight: 600;
            font-family: monospace;
            font-size: 0.95rem;
        }}
        .proc-link:hover {{ text-decoration: underline; }}
        .snippet-box {{
            margin-top: 6px;
            background: rgba(0,0,0,0.25);
            padding: 6px 10px;
            border-radius: 6px;
            font-size: 0.8rem;
            border-left: 3px solid var(--primary);
            color: #cbd5e1;
        }}
        .partes-list {{ font-size: 0.82rem; color: #cbd5e1; }}
        .rep-item {{ color: #94a3b8; margin-left: 8px; }}
    </style>
</head>
<body>
    <header>
        <h1>TJSC • Rastreabilidade Processual de Julgamentos</h1>
        <p class="subtitle">Monitoramento de processos com Advogado Dativo, Defensoria Pública (DPE) ou Polo Desacompanhado (Sem Advogado).</p>
    </header>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="label">Total Rastreados</div>
            <div class="value val-total" id="stat-total">{tot_total}</div>
        </div>
        <div class="stat-card">
            <div class="label">Advogado Dativo</div>
            <div class="value val-dativo" id="stat-dativo">{tot_dativo}</div>
        </div>
        <div class="stat-card">
            <div class="label">Defensoria Pública (DPE)</div>
            <div class="value val-dpe" id="stat-dpe">{tot_dpe}</div>
        </div>
        <div class="stat-card">
            <div class="label">Sem Advogado / Revel</div>
            <div class="value val-sem" id="stat-sem">{tot_sem_adv}</div>
        </div>
    </div>

    {cancelamentos_html}

    <div class="controls">
        <input type="text" id="search-box" class="search-input" placeholder="Pesquisar por número do processo, parte, advogado, câmara..." oninput="filtrarDados()">
        <button class="filter-btn active" onclick="setFiltro('TODOS')">Todos</button>
        <button class="filter-btn" onclick="setFiltro('DATIVO')">Advogado Dativo ({tot_dativo})</button>
        <button class="filter-btn" onclick="setFiltro('DPE')">DPE ({tot_dpe})</button>
        <button class="filter-btn" onclick="setFiltro('SEM_ADVOGADO')">Sem Advogado ({tot_sem_adv})</button>
    </div>

    <div class="table-wrapper">
        <table id="tbl-processos">
            <thead>
                <tr>
                    <th style="width: 210px;">Processo</th>
                    <th style="width: 140px;">Status / Categoria</th>
                    <th style="width: 200px;">Órgão Julgador / Data</th>
                    <th>Partes e Representantes</th>
                    <th>Fundamentação / Decisão</th>
                </tr>
            </thead>
            <tbody id="tbl-body">
            </tbody>
        </table>
    </div>

    <script>
        const processos = {dados_json};
        let filtroAtivo = 'TODOS';

        function renderBadges(categorias) {{
            return categorias.map(c => {{
                if (c === 'DATIVO') return '<span class="badge badge-dativo">Adv. Dativo</span>';
                if (c === 'DPE') return '<span class="badge badge-dpe">DPE</span>';
                if (c === 'SEM_ADVOGADO') return '<span class="badge badge-sem">Sem Advogado</span>';
                return '<span class="badge badge-const">' + c + '</span>';
            }}).join('');
        }}

        function setFiltro(tipo) {{
            filtroAtivo = tipo;
            document.querySelectorAll('.filter-btn').forEach(btn => {{
                if (btn.textContent.toUpperCase().includes(tipo)) {{
                    btn.classList.add('active');
                }} else if (tipo === 'TODOS' && btn.textContent === 'Todos') {{
                    btn.classList.add('active');
                }} else {{
                    btn.classList.remove('active');
                }}
            }});
            filtrarDados();
        }}

        function filtrarDados() {{
            const termo = document.getElementById('search-box').value.toLowerCase().trim();
            const tbody = document.getElementById('tbl-body');
            tbody.innerHTML = '';

            const filtrados = processos.filter(p => {{
                if (filtroAtivo !== 'TODOS' && !p.categorias.includes(filtroAtivo)) {{
                    return false;
                }}
                if (!termo) return true;

                const textoBusca = (
                    p.num + " " + p.classe + " " + p.orgao + " " +
                    JSON.stringify(p.partes) + " " + JSON.stringify(p.detalhes) + " " + p.decisao
                ).toLowerCase();
                return textoBusca.includes(termo);
            }});

            if (filtrados.length === 0) {{
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 24px; color: var(--text-muted);">Nenhum processo correspondente aos filtros.</td></tr>';
                return;
            }}

            filtrados.forEach(p => {{
                const tr = document.createElement('tr');

                // Formatação partes
                let partesHtml = '<div class="partes-list">';
                p.partes.forEach(pt => {{
                    partesHtml += '<div><strong>' + pt.tipo + ':</strong> ' + pt.nome;
                    if (pt.reps && pt.reps.length > 0) {{
                        pt.reps.forEach(r => {{
                            partesHtml += '<div class="rep-item">↳ ' + r + '</div>';
                        }});
                    }} else {{
                        partesHtml += '<div class="rep-item" style="color: #fca5a5;">↳ [Sem advogado cadastrado]</div>';
                    }}
                    partesHtml += '</div>';
                }});
                partesHtml += '</div>';

                // Detalhes da fundamentação
                let decisaoHtml = '';
                if (p.detalhes && p.detalhes.motivos_dativo && p.detalhes.motivos_dativo.length > 0) {{
                    const motivo = p.detalhes.motivos_dativo[0];
                    const trecho = motivo.trecho || motivo.detalhe || '';
                    decisaoHtml += '<div class="snippet-box" style="border-left-color: var(--badge-dativo);"><strong>Arbitramento Dativo:</strong> ' + trecho + '</div>';
                }}
                if (p.detalhes && p.detalhes.defensores_dpe && p.detalhes.defensores_dpe.length > 0) {{
                    const d = p.detalhes.defensores_dpe[0];
                    decisaoHtml += '<div class="snippet-box" style="border-left-color: var(--badge-dpe);"><strong>Atuação DPE:</strong> ' + d.representante + '</div>';
                }}
                if (p.decisao) {{
                    decisaoHtml += '<div style="margin-top:6px; font-size:0.8rem; color:#94a3b8;">' + (p.decisao.length > 220 ? p.decisao.substring(0, 220) + '...' : p.decisao) + '</div>';
                }}

                const linkHtml = p.link ? '<a class="proc-link" href="' + p.link + '" target="_blank">' + p.num + '</a>' : '<span class="proc-link">' + p.num + '</span>';

                tr.innerHTML = `
                    <td>
                        ${{linkHtml}}
                        <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 2px;">${{p.classe}}</div>
                    </td>
                    <td>${{renderBadges(p.categorias)}}</td>
                    <td>
                        <strong>${{p.orgao}}</strong>
                        <div style="font-size:0.8rem; color:var(--text-muted);">${{p.data}}</div>
                        <div style="font-size:0.75rem; color:#38bdf8;">${{p.tipo}}</div>
                    </td>
                    <td>${{partesHtml}}</td>
                    <td>${{decisaoHtml}}</td>
                `;
                tbody.appendChild(tr);
            }});
        }}

        // Renderização inicial
        filtrarDados();
    </script>
</body>
</html>
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        return filepath
