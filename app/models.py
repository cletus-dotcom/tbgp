import re
from datetime import datetime
from decimal import Decimal

from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.timeutil import manila_now, manila_today


def _money(value):
    if value is None:
        return None
    return round(float(value), 2)


_PHONE_RE = re.compile(r"\+?\d[\d\s\-()]{5,}\d")
_EMAIL_RE = re.compile(r"[^@\s|/,;]+@[^@\s|/,;]+\.[A-Za-z]{2,}")


def _first_phone(text):
    match = _PHONE_RE.search(text or "")
    if not match:
        return ""
    return re.sub(r"[^\d+]", "", match.group(0))


def _first_email(text):
    match = _EMAIL_RE.search(text or "")
    return match.group(0) if match else ""


class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120))
    role = db.Column(db.String(20), default="Admin")
    status = db.Column(db.String(20), default="Active")
    department = db.Column(db.String(40), nullable=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.member_id"), nullable=True)
    # Contractor-role logins: the portal contractor company they act for.
    contractor_id = db.Column(
        db.Integer, db.ForeignKey("contractors.contractor_id", ondelete="SET NULL"), nullable=True
    )
    # Supplier-role logins: the portal supplier company they act for.
    supplier_id = db.Column(
        db.Integer, db.ForeignKey("suppliers.supplier_id", ondelete="SET NULL"), nullable=True
    )
    comfort_text_size = db.Column(db.String(20), default="standard", nullable=False)
    comfort_high_contrast = db.Column(db.Boolean, default=False, nullable=False)

    linked_member = db.relationship("Member", foreign_keys=[member_id])
    linked_contractor = db.relationship("Contractor", foreign_keys=[contractor_id])
    linked_supplier = db.relationship("Supplier", foreign_keys=[supplier_id])
    duty_rows = db.relationship(
        "UserDuty", back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def duty_keys(self):
        return {row.duty for row in self.duty_rows}

    def has_duty(self, duty):
        return duty in self.duty_keys


class UserDuty(db.Model):
    """A work duty (e.g. Project Coordinator) held by a user on top of their login role."""

    __tablename__ = "user_duties"

    duty_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    duty = db.Column(db.String(40), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=manila_now)

    __table_args__ = (db.UniqueConstraint("user_id", "duty", name="uq_user_duties_user_duty"),)

    user = db.relationship("User", back_populates="duty_rows")


class Member(db.Model):
    __tablename__ = "members"

    member_id = db.Column(db.Integer, primary_key=True)
    batch = db.Column(db.Integer, nullable=False)
    referrer_id = db.Column(db.Integer, db.ForeignKey("members.member_id"), nullable=True)
    membership_type = db.Column(db.String(30))
    date_joined = db.Column(db.Date)
    last_name = db.Column(db.String(80), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    middle_name = db.Column(db.String(80))
    suffix = db.Column(db.String(20))
    address = db.Column(db.String(255))
    phone = db.Column(db.String(30))
    email = db.Column(db.String(120))
    birth_date = db.Column(db.Date)
    gender = db.Column(db.String(20))
    civil_status = db.Column(db.String(30))
    highest_education = db.Column(db.String(80))
    occupation_income_source = db.Column(db.String(120))
    monthly_income = db.Column(db.String(40))
    number_of_dependents = db.Column(db.Integer)
    beneficiary_name = db.Column(db.String(255))
    beneficiary_address = db.Column(db.String(255))
    beneficiary_phone = db.Column(db.String(120))
    status = db.Column(db.String(20), default="Active")
    termination_date = db.Column(db.Date)
    termination_type = db.Column(db.String(60))
    lifetime_cap_enabled = db.Column(db.Boolean, default=True)
    lifetime_cap_amount = db.Column(db.Numeric(14, 2), default=50000000)
    marketplace_share_code = db.Column(db.String(40), unique=True, nullable=True)
    gcash_number = db.Column(db.String(40))
    bank_account_number = db.Column(db.String(60))
    bank_name = db.Column(db.String(120))
    age = db.Column(db.Integer)
    id_picture_location = db.Column(db.String(500))
    beneficiary_relationship = db.Column(db.String(80))

    referrer = db.relationship("Member", remote_side=[member_id], backref="referrals")
    positions = db.relationship(
        "MemberPosition",
        backref="member",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def positions_by_department(self):
        """Map department name -> MemberPosition for this member."""
        return {row.department: row for row in self.positions}

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        name = " ".join(p for p in parts if p)
        if self.suffix:
            name = f"{name} {self.suffix}"
        return name.strip()

    def self_edit_payload(self):
        return {
            "member_id": self.member_id,
            "full_name": self.full_name,
            "batch": self.batch,
            "gender": self.gender or "",
            "civil_status": self.civil_status or "",
            "phone": self.phone or "",
            "email": self.email or "",
            "address": self.address or "",
            "highest_education": self.highest_education or "",
            "occupation_income_source": self.occupation_income_source or "",
            "monthly_income": self.monthly_income or "",
            "number_of_dependents": self.number_of_dependents,
            "beneficiary_name": self.beneficiary_name or "",
            "beneficiary_phone": self.beneficiary_phone or "",
            "beneficiary_address": self.beneficiary_address or "",
            "beneficiary_relationship": self.beneficiary_relationship or "",
            "gcash_number": self.gcash_number or "",
            "bank_account_number": self.bank_account_number or "",
            "bank_name": self.bank_name or "",
        }

    def edit_payload(self):
        return {
            "member_id": self.member_id,
            "batch": self.batch,
            "referrer_id": self.referrer_id,
            "membership_type": self.membership_type,
            "date_joined": self.date_joined.isoformat() if self.date_joined else "",
            "first_name": self.first_name,
            "middle_name": self.middle_name,
            "last_name": self.last_name,
            "suffix": self.suffix,
            "address": self.address,
            "phone": self.phone,
            "email": self.email,
            "birth_date": self.birth_date.isoformat() if self.birth_date else "",
            "gender": self.gender,
            "civil_status": self.civil_status,
            "highest_education": self.highest_education,
            "occupation_income_source": self.occupation_income_source,
            "monthly_income": self.monthly_income,
            "number_of_dependents": self.number_of_dependents,
            "beneficiary_name": self.beneficiary_name,
            "beneficiary_address": self.beneficiary_address,
            "beneficiary_phone": self.beneficiary_phone,
            "status": self.status,
            "termination_date": self.termination_date.isoformat() if self.termination_date else "",
            "termination_type": self.termination_type,
            "lifetime_cap_enabled": bool(self.lifetime_cap_enabled),
            "lifetime_cap_amount": _money(self.lifetime_cap_amount),
            "gcash_number": self.gcash_number,
            "bank_account_number": self.bank_account_number,
            "bank_name": self.bank_name,
            "age": self.age,
            "id_picture_location": self.id_picture_location,
            "beneficiary_relationship": self.beneficiary_relationship,
            "positions": {row.department: row.position_id for row in self.positions},
        }

    def to_dict(self):
        downline = sorted(self.referrals, key=lambda m: m.member_id)
        payload = self.edit_payload()
        payload.update({
            "referrer_name": self.referrer.full_name if self.referrer else None,
            "full_name": self.full_name,
            "referral_count": len(self.referrals),
            "downline": [
                {"member_id": m.member_id, "full_name": m.full_name, "batch": m.batch}
                for m in downline
            ],
        })
        return payload

    def search_text(self):
        parts = [
            str(self.member_id),
            self.full_name,
            self.last_name,
            self.first_name,
            self.middle_name or "",
            self.suffix or "",
            f"batch {self.batch}",
            self.membership_type or "",
            self.status or "",
            self.address or "",
            self.phone or "",
            self.email or "",
            self.gender or "",
            self.civil_status or "",
            self.highest_education or "",
            self.occupation_income_source or "",
            self.monthly_income or "",
            self.beneficiary_name or "",
            self.beneficiary_address or "",
            self.beneficiary_phone or "",
            self.termination_type or "",
        ]
        for row in self.positions:
            parts.append(row.department)
            if row.position:
                parts.append(row.position.title)
        if self.number_of_dependents is not None:
            parts.append(str(self.number_of_dependents))
        if self.referrer:
            parts.extend([str(self.referrer_id), self.referrer.full_name])
        for ref in self.referrals:
            parts.extend([str(ref.member_id), ref.full_name])
        return " ".join(parts).lower()


class Contractor(db.Model):
    __tablename__ = "contractors"

    contractor_id = db.Column(db.Integer, primary_key=True)
    batch = db.Column(db.Integer, nullable=False)
    member_referrer_id = db.Column(db.Integer, db.ForeignKey("members.member_id"), nullable=False)
    company_name = db.Column(db.String(120), nullable=False)
    company_address = db.Column(db.String(255))
    representative_name = db.Column(db.String(120))
    contact_no = db.Column(db.String(30))
    date_joined = db.Column(db.Date)

    member_referrer = db.relationship("Member", backref="contractor_referrals")

    def to_dict(self):
        return {
            "contractor_id": self.contractor_id,
            "batch": self.batch,
            "member_referrer_id": self.member_referrer_id,
            "member_referrer_name": self.member_referrer.full_name if self.member_referrer else None,
            "company_name": self.company_name,
            "company_address": self.company_address,
            "representative_name": self.representative_name,
            "contact_no": self.contact_no,
            "date_joined": self.date_joined.isoformat() if self.date_joined else None,
        }

    def search_text(self):
        parts = [
            str(self.contractor_id),
            self.company_name or "",
            self.company_address or "",
            self.representative_name or "",
            self.contact_no or "",
            f"batch {self.batch}",
        ]
        if self.member_referrer:
            parts.extend([str(self.member_referrer_id), self.member_referrer.full_name])
        return " ".join(parts).lower()


class Supplier(db.Model):
    __tablename__ = "suppliers"

    supplier_id = db.Column(db.Integer, primary_key=True)
    batch = db.Column(db.Integer, nullable=False)
    member_referrer_id = db.Column(db.Integer, db.ForeignKey("members.member_id"), nullable=False)
    company_name = db.Column(db.String(120), nullable=False)
    company_address = db.Column(db.String(255))
    representative_name = db.Column(db.String(120))
    contact_no = db.Column(db.String(30))
    date_joined = db.Column(db.Date)

    member_referrer = db.relationship("Member", backref="supplier_referrals")

    def to_dict(self):
        return {
            "supplier_id": self.supplier_id,
            "batch": self.batch,
            "member_referrer_id": self.member_referrer_id,
            "member_referrer_name": self.member_referrer.full_name if self.member_referrer else None,
            "company_name": self.company_name,
            "company_address": self.company_address,
            "representative_name": self.representative_name,
            "contact_no": self.contact_no,
            "date_joined": self.date_joined.isoformat() if self.date_joined else None,
        }

    def search_text(self):
        parts = [
            str(self.supplier_id),
            self.company_name or "",
            self.company_address or "",
            self.representative_name or "",
            self.contact_no or "",
            f"batch {self.batch}",
        ]
        if self.member_referrer:
            parts.extend([str(self.member_referrer_id), self.member_referrer.full_name])
        return " ".join(parts).lower()


class ProjectCommission(db.Model):
    __tablename__ = "project_commissions"

    project_id = db.Column(db.Integer, primary_key=True)
    project_title = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(255))
    contractor_id = db.Column(db.Integer, db.ForeignKey("contractors.contractor_id"), nullable=False)
    client_referrer_id = db.Column(db.Integer, db.ForeignKey("members.member_id"), nullable=False)
    contractor_referrer_id = db.Column(db.Integer, db.ForeignKey("members.member_id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=True, default=manila_now)

    contractor = db.relationship("Contractor", backref="project_commissions")
    client_referrer = db.relationship("Member", foreign_keys=[client_referrer_id])
    contractor_referrer = db.relationship("Member", foreign_keys=[contractor_referrer_id])
    billings = db.relationship(
        "ProjectBilling",
        backref="project",
        cascade="all, delete-orphan",
        order_by="ProjectBilling.billing_date.asc(), ProjectBilling.billing_id.asc()",
    )

    @staticmethod
    def member_referral_label(member):
        if not member:
            return None
        return f"#{member.member_id} — {member.last_name}, {member.first_name}"

    @property
    def total_billing_amount(self):
        return sum(Decimal(str(b.billing_amount or 0)) for b in self.billings)

    def to_dict(self):
        billing_rows = [billing.to_dict() for billing in self.billings]
        return {
            "project_id": self.project_id,
            "project_title": self.project_title,
            "address": self.address,
            "contractor_id": self.contractor_id,
            "contractor_name": self.contractor.company_name if self.contractor else None,
            "client_referrer_id": self.client_referrer_id,
            "client_referrer_label": self.member_referral_label(self.client_referrer),
            "contractor_referrer_id": self.contractor_referrer_id,
            "contractor_referrer_label": self.member_referral_label(self.contractor_referrer),
            "billings": billing_rows,
            "total_billing_amount": _money(self.total_billing_amount),
        }


class ProjectBilling(db.Model):
    __tablename__ = "project_billings"

    billing_id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project_commissions.project_id"), nullable=False)
    billing_date = db.Column(db.Date, nullable=False)
    billing_amount = db.Column(db.Numeric(14, 2), nullable=False)

    def to_dict(self):
        return {
            "billing_id": self.billing_id,
            "project_id": self.project_id,
            "billing_date": self.billing_date.isoformat() if self.billing_date else None,
            "billing_amount": _money(self.billing_amount),
        }


class CommissionLevel(db.Model):
    __tablename__ = "commission_levels"
    __table_args__ = (
        db.UniqueConstraint("scheme", "level", name="uq_commission_levels_scheme_level"),
    )

    level_id = db.Column(db.Integer, primary_key=True)
    scheme = db.Column(db.String(20), nullable=False, default="client")
    level = db.Column(db.Integer, nullable=False)
    percentage = db.Column(db.Numeric(6, 2), nullable=False)
    description = db.Column(db.String(120))

    def to_dict(self):
        return {
            "level_id": self.level_id,
            "scheme": self.scheme,
            "level": self.level,
            "percentage": _money(self.percentage),
            "description": self.description,
        }


class AdSplitMember(db.Model):
    """Members eligible for Admin Discretion (AD) bonus split sharing."""

    __tablename__ = "ad_split_members"

    ad_split_id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(
        db.Integer, db.ForeignKey("members.member_id"), nullable=False, unique=True
    )
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=manila_now)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=manila_now, onupdate=manila_now
    )
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)

    member = db.relationship("Member", foreign_keys=[member_id])
    created_by = db.relationship("User", foreign_keys=[created_by_user_id])

    def to_dict(self):
        return {
            "ad_split_id": self.ad_split_id,
            "member_id": self.member_id,
            "member_name": self.member.full_name if self.member else None,
            "member_batch": self.member.batch if self.member else None,
            "member_status": self.member.status if self.member else None,
            "description": self.description or "",
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


class SharingBatch(db.Model):
    __tablename__ = "sharing_batches"

    batch_id = db.Column(db.Integer, primary_key=True)
    commission_date = db.Column(db.Date, nullable=False)
    generated_at = db.Column(db.DateTime, nullable=False)
    project_count = db.Column(db.Integer, default=0)
    total_commission = db.Column(db.Numeric(14, 2), default=0)
    total_client_pool = db.Column(db.Numeric(14, 2), default=0)
    total_contractor_pool = db.Column(db.Numeric(14, 2), default=0)
    total_pool = db.Column(db.Numeric(14, 2), default=0)
    total_admin = db.Column(db.Numeric(14, 2), default=0)
    total_shared = db.Column(db.Numeric(14, 2), default=0)
    total_pop = db.Column(db.Numeric(14, 2), default=0)

    entries = db.relationship("SharingEntry", backref="batch", cascade="all, delete-orphan")
    ledger_entries = db.relationship("MemberLedger", backref="batch", cascade="all, delete-orphan")


class MemberLedger(db.Model):
    __tablename__ = "member_ledger"

    ledger_id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.member_id"), nullable=False)
    transaction_type = db.Column(db.String(10), nullable=False, default="credit")
    batch_id = db.Column(db.Integer, db.ForeignKey("sharing_batches.batch_id"), nullable=True)
    entry_id = db.Column(db.Integer, db.ForeignKey("sharing_entries.entry_id"), nullable=True)
    billing_date = db.Column(db.Date, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("project_commissions.project_id"), nullable=True)
    billing_id = db.Column(db.Integer, db.ForeignKey("project_billings.billing_id"), nullable=True)
    product_commission_id = db.Column(
        db.Integer, db.ForeignKey("product_commissions.product_commission_id"), nullable=True
    )
    project_title = db.Column(db.String(200))
    recipient_type = db.Column(db.String(20), nullable=False)
    share_scheme = db.Column(db.String(40))
    level = db.Column(db.Integer, default=0)
    share_amount = db.Column(db.Numeric(14, 2), nullable=False)
    description = db.Column(db.String(255))
    payout_request_id = db.Column(db.Integer, db.ForeignKey("payout_requests.payout_id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False)

    member = db.relationship("Member", backref="ledger_transactions")
    project = db.relationship("ProjectCommission")
    billing = db.relationship("ProjectBilling")
    sharing_entry = db.relationship("SharingEntry")
    payout_request = db.relationship(
        "PayoutRequest",
        back_populates="ledger_entry",
        foreign_keys=[payout_request_id],
    )


class PayoutRequest(db.Model):
    __tablename__ = "payout_requests"

    payout_id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.member_id"), nullable=False)
    requested_amount = db.Column(db.Numeric(14, 2), nullable=False)
    ompd_deduction = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    net_release_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    status = db.Column(db.String(30), nullable=False, default="pending")
    member_note = db.Column(db.Text)

    requested_at = db.Column(db.DateTime, nullable=False)
    requested_by_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)

    request_reviewed_at = db.Column(db.DateTime)
    request_reviewed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    request_review_note = db.Column(db.Text)

    release_method = db.Column(db.String(40))
    release_reference = db.Column(db.String(120))
    release_account_info = db.Column(db.String(255))
    release_notes = db.Column(db.Text)
    release_submitted_at = db.Column(db.DateTime)
    release_submitted_by_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))

    release_approved_at = db.Column(db.DateTime)
    release_approved_by_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    released_at = db.Column(db.DateTime)

    rejected_at = db.Column(db.DateTime)
    rejected_by_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    rejection_reason = db.Column(db.Text)

    member = db.relationship("Member", backref="payout_requests")
    requested_by = db.relationship("User", foreign_keys=[requested_by_user_id])
    request_reviewed_by = db.relationship("User", foreign_keys=[request_reviewed_by_user_id])
    release_submitted_by = db.relationship("User", foreign_keys=[release_submitted_by_user_id])
    release_approved_by = db.relationship("User", foreign_keys=[release_approved_by_user_id])
    rejected_by = db.relationship("User", foreign_keys=[rejected_by_user_id])
    ledger_entry = db.relationship(
        "MemberLedger",
        back_populates="payout_request",
        uselist=False,
        foreign_keys="MemberLedger.payout_request_id",
    )
    notifications = db.relationship("PayoutNotification", backref="payout", cascade="all, delete-orphan")
    ompd_entry = db.relationship(
        "OmpdFundEntry",
        back_populates="payout",
        uselist=False,
        cascade="all, delete-orphan",
    )


class OmpdFundEntry(db.Model):
    __tablename__ = "ompd_fund_entries"

    entry_id = db.Column(db.Integer, primary_key=True)
    payout_id = db.Column(
        db.Integer,
        db.ForeignKey("payout_requests.payout_id"),
        nullable=False,
        unique=True,
    )
    member_id = db.Column(db.Integer, db.ForeignKey("members.member_id"), nullable=False)
    gross_amount = db.Column(db.Numeric(14, 2), nullable=False)
    deduction_amount = db.Column(db.Numeric(14, 2), nullable=False)
    net_released = db.Column(db.Numeric(14, 2), nullable=False)
    release_method = db.Column(db.String(40))
    release_reference = db.Column(db.String(120))
    recorded_at = db.Column(db.DateTime, nullable=False)

    payout = db.relationship("PayoutRequest", back_populates="ompd_entry")
    member = db.relationship("Member", backref="ompd_contributions")


class PayoutNotification(db.Model):
    __tablename__ = "payout_notifications"

    notification_id = db.Column(db.Integer, primary_key=True)
    payout_id = db.Column(db.Integer, db.ForeignKey("payout_requests.payout_id"), nullable=False)
    audience_role = db.Column(db.String(20))
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)

    user = db.relationship("User", foreign_keys=[user_id])


class ProductCommission(db.Model):
    __tablename__ = "product_commissions"

    product_commission_id = db.Column(db.Integer, primary_key=True)
    product_title = db.Column(db.String(200), nullable=False, default="Products Commission")
    commission_amount = db.Column(db.Numeric(14, 2), nullable=False)
    commission_date = db.Column(db.Date, nullable=False)
    ref_seller_id = db.Column(db.Integer, db.ForeignKey("members.member_id"), nullable=False)
    ref_buyer_id = db.Column(db.Integer, db.ForeignKey("members.member_id"), nullable=False)
    bonus_type = db.Column(db.String(10), nullable=False, default="auto")
    bonus_percent = db.Column(db.Numeric(6, 2), nullable=False, default=10)
    notes = db.Column(db.Text)

    seller_pool = db.Column(db.Numeric(14, 2), default=0)
    buyer_pool = db.Column(db.Numeric(14, 2), default=0)
    pop_amount = db.Column(db.Numeric(14, 2), default=0)
    ad_fund_amount = db.Column(db.Numeric(14, 2), default=0)
    platform_amount = db.Column(db.Numeric(14, 2), default=0)
    bonus_amount = db.Column(db.Numeric(14, 2), default=0)
    total_shared = db.Column(db.Numeric(14, 2), default=0)
    total_mandate = db.Column(db.Numeric(14, 2), default=0)

    created_at = db.Column(db.DateTime, nullable=False, default=manila_now)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)

    ref_seller = db.relationship("Member", foreign_keys=[ref_seller_id])
    ref_buyer = db.relationship("Member", foreign_keys=[ref_buyer_id])
    created_by = db.relationship("User", foreign_keys=[created_by_user_id])
    shares = db.relationship(
        "ProductCommissionShare",
        backref="product_commission",
        cascade="all, delete-orphan",
        order_by="ProductCommissionShare.share_id.asc()",
    )
    ad_allocations = db.relationship(
        "ProductCommissionAdAllocation",
        backref="product_commission",
        cascade="all, delete-orphan",
        order_by="ProductCommissionAdAllocation.allocation_id.asc()",
    )

    def to_dict(self):
        shares = [share.to_dict() for share in self.shares]
        from app.product_commission_service import summarize_product_account_earnings

        return {
            "product_commission_id": self.product_commission_id,
            "product_title": self.product_title,
            "commission_amount": _money(self.commission_amount),
            "commission_date": self.commission_date.isoformat() if self.commission_date else "",
            "ref_seller_id": self.ref_seller_id,
            "ref_seller_name": self.ref_seller.full_name if self.ref_seller else None,
            "ref_buyer_id": self.ref_buyer_id,
            "ref_buyer_name": self.ref_buyer.full_name if self.ref_buyer else None,
            "bonus_type": self.bonus_type,
            "bonus_percent": _money(self.bonus_percent),
            "notes": self.notes or "",
            "seller_pool": _money(self.seller_pool),
            "buyer_pool": _money(self.buyer_pool),
            "pop_amount": _money(self.pop_amount),
            "ad_fund_amount": _money(self.ad_fund_amount),
            "platform_amount": _money(self.platform_amount),
            "bonus_amount": _money(self.bonus_amount),
            "total_shared": _money(self.total_shared),
            "total_mandate": _money(self.total_mandate),
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "shares": shares,
            "ad_allocations": [row.to_dict() for row in self.ad_allocations],
            "account_summary": summarize_product_account_earnings(shares),
        }


