from typing import List, Dict, Any, Optional
from datetime import date
from urllib.parse import quote
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.models import (
    Student,
    Expense,
    SplitGroup,
    GroupMember,
    SplitBill,
    SplitBillShare,
    SplitSettlement,
)
from app.schemas.split_bill import (
    GroupMemberCreate,
    SplitGroupCreate,
    SplitBillCreate,
    SplitSettlementCreate,
    SplitBalanceSummary,
    FriendBalance,
)


class SplitBillService:
    @staticmethod
    def create_group(db: Session, group_in: SplitGroupCreate) -> SplitGroup:
        student = db.query(Student).filter(Student.id == group_in.student_id).first()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student {group_in.student_id} not found.",
            )

        group = SplitGroup(
            student_id=group_in.student_id,
            name=group_in.name,
            description=group_in.description,
        )
        db.add(group)
        db.commit()
        db.refresh(group)

        # Add initial members if provided
        if group_in.initial_members:
            for m in group_in.initial_members:
                if m.name.strip():
                    member = GroupMember(
                        group_id=group.id,
                        name=m.name.strip(),
                        email=m.email.strip() if m.email else None,
                        upi_id=m.upi_id.strip() if m.upi_id else None,
                        student_id=m.student_id,
                    )
                    db.add(member)
            db.commit()
            db.refresh(group)

        return group

    @staticmethod
    def add_member(db: Session, group_id: int, member_in: GroupMemberCreate) -> GroupMember:
        group = db.query(SplitGroup).filter(SplitGroup.id == group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group {group_id} not found.",
            )

        member = GroupMember(
            group_id=group_id,
            name=member_in.name.strip(),
            email=member_in.email.strip() if member_in.email else None,
            upi_id=member_in.upi_id.strip() if member_in.upi_id else None,
            student_id=member_in.student_id,
        )
        db.add(member)
        db.commit()
        db.refresh(member)
        return member

    @staticmethod
    def create_split_bill(db: Session, bill_in: SplitBillCreate) -> SplitBill:
        student = db.query(Student).filter(Student.id == bill_in.student_id).first()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student {bill_in.student_id} not found.",
            )

        if bill_in.group_id:
            group = db.query(SplitGroup).filter(SplitGroup.id == bill_in.group_id).first()
            if not group:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Group {bill_in.group_id} not found.",
                )

        if not bill_in.shares:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one participant share must be specified.",
            )

        # Calculate shares
        total_amount = round(bill_in.total_amount, 2)
        shares_to_create = []

        if bill_in.split_type == "EXACT":
            sum_shares = sum(round(s.share_amount or 0.0, 2) for s in bill_in.shares)
            if abs(sum_shares - total_amount) > 0.05:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Sum of shares (₹{sum_shares:.2f}) does not match total bill amount (₹{total_amount:.2f}).",
                )
            for s in bill_in.shares:
                shares_to_create.append({
                    "member_name": s.member_name.strip(),
                    "member_id": s.member_id,
                    "share_amount": round(s.share_amount or 0.0, 2),
                })
        else:
            # EQUAL split
            n = len(bill_in.shares)
            equal_amount = round(total_amount / n, 2)
            running_sum = 0.0
            for i, s in enumerate(bill_in.shares):
                # Adjust last share for 1 cent rounding differences
                if i == n - 1:
                    amt = round(total_amount - running_sum, 2)
                else:
                    amt = equal_amount
                    running_sum += amt
                shares_to_create.append({
                    "member_name": s.member_name.strip(),
                    "member_id": s.member_id,
                    "share_amount": amt,
                })

        # Create the bill
        bill = SplitBill(
            student_id=bill_in.student_id,
            group_id=bill_in.group_id,
            title=bill_in.title.strip(),
            total_amount=total_amount,
            category=bill_in.category.strip(),
            date=bill_in.date,
            payer_name=bill_in.payer_name.strip(),
            payer_member_id=bill_in.payer_member_id,
            split_type=bill_in.split_type,
            notes=bill_in.notes.strip() if bill_in.notes else None,
        )
        db.add(bill)
        db.commit()
        db.refresh(bill)

        # Create shares
        for sc in shares_to_create:
            share = SplitBillShare(
                bill_id=bill.id,
                member_id=sc["member_id"],
                member_name=sc["member_name"],
                share_amount=sc["share_amount"],
            )
            db.add(share)
        db.commit()

        # Handle Expense Auto-Sync:
        # If user elected to sync to personal expenses, find user's personal share
        if bill_in.sync_to_expenses:
            user_share = 0.0
            for sc in shares_to_create:
                name_lower = sc["member_name"].lower()
                if name_lower in ("you", student.name.lower(), "self"):
                    user_share = sc["share_amount"]
                    break

            if user_share > 0:
                group_tag = f" in {bill.group.name}" if bill.group else ""
                expense = Expense(
                    student_id=student.id,
                    title=f"[Split] {bill.title} (Your Share)",
                    amount=user_share,
                    category=bill.category,
                    date=bill.date,
                    payment_method="UPI",
                    notes=f"Your share for split bill '{bill.title}'{group_tag}. Total bill: ₹{total_amount:.2f}.",
                    transaction_type="EXPENSE",
                    split_bill_id=bill.id,
                )
                db.add(expense)
                db.commit()
                db.refresh(expense)

                bill.synced_expense_id = expense.id
                db.commit()

        db.refresh(bill)
        return bill

    @staticmethod
    def delete_split_bill(db: Session, bill_id: int, student_id: int):
        bill = db.query(SplitBill).filter(
            SplitBill.id == bill_id,
            SplitBill.student_id == student_id,
        ).first()

        if not bill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Split bill {bill_id} not found.",
            )

        # Clean up synced expense if it exists
        if bill.synced_expense_id:
            db.query(Expense).filter(Expense.id == bill.synced_expense_id).delete()

        db.delete(bill)
        db.commit()

    @staticmethod
    def calculate_balances(
        db: Session,
        student_id: int,
        group_id: Optional[int] = None,
    ) -> SplitBalanceSummary:
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student {student_id} not found.",
            )

        # Query bills
        bills_query = db.query(SplitBill).filter(SplitBill.student_id == student_id)
        if group_id:
            bills_query = bills_query.filter(SplitBill.group_id == group_id)
        bills = bills_query.all()

        # Query settlements
        settlements_query = db.query(SplitSettlement).filter(SplitSettlement.student_id == student_id)
        if group_id:
            settlements_query = settlements_query.filter(SplitSettlement.group_id == group_id)
        settlements = settlements_query.all()

        # Build ledger for each friend:
        # key: lower-cased canonical friend name
        # ledger[key] = { "name": original_name, "owed_to_you": 0.0, "you_owe": 0.0, "group_id": ..., "group_name": ..., "upi_id": ... }
        friends_ledger: Dict[str, Dict[str, Any]] = {}

        # Preload members to get UPI IDs and groups
        members_query = db.query(GroupMember).join(SplitGroup).filter(SplitGroup.student_id == student_id)
        if group_id:
            members_query = members_query.filter(GroupMember.group_id == group_id)
        members = members_query.all()

        student_identifiers = {"you", student.name.lower() if student else "", "self"}
        if student and student.name:
            for part in student.name.lower().split():
                if len(part) > 1:
                    student_identifiers.add(part)

        for m in members:
            key = m.name.strip()
            key_lower = key.lower()
            if key_lower not in student_identifiers:
                if key_lower not in friends_ledger:
                    friends_ledger[key_lower] = {
                        "name": key,
                        "group_id": m.group_id,
                        "group_name": m.group.name if m.group else None,
                        "upi_id": m.upi_id,
                        "owed_to_you": 0.0,
                        "you_owe": 0.0,
                    }
                elif m.upi_id and not friends_ledger[key_lower]["upi_id"]:
                    friends_ledger[key_lower]["upi_id"] = m.upi_id

        for bill in bills:
            payer_name = bill.payer_name.strip()
            payer_lower = payer_name.lower()
            student_paid = payer_lower in student_identifiers

            for share in bill.shares:
                member_name = share.member_name.strip()
                member_lower = member_name.lower()

                if student_paid:
                    # Student paid the bill:
                    # If this share belongs to a friend, friend owes student
                    if member_lower not in student_identifiers:
                        if member_lower not in friends_ledger:
                            friends_ledger[member_lower] = {
                                "name": member_name,
                                "group_id": bill.group_id,
                                "group_name": bill.group.name if bill.group else None,
                                "upi_id": None,
                                "owed_to_you": 0.0,
                                "you_owe": 0.0,
                            }
                        friends_ledger[member_lower]["owed_to_you"] += share.share_amount
                else:
                    # Friend paid the bill:
                    # If this share belongs to the student, student owes the payer
                    if member_lower in student_identifiers:
                        if payer_lower not in friends_ledger:
                            friends_ledger[payer_lower] = {
                                "name": payer_name,
                                "group_id": bill.group_id,
                                "group_name": bill.group.name if bill.group else None,
                                "upi_id": None,
                                "owed_to_you": 0.0,
                                "you_owe": 0.0,
                            }
                        friends_ledger[payer_lower]["you_owe"] += share.share_amount

        # Backfill any known member upi_ids into bills where upi_id was not yet set
        for m in members:
            m_lower = m.name.strip().lower()
            if m_lower in friends_ledger and m.upi_id and not friends_ledger[m_lower]["upi_id"]:
                friends_ledger[m_lower]["upi_id"] = m.upi_id

        # Apply settlements
        for s in settlements:
            from_name = s.from_name.strip()
            from_lower = from_name.lower()
            to_name = s.to_name.strip()
            to_lower = to_name.lower()

            if from_lower not in student_identifiers and to_lower in student_identifiers:
                # Friend paid student
                if from_lower in friends_ledger:
                    friends_ledger[from_lower]["owed_to_you"] -= s.amount
                else:
                    friends_ledger[from_lower] = {
                        "name": from_name,
                        "group_id": s.group_id,
                        "group_name": s.group.name if s.group else None,
                        "upi_id": None,
                        "owed_to_you": -s.amount,
                        "you_owe": 0.0,
                    }
            elif from_lower in student_identifiers and to_lower not in student_identifiers:
                # Student paid friend
                if to_lower in friends_ledger:
                    friends_ledger[to_lower]["you_owe"] -= s.amount
                else:
                    friends_ledger[to_lower] = {
                        "name": to_name,
                        "group_id": s.group_id,
                        "group_name": s.group.name if s.group else None,
                        "upi_id": None,
                        "owed_to_you": 0.0,
                        "you_owe": -s.amount,
                    }

        friend_balances: List[FriendBalance] = []
        total_owed_to_you = 0.0
        total_you_owe = 0.0

        for key_lower, data in friends_ledger.items():
            display_name = data["name"]
            owed = round(data["owed_to_you"], 2)
            owe = round(data["you_owe"], 2)
            net = round(owed - owe, 2)

            if net > 0.01:
                status_str = "OWED_TO_YOU"
                total_owed_to_you += net
                upi_str = None
                wa_msg = f"Hey {display_name}, you have a pending split of ₹{net:.2f} for our shared expenses on SmartFinance. Please settle when you get a chance!"
            elif net < -0.01:
                status_str = "YOU_OWE"
                abs_net = abs(net)
                total_you_owe += abs_net
                upi_str = None
                if data["upi_id"]:
                    upi_str = f"upi://pay?pa={data['upi_id']}&pn={quote(display_name)}&am={abs_net:.2f}&cu=INR"
                wa_msg = f"Hey {display_name}, I owe you ₹{abs_net:.2f} for our shared expenses. Sending payment now!"
            else:
                status_str = "SETTLED"
                net = 0.0
                upi_str = None
                wa_msg = None

            friend_balances.append(
                FriendBalance(
                    name=display_name,
                    group_id=data["group_id"],
                    group_name=data["group_name"],
                    upi_id=data["upi_id"],
                    amount_owed_to_you=max(0.0, net) if net > 0 else 0.0,
                    amount_you_owe=abs(net) if net < 0 else 0.0,
                    net_balance=net,
                    status=status_str,
                    upi_link=upi_str,
                    whatsapp_message=wa_msg,
                )
            )

        # Sort so highest debts come first
        friend_balances.sort(key=lambda x: abs(x.net_balance), reverse=True)

        return SplitBalanceSummary(
            total_owed_to_you=round(total_owed_to_you, 2),
            total_you_owe=round(total_you_owe, 2),
            net_balance=round(total_owed_to_you - total_you_owe, 2),
            active_splits_count=len([f for f in friend_balances if f.status != "SETTLED"]),
            friends=friend_balances,
        )

    @staticmethod
    def record_settlement(
        db: Session,
        settlement_in: SplitSettlementCreate,
    ) -> SplitSettlement:
        student = db.query(Student).filter(Student.id == settlement_in.student_id).first()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student {settlement_in.student_id} not found.",
            )

        settlement = SplitSettlement(
            student_id=settlement_in.student_id,
            group_id=settlement_in.group_id,
            from_name=settlement_in.from_name.strip(),
            to_name=settlement_in.to_name.strip(),
            amount=round(settlement_in.amount, 2),
            payment_method=settlement_in.payment_method.strip(),
            settlement_date=settlement_in.settlement_date,
            notes=settlement_in.notes.strip() if settlement_in.notes else None,
        )
        db.add(settlement)
        db.commit()
        db.refresh(settlement)
        return settlement
