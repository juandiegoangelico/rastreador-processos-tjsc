"""
Módulo de Classificação e Análise Processual.
Identifica e categoriza a representação processual:
- DATIVO: Processos com defensor(a) dativo(a) nomeado(a) e/ou honorários fixados/arbitrados
- DPE: Processos assistidos pela Defensoria Pública do Estado de Santa Catarina
- SEM_ADVOGADO: Partes sem advogado/procurador constituído nos autos (desconsiderando entes institucionais)
- CONSTITUIDO: Advogado particular constituído
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from config import TIPO_DATIVO, TIPO_DPE, TIPO_SEM_ADVOGADO, TIPO_CONSTITUIDO


@dataclass
class Representante:
    tipo: str  # ADVOGADO(A), DEFENSOR(A), PROCURADOR(A)
    nome: str
    oab_ou_orgao: str = ""


@dataclass
class Parte:
    polo: str  # autor, reu, outros
    tipo: str  # APELANTE, APELADO, PACIENTE, AUTOR, RÉU
    nome: str
    representantes: List[Representante] = field(default_factory=list)

    @property
    def sem_representante(self) -> bool:
        return len(self.representantes) == 0


@dataclass
class ProcessoJulgado:
    numero_processo: str
    classe_processual: str
    origem: str
    seq_pauta: str
    orgao_julgador: str
    data_sessao: str
    tipo_sessao: str
    partes: List[Parte] = field(default_factory=list)
    decisao: str = ""
    categorias: List[str] = field(default_factory=list)
    detalhes_classificacao: Dict[str, Any] = field(default_factory=dict)
    link_processo: str = ""


class ProcessClassifier:
    """Classificador de representação e identificador de Dativos, DPE e ausência de advogado."""

    # Expressões regulares para Defensoria Pública
    RE_DPE = re.compile(
        r"(\b(?:DPE|DPESC)\b|defensori?a\s+p[uú]blica|defensor(?:a)?\s+p[uú]blic[oa])",
        re.IGNORECASE
    )

    # Expressões regulares para Defensoria Dativa no texto da decisão colegiada ou representação
    RE_DATIVO_TEXTO = re.compile(
        r"(defensor(?:a)?\s+dativ[oa]|advogad[oa]\s+dativ[oa]|"
        r"honor[áa]rios.*?(?:ao|à|da|do)?\s*defensor(?:a)?\s+dativ[oa]|"
        r"arbitrar\s+honor[áa]rios.*?(?:dativ|advocat[íi]cios)|"
        r"fixar\s+honor[áa]rios.*?(?:ao|em\s+favor\s+d[oa])\s+defensor(?:a)?\s+dativ[oa])",
        re.IGNORECASE
    )

    # Entidades e autoridades que atuam institucionalmente e não constituem advogado particular
    RE_INSTITUCIONAL = re.compile(
        r"(minist[ée]rio\s+p[úu]blico|ju[íi]zo|vara\s+[uú]nica|comarca|"
        r"delegad[oa]|delegacia|pol[íi]cia|estado\s+de\s+santa\s+catarina|"
        r"munic[íi]pio|uni[ãa]o|procuradoria|os\s+mesmos)",
        re.IGNORECASE
    )

    def is_ente_institucional(self, nome: str, tipo: str) -> bool:
        """Determina se a parte é uma autoridade coatora, órgão ou ministério público."""
        if self.RE_INSTITUCIONAL.search(nome) or self.RE_INSTITUCIONAL.search(tipo):
            return True
        if tipo.upper() in ["MP", "IMPETRADO", "AUTORIDADE COATORA"]:
            return True
        return False

    def classificar(self, proc: ProcessoJulgado) -> None:
        """Executa a classificação completa do processo e anota categorias e detalhes."""
        categorias = set()
        detalhes = {
            "motivos_dativo": [],
            "defensores_dpe": [],
            "partes_sem_advogado": [],
            "advogados_privados": []
        }

        # 1. Análise dos representantes das partes
        for parte in proc.partes:
            if parte.sem_representante:
                # Ignora entes institucionais
                if not self.is_ente_institucional(parte.nome, parte.tipo):
                    categorias.add(TIPO_SEM_ADVOGADO)
                    detalhes["partes_sem_advogado"].append({
                        "polo": parte.polo,
                        "tipo": parte.tipo,
                        "nome": parte.nome
                    })
            else:
                for rep in parte.representantes:
                    texto_completo = f"{rep.tipo} {rep.nome} {rep.oab_ou_orgao}"

                    # Checa DPE
                    if self.RE_DPE.search(texto_completo):
                        categorias.add(TIPO_DPE)
                        detalhes["defensores_dpe"].append({
                            "parte": parte.nome,
                            "polo": parte.polo,
                            "representante": rep.nome,
                            "tipo": rep.tipo
                        })
                    # Checa Dativo na descrição do representante
                    elif "dativ" in texto_completo.lower():
                        categorias.add(TIPO_DATIVO)
                        detalhes["motivos_dativo"].append({
                            "origem": "representante",
                            "detalhe": f"{rep.tipo}: {rep.nome}"
                        })
                    elif "procurador" not in rep.tipo.lower() and "ministério público" not in rep.nome.lower():
                        detalhes["advogados_privados"].append({
                            "parte": parte.nome,
                            "representante": rep.nome
                        })

        # 2. Análise do dispositivo da decisão (fixação de honorários dativos)
        if proc.decisao:
            matches = self.RE_DATIVO_TEXTO.finditer(proc.decisao)
            for m in matches:
                categorias.add(TIPO_DATIVO)
                ini = max(0, m.start() - 40)
                fim = min(len(proc.decisao), m.end() + 80)
                trecho = proc.decisao[ini:fim].strip()
                detalhes["motivos_dativo"].append({
                    "origem": "decisao",
                    "trecho": trecho
                })

        # Se não caiu em nenhum dos alvos, marca como constituído
        if not categorias:
            categorias.add(TIPO_CONSTITUIDO)

        proc.categorias = sorted(list(categorias))
        proc.detalhes_classificacao = detalhes


def parse_ata_html(
    html: str,
    orgao_julgador: str = "",
    data_sessao: str = "",
    tipo_sessao: str = ""
) -> List[ProcessoJulgado]:
    """Faz o parsing completo de uma Ata de Julgamento HTML gerando os processos e partes."""
    processos: List[ProcessoJulgado] = []
    classifier = ProcessClassifier()

    blocos = re.split(r'<p class=["\']identificacao_processo["\']>', html)[1:]

    ultimo_numero = "Desconhecido"
    ultima_classe = ""
    ultimo_link = ""

    for bloco in blocos:
        # 1. Número do processo e classe
        m_num = re.search(r'data-numero_processo=["\'](\d+)["\']', bloco)
        numero_proc_limpo = m_num.group(1) if m_num else ""

        if numero_proc_limpo:
            numero_proc = formatar_cnj(numero_proc_limpo)
            m_classe = re.search(r'data-classe_processo=["\'][^"\']*["\']>([^<]+)</span>', bloco)
            classe = m_classe.group(1).strip() if m_classe else ""
            link_proc = f"https://eproc2g.tjsc.jus.br/eproc/externo_controlador.php?acao=processo_seleciona_publica&num_processo={numero_proc_limpo}"
            ultimo_numero = numero_proc
            ultima_classe = classe
            ultimo_link = link_proc
        else:
            # Verifica se é incidente ou desdobramento do processo anterior
            if "incidente" in bloco[:120].lower():
                numero_proc = f"{ultimo_numero} (Incidente)"
                classe = f"Incidente em {ultima_classe}" if ultima_classe else "Incidente Processual"
                link_proc = ultimo_link
            else:
                m_text = re.search(r'N[ºo°]?\s*([0-9.\-/]+)', bloco)
                numero_proc = m_text.group(1) if m_text else ultimo_numero
                classe = ultima_classe or "Processo"
                link_proc = ultimo_link

        m_origem = re.search(r'data-origem_processo=["\']([^"\']+)["\']', bloco)
        origem = m_origem.group(1) if m_origem else "SC"

        m_pauta = re.search(r'data-tipo_pauta=["\'][^"\']*["\']>\s*\(([^)]+)\)</span>', bloco)
        seq_pauta = m_pauta.group(1).strip() if m_pauta else ""

        # 2. Partes e Representantes
        partes: List[Parte] = []
        divs_partes = re.findall(r'<div class=["\'](parte_(?:autor|re|outros))["\'][^>]*>(.*?)</div>', bloco, re.DOTALL)
        for tipo_div, div_content in divs_partes:
            polo = "autor" if "autor" in tipo_div else ("reu" if "re" in tipo_div else "outros")

            m_parte = re.search(
                r'<span class=["\']tipo_parte["\']>([^<]+)</span>:\s*<span class=["\']nome_parte["\']>([^<]+)</span>',
                div_content
            )
            if m_parte:
                t_parte = m_parte.group(1).strip()
                n_parte = m_parte.group(2).strip()
            else:
                t_parte = "PARTE"
                n_parte = "Não identificada"

            reps_encontrados: List[Representante] = []
            div_reps = re.findall(
                r'<p class=["\']representante["\'][^>]*>.*?<span class=["\']tipo_parte_representante["\']>([^<]+)</span>:\s*<span class=["\']nome_parte_representante["\']>([^<]+)</span>',
                div_content,
                re.DOTALL
            )
            for t_rep, n_rep in div_reps:
                t_rep = t_rep.strip()
                n_rep = n_rep.strip()

                oab_match = re.search(r'\(([^)]+)\)', n_rep)
                oab_orgao = oab_match.group(1) if oab_match else ""

                reps_encontrados.append(Representante(
                    tipo=t_rep,
                    nome=n_rep,
                    oab_ou_orgao=oab_orgao
                ))

            partes.append(Parte(
                polo=polo,
                tipo=t_parte,
                nome=n_parte,
                representantes=reps_encontrados
            ))

        # 3. Decisão / Dispositivo
        m_decisao = re.search(r'data-nome=["\']decisao["\'][^>]*>(.*?)</section>', bloco, re.DOTALL)
        decisao_texto = ""
        if m_decisao:
            decisao_raw = m_decisao.group(1)
            decisao_texto = re.sub(r'<[^>]+>', ' ', decisao_raw)
            decisao_texto = re.sub(r'\s+', ' ', decisao_texto).strip()

        proc = ProcessoJulgado(
            numero_processo=numero_proc,
            classe_processual=classe,
            origem=origem,
            seq_pauta=seq_pauta,
            orgao_julgador=orgao_julgador,
            data_sessao=data_sessao,
            tipo_sessao=tipo_sessao,
            partes=partes,
            decisao=decisao_texto,
            link_processo=link_proc
        )

        classifier.classificar(proc)
        processos.append(proc)

    return processos


def formatar_cnj(numero: str) -> str:
    """Formata número no padrão CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO."""
    limpo = re.sub(r'\D', '', numero)
    if len(limpo) == 20:
        return f"{limpo[0:7]}-{limpo[7:9]}.{limpo[9:13]}.{limpo[13:14]}.{limpo[14:16]}.{limpo[16:20]}"
    return numero
