"""Supplier identity only; no store operations. Codes and store ownership immutable."""
import re
from sqlalchemy import select,insert,update
from sqlalchemy.exc import IntegrityError
from app.models import Brand,Store,SourceEvent
from app.services.quality_rules import rule_connection
from app.services.quality_execution import RunError


def fail(code,message,status=422):raise RunError(status,code,message)


def supplier_map(c):
    return {r['store_id']:dict(r) for r in c.execute(select(Store.id.label('store_id'),Store.code.label('store_code'),
        Store.name.label('store_name'),Store.is_active.label('store_active'),Brand.id.label('brand_id'),
        Brand.code.label('brand_code'),Brand.name.label('brand_name'),Brand.is_active.label('brand_active'))
        .join(Brand,Brand.id==Store.brand_id)).mappings()}


def active_store(c,store_id):
    # Locks serialize assigning a supplier against deactivation.
    row=c.execute(select(Store,Brand.is_active.label('brand_active')).join(Brand).where(Store.id==store_id).with_for_update()).mappings().first()
    if not row:fail('STORE_NOT_FOUND','Không tìm thấy cửa hàng cung cấp.')
    if not row['is_active'] or not row['brand_active']:fail('STORE_INACTIVE','Cửa hàng hoặc thương hiệu đã ngưng hoạt động; chọn nguồn đang hoạt động.')
    return row


def event(c,scope,identifier,before,after,actor):
    c.execute(insert(SourceEvent).values(**{scope+'_id':identifier},before=before,after=after,actor_id=actor['user_id'] if actor else None))


def catalog():
    with rule_connection() as c:
        return dict(brands=[dict(r) for r in c.execute(select(Brand).order_by(Brand.code)).mappings()],stores=list(supplier_map(c).values()))


def save(kind,data,actor,identifier=None):
    model=Brand if kind=='brand' else Store
    values=dict(data)
    if identifier is None:
        values['code']=values['code'].strip().upper()
        if not re.fullmatch(r'[A-Z0-9][A-Z0-9_-]{0,49}',values['code']):fail('INVALID_SOURCE_CODE','Mã gồm 1–50 ký tự chữ Latin, số, gạch dưới hoặc gạch nối.')
    if 'name' in values:
        values['name']=values['name'].strip()
        if not values['name'] or len(values['name'])>200 or '\x00' in values['name']:fail('INVALID_SOURCE_NAME','Tên nguồn phải có nội dung, tối đa 200 ký tự và không chứa NUL.')
    try:
        with rule_connection() as c:
            before=None
            if identifier is not None:
                row=c.execute(select(model).where(model.id==identifier).with_for_update()).mappings().first()
                if not row:fail('SOURCE_NOT_FOUND','Không tìm thấy nguồn cung cấp.',404)
                before=dict(row)
            if kind=='store' and identifier is None:
                if not c.execute(select(Brand.id).where(Brand.id==values['brand_id'],Brand.is_active).with_for_update()).first():fail('BRAND_INACTIVE','Chọn thương hiệu đang hoạt động.')
            if identifier is None:identifier=c.execute(insert(model).values(**values).returning(model.id)).scalar_one()
            else:c.execute(update(model).where(model.id==identifier).values(**values))
            after=dict(c.execute(select(model).where(model.id==identifier)).mappings().one())
            event(c,kind,identifier,before,after,actor)
            return after
    except IntegrityError:fail('SOURCE_CODE_EXISTS','Mã nguồn đã tồn tại; mã không phân biệt chữ hoa/thường.',409)


def history():
    with rule_connection() as c:
        return [dict(r) for r in c.execute(select(SourceEvent).order_by(SourceEvent.id.desc()).limit(100)).mappings()]
