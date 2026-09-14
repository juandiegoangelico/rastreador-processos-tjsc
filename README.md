# ⚖️ Rastreador de Processos TJSC
### Monitoramento de Processos Judiciais: Advogado Dativo, Defensoria Pública (DPE) e Sem Advogado

Ferramenta desenvolvida para rastreabilidade de processos em pautas e atas de julgamento do **Tribunal de Justiça de Santa Catarina (TJSC)**, integrando:
1. **Portal Institucional do TJSC**: [Sessões do Tribunal de Justiça](https://www.tjsc.jus.br/web/judicial/sessoes-do-tribunal-de-justica)
2. **Eproc 2º Grau**: [Sessões de Julgamento](https://eprocwebcon.tjsc.jus.br/consulta2g/externo_controlador.php?acao=consultaPublica/sessoesDeJulgamento)

---

## 🎯 Categorias Rastradas

| Categoria | Identificação | Detalhes Capturados |
|---|---|---|
| 🟣 **Advogado Dativo** | Arbitramento / fixação de honorários recursais ou advocatícios na decisão colegiada | Nome do defensor, OAB e trecho da decisão concedendo os honorários dativos |
| 🟢 **Defensoria Pública (DPE)** | Marcação explícita `(DPE)` ou nome da Defensoria Pública no cadastro do representante | Nome do defensor público e parte assistida |
| 🔴 **Sem Advogado** | Partes que não possuem advogado/procurador constituído nos autos (excluindo órgãos institucionais como MP e autoridades coatoras) | Nome da parte desassistida e polo processual |

---

## 🚀 Instalação e Requisitos

O projeto foi construído utilizando **exclusivamente a biblioteca padrão do Python 3**, dispensando instalações complexas de pacotes externos.

```bash
cd /Users/juandiegoangelico/.gemini/antigravity/scratch/rastreador-processos-tjsc
python3 --version  # Requer Python 3.8+
```

---

## 💻 Como Usar

### 1. Execução Rápida (Últimos 7 dias, Câmaras Criminais)
```bash
python3 tracker.py --dias 7 --orgao criminal --filtro dativo,dpe,sem_advogado
```

### 2. Período Personalizado em Todos os Órgãos
```bash
python3 tracker.py --inicio 01/09/2026 --fim 15/09/2026 --exportar html,csv,json
```

### 3. Apenas Casos com Advogado Dativo
```bash
python3 tracker.py --filtro dativo --exportar html
```

### 4. Apenas Casos da Defensoria Pública (DPE)
```bash
python3 tracker.py --filtro dpe --exportar csv
```

### 5. Filtrar por Câmaras Específicas
- `--orgao criminal` (Câmaras Criminais de 1ª a 6ª e grupos)
- `--orgao civil` (Câmaras de Direito Civil de 1ª a 10ª)
- `--orgao publico` (Direito Público)
- `--orgao comercial` (Direito Comercial)
- `--orgao todos` (Todos os órgãos do TJSC)

---

## 📊 Formatos de Exportação

Os relatórios são salvos automaticamente no diretório `./relatorios/`:

1. **Relatório Visual Interativo (`.html`)**:
   - Dashboard moderno, escuro e responsivo.
   - Contadores de processos por categoria.
   - Campo de busca instantânea (número, parte, advogado, câmara).
   - Abas de filtro rápido.
   - Trechos destacados da decisão e links diretos para o processo no Eproc.
   - Pode ser aberto diretamente com duplo clique ou via terminal:
     ```bash
     open ./relatorios/tjsc_rastreabilidade_*.html
     ```

2. **Planilha Excel (`.csv`)**:
   - Codificação `UTF-8 com BOM` para abrir com acentuação perfeita no Excel ou Google Sheets.
   - Separador `;`.

3. **JSON Estruturado (`.json`)**:
   - Contém o payload completo de processos, partes, representantes, decisões e avisos de cancelamento do portal do TJSC.

---

## 🧪 Testes Automatizados

Para rodar a bateria de testes unitários:
```bash
python3 -m unittest tests/test_tracker.py
```
