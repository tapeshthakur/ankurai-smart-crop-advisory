"""Audit raw leaf-disease datasets and prepare a non-destructive staging set.

The script never edits files below backend/data's raw dataset directories. It
rebuilds only the generated reports and leaf_disease_unified directory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

from PIL import Image, UnidentifiedImageError


SEED = 42
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}
SPLITS = {"train", "validation", "test"}
TARGET_CROPS = {
    "Pepper", "Potato", "Tomato", "Rice", "Wheat", "Maize",
    "Sugarcane", "Soybean", "Chickpea", "Cotton", "Coffee",
}


@dataclass
class ImageRecord:
    dataset: str
    source_path: str
    original_class: str
    split: str
    path: Path
    standardized_class: str = ""
    crop: str = ""
    condition_type: str = "unknown"
    include_candidate: str = "REVIEW"
    notes: str = ""
    sha256: str = ""
    perceptual_hash: str = ""
    validation_status: str = "valid"
    validation_notes: str = ""


def image_files(path: Path) -> Iterable[Path]:
    return (p for p in path.rglob("*") if p.is_file())


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def map_class(dataset: str, original: str, relative_source: str) -> tuple[str, str, str, str, str]:
    """Return crop, standardized class, condition type, inclusion, notes."""
    raw = normalize_text(original)
    low = raw.lower()
    notes: list[str] = []

    if dataset == "PlantVillage":
        match = re.match(r"^(Pepper__bell|Potato|Tomato)(?:___|_)(.+)$", raw)
        if match:
            crop = "Pepper" if match.group(1) == "Pepper__bell" else match.group(1)
            condition = re.sub(r"^_+", "", match.group(2)).replace("__", "_")
            condition = condition.replace("_", " ").strip()
            standardized = f"{crop}___{condition.replace(' ', '_')}"
            condition_type = "pest" if "spider" in condition.lower() or "mite" in condition.lower() else (
                "healthy" if "healthy" in condition.lower() else "disease"
            )
            return crop, standardized, condition_type, "YES", "Original PlantVillage class preserved."
        return "", "", "unknown", "REVIEW", "Ambiguous PlantVillage folder; not included."

    if dataset == "FUSARIUM-22":
        if "augmented" in relative_source.lower():
            severity = {"1": "HR", "3": "R", "5": "MR", "7": "S", "9": "HS"}.get(raw.split("(", 1)[0].strip(), raw.split("(", 1)[0].strip())
            return "Chickpea", f"Chickpea___Fusarium_wilt_{severity}", "disease", "NO", "Augmented source excluded to prevent leakage."
        severity = {"1": "HR", "3": "R", "5": "MR", "7": "S", "9": "HS"}.get(raw.split("(", 1)[0].strip(), raw.split("(", 1)[0].strip())
        return "Chickpea", f"Chickpea___Fusarium_wilt_{severity}", "disease", "YES", "Raw severity category from FUSARIUM-22 readme. No verified healthy class."

    if dataset == "RoCoLe":
        condition = {"coffee___healthy": "healthy", "coffee___red_spider_mite": "Red_spider_mite", "coffee___rust": "Rust"}.get(low)
        if condition:
            kind = "healthy" if condition == "healthy" else ("pest" if "mite" in condition.lower() else "disease")
            return "Coffee", f"Coffee___{condition}", kind, "YES", "RoCoLe folder name used as source class."
        return "Coffee", "", "unknown", "REVIEW", "Unrecognized RoCoLe class."

    if dataset == "rice_leaf_diseases":
        known = {"bacterial leaf blight": "Bacterial_leaf_blight", "brown spot": "Brown_spot", "leaf smut": "Leaf_smut"}
        if low in known:
            return "Rice", f"Rice___{known[low]}", "disease", "YES", "Rice class confirmed by dataset folder and class name. No rice healthy class found."
        return "Rice", "", "unknown", "REVIEW", "Unrecognized rice class."

    if dataset == "Soybean_Diseased_Leaf":
        aliases = {
            "bacterial_blight": "Bacterial_blight", "brown_spot": "Brown_spot", "crestamento": "Crestamento",
            "ferrugen": "Ferrugen", "mossaic virus": "Mossaic_Virus", "powdery_mildew": "Powdery_mildew",
            "septoria": "Septoria", "southern blight": "Southern_blight", "sudden death syndrone": "Sudden_Death_Syndrone",
            "yellow mosaic": "Yellow_Mosaic",
        }
        if low in aliases:
            return "Soybean", f"Soybean___{aliases[low]}", "disease", "YES", "Original spelling preserved in mapping; standardized label is separate. No verified healthy class found."
        return "Soybean", "", "unknown", "REVIEW", "Unrecognized soybean class."

    if dataset == "20k_Multi_Class_Crop_Disease":
        explicit = [
            ("cotton", "Cotton"), ("rice", "Rice"), ("maize", "Maize"),
            ("sugarcane", "Sugarcane"), ("wheat", "Wheat"),
        ]
        crop = next((crop for token, crop in explicit if token in low), None)
        healthy = "healthy" in low
        pest_tokens = ("bollworm", "army worm", "aphid", "mealy bug", "whitefly", "stem borer", "fall armyworm", "thrips", "thirps", "mite", "stem fly", "red cotton bug")
        pest = any(token in low for token in pest_tokens)
        if crop and (healthy or pest or any(token in low for token in ("blight", "anthracnose", "bollrot", "brown", "rust", "smut", "curl", "spot", "blast", "tungro", "mosaic", "rot", "scab", "mildew", "wilt", "leaf"))):
            if healthy:
                condition = "healthy"
                kind = "healthy"
            elif pest:
                condition = re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_")
                kind = "pest"
            else:
                condition = re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_")
                kind = "disease"
            condition = re.sub(rf"(^|_){crop}(?=_|$)", "_", condition, flags=re.IGNORECASE)
            condition = re.sub(r"(^|_)(in|on)(?=_|$)", "_", condition, flags=re.IGNORECASE)
            condition = re.sub(r"_+", "_", condition).strip("_") or "unknown"
            if condition.lower() == "healthy":
                condition = "healthy"
            else:
                condition = "_".join(token[:1].upper() + token[1:] for token in condition.split("_"))
            return crop, f"{crop}___{condition}", kind, "YES", "Mapped from explicit crop name in multi-crop dataset."
        return "", "", "unknown", "REVIEW", "Crop or condition is ambiguous; review before training."

    return "", "", "unknown", "REVIEW", "Dataset is not recognized by the mapping rules."


def discover_records(data_dir: Path) -> list[ImageRecord]:
    records: list[ImageRecord] = []
    roots = {
        "PlantVillage": data_dir / "PlantVillage",
        "FUSARIUM-22": data_dir / "FUSARIUM-22",
        "rice_leaf_diseases": data_dir / "rice_leaf_diseases",
        "RoCoLe": data_dir / "RoCoLe",
        "Soybean_Diseased_Leaf": data_dir / "Soybean_Diseased_Leaf",
        "20k_Multi_Class_Crop_Disease": data_dir / "20k_Multi_Class_Crop_Disease",
    }

    for dataset, root in roots.items():
        if not root.exists():
            continue
        for file in image_files(root):
            relative = file.relative_to(root)
            parts = relative.parts
            if dataset == "PlantVillage":
                class_name = parts[-2] if len(parts) >= 2 else ""
                split = "unsplit"
            elif dataset == "FUSARIUM-22":
                if len(parts) < 3:
                    continue
                class_name, split = parts[-2], "unsplit"
            elif dataset == "20k_Multi_Class_Crop_Disease":
                if len(parts) < 3 or parts[0].lower() not in {"train", "validation", "test"}:
                    continue
                split, class_name = parts[0].lower(), parts[-2]
            else:
                class_name, split = parts[-2] if len(parts) >= 2 else "", "unsplit"
            source = str(file.relative_to(data_dir.parent.parent))
            crop, standardized, condition_type, include, notes = map_class(dataset, class_name, str(relative))
            records.append(ImageRecord(dataset, source, class_name, split, file, standardized, crop, condition_type, include, notes))
    return records


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def perceptual_hash(path: Path) -> str:
    with Image.open(path) as image:
        image = image.convert("L").resize((16, 16))
        pixels = list(image.getdata())
    average = sum(pixels) / len(pixels)
    return "".join("1" if pixel >= average else "0" for pixel in pixels)


def validate_image(path: Path) -> tuple[str, str]:
    if path.suffix.lower() not in IMAGE_EXTENSIONS:
        return "unsupported_format", "File extension is not a supported image format."
    if path.stat().st_size == 0:
        return "zero_byte", "File is empty."
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
            if width < 32 or height < 32:
                return "extreme_dimensions", f"Very small image: {width}x{height}."
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        return "corrupt", str(exc)
    return "valid", ""


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def split_unsplit_records(records: list[ImageRecord]) -> None:
    grouped: dict[str, list[ImageRecord]] = defaultdict(list)
    for record in records:
        if record.split == "unsplit" and record.include_candidate == "YES" and record.validation_status == "valid":
            grouped[record.standardized_class].append(record)
    rng = random.Random(SEED)
    for group in grouped.values():
        rng.shuffle(group)
        total = len(group)
        train_end = int(total * 0.70)
        validation_end = train_end + int(total * 0.15)
        for index, record in enumerate(group):
            record.split = "train" if index < train_end else "validation" if index < validation_end else "test"


def apply_duplicate_policy(records: list[ImageRecord]) -> tuple[dict[str, list[ImageRecord]], dict[str, list[ImageRecord]]]:
    exact: dict[str, list[ImageRecord]] = defaultdict(list)
    perceptual: dict[str, list[ImageRecord]] = defaultdict(list)
    for record in records:
        if record.validation_status != "valid" or record.path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        record.sha256 = sha256_file(record.path)
        try:
            record.perceptual_hash = perceptual_hash(record.path)
        except Exception as exc:
            record.validation_status = "unreadable"
            record.validation_notes = str(exc)
            continue
        exact[record.sha256].append(record)
        perceptual[record.perceptual_hash].append(record)

    priority = {"PlantVillage": 0, "20k_Multi_Class_Crop_Disease": 1, "rice_leaf_diseases": 2, "RoCoLe": 3, "Soybean_Diseased_Leaf": 4, "FUSARIUM-22": 5}
    for group in exact.values():
        if len(group) < 2:
            continue
        classes = {r.standardized_class for r in group if r.standardized_class}
        if len(classes) > 1:
            for record in group:
                record.include_candidate = "NO"
                record.notes += " Exact duplicate conflicts with another class; excluded from staging."
        else:
            keeper = sorted(group, key=lambda r: (priority.get(r.dataset, 99), str(r.path).lower()))[0]
            for record in group:
                if record is not keeper:
                    record.include_candidate = "NO"
                    record.notes += " Exact duplicate; kept higher-priority source only."
    return exact, perceptual


def stage_records(records: list[ImageRecord], staging: Path) -> None:
    if staging.exists():
        shutil.rmtree(staging)
    for split in ("train", "validation", "test"):
        (staging / split).mkdir(parents=True, exist_ok=True)
    counters: Counter[str] = Counter()
    for record in records:
        if record.include_candidate != "YES" or record.validation_status != "valid" or record.split not in SPLITS:
            continue
        if not record.standardized_class or not record.sha256:
            continue
        destination_dir = staging / record.split / record.standardized_class
        destination_dir.mkdir(parents=True, exist_ok=True)
        counters[record.sha256] += 1
        destination = destination_dir / f"{record.sha256[:16]}_{record.path.name}"
        shutil.copy2(record.path, destination)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit and stage AgroIntel crop-disease datasets")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    data_dir = project_root / "backend" / "data"
    staging = data_dir / "leaf_disease_unified"
    records = discover_records(data_dir)

    for record in records:
        record.validation_status, record.validation_notes = validate_image(record.path)
    exact, perceptual = apply_duplicate_policy(records)
    split_unsplit_records(records)
    stage_records(records, staging)

    inventory: list[dict] = []
    grouped_inventory = defaultdict(list)
    for record in records:
        grouped_inventory[(record.dataset, record.source_path, record.original_class, record.split)].append(record)
    for (dataset, source_path, original_class, split), group in sorted(grouped_inventory.items()):
        valid = [r for r in group if r.validation_status == "valid"]
        extensions = sorted({r.path.suffix.lower().lstrip(".") for r in group})
        inventory.append({
            "dataset_name": dataset, "source_path": source_path, "class_name": original_class,
            "image_count": len(valid), "split": split, "image_extensions": ";".join(extensions),
            "notes": group[0].notes,
        })
    fields = ["dataset_name", "source_path", "class_name", "image_count", "split", "image_extensions", "notes"]
    write_csv(data_dir / "dataset_inventory.csv", inventory, fields)
    (data_dir / "dataset_inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")

    mappings = {}
    for record in records:
        key = (record.dataset, record.original_class)
        _, _, _, base_include, base_notes = map_class(record.dataset, record.original_class, record.source_path)
        mappings[key] = {
            "source_dataset": record.dataset, "original_class": record.original_class,
            "crop": record.crop, "standardized_class": record.standardized_class,
            "condition_type": record.condition_type, "include_candidate": base_include,
            "notes": base_notes,
        }
    mapping_fields = ["source_dataset", "original_class", "crop", "standardized_class", "condition_type", "include_candidate", "notes"]
    write_csv(data_dir / "class_mapping.csv", list(mappings.values()), mapping_fields)

    duplicate_rows = []
    for digest, group in exact.items():
        if len(group) > 1:
            action = "KEEP" if len({r.standardized_class for r in group}) == 1 else "REVIEW"
            for record in group:
                duplicate_rows.append({"file_path": record.source_path, "dataset": record.dataset, "sha256": digest, "perceptual_hash": record.perceptual_hash, "duplicate_group": digest[:16], "duplicate_type": "exact", "recommended_action": action})
    for phash, group in perceptual.items():
        sha_values = {r.sha256 for r in group}
        if len(sha_values) > 1 and len(group) > 1:
            for record in group:
                duplicate_rows.append({"file_path": record.source_path, "dataset": record.dataset, "sha256": record.sha256, "perceptual_hash": phash, "duplicate_group": phash[:16], "duplicate_type": "perceptual_exact_hash", "recommended_action": "REVIEW"})
    duplicate_fields = ["file_path", "dataset", "sha256", "perceptual_hash", "duplicate_group", "duplicate_type", "recommended_action"]
    write_csv(data_dir / "duplicate_report.csv", duplicate_rows, duplicate_fields)

    validation_rows = [{"file_path": r.source_path, "dataset": r.dataset, "extension": r.path.suffix.lower(), "status": r.validation_status, "notes": r.validation_notes} for r in records]
    write_csv(data_dir / "image_validation_report.csv", validation_rows, ["file_path", "dataset", "extension", "status", "notes"])

    balance: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for record in records:
        if record.include_candidate == "YES" and record.validation_status == "valid" and record.split in SPLITS:
            balance[(record.crop, record.standardized_class)][record.split] += 1
    balance_rows = []
    for (crop, standardized), counts in sorted(balance.items()):
        total = sum(counts.values())
        status = "GOOD" if total >= 100 and all(counts[s] > 0 for s in SPLITS) else "LOW_DATA" if total >= 20 else "VERY_LOW_DATA"
        balance_rows.append({"crop": crop, "standardized_class": standardized, "condition_type": next((r.condition_type for r in records if r.standardized_class == standardized), "unknown"), "train_count": counts["train"], "validation_count": counts["validation"], "test_count": counts["test"], "total_count": total, "status": status})
    write_csv(data_dir / "class_balance_report.csv", balance_rows, ["crop", "standardized_class", "condition_type", "train_count", "validation_count", "test_count", "total_count", "status"])

    mapped_classes = sorted({r["standardized_class"] for r in mappings.values() if r["include_candidate"] == "YES" and r["standardized_class"]})
    all_classes = sorted({r.standardized_class for r in records if r.standardized_class and r.include_candidate == "YES" and r.validation_status == "valid"})
    crops = sorted({r.crop for r in records if r.crop})
    healthy_crops = {r.crop for r in records if r.condition_type == "healthy" and r.include_candidate == "YES"}
    disease_count = sum(1 for r in mappings.values() if r["condition_type"] == "disease" and r["include_candidate"] == "YES")
    pest_count = sum(1 for r in mappings.values() if r["condition_type"] == "pest" and r["include_candidate"] == "YES")
    staged_count = sum(1 for p in staging.rglob("*") if p.is_file())
    low_data = [r["standardized_class"] for r in balance_rows if r["status"] != "GOOD"]
    missing_healthy = sorted(TARGET_CROPS - healthy_crops)
    dataset_totals = Counter(r.dataset for r in records if r.validation_status == "valid")
    audit = f"""# AgroIntel Dataset Audit

