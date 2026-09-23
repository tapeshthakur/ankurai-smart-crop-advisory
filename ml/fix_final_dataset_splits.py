"""Repair split vocabulary using only the existing final generated dataset."""

from __future__ import annotations

import csv
import random
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "backend" / "data"
SOURCE = DATA / "leaf_disease_final"
FIXED = DATA / "leaf_disease_final_fixed"
BACKUP = DATA / "leaf_disease_final_before_split_fix"
SPLITS = ("train", "validation", "test")
SEED = 20260909
MIN_IMAGES_FOR_THREE_SPLITS = 6


def read_plan() -> dict[str, dict[str, str]]:
    plan_path = DATA / "final_training_class_plan.csv"
    with plan_path.open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.DictReader(handle)
        return {
            row["standardized_class"]: row
            for row in rows
            if row.get("include", "").strip().upper() == "TRUE"
        }


def class_sets() -> dict[str, set[str]]:
    return {
        split: {
            path.name
            for path in (SOURCE / split).iterdir()
            if path.is_dir()
        }
        for split in SPLITS
    }


def files_for(split: str, class_name: str) -> list[Path]:
    source_dir = SOURCE / split / class_name
    if not source_dir.exists():
        return []
    return sorted(
        path
        for path in source_dir.iterdir()
        if path.is_file()
    )


def partition(paths: list[Path]) -> dict[str, list[Path]]:
    shuffled = list(paths)
    random.Random(f"{SEED}:{paths[0].parent.name}").shuffle(shuffled)
    n = len(shuffled)
    validation_count = max(1, round(n * 0.15))
    test_count = max(1, round(n * 0.15))
    train_count = n - validation_count - test_count
    if train_count < 1:
        raise ValueError(f"Cannot create three non-empty splits from {n} images")
    return {
        "train": shuffled[:train_count],
        "validation": shuffled[train_count : train_count + validation_count],
        "test": shuffled[train_count + validation_count :],
    }


def copy_split(assignments: dict[str, dict[str, list[Path]]]) -> None:
    if FIXED.exists():
        shutil.rmtree(FIXED)
    for split in SPLITS:
        for class_name, paths in assignments[split].items():
            destination = FIXED / split / class_name
            destination.mkdir(parents=True, exist_ok=True)
            for source_path in paths:
                shutil.copy2(source_path, destination / source_path.name)


def verify() -> tuple[list[str], dict[str, int]]:
    sets = {
        split: {
            path.name
            for path in (FIXED / split).iterdir()
            if path.is_dir()
        }
        for split in SPLITS
    }
    if not (sets["train"] == sets["validation"] == sets["test"]):
        raise RuntimeError("Corrected split class vocabularies are not identical")
    counts = {}
    for split in SPLITS:
        counts[split] = sum(
            1
            for class_name in sets[split]
            for path in (FIXED / split / class_name).iterdir()
            if path.is_file()
        )
        if any(
            not any((FIXED / split / class_name).iterdir())
            for class_name in sets[split]
        ):
            raise RuntimeError(f"Empty class in {split}")
    return sorted(sets["train"]), counts


def write_distribution(classes: list[str], plan: dict[str, dict[str, str]]) -> None:
    output = DATA / "final_class_distribution.csv"
    fields = ["crop", "class", "condition_type", "train", "validation", "test", "total", "status"]
    rows = []
    for class_name in classes:
        row = plan[class_name]
        counts = {
            split: len(files_for_fixed(split, class_name)) for split in SPLITS
        }
        rows.append(
            {
                "crop": row["crop"],
                "class": class_name,
                "condition_type": row["condition_type"],
                "train": counts["train"],
                "validation": counts["validation"],
                "test": counts["test"],
                "total": sum(counts.values()),
                "status": "READY_AFTER_SPLIT_FIX",
            }
        )
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda item: (item["crop"], item["class"])))


def files_for_fixed(split: str, class_name: str) -> list[Path]:
    source_dir = SOURCE / split / class_name
    if not source_dir.exists():
        return []
    return [path for path in source_dir.iterdir() if path.is_file()]


