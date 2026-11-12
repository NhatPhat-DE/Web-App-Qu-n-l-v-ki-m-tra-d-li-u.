from copy import deepcopy
import pytest
from app.services.type_inference import infer_types, TypeInferenceError


@pytest.mark.parametrize('values,kind,missing', [
    (['1','-2','+3',' 0 '], 'integer',0),
    (['0','1'], 'integer',0),
    (['001','2'], 'text',0), (['-001','-2'], 'text',0), (['+001'], 'text',0),
    (['001.5'], 'text',0), (['001e2'], 'text',0),
    (['0.100000000000000000001','1e-20',' 2 '], 'decimal',0),
    (['-2.5','+3E2','.1'], 'decimal',0),
    (['true','FALSE',' True '], 'boolean',0), (['true','1'], 'text',0),
    (['2024-02-29',' 2026-10-14 '], 'date',0),
    (['2026-02-29'], 'text',0), (['2026-13-01'], 'text',0), (['01/02/2026'], 'text',0),
    (['NaN','Infinity','-Infinity'], 'text',0),
    (['NULL','Tiếng Việt','日本語'], 'text',0),
    ([None,'',' \t'], 'unknown',3),
    (['1',None,'',' '], 'integer',3),
    (['2026-01-01','1'], 'text',0),
    (['1','text'], 'text',0), (['1,000','1_000'], 'text',0),
])
def test_written_answers(values,kind,missing):
    header=[' code '];rows=[[value] for value in values];before=deepcopy((header,rows))
    assert infer_types(header,rows)==[{'column_name':' code ','position':1,'inferred_type':kind,
                                      'non_missing_count':len(values)-missing,'missing_count':missing}]
    assert (header,rows)==before


def test_order_and_entire_dataset():
    header=['code','flag','date','empty']
    rows=[['1','true','2024-02-29',None]]*9999+[['not numeric','FALSE','2026-01-01',' ']]
    before=deepcopy((header,rows))
    assert infer_types(header,rows)==[
        {'column_name':'code','position':1,'inferred_type':'text','non_missing_count':10000,'missing_count':0},
        {'column_name':'flag','position':2,'inferred_type':'boolean','non_missing_count':10000,'missing_count':0},
        {'column_name':'date','position':3,'inferred_type':'date','non_missing_count':10000,'missing_count':0},
        {'column_name':'empty','position':4,'inferred_type':'unknown','non_missing_count':0,'missing_count':10000}]
    assert (header,rows)==before


@pytest.mark.parametrize('header,rows,code', [
    ([],[],'INVALID_HEADER'), ([' '],[['x']],'INVALID_HEADER'), (['a','a'],[['x','y']],'INVALID_HEADER'),
    (['a'],[['x','y']],'INVALID_ROW'), (['a'],[[]],'INVALID_ROW'), (['a'],None,'INVALID_ROWS'),
    (['a'],[[1]],'INVALID_VALUE'), (['a'],[[False]],'INVALID_VALUE')])
def test_invalid_structure(header,rows,code):
    with pytest.raises(TypeInferenceError) as caught: infer_types(header,rows)
    assert caught.value.code==code


def test_empty_rows_unknown():
    assert infer_types(['a'],[])==[{'column_name':'a','position':1,'inferred_type':'unknown','non_missing_count':0,'missing_count':0}]