class ProductCommissionAdAllocation(db.Model):
    __tablename__ = "product_commission_ad_allocations"

    allocation_id = db.Column(db.Integer, primary_key=True)
    product_commission_id = db.Column(
        db.Integer, db.ForeignKey("product_commissions.product_commission_id"), nullable=False
    )
    member_id = db.Column(db.Integer, db.ForeignKey("members.member_id"), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    charge_from = db.Column(db.String(20), nullable=False, default="platform")

    member = db.relationship("Member")

    def to_dict(self):
        return {
            "allocation_id": self.allocation_id,
            "product_commission_id": self.product_commission_id,
            "member_id": self.member_id,
            "member_name": self.member.full_name if self.member else None,
            "amount": _money(self.amount),
            "charge_from": self.charge_from,
        }


class ProductCommissionShare(db.Model):
    __tablename__ = "product_commission_shares"

    share_id = db.Column(db.Integer, primary_key=True)
    product_commission_id = db.Column(
        db.Integer, db.ForeignKey("product_commissions.product_commission_id"), nullable=False
    )
    member_id = db.Column(db.Integer, db.ForeignKey("members.member_id"), nullable=True)
    recipient_type = db.Column(db.String(20), nullable=False, default="member")
    recipient_label = db.Column(db.String(120))
    share_scheme = db.Column(db.String(40))
    level = db.Column(db.Integer, nullable=False, default=0)
    percentage = db.Column(db.Numeric(6, 2), nullable=False, default=0)
    share_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)

    member = db.relationship("Member")

    def to_dict(self):
        return {
            "share_id": self.share_id,
            "product_commission_id": self.product_commission_id,
            "member_id": self.member_id,
            "member_name": self.member.full_name if self.member else None,
            "recipient_type": self.recipient_type,
            "recipient_label": self.recipient_label,
            "share_scheme": self.share_scheme,
            "level": self.level,
            "percentage": _money(self.percentage),
            "share_amount": _money(self.share_amount),
        }


