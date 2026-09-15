"""
Configurações para o Rastreador de Revisões Criminais do TJSC.
Foco: Processos em fase de Revisão Criminal sem advogado constituído.
"""

from typing import Dict, List

# URLs oficiais
URL_PORTAL_TJSC = "https://www.tjsc.jus.br/web/judicial/sessoes-do-tribunal-de-justica"
URL_EPROC_BASE = "https://eprocwebcon.tjsc.jus.br/consulta2g/"
URL_EPROC_SESSOES = "https://eprocwebcon.tjsc.jus.br/consulta2g/externo_controlador.php?acao=consultaPublica/sessoesDeJulgamento&acao_origem=consultaPublica/sessoesDeJulgamento"

# Headers HTTP padrão simulando navegador moderno
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
}

# Órgãos competentes para julgamento de Revisão Criminal no TJSC
ORGAOS_REVISAO_CRIMINAL: Dict[str, str] = {
    "GRUPO_1_CRIMINAL": "190090",  # Primeiro Grupo de Direito Criminal
    "GRUPO_2_CRIMINAL": "190091",  # Segundo Grupo de Direito Criminal
    "SECAO_CRIMINAL": "190010",    # Seção Criminal
}

# Tipos de status de representação do sentenciado
STATUS_SEM_ADVOGADO = "SEM_ADVOGADO_CONSTITUIDO"
STATUS_DATIVO = "DATIVO_NOMEADO"
STATUS_DPE = "DPE"
STATUS_CONSTITUIDO = "ADVOGADO_CONSTITUIDO"
