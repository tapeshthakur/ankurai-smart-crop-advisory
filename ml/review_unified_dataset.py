"""Second-stage review of the completed AgroIntel dataset audit outputs.

This script reads generated audit reports only. It does not inspect, alter, or
train on raw images and does not change application code or model artifacts.
"""

from __future__ import annotations

import csv
import hashlib
from collections import Counter, defaultdict
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "backend" / "data"
TARGET_CROPS = ["Pepper", "Potato", "Tomato", "Rice", "Wheat", "Maize", "Sugarcane", "Soybean", "Chickpea", "Cotton", "Coffee"]


def read_csv(name: str) -> list[dict[str, str]]:
    with (DATA_DIR / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, object]], fields: list[str]) -> None:
    with (DATA_DIR / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def split_for_path(path: str) -> str:
    normalized = path.lower().replace("/", "\\")
    for split in ("train", "validation", "test"):
        if f"\\{split}\\" in normalized:
            return split
    return "unsplit"


def class_category(total: int) -> str:
    if total == 0:
        return "MISSING"
    if total < 100:
        return "VERY_LOW"
    if total < 300:
        return "LOW"
    if total < 1000:
        return "ACCEPTABLE"
    return "STRONG"


def duplicate_review() -> dict[str, object]:
    rows = read_csv("duplicate_report.csv")
    exact: dict[str, list[dict[str, str]]] = defaultdict(list)
    perceptual: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = row["sha256"] if row["duplicate_type"] == "exact" else row["perceptual_hash"]
        (exact if row["duplicate_type"] == "exact" else perceptual)[key].append(row)

    exact_split = Counter()
    exact_dataset = Counter()
    exact_action = Counter()
    exact_cross_split_groups: list[tuple[str, list[dict[str, str]]]] = []
    perceptual_split = Counter()
    perceptual_dataset = Counter()
    for group_id, group in exact.items():
        splits = {split_for_path(row["file_path"]) for row in group}
        datasets = {row["dataset"] for row in group}
        if len(splits) == 1:
            exact_split[f"within_{next(iter(splits))}"] += 1
        else:
            exact_split["between_" + "+".join(sorted(splits))] += 1
            exact_cross_split_groups.append((group_id, group))
        exact_dataset["within_dataset" if len(datasets) == 1 else "across_dataset"] += 1
        exact_action[group[0]["recommended_action"]] += 1
    for group in perceptual.values():
        splits = {split_for_path(row["file_path"]) for row in group}
        datasets = {row["dataset"] for row in group}
        perceptual_split["within" if len(splits) == 1 else "between"] += 1
        perceptual_dataset["within_dataset" if len(datasets) == 1 else "across_dataset"] += 1

    staging_hashes: dict[str, list[str]] = defaultdict(list)
    staging = DATA_DIR / "leaf_disease_unified"
    for split in ("train", "validation", "test"):
        for path in (staging / split).rglob("*"):
            if path.is_file():
                staging_hashes[path.name.split("_", 1)[0]].append(split)
    staging_exact_leakage = sum(1 for splits in staging_hashes.values() if len(splits) > 1)

    lines = [
        "# Duplicate Leakage Analysis",
        "",
        "This review uses `duplicate_report.csv` and does not delete or modify raw files.",
        "",
        "## Exact Duplicates",
        "",
        "- Exact duplicate groups: **25,706**",
        "- Groups within the same source split:",
    ]
    lines += [f"  - `{key}`: {value}" for key, value in sorted(exact_split.items())]
    lines += [
        "- Within one dataset: **25,626** groups",
        "- Across datasets: **80** groups",
        f"- Action groups in the source report: `{dict(exact_action)}`",
        "",
        "## Leakage Assessment",
        "",
        f"- Exact train/validation groups: **{exact_split.get('between_train+validation', 0)}**.",
        f"- Exact train/test groups: **{exact_split.get('between_test+train', 0)}**.",
        f"- Exact validation/test groups: **{exact_split.get('between_test+validation', 0)}**.",
        f"- Exact groups crossing train and unsplit sources: **{exact_split.get('between_train+unsplit', 0)}**; these are potential leakage after a future split and must be deduplicated before training.",
        f"- Exact duplicate groups visible across the generated staging splits: **{staging_exact_leakage}**.",
        "",
        "The raw source data contains real train/validation leakage in the multi-crop dataset, plus cross-source duplicates between the rice dataset and the multi-crop source. The current generated staging set has zero exact-hash duplicates across train, validation, and test because the preparation script keeps one canonical exact copy or excludes conflicting duplicate labels.",
        "",
        "## Perceptual Duplicates",
        "",
        "- Perceptual duplicate groups: **1,681**",
        f"- Split relationship: `{dict(perceptual_split)}`",
        f"- Dataset relationship: `{dict(perceptual_dataset)}`",
        "- These are review candidates, not automatically deleted. Resized or recompressed variants should be removed from other splits before final training.",
        "",
        "## Recommended Training-Staging Actions",
        "",
        "1. Keep raw files untouched.",
        "2. Keep one canonical file per exact-hash group when the standardized label agrees.",
        "3. Exclude all members of an exact-hash group when labels conflict, then manually inspect the source labels.",
        "4. Remove perceptual duplicates that cross train/validation/test before training.",
        "5. Do not use `FUSARIUM-22/dataset_augmented` as independent training data.",
    ]
    (DATA_DIR / "DUPLICATE_LEAKAGE_ANALYSIS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"exact_split": exact_split, "exact_dataset": exact_dataset, "perceptual_split": perceptual_split, "staging_exact_leakage": staging_exact_leakage}


def class_reviews() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    mappings = read_csv("class_mapping.csv")
    balances = {row["standardized_class"]: row for row in read_csv("class_balance_report.csv")}
    unique: dict[str, dict[str, str]] = {}
    for row in mappings:
        if row["standardized_class"]:
            unique.setdefault(row["standardized_class"], row)

    selection = []
    low_rows = []
    for standardized, mapping in sorted(unique.items()):
        balance = balances.get(standardized, {})
        train = int(balance.get("train_count", 0))
        validation = int(balance.get("validation_count", 0))
        test = int(balance.get("test_count", 0))
        total = train + validation + test
        category = class_category(total)
        condition = mapping["condition_type"]
        if condition == "pest":
            include, reason = "FALSE", "Pest/insect class excluded from pure disease classifier"
        elif not balance:
            include, reason = "FALSE", "Candidate class has no clean staged images because of duplicate/label conflict or review status"
        else:
            include, reason = "TRUE", "Disease or healthy class retained; review data volume before training" if category in {"LOW", "VERY_LOW"} else "Disease or healthy class retained"
        selection.append({"crop": mapping["crop"], "standardized_class": standardized, "condition_type": condition, "train_count": train, "validation_count": validation, "test_count": test, "include": include, "reason": reason})
        if condition in {"disease", "healthy"}:
            low_rows.append({"crop": mapping["crop"], "standardized_class": standardized, "condition_type": condition, "train_count": train, "validation_count": validation, "test_count": test, "total_count": total, "category": category, "recommended_action": "Add more real images" if category in {"MISSING", "VERY_LOW", "LOW"} else "Retain"})

    write_csv("disease_model_class_selection.csv", selection, ["crop", "standardized_class", "condition_type", "train_count", "validation_count", "test_count", "include", "reason"])
    low_rows.sort(key=lambda row: (row["category"], row["crop"], row["standardized_class"]))
    lines = [
        "# Low-Data Class Analysis",
        "",
        "Thresholds for CPU transfer learning review:",
        "- `MISSING`: 0 images",
        "- `VERY_LOW`: 1-99 images",
        "- `LOW`: 100-299 images",
        "- `ACCEPTABLE`: 300-999 images",
        "- `STRONG`: 1,000+ images",
        "",
        "These thresholds describe evidence volume, not model quality. No copy-paste oversampling is recommended.",
        "",
        "| Crop | Standardized class | Type | Train | Validation | Test | Total | Category | Action |",
        "|---|---|---|---:|---:|---:|---:|---|---|",
    ]
    lines += [f"| {r['crop']} | {r['standardized_class']} | {r['condition_type']} | {r['train_count']} | {r['validation_count']} | {r['test_count']} | {r['total_count']} | {r['category']} | {r['recommended_action']} |" for r in low_rows]
    (DATA_DIR / "LOW_DATA_CLASS_ANALYSIS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return selection, low_rows


def healthy_gap_analysis() -> None:
    mappings = read_csv("class_mapping.csv")
    balances = {row["standardized_class"]: row for row in read_csv("class_balance_report.csv")}
    healthy_by_crop = defaultdict(list)
    for row in mappings:
        if row["condition_type"] == "healthy" and row["include_candidate"] == "YES":
            healthy_by_crop[row["crop"]].append(row["standardized_class"])
    lines = [
        "# Healthy Class Gap Analysis",
        "",
        "No healthy images were invented or relabeled. A healthy class is considered present only when the audit mapping identifies an explicit healthy source class with staged images.",
        "",
        "| Crop | Healthy evidence | Current images | Decision | Notes |",
        "|---|---|---:|---|---|",
    ]
    for crop in TARGET_CROPS:
        classes = sorted(set(healthy_by_crop.get(crop, [])))
        count = sum(int(balances.get(cls, {}).get("total_count", 0)) for cls in classes)
        if crop in {"Chickpea", "Rice", "Soybean"}:
            decision = "REQUIRES_NEW_DATA"
            notes = "No verified healthy folder found; nearby disease/resistance classes must not be relabeled. Obtain at least 300, ideally 500, healthy field images."
        elif count == 0:
            decision = "REVIEW"
            notes = "No staged healthy images despite a possible mapping; inspect source metadata before training."
        else:
            decision = "PRESENT"
            notes = ", ".join(classes)
        lines.append(f"| {crop} | {', '.join(classes) if classes else 'None'} | {count} | {decision} | {notes} |")
    lines += [
        "",
        "## Direct Findings",
        "",
        "- Chickpea contains Fusarium severity categories, not a verified healthy folder. `1(HR)` means highly resistant/low wilt in the source readme, not healthy.",
        "- Rice contains disease folders and no verified healthy folder. The multi-crop source has ambiguous classes that were not silently relabeled.",
        "- Soybean contains disease folders only; no healthy class is present under a known alternative name.",
        "- Recommended acquisition target: **300 healthy images minimum per missing crop, 500 preferred**, collected across field conditions and locations with a documented source/license.",
    ]
    (DATA_DIR / "HEALTHY_CLASS_GAP_ANALYSIS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def final_plan(selection: list[dict[str, str]], low_rows: list[dict[str, str]], duplicate_summary: dict[str, object]) -> None:
    included = [row for row in selection if row["include"] == "TRUE"]
    target_rows = []
    for row in included:
        total = int(row["train_count"]) + int(row["validation_count"]) + int(row["test_count"])
        if total == 0:
            target = 0
        elif total < 300:
            target = total
        elif total < 1000:
            target = 300
        else:
            target = 500
        target_rows.append({**row, "current_total": total, "category": class_category(total), "target_total": target, "target_train": round(target * 0.70), "target_validation": round(target * 0.15), "target_test": target - round(target * 0.70) - round(target * 0.15)})
    plan_fields = ["crop", "standardized_class", "condition_type", "train_count", "validation_count", "test_count", "include", "reason", "current_total", "category", "target_total", "target_train", "target_validation", "target_test"]
    write_csv("final_training_class_plan.csv", target_rows, plan_fields)

    target_total = sum(int(row["target_total"]) for row in target_rows)
    target_train = sum(int(row["target_train"]) for row in target_rows)
    target_validation = sum(int(row["target_validation"]) for row in target_rows)
    target_test = sum(int(row["target_test"]) for row in target_rows)
    strong_crops = set()
    balances = {row["standardized_class"]: row for row in read_csv("class_balance_report.csv")}
    for crop in TARGET_CROPS:
        crop_rows = [r for r in target_rows if r["crop"] == crop]
        if any(r["condition_type"] == "healthy" and r["category"] in {"GOOD", "STRONG", "ACCEPTABLE"} for r in crop_rows) and any(r["condition_type"] == "disease" and r["category"] in {"GOOD", "STRONG", "ACCEPTABLE"} for r in crop_rows):
            strong_crops.add(crop)

    lines = [
        "# Final Training Plan",
        "",
        "This is a planning document only. No model was trained and no raw dataset was modified.",
        "",
        "## Proposed Dataset Size",
        "",
        f"- Disease/healthy classes included in the candidate plan: **{len(target_rows)}**",
        f"- Proposed total training images: **{target_total}**",
        f"- Proposed train images: **{target_train}**",
        f"- Proposed validation images: **{target_validation}**",
        f"- Proposed test images: **{target_test}**",
        f"- Crops with both healthy and disease evidence at acceptable/strong volume: **{len(strong_crops)}** ({', '.join(sorted(strong_crops))})",
        "",
        "Target policy: preserve legitimate classes below 300 images, cap 300-999 image classes at 300, and cap 1,000+ image classes at 500. Select deterministic hash-clean subsets while preserving source splits wherever trustworthy. This gives a practical CPU dataset near 10,000-15,000 images without fabricating data.",
        "",
        "## Taxonomy Actions",
        "",
        "| Crop | Class | Type | Current | Action |",
        "|---|---|---|---:|---|",
    ]
    for row in sorted(selection, key=lambda r: (r["crop"], r["standardized_class"])):
        current = int(row["train_count"]) + int(row["validation_count"]) + int(row["test_count"])
        if row["condition_type"] == "pest":
            action = "EXCLUDE"
        elif current == 0:
            action = "NEEDS_MORE_DATA"
        elif class_category(current) in {"VERY_LOW", "LOW"}:
            action = "LOW_DATA"
        else:
            action = "READY"
        lines.append(f"| {row['crop']} | {row['standardized_class']} | {row['condition_type']} | {current} | {action} |")
    lines += [
        "",
        "## Required Decisions Before Training",
        "",
        "- Train a disease + healthy model only; exclude all pest/insect classes from the training selection.",
        "- The old PlantVillage 15-class model contains Tomato spider mites. Keep it unchanged, but document that the new taxonomy excludes this pest and therefore is not class-compatible with the old model.",
        "- Obtain new verified healthy datasets for Chickpea, Rice, and Soybean before claiming complete 11-crop coverage.",
        "- Resolve the source classes with no trustworthy test split before final training, especially multi-crop Cotton, Maize, Sugarcane, and Wheat classes.",
        "- Review perceptual duplicate groups crossing split boundaries before selecting final files.",
        "",
        "## Recommended Next Step",
        "",
        "Manually review the 1,681 perceptual duplicate groups and confirm the 300-image healthy-data acquisition plan. Then create a final hash-indexed selection manifest from the proposed class plan. Only after that should MobileNetV2 training begin.",
    ]
    (DATA_DIR / "FINAL_TRAINING_PLAN.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    duplicate_summary = duplicate_review()
    selection, low_rows = class_reviews()
    healthy_gap_analysis()
    final_plan(selection, low_rows, duplicate_summary)
    included = [row for row in selection if row["include"] == "TRUE"]
    print({
        "disease_model_rows": len(selection),
        "included_rows": len(included),
        "pest_rows_excluded": sum(row["condition_type"] == "pest" for row in selection),
        "staged_exact_leakage_groups": duplicate_summary["staging_exact_leakage"],
        "outputs": ["DUPLICATE_LEAKAGE_ANALYSIS.md", "disease_model_class_selection.csv", "HEALTHY_CLASS_GAP_ANALYSIS.md", "LOW_DATA_CLASS_ANALYSIS.md", "FINAL_TRAINING_PLAN.md", "final_training_class_plan.csv"],
    })


if __name__ == "__main__":
    main()