class SharingEntry(db.Model):
    __tablename__ = "sharing_entries"

    entry_id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("sharing_batches.batch_id"), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("project_commissions.project_id"), nullable=False)
    billing_id = db.Column(db.Integer, db.ForeignKey("project_billings.billing_id"), nullable=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.member_id"), nullable=True)
    recipient_type = db.Column(db.String(20), default="member")
    recipient_label = db.Column(db.String(120))
    share_scheme = db.Column(db.String(40))
    level = db.Column(db.Integer, nullable=False)
    percentage = db.Column(db.Numeric(6, 2), nullable=False)
    share_amount = db.Column(db.Numeric(14, 2), nullable=False)

    project = db.relationship("ProjectCommission")
    billing = db.relationship("ProjectBilling")
    member = db.relationship("Member")


class CmsLandingSection(db.Model):
    __tablename__ = "cms_landing_sections"

    section_key = db.Column(db.String(64), primary_key=True)
    data = db.Column(db.JSON, nullable=False)
    updated_at = db.Column(db.DateTime, default=manila_now, onupdate=manila_now)


class CmsEcosystemPage(db.Model):
    __tablename__ = "cms_ecosystem_pages"

    slug = db.Column(db.String(40), primary_key=True)
    data = db.Column(db.JSON, nullable=False)
    updated_at = db.Column(db.DateTime, default=manila_now, onupdate=manila_now)


class CmsRegistryPartner(db.Model):
    __tablename__ = "cms_registry_partners"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    partner_type = db.Column(db.String(20), nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    data = db.Column(db.JSON, nullable=False)
    updated_at = db.Column(db.DateTime, default=manila_now, onupdate=manila_now)


class CmsGalleryFolder(db.Model):
    __tablename__ = "cms_gallery_folders"

    folder_id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500))
    status = db.Column(db.String(20), nullable=False, default="published", index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    images = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime, nullable=False, default=manila_now)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=manila_now, onupdate=manila_now
    )

    def to_dict(self):
        return {
            "folder_id": self.folder_id,
            "slug": self.slug,
            "title": self.title,
            "description": self.description or "",
            "status": self.status,
            "sort_order": self.sort_order or 0,
            "images": self.images or [],
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


class MarketplaceListing(db.Model):
    __tablename__ = "marketplace_listings"

    listing_id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(40), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.String(500))
    body = db.Column(db.Text)
    price_label = db.Column(db.String(120))
    location = db.Column(db.String(255))
    status = db.Column(db.String(20), nullable=False, default="draft", index=True)
    thumbnail_url = db.Column(db.String(500))
    gallery = db.Column(db.JSON, nullable=False, default=list)
    contact_name = db.Column(db.String(120))
    contact_phone = db.Column(db.String(40))
    contact_email = db.Column(db.String(120))
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=manila_now)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=manila_now, onupdate=manila_now
    )
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)

    leads = db.relationship(
        "MarketplaceLead",
        backref="listing",
        cascade="save-update, merge",
        passive_deletes=True,
        order_by="MarketplaceLead.created_at.desc()",
    )
    created_by = db.relationship("User", foreign_keys=[created_by_user_id])

    def to_dict(self):
        return {
            "listing_id": self.listing_id,
            "category": self.category,
            "title": self.title,
            "summary": self.summary or "",
            "body": self.body or "",
            "price_label": self.price_label or "",
            "location": self.location or "",
            "status": self.status,
            "thumbnail_url": self.thumbnail_url or "",
            "gallery": self.gallery or [],
            "contact_name": self.contact_name or "",
            "contact_phone": self.contact_phone or "",
            "contact_email": self.contact_email or "",
            "sort_order": self.sort_order or 0,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


class MarketplaceLead(db.Model):
    __tablename__ = "marketplace_leads"

    lead_id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(
        db.Integer,
        db.ForeignKey("marketplace_listings.listing_id", ondelete="SET NULL"),
        nullable=True,
    )
    interest_category = db.Column(db.String(40), nullable=True, index=True)
    attributed_member_id = db.Column(
        db.Integer, db.ForeignKey("members.member_id"), nullable=True, index=True
    )
    # guest_* hold the client's representative (the person who inquired).
    guest_name = db.Column(db.String(160), nullable=True)
    guest_phone = db.Column(db.String(160))
    guest_email = db.Column(db.String(255))
    message = db.Column(db.Text)
    source_path = db.Column(db.String(255))
    status = db.Column(db.String(30), nullable=False, default="new", index=True)
    # Legacy CRM fields (pre-transaction workflow); kept for historical rows only.
    action_required = db.Column(db.String(60), nullable=True)
    final_result = db.Column(db.String(40), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=manila_now)

    transaction_type = db.Column(db.String(40), nullable=True, index=True)
    inquiry_no = db.Column(db.Integer, nullable=True)
    reference_number = db.Column(db.String(30), nullable=True, unique=True)
    item_name = db.Column(db.String(255))
    date_requested = db.Column(db.Date)
    estimated_implementation = db.Column(db.String(160))
    quantity = db.Column(db.Text)
    specifications = db.Column(db.Text)
    delivery_location = db.Column(db.Text)
    referrer_name = db.Column(db.String(255))
    referrer_phone = db.Column(db.String(120))
    referrer_email = db.Column(db.String(255))
    client_company = db.Column(db.Text)
    status_detail = db.Column(db.Text)
    action_needed = db.Column(db.Text)
    project_coordinator = db.Column(db.String(160))
    assigned_contractor = db.Column(db.String(255))
    assigned_user_id = db.Column(
        db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True
    )
    date_completed = db.Column(db.Date)
    remarks = db.Column(db.Text)
    source = db.Column(db.String(20), nullable=False, default="web")
    updated_at = db.Column(db.DateTime, nullable=True)
    status_changed_at = db.Column(db.DateTime, nullable=True)

    # Project delivery (project transactions only).
    progress_percent = db.Column(db.Integer, nullable=True)
    awarded_contractor_id = db.Column(
        db.Integer, db.ForeignKey("contractors.contractor_id", ondelete="SET NULL"), nullable=True, index=True
    )
    contract_amount = db.Column(db.Numeric(14, 2), nullable=True)
    contract_signed_on = db.Column(db.Date, nullable=True)
    commission_percent = db.Column(db.Numeric(6, 2), nullable=True)
    commission_project_id = db.Column(
        db.Integer, db.ForeignKey("project_commissions.project_id", ondelete="SET NULL"), nullable=True
    )
    # Project team beside the coordinator (assigned_user_id).
    estimator_user_id = db.Column(
        db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True
    )
    site_engineer_user_id = db.Column(
        db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Product team beside the account officer (assigned_user_id) and pricing officer (estimator_user_id).
    sourcing_user_id = db.Column(
        db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True
    )
    logistics_user_id = db.Column(
        db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True
    )
    agent_user_id = db.Column(
        db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Product order: the registered supplier filling it and the scheduled delivery date.
    supplier_id = db.Column(
        db.Integer, db.ForeignKey("suppliers.supplier_id", ondelete="SET NULL"), nullable=True, index=True
    )
    delivery_date = db.Column(db.Date, nullable=True)

    attributed_member = db.relationship("Member", foreign_keys=[attributed_member_id])
    assigned_user = db.relationship("User", foreign_keys=[assigned_user_id])
    estimator_user = db.relationship("User", foreign_keys=[estimator_user_id])
    site_engineer_user = db.relationship("User", foreign_keys=[site_engineer_user_id])
    sourcing_user = db.relationship("User", foreign_keys=[sourcing_user_id])
    logistics_user = db.relationship("User", foreign_keys=[logistics_user_id])
    agent_user = db.relationship("User", foreign_keys=[agent_user_id])
    supplier = db.relationship("Supplier", foreign_keys=[supplier_id])
    awarded_contractor = db.relationship("Contractor", foreign_keys=[awarded_contractor_id])
    commission_project = db.relationship("ProjectCommission", foreign_keys=[commission_project_id])
    history_entries = db.relationship(
        "MarketplaceLeadHistory",
        backref="lead",
        cascade="all, delete-orphan",
        order_by="MarketplaceLeadHistory.created_at.asc()",
    )

    __table_args__ = (
        db.UniqueConstraint("transaction_type", "inquiry_no", name="uq_marketplace_leads_type_inquiry_no"),
    )

    @property
    def is_closed(self):
        return (self.status or "new") in ("completed", "terminated")

    @property
    def aging_days(self):
        start = self.date_requested or (self.created_at.date() if self.created_at else None)
        if not start:
            return 0
        if self.is_closed:
            end = self.date_completed or (
                self.updated_at.date() if self.updated_at else manila_today()
            )
        else:
            end = manila_today()
        return max(0, (end - start).days)

    @property
    def days_in_status(self):
        since = self.status_changed_at or self.updated_at or self.created_at
        if not since:
            return 0
        return max(0, (manila_today() - since.date()).days)

    @property
    def last_activity_at(self):
        stamps = [stamp for stamp in (self.updated_at, self.created_at) if stamp]
        return max(stamps) if stamps else None

    @property
    def display_item(self):
        if self.item_name:
            return self.item_name
        if self.listing is not None:
            return self.listing.title
        return ""

    @property
    def referred_by_name(self):
        if self.attributed_member is not None:
            return self.attributed_member.full_name
        return self.referrer_name or ""

    @property
    def client_tel(self):
        return _first_phone(self.guest_phone)

    @property
    def client_mailto(self):
        return _first_email(self.guest_email)

    @property
    def referrer_tel(self):
        member = self.attributed_member
        return _first_phone(self.referrer_phone or (member.phone if member else None))

    @property
    def referrer_mailto(self):
        member = self.attributed_member
        return _first_email(self.referrer_email or (member.email if member else None))

    def to_dict(self):
        listing = self.listing
        member = self.attributed_member
        return {
            "lead_id": self.lead_id,
            "reference_number": self.reference_number or "",
            "transaction_type": self.transaction_type or "",
            "listing_id": self.listing_id,
            "listing_title": listing.title if listing else None,
            "listing_category": (
                listing.category if listing else (self.interest_category or None)
            ),
            "interest_category": self.interest_category or "",
            "item_name": self.display_item,
            "attributed_member_id": self.attributed_member_id,
            "attributed_member_name": member.full_name if member else None,
            "referred_by": self.referred_by_name,
            "guest_name": self.guest_name or "",
            "guest_phone": self.guest_phone or "",
            "guest_email": self.guest_email or "",
            "client_company": self.client_company or "",
            "message": self.message or "",
            "source_path": self.source_path or "",
            "status": self.status or "new",
            "aging_days": self.aging_days,
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


class MarketplaceLeadHistory(db.Model):
    """Ledger of marketplace inquiry status / action / result changes."""

    __tablename__ = "marketplace_lead_history"

    history_id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(
        db.Integer,
        db.ForeignKey("marketplace_leads.lead_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = db.Column(db.String(40), nullable=False, default="update")
    status = db.Column(db.String(30))
    action_required = db.Column(db.String(60))
    final_result = db.Column(db.String(40))
    note = db.Column(db.Text)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=manila_now)

    created_by = db.relationship("User", foreign_keys=[created_by_user_id])

    def to_dict(self):
        return {
            "history_id": self.history_id,
            "lead_id": self.lead_id,
            "event_type": self.event_type,
            "status": self.status or "",
            "action_required": self.action_required or "",
            "final_result": self.final_result or "",
            "note": self.note or "",
            "created_by_user_id": self.created_by_user_id,
            "created_by_name": self.created_by.full_name if self.created_by else "",
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }


class MarketplaceLeadRead(db.Model):
    """Per-user seen marker so Admin/Staff are notified of new or assigned transactions."""

    __tablename__ = "marketplace_lead_reads"

    read_id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(
        db.Integer,
        db.ForeignKey("marketplace_leads.lead_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    read_at = db.Column(db.DateTime, nullable=False, default=manila_now)

    __table_args__ = (
        db.UniqueConstraint("lead_id", "user_id", name="uq_marketplace_lead_reads_lead_user"),
    )


class ProjectStagePlan(db.Model):
    """Target / reached date per delivery stage of a project transaction."""

    __tablename__ = "project_stage_plans"

    plan_id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(
        db.Integer, db.ForeignKey("marketplace_leads.lead_id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage = db.Column(db.String(30), nullable=False)
    target_date = db.Column(db.Date, nullable=True)
    reached_on = db.Column(db.Date, nullable=True)

    __table_args__ = (
        db.UniqueConstraint("lead_id", "stage", name="uq_project_stage_plans_lead_stage"),
    )


class ProjectDocument(db.Model):
    """File (stored in the database) or external link attached to a project or product transaction.

    shared_with_contractor means "shared with the partner": the contractor on projects, the supplier on products.
    """

    __tablename__ = "project_documents"

    document_id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(
        db.Integer, db.ForeignKey("marketplace_leads.lead_id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind = db.Column(db.String(30), nullable=False, default="other")
    title = db.Column(db.String(255), nullable=False)
    file_name = db.Column(db.String(255), nullable=True)
    content_type = db.Column(db.String(120), nullable=True)
    size_bytes = db.Column(db.Integer, nullable=True)
    file_data = db.deferred(db.Column(db.LargeBinary, nullable=True))
    external_url = db.Column(db.String(500), nullable=True)
    shared_with_contractor = db.Column(db.Boolean, nullable=False, default=False)
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=manila_now)

    uploaded_by = db.relationship("User", foreign_keys=[uploaded_by_user_id])

    @property
    def is_image(self):
        return (self.content_type or "").startswith("image/")


class ProjectEvent(db.Model):
    """Site ocular, meeting, or Zoom call scheduled for a project."""

    __tablename__ = "project_events"

    event_id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(
        db.Integer, db.ForeignKey("marketplace_leads.lead_id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind = db.Column(db.String(20), nullable=False, default="site_visit")
    title = db.Column(db.String(255), nullable=False)
    starts_at = db.Column(db.DateTime, nullable=False, index=True)
    ends_at = db.Column(db.DateTime, nullable=True)
    location = db.Column(db.String(255), nullable=True)
    meeting_link = db.Column(db.String(500), nullable=True)
    assigned_user_id = db.Column(
        db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True
    )
    status = db.Column(db.String(20), nullable=False, default="scheduled")
    notes = db.Column(db.Text)
    outcome = db.Column(db.Text)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=manila_now)

    lead = db.relationship("MarketplaceLead", backref=db.backref("events", passive_deletes=True))
    assigned_user = db.relationship("User", foreign_keys=[assigned_user_id])

    @property
    def is_overdue(self):
        return self.status == "scheduled" and self.starts_at < manila_now()


class ProjectPayment(db.Model):
    """Client payment milestone; a paid milestone can be posted as a project commission billing."""

    __tablename__ = "project_payments"

    payment_id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(
        db.Integer, db.ForeignKey("marketplace_leads.lead_id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = db.Column(db.String(160), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    paid_on = db.Column(db.Date, nullable=True)
    reference = db.Column(db.String(120), nullable=True)
    commission_amount = db.Column(db.Numeric(14, 2), nullable=True)
    billing_id = db.Column(
        db.Integer, db.ForeignKey("project_billings.billing_id", ondelete="SET NULL"), nullable=True
    )
    notes = db.Column(db.Text)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=manila_now)

    lead = db.relationship("MarketplaceLead", backref=db.backref("payments", passive_deletes=True))

    @property
    def is_paid(self):
        return self.paid_on is not None

    @property
    def is_overdue(self):
        return not self.is_paid and self.due_date is not None and self.due_date < manila_today()


class PortalPosition(db.Model):
    """A position title available within one department (e.g. Sales -> Team Lead)."""

    __tablename__ = "portal_positions"

    position_id = db.Column(db.Integer, primary_key=True)
    department = db.Column(db.String(40), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=manila_now)

    __table_args__ = (
        db.UniqueConstraint("department", "title", name="uq_portal_positions_department_title"),
    )

    assignments = db.relationship("MemberPosition", back_populates="position", passive_deletes=True)


class MemberPosition(db.Model):
    """A member's position within a department; at most one per department."""

    __tablename__ = "member_positions"

    member_position_id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(
        db.Integer,
        db.ForeignKey("members.member_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    department = db.Column(db.String(40), nullable=False)
    position_id = db.Column(
        db.Integer,
        db.ForeignKey("portal_positions.position_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_at = db.Column(db.DateTime, nullable=False, default=manila_now)

    __table_args__ = (
        db.UniqueConstraint("member_id", "department", name="uq_member_positions_member_department"),
    )

    position = db.relationship("PortalPosition", back_populates="assignments")


class AuditLog(db.Model):
    """One traced request: who did what, from where, the outcome, and which records changed."""

    __tablename__ = "audit_logs"

    log_id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=manila_now, index=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Snapshots so the trail survives renamed or deleted accounts.
    username = db.Column(db.String(80))
    full_name = db.Column(db.String(120))
    role = db.Column(db.String(20))
    ip_address = db.Column(db.String(64))
    user_agent = db.Column(db.String(255))
    method = db.Column(db.String(10))
    path = db.Column(db.String(500))
    endpoint = db.Column(db.String(120), index=True)
    category = db.Column(db.String(30), index=True)
    action = db.Column(db.String(160))
    target_type = db.Column(db.String(40), index=True)
    target_id = db.Column(db.String(60), index=True)
    target_label = db.Column(db.String(200))
    outcome = db.Column(db.String(20), index=True)
    status_code = db.Column(db.Integer)
    summary = db.Column(db.Text)
    details = db.Column(db.JSON)
    changes = db.Column(db.JSON)


class MemberSanction(db.Model):
    """A time-limited suspension of a member's ad posting and/or contractor endorsement privileges."""

    __tablename__ = "member_sanctions"

    sanction_id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(
        db.Integer,
        db.ForeignKey("members.member_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    memo_number = db.Column(db.String(80))
    reason = db.Column(db.Text, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    # Last suspended day (inclusive).
    end_date = db.Column(db.Date, nullable=False)
    blocks_ads = db.Column(db.Boolean, nullable=False, default=True)
    blocks_endorsement = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=manila_now)
    created_by_user_id = db.Column(
        db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    lifted_at = db.Column(db.DateTime, nullable=True)
    lifted_by_user_id = db.Column(
        db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    lift_reason = db.Column(db.String(255))

    member = db.relationship("Member", foreign_keys=[member_id])
    created_by = db.relationship("User", foreign_keys=[created_by_user_id])
    lifted_by = db.relationship("User", foreign_keys=[lifted_by_user_id])

    @property
    def total_days(self):
        return (self.end_date - self.start_date).days + 1

    def is_active_on(self, day=None):
        day = day or manila_today()
        return self.lifted_at is None and self.start_date <= day <= self.end_date

    def status_on(self, day=None):
        day = day or manila_today()
        if self.lifted_at is not None:
            return "lifted"
        if day < self.start_date:
            return "scheduled"
        if day > self.end_date:
            return "served"
        return "active"

    @property
    def scope_labels(self):
        labels = []
        if self.blocks_ads:
            labels.append("Posting ads")
        if self.blocks_endorsement:
            labels.append("Endorsing contractors")
        return labels


class PortalNotice(db.Model):
    """Policy, memo, or announcement visible on role dashboards."""

    __tablename__ = "portal_notices"

    notice_id = db.Column(db.Integer, primary_key=True)
    notice_type = db.Column(db.String(20), nullable=False, default="announcement", index=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    reference_number = db.Column(db.String(60), nullable=True)
    effective_date = db.Column(db.Date, nullable=True)
    issued_by = db.Column(db.String(160), nullable=True)
    issued_date = db.Column(db.Date, nullable=True)
    # JSON list of roles; empty list means all roles.
    audience_roles = db.Column(db.JSON, nullable=False, default=list)
    is_published = db.Column(db.Boolean, nullable=False, default=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=manila_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=manila_now, onupdate=manila_now)

    created_by = db.relationship("User", foreign_keys=[created_by_user_id])
    reads = db.relationship(
        "PortalNoticeRead",
        backref="notice",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )


class PortalNoticeRead(db.Model):
    """Tracks which users have seen a portal notice."""

    __tablename__ = "portal_notice_reads"

    read_id = db.Column(db.Integer, primary_key=True)
    notice_id = db.Column(
        db.Integer,
        db.ForeignKey("portal_notices.notice_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    read_at = db.Column(db.DateTime, nullable=False, default=manila_now)

    __table_args__ = (
        db.UniqueConstraint("notice_id", "user_id", name="uq_portal_notice_reads_notice_user"),
    )

    user = db.relationship("User", foreign_keys=[user_id])
