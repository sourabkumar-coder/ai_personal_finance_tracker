from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database.database import get_db
from app.database.models import Student, SplitGroup, GroupMember, SplitBill, SplitSettlement
from app.schemas.split_bill import (
    GroupMemberCreate,
    GroupMemberResponse,
    SplitGroupCreate,
    SplitGroupResponse,
    SplitBillCreate,
    SplitBillResponse,
    SplitBillShareResponse,
    SplitSettlementCreate,
    SplitSettlementResponse,
    SplitBalanceSummary,
)
from app.services.split_bill_service import SplitBillService
from app.utils.auth import get_current_student

router = APIRouter(prefix="/api/split-bills", tags=["Split Bills"])


@router.post("/groups", response_model=SplitGroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
    group_in: SplitGroupCreate,
    db: Session = Depends(get_db),
    current_student: Optional[Student] = Depends(get_current_student),
):
    """Create a new split expense group (e.g. Roommates, Trip, Canteen Squad)."""
    if current_student and group_in.student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")

    group = SplitBillService.create_group(db, group_in)
    return SplitGroupResponse(
        id=group.id,
        student_id=group.student_id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        members=[GroupMemberResponse.model_validate(m) for m in group.members],
        bills_count=0,
        total_spend=0.0,
    )


@router.get("/groups/{student_id}", response_model=List[SplitGroupResponse])
def get_student_groups(
    student_id: int,
    db: Session = Depends(get_db),
    current_student: Optional[Student] = Depends(get_current_student),
):
    """List all split groups created by or associated with the student."""
    if current_student and student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")

    groups = db.query(SplitGroup).filter(SplitGroup.student_id == student_id).order_by(desc(SplitGroup.created_at)).all()
    res = []
    for g in groups:
        total_spend = sum(b.total_amount for b in g.bills) if g.bills else 0.0
        res.append(
            SplitGroupResponse(
                id=g.id,
                student_id=g.student_id,
                name=g.name,
                description=g.description,
                created_at=g.created_at,
                members=[GroupMemberResponse.model_validate(m) for m in g.members],
                bills_count=len(g.bills),
                total_spend=round(total_spend, 2),
            )
        )
    return res


