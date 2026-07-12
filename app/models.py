from datetime import datetime
from decimal import Decimal

from werkzeug.security import check_password_hash, generate_password_hash

from app import db


def _money(value):
    if value is None:
        return None
    return round(float(value), 2)


class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120))
    role = db.Column(db.String(20), default="Admin")
    status = db.Column(db.String(20), default="Active")
    member_id = db.Column(db.Integer, db.ForeignKey("members.member_id"), nullable=True)
    comfort_text_size = db.Column(db.String(20), default="standard", nullable=False)
    comfort_high_contrast = db.Column(db.Boolean, default=False, nullable=False)

    linked_member = db.relationship("Member", foreign_keys=[member_id])

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


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
    beneficiary_name = db.Column(db.String(120))
    beneficiary_address = db.Column(db.String(255))
    beneficiary_phone = db.Column(db.String(30))
    status = db.Column(db.String(20), default="Active")
    termination_date = db.Column(db.Date)
    termination_type = db.Column(db.String(60))
    lifetime_cap_enabled = db.Column(db.Boolean, default=True)
    lifetime_cap_amount = db.Column(db.Numeric(14, 2), default=50000000)

    referrer = db.relationship("Member", remote_side=[member_id], backref="referrals")

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
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CmsEcosystemPage(db.Model):
    __tablename__ = "cms_ecosystem_pages"

    slug = db.Column(db.String(40), primary_key=True)
    data = db.Column(db.JSON, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CmsRegistryPartner(db.Model):
    __tablename__ = "cms_registry_partners"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    partner_type = db.Column(db.String(20), nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    data = db.Column(db.JSON, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
