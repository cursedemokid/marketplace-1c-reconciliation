"""Небольшой XLSX-экспорт без внешних пакетов; Decimal сохраняются как текст."""

from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

MAIN = 'http://internal.internal.example.invalid/spreadsheetml/2006/main'
REL = 'http://internal.internal.example.invalid/package/2006/relationships'
OFFICE_REL = 'http://internal.internal.example.invalid/officeDocument/2006/relationships'
XML = 'http://internal.example.invalid/XML/1998/namespace'


def _xml(element):
    return ET.tostring(element, encoding='utf-8', xml_declaration=True)


def _column(index: int) -> str:
    result = ''
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _sheet(rows) -> bytes:
    root = ET.Element('worksheet', xmlns=MAIN)
    views = ET.SubElement(root, 'sheetViews')
    view = ET.SubElement(views, 'sheetView', workbookViewId='0')
    ET.SubElement(view, 'pane', ySplit='1', topLeftCell='A2', activePane='bottomLeft', state='frozen')
    columns = max((len(row) for row in rows), default=1)
    cols = ET.SubElement(root, 'cols')
    ET.SubElement(cols, 'col', min='1', max=str(columns), width='24', customWidth='1')
    data = ET.SubElement(root, 'sheetData')
    for number, values in enumerate(rows, 1):
        row = ET.SubElement(data, 'row', r=str(number))
        for index, value in enumerate(values, 1):
            cell = ET.SubElement(row, 'c', r=f'{_column(index)}{number}', t='inlineStr', s='1' if number == 1 else '0')
            if value is not None:
                text = str(value)
                if len(text) > 32767 or re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', text):
                    raise ValueError('Значение не может быть сохранено в ячейке Excel')
                inline = ET.SubElement(cell, 'is')
                ET.SubElement(inline, 't', {f'{{{XML}}}space': 'preserve'}).text = text
    if rows:
        ET.SubElement(root, 'autoFilter', ref=f'A1:{_column(columns)}{len(rows)}')
    return _xml(root)


STYLES = b'''<?xml version="1.0" encoding="UTF-8"?>
<styleSheet xmlns="http://internal.internal.example.invalid/spreadsheetml/2006/main">
<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts>
<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF203864"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"><alignment vertical="top" wrapText="1"/></xf><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''


def write_workbook(path: Path, sheets: dict[str, list[tuple]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = ET.Element('Types', xmlns='http://internal.internal.example.invalid/package/2006/content-types')
    for ext, kind in [('rels', 'application/vnd.openxmlformats-package.relationships+xml'), ('xml', 'application/xml')]:
        ET.SubElement(content, 'Default', Extension=ext, ContentType=kind)
    for part, kind in [('workbook.xml', 'sheet.main+xml'), ('styles.xml', 'styles+xml')]:
        ET.SubElement(content, 'Override', PartName=f'/xl/{part}', ContentType=f'application/vnd.openxmlformats-officedocument.spreadsheetml.{kind}')
    workbook = ET.Element('workbook', xmlns=MAIN)
    sheet_list = ET.SubElement(workbook, 'sheets')
    relationships = ET.Element('Relationships', xmlns=REL)
    package = ET.Element('Relationships', xmlns=REL)
    ET.SubElement(package, 'Relationship', Id='rId1', Type=f'{OFFICE_REL}/officeDocument', Target='xl/workbook.xml')
    ET.SubElement(relationships, 'Relationship', Id='style', Type=f'{OFFICE_REL}/styles', Target='styles.xml')
    temp_path = None
    try:
        with NamedTemporaryFile(dir=path.parent, suffix='.tmp', delete=False) as temporary:
            temp_path = Path(temporary.name)
        with ZipFile(temp_path, 'w', ZIP_DEFLATED) as archive:
            for index, (name, rows) in enumerate(sheets.items(), 1):
                ET.SubElement(sheet_list, 'sheet', name=name, sheetId=str(index), attrib={f'{{{OFFICE_REL}}}id': f'rId{index}'})
                ET.SubElement(relationships, 'Relationship', Id=f'rId{index}', Type=f'{OFFICE_REL}/worksheet', Target=f'worksheets/sheet{index}.xml')
                ET.SubElement(content, 'Override', PartName=f'/xl/worksheets/sheet{index}.xml', ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml')
                archive.writestr(f'xl/worksheets/sheet{index}.xml', _sheet(rows))
            archive.writestr('[Content_Types].xml', _xml(content))
            archive.writestr('_rels/.rels', _xml(package))
            archive.writestr('xl/workbook.xml', _xml(workbook))
            archive.writestr('xl/_rels/workbook.xml.rels', _xml(relationships))
            archive.writestr('xl/styles.xml', STYLES)
        temp_path.replace(path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
