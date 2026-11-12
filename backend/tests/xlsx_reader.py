"""Read OOXML parts using the standard library; never execute formulas."""
from io import BytesIO
import re
import zipfile
from xml.etree import ElementTree as ET

NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def decoded(value):
    # One pass only: _x005F_x000D_ represents literal _x000D_, not a CR.
    return re.sub(r'_x([0-9a-fA-F]{4})_', lambda match: chr(int(match[1],16)), value)

def read_xlsx(content):
    with zipfile.ZipFile(BytesIO(content)) as archive:
        assert archive.testzip() is None
        workbook=ET.fromstring(archive.read('xl/workbook.xml'))
        styles=ET.fromstring(archive.read('xl/styles.xml'))
        formats=[int(item.attrib['numFmtId']) for item in styles.find('s:cellXfs',NS)]
        custom={int(item.attrib['numFmtId']):item.attrib['formatCode'] for item in styles.findall('s:numFmts/s:numFmt',NS)}
        sheets={}
        for index,sheet in enumerate(workbook.find('s:sheets',NS),1):
            xml=ET.fromstring(archive.read(f'xl/worksheets/sheet{index}.xml'))
            rows=[];types=[]
            for row in xml.findall('s:sheetData/s:row',NS):
                values=[]
                for cell in row:
                    assert cell.find('s:f',NS) is None
                    kind=cell.attrib.get('t');types.append(kind)
                    assert kind=='inlineStr',kind
                    number_format=formats[int(cell.attrib.get('s',0))]
                    assert number_format==49 or custom.get(number_format)=='@'
                    values.append(decoded(''.join(cell.find('s:is',NS).itertext())))
                rows.append(values)
            sheets[sheet.attrib['name']]={'rows':rows,'types':types,'xml':xml,'filter':xml.find('s:autoFilter',NS),'pane':xml.find('s:sheetViews/s:sheetView/s:pane',NS)}
        return sheets
