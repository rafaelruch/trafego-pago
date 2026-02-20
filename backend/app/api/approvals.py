"""
Fila de aprovações — gerencia sugestões de otimização criadas pela IA.
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.models.database import get_db
from app.models.user import User
from app.models.approval import Approval, ApprovalStatus
from app.schemas.approval import ApprovalOut, ApprovalDecision
from app.services.optimization_service import execute_approved_action

router = APIRouter()


@router.get("", response_model=List[ApprovalOut], summary="Listar aprovações")
def list_approvals(
    status: Optional[str] = Query(None, description="Filtrar por status: pending, approved, rejected, executed"),
    limit: int = Query(50, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna a fila de sugestões de otimização da IA."""
    query = db.query(Approval).filter(Approval.user_id == current_user.id)
    if status:
        query = query.filter(Approval.status == status)
    return query.order_by(Approval.created_at.desc()).limit(limit).all()


@router.get("/pending/count", summary="Contador de aprovações pendentes")
def count_pending(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna o número de sugestões aguardando aprovação (para badge no menu)."""
    count = (
        db.query(Approval)
        .filter(Approval.user_id == current_user.id, Approval.status == ApprovalStatus.PENDING)
        .count()
    )
    return {"pending": count}


@router.get("/{approval_id}", response_model=ApprovalOut, summary="Detalhe de uma aprovação")
def get_approval(
    approval_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    approval = db.query(Approval).filter(
        Approval.id == approval_id, Approval.user_id == current_user.id
    ).first()
    if not approval:
        raise HTTPException(404, "Aprovação não encontrada")
    return approval


@router.post("/{approval_id}/approve", summary="Aprovar e executar ação")
def approve_action(
    approval_id: int,
    decision: ApprovalDecision = ApprovalDecision(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Aprova a sugestão da IA e executa a ação imediatamente via Meta API.
    """
    approval = db.query(Approval).filter(
        Approval.id == approval_id, Approval.user_id == current_user.id
    ).first()
    if not approval:
        raise HTTPException(404, "Aprovação não encontrada")
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(400, f"Esta ação já foi {approval.status}")

    approval.status = ApprovalStatus.APPROVED
    approval.decided_at = datetime.utcnow()
    db.commit()

    # Executa a ação via Meta API
    result = execute_approved_action(approval=approval, db=db)

    if result["success"]:
        return {"message": result["message"], "status": "executed"}
    else:
        return {"message": f"Aprovado mas falhou ao executar: {result['error']}", "status": "failed"}


@router.post("/{approval_id}/reject", summary="Rejeitar sugestão")
def reject_action(
    approval_id: int,
    decision: ApprovalDecision = ApprovalDecision(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rejeita a sugestão da IA sem executar nenhuma ação."""
    approval = db.query(Approval).filter(
        Approval.id == approval_id, Approval.user_id == current_user.id
    ).first()
    if not approval:
        raise HTTPException(404, "Aprovação não encontrada")
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(400, f"Esta ação já foi {approval.status}")

    approval.status = ApprovalStatus.REJECTED
    approval.decided_at = datetime.utcnow()
    if decision.notes:
        approval.execution_result = f"Rejeitado: {decision.notes}"
    db.commit()

    return {"message": "Sugestão rejeitada com sucesso"}


@router.post("/bulk/approve", summary="Aprovar múltiplas sugestões")
def bulk_approve(
    approval_ids: List[int],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aprova e executa múltiplas sugestões de uma vez."""
    results = []
    for approval_id in approval_ids:
        approval = db.query(Approval).filter(
            Approval.id == approval_id,
            Approval.user_id == current_user.id,
            Approval.status == ApprovalStatus.PENDING,
        ).first()
        if not approval:
            results.append({"id": approval_id, "status": "not_found"})
            continue

        approval.status = ApprovalStatus.APPROVED
        approval.decided_at = datetime.utcnow()
        db.commit()

        result = execute_approved_action(approval=approval, db=db)
        results.append({
            "id": approval_id,
            "status": "executed" if result["success"] else "failed",
            "message": result.get("message") or result.get("error"),
        })

    return {"results": results}
