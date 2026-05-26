"""
Find whether businesses tied to api.py random review IDs share an address
with other Yelp businesses.

Only considers the review_ids hardcoded in api.py (the pool used by the API).
"""

import argparse
import ast
import json
import os
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
API_PATH = PROJECT_ROOT / "api.py"
DEFAULT_SOURCE = DATA_DIR / "yelp_academic_dataset_business.json"
DEFAULT_REVIEW_SOURCE = DATA_DIR / "yelp_academic_dataset_review.json"
DEFAULT_OUTPUT = DATA_DIR / "duplicate_addresses_api_reviews.json"


def load_api_review_ids() -> list[str]:
    """Read review_ids from api.py without importing Flask."""
    tree = ast.parse(API_PATH.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "review_ids":
                    value = ast.literal_eval(node.value)
                    if not isinstance(value, list):
                        raise ValueError("api.py review_ids is not a list")
                    return value
    raise ValueError("Could not find review_ids in api.py")


def normalize_part(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def build_address_key(biz: dict[str, Any]) -> tuple[str, ...] | None:
    street = normalize_part(biz.get("address"))
    if not street:
        return None

    return (
        street,
        normalize_part(biz.get("city")),
        normalize_part(biz.get("state")),
        normalize_part(biz.get("postal_code")),
    )


def format_full_address(
    address: str, city: str, state: str, postal_code: str
) -> str:
    parts = [p for p in [address, city, state] if p]
    line = ", ".join(parts)
    if postal_code:
        line = f"{line} {postal_code}".strip() if line else postal_code
    return line


def map_review_ids_to_business_ids(
    review_path: Path, review_ids: list[str]
) -> dict[str, str]:
    """Look up business_id for each review_id in the Yelp review dataset."""
    remaining = set(review_ids)
    mapping: dict[str, str] = {}

    with review_path.open("r", encoding="utf-8-sig") as f:
        for line in f:
            if not remaining:
                break
            line = line.strip()
            if not line:
                continue
            try:
                review = json.loads(line)
            except json.JSONDecodeError:
                continue

            review_id = review.get("review_id")
            if review_id in remaining:
                mapping[review_id] = review["business_id"]
                remaining.remove(review_id)

    if remaining:
        missing = ", ".join(sorted(remaining))
        raise ValueError(
            f"Could not find {len(remaining)} review_id(s) in {review_path}: {missing}"
        )

    return mapping


def build_address_groups(business_path: Path) -> dict[tuple[str, ...], dict[str, Any]]:
    """Index all businesses by normalized address."""
    groups: dict[tuple[str, ...], dict[str, Any]] = {}

    with business_path.open("r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                biz = json.loads(line)
            except json.JSONDecodeError:
                continue

            key = build_address_key(biz)
            if key is None:
                continue

            entry = {
                "business_id": biz["business_id"],
                "name": biz.get("name", ""),
            }

            if key not in groups:
                groups[key] = {
                    "address": (biz.get("address") or "").strip(),
                    "city": (biz.get("city") or "").strip(),
                    "state": (biz.get("state") or "").strip(),
                    "postal_code": (biz.get("postal_code") or "").strip(),
                    "businesses": [entry],
                }
            else:
                groups[key]["businesses"].append(entry)

    return groups


def find_api_review_duplicate_memberships(
    business_path: Path,
    review_path: Path,
    review_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    For each api.py review_id, report its business and whether that business
    shares an address with any other Yelp business.
    """
    review_ids = review_ids or load_api_review_ids()
    review_to_business = map_review_ids_to_business_ids(review_path, review_ids)
    address_groups = build_address_groups(business_path)

    business_lookup: dict[str, dict[str, Any]] = {}
    for group in address_groups.values():
        for biz in group["businesses"]:
            business_lookup[biz["business_id"]] = group

    results: list[dict[str, Any]] = []
    for review_id in review_ids:
        business_id = review_to_business[review_id]
        biz_record = business_lookup.get(business_id)

        if biz_record is None:
            results.append(
                {
                    "review_id": review_id,
                    "business_id": business_id,
                    "business_name": None,
                    "address": None,
                    "city": None,
                    "state": None,
                    "postal_code": None,
                    "full_address": None,
                    "is_duplicate_address": False,
                    "duplicate_group": None,
                    "note": "Business not found or has no street address in dataset",
                }
            )
            continue

        businesses = biz_record["businesses"]
        is_duplicate = len(businesses) >= 2
        full_address = format_full_address(
            biz_record["address"],
            biz_record["city"],
            biz_record["state"],
            biz_record["postal_code"],
        )
        matching = next(b for b in businesses if b["business_id"] == business_id)

        duplicate_group = None
        if is_duplicate:
            duplicate_group = {
                "full_address": full_address,
                "address": biz_record["address"],
                "city": biz_record["city"],
                "state": biz_record["state"],
                "postal_code": biz_record["postal_code"],
                "count": len(businesses),
                "business_ids": [b["business_id"] for b in businesses],
                "businesses": businesses,
            }

        results.append(
            {
                "review_id": review_id,
                "business_id": business_id,
                "business_name": matching["name"],
                "address": biz_record["address"],
                "city": biz_record["city"],
                "state": biz_record["state"],
                "postal_code": biz_record["postal_code"],
                "full_address": full_address,
                "is_duplicate_address": is_duplicate,
                "duplicate_group": duplicate_group,
            }
        )

    members = [row for row in results if row["is_duplicate_address"]]
    return {
        "review_ids_checked": len(review_ids),
        "duplicate_address_members": len(members),
        "non_members": len(results) - len(members),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Check whether businesses for api.py random review IDs "
            "share an address with other Yelp businesses."
        )
    )
    parser.add_argument(
        "--source",
        default=str(DEFAULT_SOURCE),
        help=f"Path to yelp_academic_dataset_business.json (default: {DEFAULT_SOURCE})",
    )
    parser.add_argument(
        "--review-source",
        default=str(DEFAULT_REVIEW_SOURCE),
        help=f"Path to yelp_academic_dataset_review.json (default: {DEFAULT_REVIEW_SOURCE})",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=str(DEFAULT_OUTPUT),
        help=f"Path to write results as JSON (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    for label, path in (
        ("Business dataset", args.source),
        ("Review dataset", args.review_source),
    ):
        if not os.path.isfile(path):
            raise SystemExit(f"{label} not found: {path}")

    if not API_PATH.is_file():
        raise SystemExit(f"api.py not found: {API_PATH}")

    report = find_api_review_duplicate_memberships(
        Path(args.source),
        Path(args.review_source),
    )
    results = report["results"]
    members = [row for row in results if row["is_duplicate_address"]]

    print(f"Checked {report['review_ids_checked']} review IDs from api.py")
    print(f"  {report['duplicate_address_members']} share an address with other businesses")
    print(f"  {report['non_members']} do not\n")

    for row in members:
        group = row["duplicate_group"]
        print(f"review_id: {row['review_id']}")
        print(f"  business: {row['business_name']} ({row['business_id']})")
        print(f"  address:  {row['full_address']}")
        print(
            f"  shares address with {group['count'] - 1} other business(es): "
            f"{', '.join(group['business_ids'])}\n"
        )

    non_members_with_address = [
        row
        for row in results
        if not row["is_duplicate_address"] and row.get("full_address")
    ]
    if non_members_with_address:
        print("Reviews with unique addresses:")
        for row in non_members_with_address[:10]:
            print(f"  {row['review_id']}: {row['business_name']} @ {row['full_address']}")
        if len(non_members_with_address) > 10:
            print(f"  ... and {len(non_members_with_address) - 10} more")

    missing = [row for row in results if row.get("note")]
    if missing:
        print(f"\n{len(missing)} review(s) could not be matched to a business address.")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nWrote full results to {output_path}")


if __name__ == "__main__":
    main()
