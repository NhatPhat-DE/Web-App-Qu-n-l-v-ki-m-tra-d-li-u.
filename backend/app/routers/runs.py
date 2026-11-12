import json
from fastapi import APIRouter, Query, Request, Path
import anyio
import threading
from app.services.pattern_worker import CANCEL_EVENT
from fastapi.responses import JSONResponse, Response
from fastapi.encoders import jsonable_encoder
from app.services.quality_execution import execute_run, RunError
from app.services import quality_history
from app.routers.datasets import catalog_response, error_response

router = APIRouter(tags=['quality runs'])


@router.get('/batch-dashboard')
def batch_dashboard(batch_id: list[int] | None = Query(None),brand_id:int|None=Query(None,ge=1),store_id:int|None=Query(None,ge=0)):
    from app.services.batch_dashboard import dashboard
    if batch_id and (len(batch_id) > 200 or any(i < 1 for i in batch_id)):
        return error_response(422, 'INVALID_BATCH_FILTER', 'Chọn tối đa 200 đợt hợp lệ.')
    return read_history(dashboard, batch_id,brand_id,store_id)


@router.post('/datasets/{dataset_id}/versions/{version_id}/runs', status_code=201)
async def run(dataset_id: int, version_id: int, request: Request):
    cancelled = threading.Event()
    context_token = CANCEL_EVENT.set(cancelled)
    async def watch_disconnect():
        while True:
            if await request.is_disconnected():
                cancelled.set()
                return
            await anyio.sleep(0.05)
    try:
        async with anyio.create_task_group() as group:
            group.start_soon(watch_disconnect)
            try:
                # AnyIO propagates contextvars and waits for thread cleanup on cancellation.
                return await anyio.to_thread.run_sync(execute_run, dataset_id, version_id)
            except RunError as error:
                payload = {'code': error.code, 'message': error.message}
                if error.run_id is not None:
                    payload['run_id'] = error.run_id
                    payload['failure_recorded'] = error.failure_recorded
                return JSONResponse(status_code=error.status, content={'error': payload})
            finally:
                cancelled.set()
                group.cancel_scope.cancel()
    finally:
        CANCEL_EVENT.reset(context_token)


def read_history(operation, *args, **kwargs):
    def invoke():
        try:
            return operation(*args, **kwargs)
        except RunError as error:
            return error_response(error.status, error.code, error.message)
    return catalog_response(invoke)


@router.get('/datasets/{dataset_id}/runs')
def history(dataset_id: int, version_id: int | None = Query(None, ge=1),
            batch_id: int | None = Query(None, ge=1),
            page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    return read_history(quality_history.list_runs, dataset_id, version_id, page, page_size, batch_id=batch_id)


@router.get('/datasets/{dataset_id}/run-comparison')
def comparison(dataset_id: int = Path(..., ge=1), a_run_id: int = Query(..., ge=1), b_run_id: int = Query(..., ge=1)):
    from app.services.quality_comparison import compare_runs
    return read_history(compare_runs, dataset_id, a_run_id, b_run_id)


@router.get('/datasets/{dataset_id}/runs/{run_id}')
def detail(dataset_id: int, run_id: int):
    return read_history(quality_history.run_detail, dataset_id, run_id)


@router.get('/datasets/{dataset_id}/runs/{run_id}/violations')
def violations(dataset_id: int, run_id: int, rule_id_snapshot: int | None = Query(None, ge=1),
               row_number: int | None = Query(None, ge=1), page: int = Query(1, ge=1),
               page_size: int = Query(20, ge=1, le=100)):
    return read_history(quality_history.list_violations, dataset_id, run_id, rule_id_snapshot, row_number, page, page_size)


@router.get('/datasets/{dataset_id}/runs/{run_id}/error-export-context')
def error_export_context(dataset_id:int,run_id:int):
    from app.services.error_export import context
    return read_history(context,dataset_id,run_id)


@router.get('/datasets/{dataset_id}/runs/{run_id}/quality-summary')
def summary(dataset_id: int = Path(..., ge=1), run_id: int = Path(..., ge=1),
            rule_page: int = Query(1, ge=1), column_page: int = Query(1, ge=1),
            page_size: int = Query(20, ge=1, le=100)):
    from app.services.quality_summary import quality_summary
    return read_history(quality_summary, dataset_id, run_id, rule_page, column_page, page_size)


@router.get('/datasets/{dataset_id}/runs/{run_id}/report')
def report(dataset_id: int, run_id: int):
    def download():
        data = quality_history.export_report(dataset_id, run_id)
        # Preserve the schema and logical values; change serialization only.
        return Response(content=json.dumps(jsonable_encoder(data), ensure_ascii=False, allow_nan=False, indent=2).encode('utf-8'), media_type='application/json', headers={
            'Content-Disposition': f'attachment; filename="dataset-{dataset_id}-run-{run_id}-report.json"'})
    return read_history(download)


@router.get('/datasets/{dataset_id}/quality-trend')
def trend(dataset_id: int, limit: int = Query(30,ge=1,le=100),version_id: int | None = Query(None,ge=1)):
    from app.services.quality_trend import quality_trend
    return read_history(quality_trend,dataset_id,limit,version_id)


@router.get('/datasets/{dataset_id}/runs/{run_id}/report.xlsx')
def report_excel(dataset_id: int, run_id: int):
    from app.services.report_excel import export_xlsx, XLSX_MIME
    def download():
        return Response(content=export_xlsx(dataset_id, run_id), media_type=XLSX_MIME, headers={
            'Content-Disposition': f'attachment; filename="dataset-{dataset_id}-run-{run_id}-report.xlsx"'})
    return read_history(download)
