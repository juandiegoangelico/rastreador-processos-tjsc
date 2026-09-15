"""
Módulo para coleta e extração de dados do Eproc 2G do TJSC:
https://eprocwebcon.tjsc.jus.br/consulta2g/externo_controlador.php?acao=consultaPublica/sessoesDeJulgamento

Especializado na busca de sessões colegiadas e extração de Revisões Criminais.
"""

import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from config import URL_EPROC_BASE, URL_EPROC_SESSOES, DEFAULT_HEADERS
from classifier import RevisaoCriminal, parse_ata_revisao_criminal


@dataclass
class SessaoJulgamento:
    id_sessao: str
    periodo_data: str
    tipo_sessao: str
    orgao_julgador: str
    desembargadores: List[str]
    url_pauta: str = ""
    url_ata: str = ""
    possui_ata: bool = False
    revisoes_criminais: List[RevisaoCriminal] = field(default_factory=list)


class EprocScraper:
    def __init__(self, timeout: int = 30, delay: float = 0.5):
        self.timeout = timeout
        self.delay = delay
        self.ssl_context = ssl._create_unverified_context()
        self.cookie_jar: Dict[str, str] = {}

    def _build_request(self, url: str, data: Optional[bytes] = None, headers: Optional[Dict[str, str]] = None) -> urllib.request.Request:
        h = DEFAULT_HEADERS.copy()
        if headers:
            h.update(headers)
        if self.cookie_jar:
            h["Cookie"] = "; ".join([f"{k}={v}" for k, v in self.cookie_jar.items()])
        return urllib.request.Request(url, data=data, headers=h)

    def _update_cookies(self, response_headers) -> None:
        cookies = response_headers.get_all("Set-Cookie") or []
        for c in cookies:
            partes = c.split(";")[0].split("=", 1)
            if len(partes) == 2:
                self.cookie_jar[partes[0].strip()] = partes[1].strip()

    def fetch_url(self, url: str, data: Optional[bytes] = None, extra_headers: Optional[Dict[str, str]] = None) -> str:
        if not url.startswith("http"):
            url = urllib.parse.urljoin(URL_EPROC_BASE, url)

        req = self._build_request(url, data=data, headers=extra_headers)
        try:
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=self.timeout) as resp:
                self._update_cookies(resp.headers)
                raw = resp.read()
                try:
                    return raw.decode("iso-8859-1")
                except UnicodeDecodeError:
                    return raw.decode("utf-8", errors="replace")
        except Exception as e:
            print(f"[ERRO EPROC] Falha ao acessar {url}: {e}")
            return ""

    def buscar_sessoes(
        self,
        data_inicio: str = "",
        data_termino: str = "",
        id_orgao: str = ""
    ) -> List[SessaoJulgamento]:
        post_data = urllib.parse.urlencode({
            "numIdOrgao": id_orgao,
            "txtDataInicio": data_inicio,
            "txtDataTermino": data_termino
        }).encode("utf-8")

        html = self.fetch_url(URL_EPROC_SESSOES, data=post_data)
        if not html:
            html = self.fetch_url(URL_EPROC_SESSOES)

        return self._parse_tabela_sessoes(html)

    def _parse_tabela_sessoes(self, html: str) -> List[SessaoJulgamento]:
        sessoes: List[SessaoJulgamento] = []

        linhas = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE)
        for linha in linhas:
            colunas = re.findall(r'<td[^>]*>(.*?)</td>', linha, re.DOTALL | re.IGNORECASE)
            if len(colunas) < 4:
                continue

            periodo = re.sub(r'<[^>]+>', ' ', colunas[0])
            periodo = re.sub(r'\s+', ' ', periodo).strip()

            tipo_sessao = re.sub(r'<[^>]+>', ' ', colunas[1])
            tipo_sessao = re.sub(r'\s+', ' ', tipo_sessao).strip()

            orgao_bloco = colunas[2]
            m_orgao = re.search(r'<span[^>]*font-weight-bold[^>]*>([^<]+)</span>', orgao_bloco)
            orgao_nome = m_orgao.group(1).strip() if m_orgao else ""

            magistrados = []
            mag_limpo = re.sub(r'<span[^>]*>.*?</span>', '', orgao_bloco, flags=re.DOTALL)
            for m in re.split(r'<br\s*/?>', mag_limpo):
                m_txt = re.sub(r'<[^>]+>', '', m).strip()
                if m_txt and ("Des" in m_txt or "Juiz" in m_txt):
                    magistrados.append(m_txt)

            if not orgao_nome:
                orgao_nome = "Órgão Não Identificado"

            acoes_bloco = colunas[3]
            m_pauta = re.search(r'href=["\']([^"\']*listar_itens[^"\']*)["\']', acoes_bloco)
            url_pauta = m_pauta.group(1) if m_pauta else ""

            m_ata = re.search(
                r'showPautaSessaoJulgamento\([\'"]([^\'"]*sessao_julgamento_relatorio_ata[^\'"]*)[\'"]\)',
                acoes_bloco
            )
            if not m_ata:
                m_ata = re.search(r'href=["\']([^"\']*sessao_julgamento_relatorio_ata[^\'"]*)["\']', acoes_bloco)

            url_ata = m_ata.group(1) if m_ata else ""
            possui_ata = bool(url_ata and "hash=" in url_ata)

            m_idsessao = re.search(r'idsessao=([0-9]+)', url_pauta)
            if not m_idsessao and url_ata:
                m_idsessao = re.search(r'id_sessao_julgamento=([0-9]+)', url_ata)

            id_sessao = m_idsessao.group(1) if m_idsessao else ""

            if id_sessao or url_pauta or url_ata:
                sessoes.append(SessaoJulgamento(
                    id_sessao=id_sessao,
                    periodo_data=periodo,
                    tipo_sessao=tipo_sessao,
                    orgao_julgador=orgao_nome,
                    desembargadores=magistrados,
                    url_pauta=url_pauta,
                    url_ata=url_ata,
                    possui_ata=possui_ata
                ))

        return sessoes

    def carregar_revisoes_criminais_da_ata(self, sessao: SessaoJulgamento) -> List[RevisaoCriminal]:
        """Baixa e extrai exclusivamente os processos de Revisão Criminal da Ata."""
        if not sessao.url_ata:
            return []

        time.sleep(self.delay)
        html_ata = self.fetch_url(sessao.url_ata)
        if not html_ata:
            return []

        revisoes = parse_ata_revisao_criminal(
            html=html_ata,
            orgao_julgador=sessao.orgao_julgador,
            data_sessao=sessao.periodo_data,
            tipo_sessao=sessao.tipo_sessao
        )
        sessao.revisoes_criminais = revisoes
        return revisoes
