"""Update members.xlsx to the new member column schema."""

from pathlib import Path

import pandas as pd

MEMBER_COLUMNS = [
    "member_id",
    "batch",
    "referrer_id",
    "date_joined",
    "last_name",
    "first_name",
    "middle_name",
    "suffix",
    "address",
    "phone",
    "email",
    "birth_date",
    "gender",
    "civil_status",
    "highest_education",
    "occupation_income_source",
    "monthly_income",
    "number_of_dependents",
    "beneficiary_name",
    "beneficiary_address",
    "beneficiary_phone",
    "status",
    "termination_date",
    "termination_type",
]


def main():
    path = Path(__file__).resolve().parent.parent / "data" / "members.xlsx"
    xl = pd.ExcelFile(path)
    members = pd.read_excel(path, sheet_name="members").copy()
    contractors = pd.read_excel(path, sheet_name="contractors") if "contractors" in xl.sheet_names else None

    if "phone" not in members.columns and "cp_no" in members.columns:
        members["phone"] = members["cp_no"]

    if "membership_type" in members.columns:
        members = members.drop(columns=["membership_type"])

    if "status" not in members.columns:
        members["status"] = "Active"

    for col in MEMBER_COLUMNS:
        if col not in members.columns:
            members[col] = None

    members = members[MEMBER_COLUMNS]

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        members.to_excel(writer, sheet_name="members", index=False)
        if contractors is not None:
            contractors.to_excel(writer, sheet_name="contractors", index=False)

    print(f"Updated {path} ({len(members)} member rows)")


if __name__ == "__main__":
    main()
