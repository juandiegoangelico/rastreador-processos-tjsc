"""
Módulo de Configuração para o Rastreador de Processos TJSC.
Centraliza URLs, cabeçalhos HTTP, mapeamentos de órgãos julgadores e padrões de classificação.
"""

from typing import Dict, List

# URLs das fontes oficiais
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

# Tipos de classificação de representação
TIPO_DATIVO = "DATIVO"
TIPO_DPE = "DPE"
TIPO_SEM_ADVOGADO = "SEM_ADVOGADO"
TIPO_CONSTITUIDO = "CONSTITUIDO"

# Mapeamento de Câmaras / Órgãos Julgadores (IDs do Eproc TJSC)
ORGAOS_EPROC: Dict[str, str] = {
    "TODOS": "",
    # Câmaras Criminais
    "1_CAM_CRIMINAL": "190005",
    "2_CAM_CRIMINAL": "190006",
    "3_CAM_CRIMINAL": "190055",
    "4_CAM_CRIMINAL": "190084",
    "5_CAM_CRIMINAL": "190089",
    "6_CAM_CRIMINAL": "190099",
    "SECAO_CRIMINAL": "190010",
    "GRUPO_1_CRIMINAL": "190090",
    "GRUPO_2_CRIMINAL": "190091",
    # Câmaras Cíveis
    "1_CAM_CIVIL": "190001",
    "2_CAM_CIVIL": "190002",
    "3_CAM_CIVIL": "190040",
    "4_CAM_CIVIL": "190052",
    "5_CAM_CIVIL": "190081",
    "6_CAM_CIVIL": "190082",
    "7_CAM_CIVIL": "190094",
    "8_CAM_CIVIL": "190098",
    "9_CAM_CIVIL": "190085",
    "10_CAM_CIVIL": "190086",
    "GRUPO_CIVIL": "190007",
    # Direito Público
    "1_CAM_PUBLICO": "190024",
    "2_CAM_PUBLICO": "190025",
    "3_CAM_PUBLICO": "190041",
    "4_CAM_PUBLICO": "190054",
    "5_CAM_PUBLICO": "190092",
    "GRUPO_PUBLICO": "190026",
    # Direito Comercial
    "1_CAM_COMERCIAL": "190003",
    "2_CAM_COMERCIAL": "190004",
    "3_CAM_COMERCIAL": "190039",
    "4_CAM_COMERCIAL": "190053",
    "5_CAM_COMERCIAL": "190083",
    "6_CAM_COMERCIAL": "190097",
    "GRUPO_COMERCIAL": "190008",
    # Outros
    "ORGAO_ESPECIAL": "190080",
    "TURMA_UNIFORMIZACAO": "190095",
}

# Grupos de órgãos para filtros rápidos
GRUPOS_ORGAOS: Dict[str, List[str]] = {
    "criminal": [
        "190005", "190006", "190055", "190084", "190089", "190099",
        "190010", "190090", "190091"
    ],
    "civil": [
        "190001", "190002", "190040", "190052", "190081", "190082",
        "190094", "190098", "190085", "190086", "190007"
    ],
    "publico": [
        "190024", "190025", "190041", "190054", "190092", "190026"
    ],
    "comercial": [
        "190003", "190004", "190039", "190053", "190083", "190097",
        "190008"
    ],
}
