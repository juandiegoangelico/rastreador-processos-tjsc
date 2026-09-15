"""
Classificador especializado em Revisões Criminais do TJSC.
Filtra e analisa especificamente pedidos de Revisão Criminal,
com ênfase em sentenciados que não possuem advogado constituído (de próprio punho / jus postulandi).
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from config import (
    STATUS_SEM_ADVOGADO,
    STATUS_DATIVO,
    STATUS_DPE,
    STATUS_CONSTITUIDO,
)


@dataclass
class Representante:
    tipo: str
    nome: str
    oab_ou_orgao: str = ""


@dataclass
class Parte:
    polo: str  # autor (requerente), reu (requerido), outros
    tipo: str  # REQUERENTE, REQUERIDO, INTERESSADO, MP
    nome: str
    representantes: List[Representante] = field(default_factory=list)

    @property
    def sem_representante(self) -> bool:
        return len(self.representantes) == 0


@dataclass
class RevisaoCriminal:
    numero_processo: str
    classe_processual: str
    nome_sentenciado: str
    status_defesa: str
    comarca_origem: str
    orgao_julgador: str
    data_sessao: str
    tipo_sessao: str
    partes: List[Parte] = field(default_factory=list)
    decisao: str = ""
    detalhes_defesa: Dict[str, Any] = field(default_factory=dict)
    link_processo: str = ""

    @property
    def sem_advogado_constituido(self) -> bool:
        return self.status_defesa == STATUS_SEM_ADVOGADO


class RevisaoCriminalClassifier:
    """Classifica a representação do sentenciado em pedidos de Revisão Criminal."""

    RE_DPE = re.compile(r"(\b(?:DPE|DPESC)\b|defensori?a\s+p[uú]blica|defensor(?:a)?\s+p[uú]blic[oa])", re.IGNORECASE)
    RE_DATIVO = re.compile(r"(defensor(?:a)?\s+dativ[oa]|advogad[oa]\s+dativ[oa]|honor[áa]rios.*?(?:dativ|arbitr))", re.IGNORECASE)
    RE_NOMES_DECISAO = re.compile(
        r"(?:condenaç[ãa]o\s+de|pena\s+imposta\s+a|em\s+favor\s+(?:de|do\s+requerente)|revis[ãa]o\s+criminal\s+(?:ajuizada|interposta|proposta)\s+por|revisional\s+(?:ajuizada|interposta|proposta)\s+por|requerente\s+|sentenciad[oa]\s+|reeducand[oa]\s+|apenad[oa]\s+)\s*([A-ZÀ-Úa-zà-ú\s]{4,50}?)(?=\s+(?:pela|pelo|para|no\s+sentido|com\s+base|em\s+regime|além|\.|\,|\;|\:|\-|\())",
        re.IGNORECASE
    )

    def classificar(self, rev: RevisaoCriminal) -> None:
        """Determina o status da defesa do sentenciado (Requerente)."""
        detalhes = {
            "reps_sentenciado": [],
            "trecho_decisao_dativo": "",
            "justificativa": ""
        }

        # Checa casos preliminares de pauta
        decisao_low = rev.decisao.lower()
        if "retirado de pauta" in decisao_low:
            rev.status_defesa = "RETIRADO_DE_PAUTA"
            if not rev.nome_sentenciado:
                rev.nome_sentenciado = "(Processo Retirado de Pauta)"
            detalhes["justificativa"] = "Processo retirado de pauta antes do julgamento."
            rev.detalhes_defesa = detalhes
            return

        if "adiado" in decisao_low:
            rev.status_defesa = "ADIADO"
            if not rev.nome_sentenciado:
                rev.nome_sentenciado = "(Processo com Julgamento Adiado)"
            detalhes["justificativa"] = "Julgamento adiado para sessão posterior."
            rev.detalhes_defesa = detalhes
            return

        # Localiza o sentenciado (polo Requerente)
        requerente = None
        for p in rev.partes:
            if p.tipo.upper() in ["REQUERENTE", "APELANTE", "PACIENTE", "AUTOR"] or p.polo == "autor":
                requerente = p
                break

        if not requerente and rev.partes:
            for p in rev.partes:
                p_nome_low = p.nome.lower()
                if "ministério público" not in p_nome_low and "juízo" not in p_nome_low and "câmara" not in p_nome_low:
                    requerente = p
                    break

        # Se não há requerente expresso nas partes, tenta recuperar o nome pela decisão
        if not requerente or not requerente.nome:
            m_nome = self.RE_NOMES_DECISAO.search(rev.decisao)
            if m_nome:
                nome_candidato = m_nome.group(1).strip()
                # Validação básica para evitar palavras soltas
                if len(nome_candidato.split()) >= 2 and not any(k in nome_candidato.lower() for k in ["desembargador", "ministério", "tribunal"]):
                    rev.nome_sentenciado = nome_candidato

        if requerente and requerente.nome:
            rev.nome_sentenciado = requerente.nome

        # Análise dos representantes
        if requerente and not requerente.sem_representante:
            tem_dpe = False
            tem_dativo = False
            tem_oab = False

            for r in requerente.representantes:
                txt = f"{r.tipo} {r.nome} {r.oab_ou_orgao}".lower()
                detalhes["reps_sentenciado"].append(f"{r.tipo}: {r.nome}")

                if self.RE_DPE.search(txt):
                    tem_dpe = True
                elif "dativ" in txt:
                    tem_dativo = True
                elif "oab" in txt or "advogad" in txt:
                    tem_oab = True

            if tem_dpe:
                rev.status_defesa = STATUS_DPE
                detalhes["justificativa"] = "Assistido pela Defensoria Pública do Estado."
            elif tem_dativo:
                rev.status_defesa = STATUS_DATIVO
                detalhes["justificativa"] = "Advogado Dativo indicado nos autos."
            elif tem_oab:
                rev.status_defesa = STATUS_CONSTITUIDO
                detalhes["justificativa"] = "Possui advogado particular constituído nos autos."
            else:
                rev.status_defesa = STATUS_SEM_ADVOGADO
                detalhes["justificativa"] = "Sem procurador habilitado com OAB."
        else:
            # Sem representantes formais cadastrados no polo
            # 1. Verifica se houve arbitramento de honorários ao dativo no acórdão
            if rev.decisao and self.RE_DATIVO.search(rev.decisao):
                rev.status_defesa = STATUS_DATIVO
                m = self.RE_DATIVO.search(rev.decisao)
                ini = max(0, m.start() - 30)
                fim = min(len(rev.decisao), m.end() + 70)
                detalhes["trecho_decisao_dativo"] = rev.decisao[ini:fim].strip()
                detalhes["justificativa"] = "Defensor dativo nomeado pelo Tribunal com honorários fixados no acórdão."
            # 2. Verifica se o pedido de sustentação oral partiu de advogado
            elif rev.detalhes_defesa.get("advogado_pedido"):
                rev.status_defesa = STATUS_CONSTITUIDO
                adv = rev.detalhes_defesa.get("advogado_pedido")
                detalhes["justificativa"] = f"Advogado requereu sustentação oral / preferência: {adv}"
            else:
                rev.status_defesa = STATUS_SEM_ADVOGADO
                if not rev.nome_sentenciado:
                    detalhes["justificativa"] = "Revisão proposta de próprio punho (qualificação reservada na ata)."
                else:
                    detalhes["justificativa"] = "Sentenciado ingressou sem advogado constituído (jus postulandi / de próprio punho)."

        if not rev.nome_sentenciado:
            rev.nome_sentenciado = "Sentenciado sob Sigilo / Não identificado"

        rev.detalhes_defesa = detalhes


def parse_ata_revisao_criminal(
    html: str,
    orgao_julgador: str = "",
    data_sessao: str = "",
    tipo_sessao: str = ""
) -> List[RevisaoCriminal]:
    """Extrai exclusivamente processos da classe Revisão Criminal de uma Ata de Julgamento."""
    revisoes: List[RevisaoCriminal] = []
    classifier = RevisaoCriminalClassifier()

    # Cada processo na ata é uma section com data-nome="identificacao_processo"
    blocos = re.split(r'(?=<section\b[^>]*data-nome=[\'"]identificacao_processo[\'"])', html)[1:]
    
    ultimo_num = ""
    ultima_classe = ""
    ultimo_link = ""
    ultimo_sentenciado = ""
    ultima_comarca = "TJSC"

    re_comarca = re.compile(
        r"(?:comarca\s+de|ju[íi]zo\s+da\s+[0-9ªa]+\s+vara\s+criminal\s+da\s+comarca\s+de)\s+([A-ZÀ-Úa-zà-ú\s]{3,35}?)(?=\s*(?:\.|\,|\;|\:|\-|\(|\d|$))",
        re.IGNORECASE
    )

    for bloco in blocos:
        m_classe = re.search(r'data-classe_processo=[\'"][^\'"]*[\'"]>([^<]+)</span>', bloco)
        classe = m_classe.group(1).strip() if m_classe else ""

        eh_revisao = "revisão criminal" in classe.lower() or "revisao criminal" in classe.lower()
        eh_incidente = "incidente" in bloco[:200].lower() and ("revisão criminal" in ultima_classe.lower() or "revisao criminal" in ultima_classe.lower())

        if not eh_revisao and not eh_incidente:
            m_num = re.search(r'data-numero_processo=[\'"](\d+)[\'"]', bloco)
            if m_num:
                ultimo_num = formatar_cnj(m_num.group(1))
                ultima_classe = classe
                ultimo_link = f"https://eproc2g.tjsc.jus.br/eproc/externo_controlador.php?acao=processo_seleciona_publica&num_processo={m_num.group(1)}"
            continue

        m_num = re.search(r'data-numero_processo=[\'"](\d+)[\'"]', bloco)
        if m_num:
            num_proc_limpo = m_num.group(1)
            num_proc = formatar_cnj(num_proc_limpo)
            link_proc = f"https://eproc2g.tjsc.jus.br/eproc/externo_controlador.php?acao=processo_seleciona_publica&num_processo={num_proc_limpo}"
            ultimo_num = num_proc
            ultima_classe = classe
            ultimo_link = link_proc
        else:
            if eh_incidente:
                num_proc = f"{ultimo_num} (Incidente)"
                classe = f"Incidente em {ultima_classe}"
                link_proc = ultimo_link
            else:
                m_txt = re.search(r'N[ºo°]?\s*([0-9.\-/]+)', bloco)
                num_proc = m_txt.group(1) if m_txt else ultimo_num
                link_proc = ultimo_link

        # Extração de Partes (se houver na ata)
        partes: List[Parte] = []
        divs_partes = re.findall(r'<div class=[\'"](parte_(?:autor|re|outros))[\'"][^>]*>(.*?)</div>', bloco, re.DOTALL)
        comarca_origem = "TJSC"

        for tipo_div, div_content in divs_partes:
            polo = "autor" if "autor" in tipo_div else ("reu" if "re" in tipo_div else "outros")

            m_parte = re.search(
                r'<span class=[\'"]tipo_parte[\'"]>([^<]+)</span>:\s*<span class=[\'"]nome_parte[\'"]>([^<]+)</span>',
                div_content
            )
            t_parte = m_parte.group(1).strip() if m_parte else ("REQUERENTE" if polo == "autor" else "REQUERIDO")
            n_parte = m_parte.group(2).strip() if m_parte else ""

            if polo == "reu" and ("vara" in n_parte.lower() or "comarca" in n_parte.lower() or "câmara" in n_parte.lower()):
                comarca_origem = n_parte

            reps_encontrados: List[Representante] = []
            div_reps = re.findall(
                r'<p class=[\'"]representante[\'"][^>]*>.*?<span class=[\'"]tipo_parte_representante[\'"]>([^<]+)</span>:\s*<span class=[\'"]nome_parte_representante[\'"]>([^<]+)</span>',
                div_content,
                re.DOTALL
            )
            for t_rep, n_rep in div_reps:
                t_rep = t_rep.strip()
                n_rep = n_rep.strip()
                oab_match = re.search(r'\(([^)]+)\)', n_rep)
                oab_orgao = oab_match.group(1) if oab_match else ""
                reps_encontrados.append(Representante(tipo=t_rep, nome=n_rep, oab_ou_orgao=oab_orgao))

            partes.append(Parte(polo=polo, tipo=t_parte, nome=n_parte, representantes=reps_encontrados))

        # Decisão
        m_decisao = re.search(r'data-nome=[\'"]decisao[\'"][^>]*>(.*?)</section>', bloco, re.DOTALL)
        decisao_texto = ""
        if m_decisao:
            decisao_raw = m_decisao.group(1)
            decisao_texto = re.sub(r'<[^>]+>', ' ', decisao_raw)
            decisao_texto = re.sub(r'\s+', ' ', decisao_texto).strip()

        # Pedido (Sustentação oral ou preferência registrada)
        advogado_pedido = ""
        m_pedido = re.search(r'data-nome=[\'"]pedido[\'"][^>]*>(.*?)</section>', bloco, re.DOTALL)
        if m_pedido:
            ped_limpo = re.sub(r'<[^>]+>', ' ', m_pedido.group(1))
            m_adv_ped = re.search(r'(?:SUSTENTAÇÃO DE ARGUMENTOS|PREFERÊNCIA|ADVOGADO)\s*:\s*([A-ZÀ-Ú\s]+)', ped_limpo, re.IGNORECASE)
            if m_adv_ped:
                advogado_pedido = m_adv_ped.group(1).strip()

        # Comarca de Origem via texto caso não estivesse nas partes
        if comarca_origem == "TJSC":
            m_com = re_comarca.search(bloco)
            if m_com:
                comarca_origem = m_com.group(0).strip().capitalize()
            elif eh_incidente and ultima_comarca != "TJSC":
                comarca_origem = ultima_comarca

        rev = RevisaoCriminal(
            numero_processo=num_proc,
            classe_processual=classe,
            nome_sentenciado="",
            status_defesa="",
            comarca_origem=comarca_origem,
            orgao_julgador=orgao_julgador,
            data_sessao=data_sessao,
            tipo_sessao=tipo_sessao,
            partes=partes,
            decisao=decisao_texto,
            detalhes_defesa={"advogado_pedido": advogado_pedido} if advogado_pedido else {},
            link_processo=link_proc
        )

        classifier.classificar(rev)

        if rev.nome_sentenciado and not rev.nome_sentenciado.startswith("("):
            ultimo_sentenciado = rev.nome_sentenciado
            ultima_comarca = rev.comarca_origem

        revisoes.append(rev)

    return revisoes


def formatar_cnj(numero: str) -> str:
    """Formata número no padrão CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO."""
    limpo = re.sub(r'\D', '', numero)
    if len(limpo) == 20:
        return f"{limpo[0:7]}-{limpo[7:9]}.{limpo[9:13]}.{limpo[13:14]}.{limpo[14:16]}.{limpo[16:20]}"
    return numero
