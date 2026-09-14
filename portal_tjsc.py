"""
Módulo para coleta de dados do Portal Institucional do TJSC:
https://www.tjsc.jus.br/web/judicial/sessoes-do-tribunal-de-justica

Extrai:
- Tabela de transferências e cancelamentos de sessões
- Calendário de sessões físicas presenciais
- Links e avisos regimentais
"""

import re
import ssl
import urllib.request
from dataclasses import dataclass
from typing import List, Dict, Any
from config import URL_PORTAL_TJSC, DEFAULT_HEADERS


@dataclass
class CancelamentoSessao:
    orgao_julgador: str
    sessao_original: str
    descricao_alteracao: str


@dataclass
class SessaoFisicaCalendario:
    orgao_julgador: str
    data: str
    dia_semana: str
    sala: str


class PortalTJSCScraper:
    def __init__(self, timeout: int = 25):
        self.timeout = timeout
        self.ssl_context = ssl._create_unverified_context()

    def fetch_page_html(self) -> str:
        """Baixa o HTML da página institucional de sessões do TJSC."""
        req = urllib.request.Request(
            URL_PORTAL_TJSC,
            headers=DEFAULT_HEADERS
        )
        try:
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=self.timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except Exception as e:
            print(f"[AVISO] Não foi possível acessar o portal TJSC ({e}). Continuando com dados locais/eproc.")
            return ""

    def extrair_cancelamentos(self, html: str) -> List[CancelamentoSessao]:
        """Extrai as alterações e cancelamentos informados na página."""
        cancelamentos = []
        if not html:
            return cancelamentos

        # Localiza a tabela transferencias-e-cancelamentos
        match = re.search(
            r'<table[^>]*id=["\']transferencias-e-cancelamentos["\'][^>]*>(.*?)</table>',
            html,
            re.DOTALL | re.IGNORECASE
        )
        if not match:
            # Tenta busca genérica por cabeçalho
            match = re.search(
                r'<th[^>]*>Órgão julgador</th>\s*<th[^>]*>Sessão original</th>\s*<th[^>]*>Descrição da alteração</th>(.*?)</table>',
                html,
                re.DOTALL | re.IGNORECASE
            )

        if match:
            tbody_content = match.group(1)
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', tbody_content, re.DOTALL | re.IGNORECASE)
            for r in rows:
                cols = re.findall(r'<td[^>]*>(.*?)</td>', r, re.DOTALL | re.IGNORECASE)
                if len(cols) >= 3:
                    orgao = self._clean_text(cols[0])
                    sessao = self._clean_text(cols[1])
                    desc = self._clean_text(cols[2])
                    if orgao and sessao:
                        cancelamentos.append(CancelamentoSessao(
                            orgao_julgador=orgao,
                            sessao_original=sessao,
                            descricao_alteracao=desc
                        ))
        return cancelamentos

    def extrair_calendario_fisico(self, html: str) -> List[SessaoFisicaCalendario]:
        """Extrai o cronograma de sessões presenciais/físicas."""
        sessoes = []
        if not html:
            return sessoes

        # Procura tabelas que contenham colunas Órgão, Data, Dia da Semana, Sala
        tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.DOTALL | re.IGNORECASE)
        for t in tables:
            if "Sala" in t and "Dia da Semana" in t:
                rows = re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.DOTALL | re.IGNORECASE)
                for r in rows:
                    cols = re.findall(r'<td[^>]*>(.*?)</td>', r, re.DOTALL | re.IGNORECASE)
                    if len(cols) >= 4:
                        orgao = self._clean_text(cols[0])
                        data = self._clean_text(cols[1])
                        dia = self._clean_text(cols[2])
                        sala = self._clean_text(cols[3])
                        if orgao and data and "/" in data:
                            sessoes.append(SessaoFisicaCalendario(
                                orgao_julgador=orgao,
                                data=data,
                                dia_semana=dia,
                                sala=sala
                            ))
        return sessoes

    def obter_dados_completos(self) -> Dict[str, Any]:
        """Obtém e formata os dados do portal TJSC."""
        html = self.fetch_page_html()
        cancelamentos = self.extrair_cancelamentos(html)
        calendario = self.extrair_calendario_fisico(html)
        return {
            "cancelamentos": [c.__dict__ for c in cancelamentos],
            "calendario_fisico": [s.__dict__ for s in calendario],
            "total_cancelamentos": len(cancelamentos),
            "total_sessoes_fisicas": len(calendario),
        }

    @staticmethod
    def _clean_text(text: str) -> str:
        text = re.sub(r'<[^>]+>', ' ', text)
        text = text.replace("&nbsp;", " ").replace("&amp;", "&")
        return re.sub(r'\s+', ' ', text).strip()
