"""Read-only completed-run trends and versioned snapshot fingerprints."""
import hashlib
import json
from decimal import Decimal, localcontext
from sqlalchemy import select,func
from app.models import Dataset,DatasetVersion,QualityRun
from app.services.dataset_catalog import catalog_connection,CatalogNotFound
from app.services.quality_execution import RunError
from app.services.quality_engine import _decimal, _validate_allowed_values_config, QualityInputError

FINGERPRINT_VERSION='rules-v1'
DATA_TYPE_FINGERPRINT_VERSION='rules-v2'


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def decimal_key(value):
    # Never normalize()/quantize(): both can round under Decimal context.
    if isinstance(value,bool) or not isinstance(value,(str,int)):raise ValueError()
    number=_decimal(value)
    if number is None:raise ValueError()
    sign,digits,exponent=number.as_tuple()
    if not any(digits):return [0,'0',0]
    end=len(digits)
    while digits[end-1]==0:end-=1;exponent+=1
    return [sign,''.join(str(digit) for digit in digits[:end]),exponent]


def fingerprint(snapshot):
    try:
        if not isinstance(snapshot,list):raise ValueError()
        rules=[]
        version=FINGERPRINT_VERSION
        for rule in snapshot:
            kind=rule['rule_type'];columns=rule['columns'];config=rule['config']
            if kind not in ('required','unique','numeric_range','data_type','date_format','allowed_values','pattern') or not isinstance(columns,list) or not columns or any(not isinstance(c,str) or not c for c in columns) or len(set(columns))!=len(columns):raise ValueError()
            if kind!='unique' and len(columns)!=1:raise ValueError()
            expected_keys={'min','max'} if kind=='numeric_range' else {'type'} if kind=='data_type' else {'format'} if kind=='date_format' else {'values'} if kind=='allowed_values' else {'pattern','dialect'} if kind=='pattern' else set()
            if not isinstance(config,dict) or (set(config)!=expected_keys and not (kind=='date_format' and set(config)=={'format','min','max'})):raise ValueError()
            if kind=='numeric_range':
                config_key={key:decimal_key(config[key]) for key in ('min','max')}
            elif kind=='data_type':
                if not isinstance(config['type'],str) or config['type'] not in ('integer','decimal','boolean'):raise ValueError()
                config_key={'type':config['type']}
                version=DATA_TYPE_FINGERPRINT_VERSION
            elif kind=='pattern':
                from app.services.pattern_dialect import validate_config
                validate_config(config)
                config_key={'pattern':config['pattern'],'dialect':config['dialect']}
                version=DATA_TYPE_FINGERPRINT_VERSION
            elif kind=='allowed_values':
                _validate_allowed_values_config(config)
                config_key={'values':sorted(config['values'])}
                version=DATA_TYPE_FINGERPRINT_VERSION
            elif kind=='date_format':
                from app.services.quality_engine import _validate_date_format_config
                _validate_date_format_config(config)
                if not isinstance(config['format'],str) or config['format'] not in ('YYYY-MM-DD','DD/MM/YYYY','MM/DD/YYYY'):raise ValueError()
                config_key=dict(config)
                version=DATA_TYPE_FINGERPRINT_VERSION
            else:config_key={}
            rules.append(canonical({'rule_type':kind,'columns':sorted(columns) if kind=='unique' else columns,'config':config_key}))
        # Legacy-only snapshots keep the exact rules-v1 canonical bytes, including
        # their numeric bounds. Select the version from the stored snapshot only.
        value=canonical({'algorithm':version,'rules':sorted(rules)})
        return version+':'+hashlib.sha256(value.encode('utf-8')).hexdigest()
    except (ValueError,TypeError,KeyError,UnicodeError,AttributeError,QualityInputError):
        raise RunError(500,'INVALID_RULE_SNAPSHOT','Snapshot quy tắc không hợp lệ; không thể so sánh cấu hình.') from None


def quality_trend(dataset_id,limit=30,version_id=None):
    with catalog_connection() as c:
        if c.execute(select(Dataset.id).where(Dataset.id==dataset_id)).first() is None:raise CatalogNotFound()
        if version_id is not None and c.execute(select(DatasetVersion.id).where(DatasetVersion.id==version_id,DatasetVersion.dataset_id==dataset_id)).first() is None:raise CatalogNotFound()
        predicate=[DatasetVersion.dataset_id==dataset_id,QualityRun.status=='completed']
        if version_id is not None:predicate.append(QualityRun.dataset_version_id==version_id)
        total=c.execute(select(func.count()).select_from(QualityRun).join(DatasetVersion).where(*predicate)).scalar_one()
        fields=[QualityRun.id.label('run_id'),QualityRun.dataset_version_id.label('version_id'),DatasetVersion.version_number,
                QualityRun.started_at,QualityRun.finished_at,QualityRun.engine_version,QualityRun.total_rows,
                QualityRun.error_row_count,QualityRun.violation_count,QualityRun.error_row_rate,QualityRun.rule_snapshot]
        rows=c.execute(select(*fields).join(DatasetVersion).where(*predicate).order_by(QualityRun.started_at.desc(),QualityRun.id.desc()).limit(limit)).mappings().all()
        points=[]
        for row in reversed(rows):
            point=dict(row);snapshot=point.pop('rule_snapshot');rate=point['error_row_rate']
            with localcontext() as ctx:
                ctx.prec=16
                point['error_row_rate']=format(rate,'.4f');point['pass_rate']=format(Decimal(100)-rate,'.4f')
            point['rule_count']=len(snapshot)
            point['rule_set_fingerprint']=fingerprint(snapshot)
            points.append(point)
        return {'dataset_id':dataset_id,'version_id':version_id,'limit':limit,'total_completed':total,'truncated':total>len(points),'points':points}
