"""Write endpoints: simulate updates, bulk move, pending queue, execute, discard."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...schemas.domain import WriteOperation
from ...schemas.requests import OperationIdsRequest, WriteBulkMoveRequest, WriteUpdateRequest
from ...services.issue_writer import IssueWriter
from ..deps import get_writer

router = APIRouter(prefix="/write", tags=["write"])


@router.post("/update", response_model=WriteOperation)
def simulate_update(
    req: WriteUpdateRequest, writer: IssueWriter = Depends(get_writer)
) -> WriteOperation:
    try:
        return writer.simulate_update(req.issue_key, req.field, req.new_value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/bulk", response_model=list[WriteOperation])
def bulk_move(
    req: WriteBulkMoveRequest, writer: IssueWriter = Depends(get_writer)
) -> list[WriteOperation]:
    try:
        return writer.move_to_sprint(req.issue_keys, req.sprint_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/pending", response_model=list[WriteOperation])
def get_pending(writer: IssueWriter = Depends(get_writer)) -> list[WriteOperation]:
    return writer.get_pending()


@router.post("/execute", response_model=list[WriteOperation])
def execute(
    req: OperationIdsRequest, writer: IssueWriter = Depends(get_writer)
) -> list[WriteOperation]:
    return writer.execute_pending(req.operation_ids)


@router.post("/discard")
def discard(req: OperationIdsRequest, writer: IssueWriter = Depends(get_writer)) -> dict:
    return {"discarded": writer.discard_pending(req.operation_ids)}