Generated with seed `{SEED}` by `ml/prepare_unified_dataset.py`. Raw dataset files were not modified.

## Dataset Inventory

Raw roots under `backend/data/`: {', '.join(sorted(dataset_totals))}.

| Dataset | Valid image files |
|---|---:|
""" + "\n".join(f"| {name} | {count} |" for name, count in sorted(dataset_totals.items())) + f"""

## Findings

- Detected crops: {', '.join(crops)}
- Unique standardized class mappings: {len(mapped_classes)}
- Standardized classes selected for staging: {len(all_classes)}
- Candidate healthy class mappings: {len(healthy_crops)} crops with at least one healthy class
- Disease class mappings: {disease_count}
- Pest class mappings: {pest_count}
- Missing verified healthy crops: {', '.join(missing_healthy) if missing_healthy else 'None'}
- Exact duplicate groups: {sum(1 for group in exact.values() if len(group) > 1)}
- Perceptual-hash duplicate groups: {sum(1 for group in perceptual.values() if len({r.sha256 for r in group}) > 1 and len(group) > 1)}
- Corrupt/unreadable image files: {sum(1 for r in records if r.validation_status not in {'valid'})}
- Low-data candidate classes: {', '.join(low_data) if low_data else 'None'}
- Images selected for staging: {staged_count}