def write_readiness(classes: list[str], plan: dict[str, dict[str, str]], counts: dict[str, int], excluded: list[tuple[str, int]]) -> None:
    by_crop: dict[str, list[str]] = defaultdict(list)
    for class_name in classes:
        by_crop[plan[class_name]["crop"]].append(class_name)
    lines = [
        "# AgroIntel 11-Crop Disease Model Readiness",
        "",
        "This report describes the corrected final generated dataset. No raw datasets were scanned or modified, and no model was trained.",
        "",
        f"- Classes: {len(classes)}",
        f"- Images: train {counts['train']}, validation {counts['validation']}, test {counts['test']}",
        "- Split vocabulary: identical across train, validation, and test",
        "- Excluded from this corrected training dataset because they have fewer than six existing images: "
        + (", ".join(f"{name} ({count})" for name, count in excluded) if excluded else "none")
        + ".",
        "",
        "## Crop Status",
    ]
    for crop in sorted(by_crop):
        crop_classes = sorted(by_crop[crop])
        image_count = sum(
            len(files_for_fixed(split, class_name))
            for split in SPLITS
            for class_name in crop_classes
        )
        healthy = [name for name in crop_classes if plan[name]["condition_type"] == "healthy"]
        disease = [name for name in crop_classes if plan[name]["condition_type"] == "disease"]
        lines.extend(
            [
                f"\n### {crop}",
                "status: READY_AFTER_SPLIT_FIX",
                "disease classes: " + (", ".join(disease) if disease else "none"),
                "healthy: " + (", ".join(healthy) if healthy else "MISSING"),
                f"image count: {image_count}",
            ]
        )
    (DATA / "FINAL_11_CROP_READINESS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    plan = read_plan()
    existing = class_sets()
    union = set.union(*existing.values())
    unexpected = union - set(plan)
    if unexpected:
        raise RuntimeError(f"Final dataset contains classes not in the final plan: {sorted(unexpected)}")

    train_only = sorted(existing["train"] - existing["validation"] - existing["test"])
    validation_only = sorted(existing["validation"] - existing["train"] - existing["test"])
    test_only = sorted(existing["test"] - existing["train"] - existing["validation"])
    common = existing["train"] & existing["validation"] & existing["test"]

    all_files: dict[str, list[Path]] = {}
    excluded: list[tuple[str, int]] = []
    repaired: list[str] = []
    assignments = {split: {} for split in SPLITS}
    for class_name in sorted(union):
        paths_by_split = {split: files_for(split, class_name) for split in SPLITS}
        combined = [path for split in SPLITS for path in paths_by_split[split]]
        all_files[class_name] = combined
        if len(combined) < MIN_IMAGES_FOR_THREE_SPLITS:
            excluded.append((class_name, len(combined)))
            continue
        if class_name in common:
            for split in SPLITS:
                assignments[split][class_name] = paths_by_split[split]
        else:
            repaired.append(class_name)
            split_paths = partition(combined)
            for split in SPLITS:
                assignments[split][class_name] = split_paths[split]

    copy_split(assignments)
    classes, counts = verify()
    if BACKUP.exists():
        raise RuntimeError(f"Backup already exists; refusing to replace {SOURCE}: {BACKUP}")
    SOURCE.rename(BACKUP)
    FIXED.rename(SOURCE)

    # Reports must describe the now-active dataset, so point the helpers at the new path.
    write_distribution(classes, plan)
    write_readiness(classes, plan, counts, excluded)
    report = [
        "# Final Split Fix Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Previous vocabulary",
        f"- train classes: {len(existing['train'])}",
        f"- validation classes: {len(existing['validation'])}",
        f"- test classes: {len(existing['test'])}",
        f"- train_only: {', '.join(train_only) or 'none'}",
        f"- validation_only: {', '.join(validation_only) or 'none'}",
        f"- test_only: {', '.join(test_only) or 'none'}",
        f"- common_to_all: {len(common)} classes",
        "",
        "## Corrected dataset",
        f"- corrected classes: {len(classes)}",
        f"- train images: {counts['train']}",
        f"- validation images: {counts['validation']}",
        f"- test images: {counts['test']}",
        "- train_only: 0",
        "- validation_only: 0",
        "- test_only: 0",
        "- all classes have non-empty train, validation, and test folders: yes",
        "- all three splits have identical class vocabulary: yes",
        "",
        "## Repair decisions",
        f"- Classes requiring deterministic split repair: {', '.join(repaired) or 'none'}",
        f"- Classes excluded as too small: {', '.join(f'{name} ({count} images)' for name, count in excluded) or 'none'}",
        "- Chickpea Fusarium severity folders were not merged: the existing class mapping and final plan retain HR, HS, MR, R, and S as separate standardized classes.",
        "- Rice Bacterial leaf blight and Becterial Blight were not merged: the existing class mapping and final plan retain them as separate standardized classes; no taxonomy was guessed.",
        "- No raw dataset, application code, model, or training process was modified.",
    ]
    (DATA / "FINAL_SPLIT_FIX_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"classes={len(classes)}")
    print(f"train={counts['train']} validation={counts['validation']} test={counts['test']}")
    print("train_only=0 validation_only=0 test_only=0")
    print(f"excluded={excluded}")
    print(f"dataset={SOURCE}")


if __name__ == "__main__":
    main()
