# ⚖️ Rastreador de Revisões Criminais — TJSC (Eproc)
### Monitoramento Especializado de Revisões Criminais e Situação Defensiva dos Sentenciados

Ferramenta desenvolvida para rastrear especificamente processos de **Revisão Criminal** em trâmite e julgamento no **Tribunal de Justiça de Santa Catarina (TJSC)**, com foco em identificar pedidos propostos **sem advogado constituído** (de próprio punho / *jus postulandi*), com **defensor dativo nomeado** ou assistidos pela **Defensoria Pública (DPE)**.

🌐 **Dashboard Público no GitHub Pages:** [https://juandiegoangelico.github.io/rastreador-processos-tjsc/](https://juandiegoangelico.github.io/rastreador-processos-tjsc/)

---

## 🎯 Órgãos Colegiados Monitorados

No TJSC, os pedidos de Revisão Criminal são de competência privativa dos Grupos de Câmaras Criminais e da Seção Criminal:
1. **Primeiro Grupo de Direito Criminal** (1ª e 2ª Câmaras Criminais) — ID `190090`
2. **Segundo Grupo de Direito Criminal** (3ª, 4ª e 5ª Câmaras Criminais) — ID `190091`
3. **Seção Criminal** — ID `190010`

---

## 🔍 Categorias de Situação Defensiva

| Categoria | Descrição | Detalhes Capturados |
|---|---|---|
| 🔴 **Sem Advogado Constituído** | Pedido formulado pelo próprio sentenciado no estabelecimento prisional (*jus postulandi*) sem representação técnica habilitada. | Nome do sentenciado, comarca de origem da condenação, número CNJ e link no Eproc. |
| 🟣 **Advogado Dativo Nomeado** | Casos em que o Tribunal arbitrou ou fixou honorários advocatícios a defensor dativo nomeado para patrocinar a revisão. | Trecho da decisão colegiada com a fixação de honorários e dados do processo. |
| 🟢 **Defensoria Pública (DPE)** | Processos patrocinados pela Defensoria Pública do Estado de Santa Catarina. | Nome do órgão defensorial e do sentenciado assistido. |
| ⚪ **Advogado Constituído** | Processos com advogado particular com procuração e OAB cadastrada nos autos. | Filtrado por padrão para focar em sentenciados desassistidos. |

---

## ⚖️ Informações Extraídas e Limites Legais / LGPD

### 📌 Dados Públicos Capturados das Sessões e Atas:
- **Número Único CNJ** e link direto para os autos públicos no Eproc 2G do TJSC;
- **Nome Completo do Sentenciado** (Requerente);
- **Comarca e Vara de Origem** (ex: *Juízo da 1ª Vara Criminal da Comarca de Criciúma*);
- **Órgão Julgador Colegiado** e Data da Sessão;
- **Teor da Decisão / Acórdão** (concessão de liminar, conhecimento, improcedência, arbitramento de honorários dativos);
- **Avisos Regimentais e Cancelamentos** de sessões via Portal do TJSC.

### ⚠️ Observação sobre Dados de Contato Direto e Ética OAB:
> **Transparência e LGPD:** Os tribunais brasileiros (TJSC/Eproc) **não disponibilizam publicamente** telefones pessoais, WhatsApp, endereços residenciais ou unidades prisionais de sentenciados por imperativo da Lei Geral de Proteção de Dados (LGPD) e segurança orgânica.  
> **Código de Ética e Disciplina da OAB (Art. 5º e 7º):** É vedada a captação ativa de clientela ou oferta de serviços a réus e sentenciados sem procuração prévia. O contato lícito e ético ocorre mediante habilitação nos autos públicos quando requisitado pelo próprio sentenciado/família, atuação via convênio da Defensoria Pública/OAB, ou atendimento na comarca/estabelecimento prisional onde o sentenciado cumpre pena.

---

## 🚀 Como Executar

### 1. Requisitos
- Python 3.8+ (apenas biblioteca padrão, sem dependências externas pesadas).

```bash
cd rastreador-processos-tjsc
```

### 2. Rastreamento Padrão (Últimos 30 dias de Revisões Criminais)
```bash
python3 tracker.py --dias 30
```

### 3. Rastreamento de Período Específico
```bash
python3 tracker.py --inicio 01/08/2026 --fim 15/09/2026
```

### 4. Incluir Também Revisões com Advogado Constituído (Para Comparativo Estatístico)
```bash
python3 tracker.py --dias 60 --todos-status
```

---

## 📊 Arquivos Gerados

A cada execução, os relatórios são salvos em:
1. **`./docs/index.html`**: Dashboard interativo pronto para o **GitHub Pages**, com busca instantânea, contadores dinâmicos, filtros de status e links diretos ao Eproc.
2. **`./relatorios/*.csv`**: Planilha em formato Excel (UTF-8 com BOM e delimitador ponto e vírgula).
3. **`./relatorios/*.json`**: Base de dados estruturada com metadados e cancelamentos.
4. **`./relatorios/*.html`**: Cópia local do relatório para visualização offline.

---

## 🧪 Testes Automatizados

Para rodar os testes unitários:
```bash
python3 -m unittest discover tests
```
