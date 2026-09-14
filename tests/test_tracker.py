"""
Testes unitários automatizados para o Rastreador de Processos TJSC.
"""

import os
import unittest

from config import TIPO_DATIVO, TIPO_DPE, TIPO_SEM_ADVOGADO, TIPO_CONSTITUIDO
from portal_tjsc import PortalTJSCScraper
from classifier import (
    ProcessClassifier,
    ProcessoJulgado,
    Parte,
    Representante,
    parse_ata_html,
    formatar_cnj,
)
from exporter import Exporter


class TestPortalTJSC(unittest.TestCase):
    def test_extrair_cancelamentos(self):
        html_exemplo = """
        <table id="transferencias-e-cancelamentos">
            <tbody>
                <tr>
                    <td>6ª Câmara Criminal</td>
                    <td>15/09/2026</td>
                    <td>A sessão física ordinária foi cancelada.</td>
                </tr>
            </tbody>
        </table>
        """
        scraper = PortalTJSCScraper()
        canc = scraper.extrair_cancelamentos(html_exemplo)
        self.assertEqual(len(canc), 1)
        self.assertEqual(canc[0].orgao_julgador, "6ª Câmara Criminal")
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
                    <td>1ª Câmara de Direito Público</td>
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


class TestClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = ProcessClassifier()

    def test_formatar_cnj(self):
        self.assertEqual(
            formatar_cnj("50005415220238240048"),
            "5000541-52.2023.8.24.0048"
        )

    def test_classificar_dpe(self):
        proc = ProcessoJulgado(
            numero_processo="5000000-00.2026.8.24.0000",
            classe_processual="Apelação Criminal",
            origem="SC",
            seq_pauta="1",
            orgao_julgador="1ª Câmara Criminal",
            data_sessao="15/09/2026",
            tipo_sessao="Virtual",
            partes=[
                Parte(
                    polo="autor",
                    tipo="APELANTE",
                    nome="JOÃO DA SILVA (RÉU)",
                    representantes=[
                        Representante(tipo="ADVOGADO(A)", nome="MARIA SANTOS (DPE)")
                    ]
                )
            ]
        )
        self.classifier.classificar(proc)
        self.assertIn(TIPO_DPE, proc.categorias)
        self.assertEqual(len(proc.detalhes_classificacao["defensores_dpe"]), 1)

    def test_classificar_dativo_por_decisao(self):
        proc = ProcessoJulgado(
            numero_processo="5000001-00.2026.8.24.0000",
            classe_processual="Apelação Criminal",
            origem="SC",
            seq_pauta="2",
            orgao_julgador="2ª Câmara Criminal",
            data_sessao="15/09/2026",
            tipo_sessao="Virtual",
            partes=[
                Parte(
                    polo="autor",
                    tipo="APELANTE",
                    nome="RÉU TESTE",
                    representantes=[
                        Representante(tipo="ADVOGADO(A)", nome="ADVOGADO NOMEADO (OAB SC99999)")
                    ]
                )
            ],
            decisao="A CÂMARA DECIDIU, POR UNANIMIDADE, CONHECER DO RECURSO E FIXAR HONORÁRIOS RECURSAIS AO DEFENSOR DATIVO NO VALOR DE TABELA."
        )
        self.classifier.classificar(proc)
        self.assertIn(TIPO_DATIVO, proc.categorias)
        self.assertTrue(len(proc.detalhes_classificacao["motivos_dativo"]) > 0)

    def test_classificar_sem_advogado(self):
        proc = ProcessoJulgado(
            numero_processo="5000002-00.2026.8.24.0000",
            classe_processual="Ação Penal",
            origem="SC",
            seq_pauta="3",
            orgao_julgador="3ª Câmara Criminal",
            data_sessao="15/09/2026",
            tipo_sessao="Virtual",
            partes=[
                Parte(
                    polo="reu",
                    tipo="RÉU",
                    nome="RÉU SEM DEFESA CONSTITUÍDA",
                    representantes=[]
                ),
                Parte(
                    polo="autor",
                    tipo="AUTOR",
                    nome="MINISTÉRIO PÚBLICO DO ESTADO DE SANTA CATARINA",
                    representantes=[]  # Institucional: não deve contar como sem advogado
                )
            ]
        )
        self.classifier.classificar(proc)
        self.assertIn(TIPO_SEM_ADVOGADO, proc.categorias)
        sem_adv = proc.detalhes_classificacao["partes_sem_advogado"]
        self.assertEqual(len(sem_adv), 1)
        self.assertEqual(sem_adv[0]["nome"], "RÉU SEM DEFESA CONSTITUÍDA")


class TestExporter(unittest.TestCase):
    def test_export_all_formats(self):
        proc = ProcessoJulgado(
            numero_processo="5000000-00.2026.8.24.0000",
            classe_processual="Apelação",
            origem="SC",
            seq_pauta="1",
            orgao_julgador="Câmara Teste",
            data_sessao="15/09/2026",
            tipo_sessao="Virtual",
            partes=[
                Parte(
                    polo="autor",
                    tipo="AUTOR",
                    nome="Parte Teste",
                    representantes=[Representante(tipo="ADVOGADO", nome="Adv Teste (DPE)")]
                )
            ],
            categorias=[TIPO_DPE],
            detalhes_classificacao={"defensores_dpe": [{"representante": "Adv Teste (DPE)", "parte": "Parte Teste"}]},
            decisao="Decisão de teste"
        )

        tmp_dir = "/Users/juandiegoangelico/.gemini/antigravity/scratch/rastreador-processos-tjsc/tests_tmp"
        os.makedirs(tmp_dir, exist_ok=True)

        csv_file = os.path.join(tmp_dir, "test.csv")
        json_file = os.path.join(tmp_dir, "test.json")
        html_file = os.path.join(tmp_dir, "test.html")

        Exporter.export_csv([proc], csv_file)
        Exporter.export_json([proc], json_file)
        Exporter.export_html([proc], html_file)

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
