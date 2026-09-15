"""
Módulo de Exportação para o Rastreador de Revisões Criminais do TJSC.
Gera saídas em:
- CSV (com acentuação correta para Excel em utf-8-sig)
- JSON estruturado
- Relatório HTML / Dashboard para o GitHub Pages (em docs/index.html)
"""

import csv
import json
import os
from typing import List, Dict, Any
from classifier import RevisaoCriminal, STATUS_SEM_ADVOGADO, STATUS_DATIVO, STATUS_DPE, STATUS_CONSTITUIDO


class Exporter:
    @staticmethod
    def export_csv(revisoes: List[RevisaoCriminal], filepath: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow([
                "Numero_Processo",
                "Nome_Sentenciado",
                "Status_Defesa",
                "Comarca_Origem",
                "Orgao_Julgador",
                "Data_Sessao",
                "Tipo_Sessao",
                "Justificativa_Defesa",
                "Decisao_Colegiada",
                "Link_Eproc"
            ])

            for r in revisoes:
                just = r.detalhes_defesa.get("justificativa", "")
                if r.status_defesa == STATUS_DATIVO and r.detalhes_defesa.get("trecho_decisao_dativo"):
                    just += f" ({r.detalhes_defesa['trecho_decisao_dativo']})"

                writer.writerow([
                    r.numero_processo,
                    r.nome_sentenciado,
                    r.status_defesa,
                    r.comarca_origem,
                    r.orgao_julgador,
                    r.data_sessao,
                    r.tipo_sessao,
                    just,
                    r.decisao[:300] + ("..." if len(r.decisao) > 300 else ""),
                    r.link_processo
                ])

        return filepath

    @staticmethod
    def export_json(revisoes: List[RevisaoCriminal], filepath: str, cancelamentos: List[Dict[str, Any]] = None) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        dados = {
            "total_revisoes": len(revisoes),
            "estatisticas": {
                "sem_advogado_constituido": sum(1 for r in revisoes if r.status_defesa == STATUS_SEM_ADVOGADO),
                "dativo_nomeado": sum(1 for r in revisoes if r.status_defesa == STATUS_DATIVO),
                "dpe": sum(1 for r in revisoes if r.status_defesa == STATUS_DPE),
                "advogado_constituido": sum(1 for r in revisoes if r.status_defesa == STATUS_CONSTITUIDO),
            },
            "cancelamentos_tjsc": cancelamentos or [],
            "processos": [
                {
                    "numero_processo": r.numero_processo,
                    "classe_processual": r.classe_processual,
                    "nome_sentenciado": r.nome_sentenciado,
                    "status_defesa": r.status_defesa,
                    "comarca_origem": r.comarca_origem,
                    "orgao_julgador": r.orgao_julgador,
                    "data_sessao": r.data_sessao,
                    "tipo_sessao": r.tipo_sessao,
                    "detalhes_defesa": r.detalhes_defesa,
                    "decisao": r.decisao,
                    "link_processo": r.link_processo
                }
                for r in revisoes
            ]
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        return filepath

    @staticmethod
    def export_html(revisoes: List[RevisaoCriminal], filepath: str, cancelamentos: List[Dict[str, Any]] = None) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        tot_sem = sum(1 for r in revisoes if r.status_defesa == STATUS_SEM_ADVOGADO)
        tot_dat = sum(1 for r in revisoes if r.status_defesa == STATUS_DATIVO)
        tot_dpe = sum(1 for r in revisoes if r.status_defesa == STATUS_DPE)
        tot_const = sum(1 for r in revisoes if r.status_defesa == STATUS_CONSTITUIDO)
        tot_geral = len(revisoes)

        dados_json = json.dumps([
            {
                "num": r.numero_processo,
                "classe": r.classe_processual,
                "sentenciado": r.nome_sentenciado,
                "status": r.status_defesa,
                "comarca": r.comarca_origem,
                "orgao": r.orgao_julgador,
                "data": r.data_sessao,
                "tipo": r.tipo_sessao,
                "detalhes": r.detalhes_defesa,
                "decisao": r.decisao,
                "link": r.link_processo
            }
            for r in revisoes
        ], ensure_ascii=False)

        cancelamentos_json = json.dumps(cancelamentos or [], ensure_ascii=False)

        template = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TJSC • Rastreador de Revisões Criminais</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0b0f19;
            --surface: #151d30;
            --surface-hover: #1c2742;
            --border: #263353;
            --primary: #38bdf8;
            --primary-glow: rgba(56, 189, 248, 0.15);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --badge-sem: #ef4444;
            --badge-sem-bg: rgba(239, 68, 68, 0.15);
            --badge-dativo: #c084fc;
            --badge-dativo-bg: rgba(192, 132, 252, 0.15);
            --badge-dpe: #34d399;
            --badge-dpe-bg: rgba(52, 211, 153, 0.15);
            --badge-const: #64748b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            padding: 24px;
            line-height: 1.5;
            min-height: 100vh;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        header {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 16px;
            margin-bottom: 24px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border);
        }
        .title-group h1 {
            font-size: 1.75rem;
            font-weight: 700;
            background: linear-gradient(135deg, #fff 40%, #94a3b8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .title-group p {
            color: var(--text-muted);
            font-size: 0.9rem;
            margin-top: 4px;
        }
        .header-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            border: 1px solid var(--border);
            background: var(--surface);
            color: var(--text-main);
        }
        .btn:hover {
            background: var(--surface-hover);
            border-color: var(--primary);
        }
        .btn-primary {
            background: var(--primary);
            color: #0b0f19;
            border-color: var(--primary);
        }
        .btn-primary:hover {
            background: #7dd3fc;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .stat-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px 20px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .stat-label {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            font-weight: 600;
        }
        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            line-height: 1;
        }
        .stat-sem { color: var(--badge-sem); }
        .stat-dativo { color: var(--badge-dativo); }
        .stat-dpe { color: var(--badge-dpe); }
        .stat-total { color: var(--primary); }
        .controls-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 20px;
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            align-items: center;
        }
        .search-box {
            flex: 1;
            min-width: 280px;
        }
        .search-box input {
            width: 100%;
            padding: 10px 16px;
            border-radius: 8px;
            background: var(--bg);
            border: 1px solid var(--border);
            color: #fff;
            font-size: 0.9rem;
            outline: none;
        }
        .search-box input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px var(--primary-glow);
        }
        .filter-tabs {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }
        .tab-btn {
            background: var(--bg);
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }
        .tab-btn.active {
            background: var(--primary);
            color: #0b0f19;
            font-weight: 700;
            border-color: var(--primary);
        }
        .results-count {
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 12px;
            padding: 0 4px;
        }
        .table-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
        }
        .table-responsive {
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
            text-align: left;
        }
        th {
            background: #0f1626;
            color: var(--text-muted);
            padding: 14px 16px;
            font-weight: 600;
            border-bottom: 1px solid var(--border);
            white-space: nowrap;
        }
        td {
            padding: 14px 16px;
            border-bottom: 1px solid var(--border);
            vertical-align: top;
        }
        tr:hover td {
            background: rgba(255,255,255,0.015);
        }
        .badge {
            display: inline-flex;
            align-items: center;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            text-transform: uppercase;
        }
        .badge-sem {
            background: var(--badge-sem-bg);
            color: var(--badge-sem);
            border: 1px solid var(--badge-sem);
        }
        .badge-dativo {
            background: var(--badge-dativo-bg);
            color: var(--badge-dativo);
            border: 1px solid var(--badge-dativo);
        }
        .badge-dpe {
            background: var(--badge-dpe-bg);
            color: var(--badge-dpe);
            border: 1px solid var(--badge-dpe);
        }
        .badge-const {
            background: rgba(100, 116, 139, 0.2);
            color: #cbd5e1;
        }
        .proc-link {
            color: var(--primary);
            text-decoration: none;
            font-weight: 700;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
            font-size: 0.92rem;
        }
        .proc-link:hover { text-decoration: underline; }
        .copy-btn {
            background: none;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 0.8rem;
            padding: 2px 4px;
        }
        .copy-btn:hover { color: #fff; }
        .sentenciado-nome {
            font-size: 1rem;
            font-weight: 600;
            color: #f1f5f9;
        }
        .comarca-origem {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 2px;
        }
        .justificativa-box {
            font-size: 0.8rem;
            color: #cbd5e1;
            background: rgba(0,0,0,0.25);
            padding: 6px 10px;
            border-radius: 6px;
            border-left: 3px solid var(--primary);
            margin-top: 6px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="title-group">
                <h1>⚖️ TJSC • Rastreador de Revisões Criminais</h1>
                <p>Monitoramento de processos em fase de Revisão Criminal com foco em sentenciados sem advogado constituído.</p>
            </div>
            <div class="header-actions">
                <button class="btn btn-primary" onclick="exportarCSV()">📥 Baixar Visão (CSV)</button>
            </div>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <span class="stat-label">Sem Advogado Constituído</span>
                <span class="stat-value stat-sem">__TOT_SEM__</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Dativo Nomeado pelo TJ</span>
                <span class="stat-value stat-dativo">__TOT_DAT__</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Defensoria Pública (DPE)</span>
                <span class="stat-value stat-dpe">__TOT_DPE__</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Total de Revisões</span>
                <span class="stat-value stat-total">__TOT_GERAL__</span>
            </div>
        </div>

        <div class="controls-card">
            <div class="search-box">
                <input type="text" id="search-input" placeholder="Buscar por número CNJ, nome do sentenciado, comarca de condenação..." oninput="filtrar()">
            </div>
            <div class="filter-tabs">
                <button class="tab-btn active" onclick="setFiltro('TODOS')">Todas as Revisões</button>
                <button class="tab-btn" onclick="setFiltro('SEM_ADVOGADO')">🔴 Sem Advogado Constituído</button>
                <button class="tab-btn" onclick="setFiltro('DATIVO')">🟣 Dativo Nomeado</button>
                <button class="tab-btn" onclick="setFiltro('DPE')">🟢 DPE</button>
            </div>
        </div>

        <div class="results-count" id="results-count">Exibindo processos...</div>

        <div class="table-card">
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th style="width: 220px;">Processo</th>
                            <th style="width: 280px;">Sentenciado (Requerente)</th>
                            <th style="width: 170px;">Status da Defesa</th>
                            <th style="width: 200px;">Órgão Julgador / Data</th>
                            <th>Decisão / Dispositivo</th>
                        </tr>
                    </thead>
                    <tbody id="table-body">
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        const revisoes = __DADOS_JSON__;
        let filtroAtivo = "TODOS";

        function setFiltro(tipo) {
            filtroAtivo = tipo;
            document.querySelectorAll(".tab-btn").forEach(btn => {
                if ((tipo === "TODOS" && btn.textContent.includes("Todas")) ||
                    (tipo === "SEM_ADVOGADO" && btn.textContent.includes("Sem Advogado")) ||
                    (tipo === "DATIVO" && btn.textContent.includes("Dativo")) ||
                    (tipo === "DPE" && btn.textContent.includes("DPE"))) {
                    btn.classList.add("active");
                } else {
                    btn.classList.remove("active");
                }
            });
            filtrar();
        }

        function filtrar() {
            const termo = document.getElementById("search-input").value.toLowerCase().trim();
            const tbody = document.getElementById("table-body");
            tbody.innerHTML = "";

            const filtradas = revisoes.filter(r => {
                if (filtroAtivo === "SEM_ADVOGADO" && r.status !== "SEM_ADVOGADO_CONSTITUIDO") return false;
                if (filtroAtivo === "DATIVO" && r.status !== "DATIVO_NOMEADO") return false;
                if (filtroAtivo === "DPE" && r.status !== "DPE") return false;

                if (!termo) return true;
                const texto = (
                    (r.num || "") + " " +
                    (r.sentenciado || "") + " " +
                    (r.comarca || "") + " " +
                    (r.orgao || "") + " " +
                    (r.decisao || "")
                ).toLowerCase();
                return texto.includes(termo);
            });

            document.getElementById("results-count").textContent = `Exibindo ${filtradas.length} de ${revisoes.length} revisões criminais.`;

            if (filtradas.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 32px; color: var(--text-muted);">Nenhuma revisão criminal encontrada com os filtros selecionados.</td></tr>';
                return;
            }

            filtradas.forEach(r => {
                const tr = document.createElement("tr");

                let badgeHtml = "";
                if (r.status === "SEM_ADVOGADO_CONSTITUIDO") {
                    badgeHtml = '<span class="badge badge-sem">Sem Advogado</span>';
                } else if (r.status === "DATIVO_NOMEADO") {
                    badgeHtml = '<span class="badge badge-dativo">Dativo Nomeado</span>';
                } else if (r.status === "DPE") {
                    badgeHtml = '<span class="badge badge-dpe">DPE</span>';
                } else {
                    badgeHtml = '<span class="badge badge-const">Advogado Constituído</span>';
                }

                let justHtml = "";
                if (r.detalhes && r.detalhes.justificativa) {
                    justHtml = `<div class="justificativa-box">${r.detalhes.justificativa}</div>`;
                }

                const linkHtml = r.link ?
                    `<a class="proc-link" href="${r.link}" target="_blank">${r.num}</a>` :
                    `<span class="proc-link">${r.num}</span>`;

                tr.innerHTML = `
                    <td>
                        <div style="display:flex; align-items:center; gap:6px;">
                            ${linkHtml}
                            <button class="copy-btn" title="Copiar CNJ" onclick="copiar('${r.num}', this)">📋</button>
                        </div>
                        <div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;">${r.classe}</div>
                    </td>
                    <td>
                        <div class="sentenciado-nome">${r.sentenciado}</div>
                        <div class="comarca-origem">📍 ${r.comarca}</div>
                        ${justHtml}
                    </td>
                    <td>${badgeHtml}</td>
                    <td>
                        <strong>${r.orgao}</strong>
                        <div style="font-size:0.8rem; color:var(--text-muted);">${r.data}</div>
                        <div style="font-size:0.72rem; color:var(--primary);">${r.tipo}</div>
                    </td>
                    <td>
                        <div style="font-size:0.82rem; color:#cbd5e1;">${r.decisao ? (r.decisao.length > 250 ? r.decisao.substring(0, 250) + "..." : r.decisao) : "Dispositivo em processamento"}</div>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        function copiar(texto, el) {
            navigator.clipboard.writeText(texto).then(() => {
                const orig = el.textContent;
                el.textContent = "✔";
                setTimeout(() => { el.textContent = orig; }, 1200);
            });
        }

        function exportarCSV() {
            const termo = document.getElementById("search-input").value.toLowerCase().trim();
            const visiveis = revisoes.filter(r => {
                if (filtroAtivo === "SEM_ADVOGADO" && r.status !== "SEM_ADVOGADO_CONSTITUIDO") return false;
                if (filtroAtivo === "DATIVO" && r.status !== "DATIVO_NOMEADO") return false;
                if (filtroAtivo === "DPE" && r.status !== "DPE") return false;
                if (!termo) return true;
                const texto = ((r.num||"") + " " + (r.sentenciado||"") + " " + (r.comarca||"") + " " + (r.decisao||"")).toLowerCase();
                return texto.includes(termo);
            });

            let csv = "Numero_Processo;Sentenciado;Status_Defesa;Comarca_Origem;Orgao;Data_Sessao;Decisao;Link\\n";
            visiveis.forEach(r => {
                const dec = (r.decisao || "").replace(/\\r?\\n/g, " ").replace(/;/g, ",");
                csv += `"${r.num}";"${r.sentenciado}";"${r.status}";"${r.comarca}";"${r.orgao}";"${r.data}";"${dec}";"${r.link}"\\n`;
            });

            const blob = new Blob(["\\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `revisoes_criminais_tjsc_${new Date().toISOString().slice(0,10)}.csv`;
            a.click();
            URL.revokeObjectURL(url);
        }

        window.onload = filtrar;
    </script>
</body>
</html>
"""
        final_html = (
            template
            .replace("__TOT_SEM__", str(tot_sem))
            .replace("__TOT_DAT__", str(tot_dat))
            .replace("__TOT_DPE__", str(tot_dpe))
            .replace("__TOT_GERAL__", str(tot_geral))
            .replace("__DADOS_JSON__", dados_json)
        )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_html)

        # Salva também automaticamente na pasta docs/index.html para o GitHub Pages
        docs_path = os.path.join(os.path.dirname(os.path.abspath(filepath)), "..", "docs", "index.html")
        os.makedirs(os.path.dirname(docs_path), exist_ok=True)
        with open(docs_path, "w", encoding="utf-8") as f:
            f.write(final_html)

        return filepath