## Inclusion Rules

- PlantVillage's existing 15 classes were preserved in the mapping; the spider-mite class is categorized as `pest`.
- `FUSARIUM-22/dataset_raw` is the only Fusarium source eligible for staging. `dataset_augmented` is excluded to prevent leakage.
- Ambiguous multi-crop folders are marked `REVIEW` and excluded from staging.
- Pest classes are retained as clearly identified condition candidates but should be excluded if training a pure disease-only model.
- No synthetic healthy classes were created.

## Healthy-Class Review

Healthy evidence was found for: {', '.join(sorted(healthy_crops)) if healthy_crops else 'None'}.
The missing list above means no verified healthy folder was found for that crop in the included sources.

## Licensing and Sources

FUSARIUM-22 includes a `readme.txt` with citation requirements. Other source/license metadata should be reviewed in the original download locations before redistribution. Raw folders remain untouched.

## Generated Artifacts

- `dataset_inventory.csv` and `dataset_inventory.json`
- `class_mapping.csv`
- `duplicate_report.csv`
- `class_balance_report.csv`
- `image_validation_report.csv`
- `leaf_disease_unified/` with deterministic train/validation/test staging
"""
    (data_dir / "DATASET_AUDIT.md").write_text(audit, encoding="utf-8")

    print(json.dumps({"raw_records": len(records), "datasets": dict(dataset_totals), "crops": crops, "candidate_classes": len(all_classes), "exact_duplicate_groups": sum(1 for group in exact.values() if len(group) > 1), "invalid_files": sum(1 for r in records if r.validation_status != "valid"), "staged_images": staged_count, "reports_dir": str(data_dir)}, indent=2))


if __name__ == "__main__":
    main()
