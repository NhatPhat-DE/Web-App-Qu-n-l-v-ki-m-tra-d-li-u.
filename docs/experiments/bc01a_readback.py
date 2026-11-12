"""Independent readback tool only. Requires openpyxl in the isolated reader venv."""
import json
from pathlib import Path
from datetime import datetime
import openpyxl

root=Path('backend/samples/bc01a')
proof=[]
for path in sorted(root.glob('*.xlsx')):
    data=json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
    book=openpyxl.load_workbook(path,data_only=False)
    assert book.sheetnames==['Tổng quan','Chi tiết lỗi','Quy tắc đã áp dụng']
    for sheet in book:
        assert sheet.freeze_panes=='A2' and sheet.column_dimensions['A'].width>10
        assert sheet['A1'].font.bold and sheet['A1'].alignment.wrap_text
        assert sheet['A1'].fill.fgColor.rgb=='FF174F56'
        for row in sheet:
            for cell in row:
                assert cell.data_type!='f' and cell.hyperlink is None
                if cell.value is not None:
                    assert cell.data_type=='s' and cell.number_format=='@' and cell.alignment.wrap_text
    errors=book['Chi tiết lỗi'];rules=book['Quy tắc đã áp dụng']
    assert errors.auto_filter.ref and rules.auto_filter.ref
    assert errors.max_row==max(1,len(data['violations']))+1 and rules.max_row==len(data['rule_snapshot'])+1
    for row,item in zip(errors.iter_rows(min_row=2,values_only=True),data['violations']):
        assert row[0]==str(item['row_number']) and json.loads(row[3])==item['columns'] and json.loads(row[4])==item['values']
        assert row[6:8]==(item['error_code'],item['message'])
    assert [json.loads(row[5]) for row in rules.iter_rows(min_row=2,values_only=True)]==[r['config'] for r in data['rule_snapshot']]
    overview={a.value:b.value for a,b in book['Tổng quan'].iter_rows(min_row=2,max_col=2)}
    assert datetime.fromisoformat(overview['Thời điểm xuất']).utcoffset() is not None
    proof.append({'file':path.name,'sheets':book.sheetnames,'violation_rows':len(data['violations']),'all_nonblank_cells_text':True,'no_formulas_or_hyperlinks':True,'freeze_wrap_filters_widths_verified':True})
    book.close()
assert len(proof)==5
(root/'library_readback.json').write_text(json.dumps({'tool':'openpyxl '+openpyxl.__version__+' (isolated verification environment only)','manual_excel_or_libreoffice':False,'results':proof},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PASS: openpyxl independently reopened all5 final HTTP workbooks; sheets/rows/values/config/text/no formulas/styles/timezone verified. No manual Excel/LibreOffice test.')
