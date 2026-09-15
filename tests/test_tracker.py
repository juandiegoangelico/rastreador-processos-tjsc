"""
Testes unitários automatizados para o Rastreador de Revisões Criminais TJSC.
"""

import os
import unittest

from config import STATUS_SEM_ADVOGADO, STATUS_DATIVO, STATUS_DPE, STATUS_CONSTITUIDO
from portal_tjsc import PortalTJSCScraper
from classifier import (
    RevisaoCriminalClassifier,
    RevisaoCriminal,
    Parte,
    Representante,
    parse_ata_revisao_criminal,
    formatar_cnj,
)
from exporter import Exporter


class TestPortalTJSC(unittest.TestCase):
    def test_extrair_cancelamentos(self):
        html_exemplo = """
        <table id="transferencias-e-cancelamentos">
            <tbody>
                <tr>
                    <td>Primeiro Grupo de Direito Criminal</td>
                    <td>15/09/2026</td>
                    <td>A sessão presencial foi cancelada.</td>
                </tr>
            </tbody>
        </table>
        """
        scraper = PortalTJSCScraper()
        canc = scraper.extrair_cancelamentos(html_exemplo)
        self.assertEqual(len(canc), 1)
        self.assertEqual(canc[0].orgao_julgador, "Primeiro Grupo de Direito Criminal")
        self.assertEqual(canc[0].sessao_original, "15/09/2026")
        self.assertIn("cancelada", canc[0].descricao_alteracao)

    def test_extrair_calendario(self):
        html_exemplo = """
        <table>
            <thead>
                <tr><th>Órgão</th><th>Data</th><th>Dia da Semana</th><th>Sala</th></tr>
            </thead>
            <tbody>
                <tr>
                    <td>Primeiro Grupo de Direito Criminal</td>
                    <td>18/08/2026</td>
                    <td>terça-feira</td>
                    <td>Torre II - Sala 106</td>
                </tr>
            </tbody>
        </table>
        """
        scraper = PortalTJSCScraper()
        cal = scraper.extrair_calendario_fisico(html_exemplo)
        self.assertEqual(len(cal), 1)
        self.assertEqual(cal[0].data, "18/08/2026")
        self.assertEqual(cal[0].sala, "Torre II - Sala 106")


class TestRevisaoClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = RevisaoCriminalClassifier()

    def test_formatar_cnj(self):
        self.assertEqual(
            formatar_cnj("50005415220238240048"),
            "5000541-52.2023.8.24.0048"
        )

    def test_classificar_sem_advogado(self):
        rev = RevisaoCriminal(
            numero_processo="5000000-00.2026.8.24.0000",
            classe_processual="Revisão Criminal",
            nome_sentenciado="",
            status_defesa="",
            comarca_origem="TJSC",
            orgao_julgador="Primeiro Grupo de Direito Criminal",
            data_sessao="15/09/2026",
            tipo_sessao="Virtual",
            partes=[
                Parte(
                    polo="autor",
                    tipo="REQUERENTE",
                    nome="FULANO DE TAL (SENTENCIADO)",
                    representantes=[]  # Sem advogado
                ),
                Parte(
                    polo="reu",
                    tipo="REQUERIDO",
                    nome="Juízo da 1ª Vara Criminal da Comarca de Criciúma",
                    representantes=[]
                )
            ]
        )
        self.classifier.classificar(rev)
        self.assertEqual(rev.status_defesa, STATUS_SEM_ADVOGADO)
        self.assertEqual(rev.nome_sentenciado, "FULANO DE TAL (SENTENCIADO)")
        self.assertTrue(rev.sem_advogado_constituido)

    def test_classificar_dativo_por_decisao(self):
        rev = RevisaoCriminal(
            numero_processo="5000001-00.2026.8.24.0000",
            classe_processual="Revisão Criminal",
            nome_sentenciado="",
            status_defesa="",
            comarca_origem="TJSC",
            orgao_julgador="Segundo Grupo de Direito Criminal",
            data_sessao="15/09/2026",
            tipo_sessao="Virtual",
            partes=[
                Parte(
                    polo="autor",
                    tipo="REQUERENTE",
                    nome="BELTRANO SILVA",
                    representantes=[]
                )
            ],
            decisao="O GRUPO DECIDIU, POR UNANIMIDADE, CONHECER DO PEDIDO E FIXAR HONORARIOS AO DEFENSOR DATIVO NO VALOR DE TABELA."
        )
        self.classifier.classificar(rev)
        self.assertEqual(rev.status_defesa, STATUS_DATIVO)
        self.assertIn("Defensor dativo", rev.detalhes_defesa["justificativa"])

    def test_classificar_dpe(self):
        rev = RevisaoCriminal(
            numero_processo="5000002-00.2026.8.24.0000",
            classe_processual="Revisão Criminal",
            nome_sentenciado="",
            status_defesa="",
            comarca_origem="TJSC",
            orgao_julgador="Primeiro Grupo de Direito Criminal",
            data_sessao="15/09/2026",
            tipo_sessao="Virtual",
            partes=[
                Parte(
                    polo="autor",
                    tipo="REQUERENTE",
                    nome="CICLANO OLIVEIRA",
                    representantes=[
                        Representante(tipo="DEFENSOR(A)", nome="DEFENSORIA PÚBLICA DO ESTADO DE SANTA CATARINA")
                    ]
                )
            ]
        )
        self.classifier.classificar(rev)
        self.assertEqual(rev.status_defesa, STATUS_DPE)

    def test_classificar_constituido(self):
        rev = RevisaoCriminal(
            numero_processo="5000003-00.2026.8.24.0000",
            classe_processual="Revisão Criminal",
            nome_sentenciado="",
            status_defesa="",
            comarca_origem="TJSC",
            orgao_julgador="Primeiro Grupo de Direito Criminal",
            data_sessao="15/09/2026",
            tipo_sessao="Virtual",
            partes=[
                Parte(
                    polo="autor",
                    tipo="REQUERENTE",
                    nome="SENTENCIADO COM ADVOGADO",
                    representantes=[
                        Representante(tipo="ADVOGADO(A)", nome="DR. ADVOGADO PARTICULAR", oab_ou_orgao="OAB/SC 12345")
                    ]
                )
            ]
        )
        self.classifier.classificar(rev)
        self.assertEqual(rev.status_defesa, STATUS_CONSTITUIDO)


class TestExporter(unittest.TestCase):
    def test_export_all_formats(self):
        rev = RevisaoCriminal(
            numero_processo="5000000-00.2026.8.24.0000",
            classe_processual="Revisão Criminal",
            nome_sentenciado="Sentenciado Exemplo",
            status_defesa=STATUS_SEM_ADVOGADO,
            comarca_origem="Comarca de Florianópolis",
            orgao_julgador="Primeiro Grupo de Direito Criminal",
            data_sessao="15/09/2026",
            tipo_sessao="Virtual",
            partes=[
                Parte(
                    polo="autor",
                    tipo="REQUERENTE",
                    nome="Sentenciado Exemplo",
                    representantes=[]
                )
            ],
            detalhes_defesa={"justificativa": "Sem advogado constituído."},
            decisao="Decisão de teste"
        )

        tmp_dir = "/Users/juandiegoangelico/.gemini/antigravity/scratch/rastreador-processos-tjsc/tests_tmp"
        os.makedirs(tmp_dir, exist_ok=True)

        csv_file = os.path.join(tmp_dir, "test.csv")
        json_file = os.path.join(tmp_dir, "test.json")
        html_file = os.path.join(tmp_dir, "test.html")

        Exporter.export_csv([rev], csv_file)
        Exporter.export_json([rev], json_file)
        Exporter.export_html([rev], html_file)

        self.assertTrue(os.path.exists(csv_file))
        self.assertTrue(os.path.exists(json_file))
        self.assertTrue(os.path.exists(html_file))

        # cleanup
        for f in [csv_file, json_file, html_file]:
            if os.path.exists(f):
                os.remove(f)
        if os.path.exists(tmp_dir):
            os.rmdir(tmp_dir)


if __name__ == "__main__":
    unittest.main()