@router.get("/groups/{group_id}/details", response_model=SplitGroupResponse)
def get_group_details(
    group_id: int,
    db: Session = Depends(get_db),
    current_student: Optional[Student] = Depends(get_current_student),
):
    """Get single group details with members and total spend."""
    group = db.query(SplitGroup).filter(SplitGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Group {group_id} not found.")

    if current_student and group.student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")

    total_spend = sum(b.total_amount for b in group.bills) if group.bills else 0.0
    return SplitGroupResponse(
        id=group.id,
        student_id=group.student_id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        members=[GroupMemberResponse.model_validate(m) for m in group.members],
        bills_count=len(group.bills),
        total_spend=round(total_spend, 2),
    )


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_student: Optional[Student] = Depends(get_current_student),
):
    """Delete a split group and all associated members and bills."""
    group = db.query(SplitGroup).filter(SplitGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Group {group_id} not found.")

    if current_student and group.student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")

    db.delete(group)
    db.commit()
    return None


@router.post("/groups/{group_id}/members", response_model=GroupMemberResponse, status_code=status.HTTP_201_CREATED)
def add_group_member(
    group_id: int,
    member_in: GroupMemberCreate,
    db: Session = Depends(get_db),
    current_student: Optional[Student] = Depends(get_current_student),
):
    """Add a friend/roommate to an existing split group."""
    group = db.query(SplitGroup).filter(SplitGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Group {group_id} not found.")

    if current_student and group.student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")

    member = SplitBillService.add_member(db, group_id, member_in)
    return GroupMemberResponse.model_validate(member)


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_group_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_student: Optional[Student] = Depends(get_current_student),
):
    """Remove a member from a group."""
    member = db.query(GroupMember).filter(GroupMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Member {member_id} not found.")

    if current_student and member.group.student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")

    db.delete(member)
    db.commit()
    return None


@router.post("/bills", response_model=SplitBillResponse, status_code=status.HTTP_201_CREATED)
def create_split_bill(
    bill_in: SplitBillCreate,
    db: Session = Depends(get_db),
    current_student: Optional[Student] = Depends(get_current_student),
):
    """
    Log a shared bill. Automatically splits among participants (Equal or Exact)
    and optionally auto-syncs the student's personal share to their Personal Expenses.
    """
    if current_student and bill_in.student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")

    bill = SplitBillService.create_split_bill(db, bill_in)

    # Calculate user's share for response
    student = db.query(Student).filter(Student.id == bill.student_id).first()
    student_identifiers = {"you", student.name.lower() if student else "", "self"}
    user_share = 0.0
    for s in bill.shares:
        if s.member_name.lower() in student_identifiers:
            user_share = s.share_amount
            break

    payer_lower = bill.payer_name.lower()
    if payer_lower in student_identifiers:
        net_impact = bill.total_amount - user_share  # others owe you this
    else:
        net_impact = -user_share  # you owe payer this

    return SplitBillResponse(
        id=bill.id,
        student_id=bill.student_id,
        group_id=bill.group_id,
        group_name=bill.group.name if bill.group else None,
        title=bill.title,
        total_amount=bill.total_amount,
        category=bill.category,
        date=bill.date,
        payer_name=bill.payer_name,
        payer_member_id=bill.payer_member_id,
        split_type=bill.split_type,
        notes=bill.notes,
        synced_expense_id=bill.synced_expense_id,
        created_at=bill.created_at,
        shares=[SplitBillShareResponse.model_validate(s) for s in bill.shares],
        your_share=round(user_share, 2),
        your_net_impact=round(net_impact, 2),
    )


@router.get("/bills/{student_id}", response_model=List[SplitBillResponse])
def get_split_bills(
    student_id: int,
    group_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_student: Optional[Student] = Depends(get_current_student),
):
    """List split bills for a student, optionally filtered by group."""
    if current_student and student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")

    student = db.query(Student).filter(Student.id == student_id).first()
    query = db.query(SplitBill).filter(SplitBill.student_id == student_id)
    if group_id:
        query = query.filter(SplitBill.group_id == group_id)
    bills = query.order_by(desc(SplitBill.date), desc(SplitBill.created_at)).all()

    student_identifiers = {"you", student.name.lower() if student else "", "self"}
    res = []
    for b in bills:
        user_share = 0.0
        for s in b.shares:
            if s.member_name.lower() in student_identifiers:
                user_share = s.share_amount
                break

        payer_lower = b.payer_name.lower()
        if payer_lower in student_identifiers:
            net_impact = b.total_amount - user_share
        else:
            net_impact = -user_share

        res.append(
            SplitBillResponse(
                id=b.id,
                student_id=b.student_id,
                group_id=b.group_id,
                group_name=b.group.name if b.group else None,
                title=b.title,
                total_amount=b.total_amount,
                category=b.category,
                date=b.date,
                payer_name=b.payer_name,
                payer_member_id=b.payer_member_id,
                split_type=b.split_type,
                notes=b.notes,
                synced_expense_id=b.synced_expense_id,
                created_at=b.created_at,
                shares=[SplitBillShareResponse.model_validate(s) for s in b.shares],
                your_share=round(user_share, 2),
                your_net_impact=round(net_impact, 2),
            )
        )
    return res


@router.delete("/bills/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_split_bill(
    bill_id: int,
    student_id: int = Query(...),
    db: Session = Depends(get_db),
    current_student: Optional[Student] = Depends(get_current_student),
):
    """Delete a split bill and automatically delete any synced personal expense."""
    if current_student and student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")

    SplitBillService.delete_split_bill(db, bill_id, student_id)
    return None


@router.get("/balances/{student_id}", response_model=SplitBalanceSummary)
def get_split_balances(
    student_id: int,
    group_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_student: Optional[Student] = Depends(get_current_student),
):
    """
    Get consolidated net balances: Total Owed to You, Total You Owe,
    and a per-friend ledger with pre-filled WhatsApp and UPI settle deep links.
    """
    if current_student and student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")

    return SplitBillService.calculate_balances(db, student_id, group_id)


@router.post("/settle", response_model=SplitSettlementResponse, status_code=status.HTTP_201_CREATED)
def record_settlement(
    settlement_in: SplitSettlementCreate,
    db: Session = Depends(get_db),
    current_student: Optional[Student] = Depends(get_current_student),
):
    """Record a debt settlement payment between the student and a friend."""
    if current_student and settlement_in.student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")

    settlement = SplitBillService.record_settlement(db, settlement_in)
    return SplitSettlementResponse(
        id=settlement.id,
        student_id=settlement.student_id,
        group_id=settlement.group_id,
        group_name=settlement.group.name if settlement.group else None,
        from_name=settlement.from_name,
        to_name=settlement.to_name,
        amount=settlement.amount,
        payment_method=settlement.payment_method,
        settlement_date=settlement.settlement_date,
        notes=settlement.notes,
        created_at=settlement.created_at,
    )


@router.get("/settlements/{student_id}", response_model=List[SplitSettlementResponse])
def get_settlements(
    student_id: int,
    group_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_student: Optional[Student] = Depends(get_current_student),
):
    """Get history of recorded settlements."""
    if current_student and student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")

    query = db.query(SplitSettlement).filter(SplitSettlement.student_id == student_id)
    if group_id:
        query = query.filter(SplitSettlement.group_id == group_id)
    settlements = query.order_by(desc(SplitSettlement.settlement_date), desc(SplitSettlement.created_at)).all()

    return [
        SplitSettlementResponse(
            id=s.id,
            student_id=s.student_id,
            group_id=s.group_id,
            group_name=s.group.name if s.group else None,
            from_name=s.from_name,
            to_name=s.to_name,
            amount=s.amount,
            payment_method=s.payment_method,
            settlement_date=s.settlement_date,
            notes=s.notes,
            created_at=s.created_at,
        )
        for s in settlements
    ]


@router.delete("/settlements/{settlement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_settlement(
    settlement_id: int,
    student_id: int = Query(...),
    db: Session = Depends(get_db),
    current_student: Optional[Student] = Depends(get_current_student),
):
    """Delete a recorded settlement."""
    if current_student and student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")

    settlement = db.query(SplitSettlement).filter(
        SplitSettlement.id == settlement_id,
        SplitSettlement.student_id == student_id,
    ).first()
    if not settlement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Settlement {settlement_id} not found.")

    db.delete(settlement)
    db.commit()
    return None

