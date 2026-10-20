from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from wb_reconcile.excel import write_workbook


class ExportTests(unittest.TestCase):
    def test_strings_cannot_become_excel_formulas(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'safe.xlsx'
            write_workbook(path, {'Лист': [('значение',), ('=HYPERLINK("bad")',)]})
            with ZipFile(path) as workbook:
                xml = ET.fromstring(workbook.read('xl/worksheets/sheet1.xml'))
                ns = {'m': 'http://internal.internal.example.invalid/spreadsheetml/2006/main'}
                self.assertFalse(xml.findall('.//m:f', ns))
                self.assertIn('=HYPERLINK', ''.join(xml.itertext()))


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-m', 'wb_reconcile', *args],
                              capture_output=True, text=True)

    def test_all_modes_produce_valid_demo_workbooks(self):
        with TemporaryDirectory() as directory:
            for mode, first, last in [('daily', '2026-08-01', '2026-08-01'),
                                       ('weekly', '2026-08-03', '2026-08-09'),
                                       ('monthly', '2026-08-01', '2026-08-31')]:
                with self.subTest(mode=mode):
                    result = self.run_cli('run', '--mode', mode, '--start', first, '--end', last,
                                          '--demo', '--output-dir', directory)
                    self.assertEqual(result.returncode, 2, result.stderr)
            files = list(Path(directory).glob('*.xlsx'))
            self.assertEqual(len(files), 3)
            for path in files:
                with ZipFile(path) as workbook:
                    ns = {'m': 'http://internal.internal.example.invalid/spreadsheetml/2006/main'}
                    root = ET.fromstring(workbook.read('xl/workbook.xml'))
                    names = [s.attrib['name'] for s in root.findall('m:sheets/m:sheet', ns)]
                    self.assertEqual(names, ['Сводка', 'Сравнения', 'Источники', 'Покрытие', 'Документы'])
                    self.assertIn('ДЕМОНСТРАЦИЯ', workbook.read('xl/worksheets/sheet1.xml').decode())

    def test_repeated_runs_keep_history(self):
        with TemporaryDirectory() as directory:
            args = ('run', '--mode', 'daily', '--start', '2026-08-01', '--end', '2026-08-01', '--demo', '--output-dir', directory)
            self.assertEqual(self.run_cli(*args).returncode, 2)
            self.assertEqual(self.run_cli(*args).returncode, 2)
            self.assertEqual(len(list(Path(directory).glob('*.xlsx'))), 2)

    def test_live_unconfigured_reports_failure_instead_of_zero_match(self):
        with TemporaryDirectory() as directory:
            result = self.run_cli('run', '--mode', 'daily', '--start', '2026-08-01', '--end', '2026-08-01', '--output-dir', directory)
            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertEqual(len(list(Path(directory).glob('*.xlsx'))), 1)

    def test_bad_dates_do_not_generate_a_report(self):
        with TemporaryDirectory() as directory:
            result = self.run_cli('run', '--mode', 'monthly', '--start', '2026-08-02', '--end', '2026-08-31', '--demo', '--output-dir', directory)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
