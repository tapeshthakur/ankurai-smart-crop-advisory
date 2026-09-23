"""Create the final disease+healthy staging dataset from the audited staging set.

Raw datasets are never changed. This script only rebuilds the generated
leaf_disease_final directory and final review artifacts.
"""

from __future__ import annotations

import csv
import hashlib
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "backend" / "data"
SOURCE = DATA / "leaf_disease_unified"
FINAL = DATA / "leaf_disease_final"
CROPS = ["Pepper", "Potato", "Tomato", "Rice", "Wheat", "Maize", "Sugarcane", "Soybean", "Chickpea", "Cotton", "Coffee"]
SPLITS = ["train", "validation", "test"]


def rows(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, values: list[dict[str, object]], fields: list[str]) -> None:
    with (DATA / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(values)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def phash(path: Path) -> str:
    with Image.open(path) as image:
        pixels = list(image.convert("L").resize((16, 16)).getdata())
    average = sum(pixels) / len(pixels)
    return "".join("1" if pixel >= average else "0" for pixel in pixels)


def category(total: int) -> str:
    if total == 0:
        return "MISSING"
    if total < 100:
        return "VERY_LOW"
    if total < 300:
        return "LOW"
    if total < 1000:
        return "ACCEPTABLE"
    return "STRONG"


def main() -> None:
    mapping_rows = rows("class_mapping.csv")
    mapping: dict[str, dict[str, str]] = {}
    for row in mapping_rows:
        if row["standardized_class"] and row["include_candidate"] == "YES":
            current = mapping.setdefault(row["standardized_class"], {"crop": row["crop"], "condition_type": row["condition_type"], "original_class": row["original_class"], "dataset": row["source_dataset"]})
            if row["original_class"] not in current["original_class"].split(" | "):
                current["original_class"] += " | " + row["original_class"]
            if row["source_dataset"] not in current["dataset"].split(" | "):
                current["dataset"] += " | " + row["source_dataset"]

    plan = {row["standardized_class"]: row for row in rows("final_training_class_plan.csv") if row["include"] == "TRUE"}
    source_snapshot = {path: path.stat().st_size for path in SOURCE.rglob("*") if path.is_file()}
    candidates = []
    for split in SPLITS:
        for path in (SOURCE / split).rglob("*"):
            if not path.is_file():
                continue
            standardized = path.parent.name
            if standardized not in plan or standardized not in mapping:
                continue
            candidates.append({"path": path, "split": split, "standardized_class": standardized, "sha256": sha256(path), "perceptual_hash": phash(path)})

    # Remove exact or perceptual duplicates deterministically before target selection.
    exact_groups: dict[str, list[dict]] = defaultdict(list)
    perceptual_groups: dict[str, list[dict]] = defaultdict(list)
    for item in candidates:
        exact_groups[item["sha256"]].append(item)
        perceptual_groups[item["perceptual_hash"]].append(item)

    duplicate_review = []
    removed_ids: set[int] = set()
    for digest, group in exact_groups.items():
        if len(group) > 1:
            # leaf_disease_unified should already have no exact duplicates; keep a guard here.
            keeper = sorted(group, key=lambda item: (SPLITS.index(item["split"]), str(item["path"]))) [0]
            for item in group:
                if item is not keeper:
                    removed_ids.add(id(item))
                    duplicate_review.append({"filepath": str(item["path"].relative_to(ROOT)), "duplicate_group": digest[:16], "duplicate_type": "exact", "split": item["split"], "action": "EXCLUDE", "notes": "Exact duplicate; canonical copy retained."})
    for digest, group in perceptual_groups.items():
        if len(group) < 2:
            continue
        classes = {item["standardized_class"] for item in group}
        # Equal average hashes are treated as obvious copies. A mixed-label group is safer to review/exclude.
        if len(classes) > 1:
            action = "REVIEW"
            note = "Perceptual duplicate group has conflicting standardized labels; excluded from final manifest."
            for item in group:
                removed_ids.add(id(item))
        else:
            action = "EXCLUDE"
            note = "Obvious perceptual duplicate/augmented copy; one canonical image retained."
            keeper = sorted(group, key=lambda item: (SPLITS.index(item["split"]), str(item["path"]))) [0]
            for item in group:
                if item is not keeper:
                    removed_ids.add(id(item))
        for item in group:
            duplicate_review.append({"filepath": str(item["path"].relative_to(ROOT)), "duplicate_group": digest[:16], "duplicate_type": "perceptual_exact_hash", "split": item["split"], "action": action if id(item) in removed_ids else "KEEP", "notes": note})

    clean = [item for item in candidates if id(item) not in removed_ids]
    by_class_split: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for item in clean:
        by_class_split[(item["standardized_class"], item["split"])].append(item)

    selected = []
    for standardized, target in sorted(plan.items()):
        for split, field in (("train", "target_train"), ("validation", "target_validation"), ("test", "target_test")):
            available = sorted(by_class_split[(standardized, split)], key=lambda item: (item["sha256"], str(item["path"])))
            selected.extend(available[: min(len(available), int(target[field]))])

    if FINAL.exists():
        shutil.rmtree(FINAL)
    for split in SPLITS:
        (FINAL / split).mkdir(parents=True, exist_ok=True)

    manifest = []
    for item in selected:
        destination_dir = FINAL / item["split"] / item["standardized_class"]
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / f"{item['sha256'][:16]}_{item['path'].name}"
        shutil.copy2(item["path"], destination)
        info = mapping[item["standardized_class"]]
        manifest.append({
            "filepath": str(destination.relative_to(ROOT)),
            "dataset": info["dataset"],
            "crop": info["crop"],
            "original_class": info["original_class"],
            "standardized_class": item["standardized_class"],
            "condition_type": info["condition_type"],
            "split": item["split"],
            "sha256": item["sha256"],
            "perceptual_hash": item["perceptual_hash"],
            "duplicate_group": item["perceptual_hash"][:16] if item["perceptual_hash"] in perceptual_groups else "",
            "source_status": "CLEANED_INCLUDED",
        })
    current_snapshot = {path: path.stat().st_size for path in SOURCE.rglob("*") if path.is_file()}
    if current_snapshot != source_snapshot:
        raise RuntimeError("Source staging changed during finalization; refusing to continue.")
    manifest.sort(key=lambda row: row["filepath"])
    write_csv("final_training_manifest.csv", manifest, ["filepath", "dataset", "crop", "original_class", "standardized_class", "condition_type", "split", "sha256", "perceptual_hash", "duplicate_group", "source_status"])
    write_csv("perceptual_duplicate_review.csv", duplicate_review, ["filepath", "duplicate_group", "duplicate_type", "split", "action", "notes"])

    distribution = []
    counts = defaultdict(lambda: defaultdict(int))
    for item in manifest:
        counts[item["standardized_class"]][item["split"]] += 1
    for standardized, info in sorted(mapping.items()):
        if info["condition_type"] == "pest" or standardized not in plan:
            continue
        values = counts[standardized]
        total = sum(values.values())
        status = "NEEDS_HEALTHY_DATA" if standardized in {"Chickpea___healthy", "Rice___healthy", "Soybean___healthy"} else "LOW_DATA" if category(total) in {"LOW", "VERY_LOW", "MISSING"} else "READY_AFTER_CLEANING"
        distribution.append({"crop": info["crop"], "class": standardized, "condition_type": info["condition_type"], "train": values["train"], "validation": values["validation"], "test": values["test"], "total": total, "status": status})
    for crop, standardized in [("Chickpea", "Chickpea___healthy"), ("Rice", "Rice___healthy"), ("Soybean", "Soybean___healthy")]:
        distribution.append({"crop": crop, "class": standardized, "condition_type": "healthy", "train": 0, "validation": 0, "test": 0, "total": 0, "status": "NEEDS_HEALTHY_DATA"})
    distribution.sort(key=lambda row: (CROPS.index(row["crop"]), row["class"]))
    write_csv("final_class_distribution.csv", distribution, ["crop", "class", "condition_type", "train", "validation", "test", "total", "status"])

    by_crop = defaultdict(list)
    for row in distribution:
        by_crop[row["crop"]].append(row)
    statuses = {}
    for crop in CROPS:
        crop_rows = by_crop[crop]
        if crop in {"Chickpea", "Rice", "Soybean"}:
            statuses[crop] = "NEEDS_HEALTHY_DATA"
        elif any(row["status"] == "LOW_DATA" for row in crop_rows):
            statuses[crop] = "LOW_DATA"
        else:
            statuses[crop] = "READY_AFTER_CLEANING"

    disease_classes = sorted({row["class"] for row in distribution if row["condition_type"] == "disease" and row["total"] > 0})
    healthy_classes = sorted({row["class"] for row in distribution if row["condition_type"] == "healthy" and row["total"] > 0})
    low_classes = sorted({row["class"] for row in distribution if row["status"] == "LOW_DATA"})
    final_counts = Counter(row["split"] for row in manifest)
    readiness = [
        "# AgroIntel 11-Crop Disease Model Readiness",
        "",
        "This final preparation stage did not train a model, download data, or modify raw datasets. Pest classes were excluded from the manifest but remain in their raw sources.",
        "",
        "## Crop Status",
        "",
    ]
    notes_by_crop = {
        "Pepper": "PlantVillage disease and healthy classes are strong after duplicate cleaning.",
        "Potato": "PlantVillage disease classes are strong; healthy class is smaller but valid.",
        "Tomato": "PlantVillage disease and healthy classes are strong. Spider mites are excluded as pest.",
        "Rice": "Valid rice disease classes retained. Brown spot and Leaf smut remain excluded because of duplicate/label conflicts. Healthy data is missing.",
        "Wheat": "Disease and healthy data retained, but several classes have low volume and no independent test split.",
        "Maize": "Disease and healthy data retained, but low-data classes and split quality need review.",
        "Sugarcane": "Disease and healthy data retained, but several classes lack independent validation/test coverage.",
        "Soybean": "Disease classes retained. Healthy class is missing and several disease classes are low-data.",
        "Chickpea": "FUSARIUM-22 raw severity classes retained. Healthy class is missing; resistance severity is not relabeled as healthy.",
        "Cotton": "Disease and healthy data retained. Multiple pest classes are excluded and several disease classes are low-data.",
        "Coffee": "RoCoLe healthy and Rust classes are usable; Red spider mite is excluded as pest.",
    }
    disease_by_crop = defaultdict(list)
    for row in distribution:
        if row["condition_type"] == "disease" and row["total"] > 0:
            disease_by_crop[row["crop"]].append(row["class"])
    healthy_by_crop = defaultdict(list)
    for row in distribution:
        if row["condition_type"] == "healthy" and row["total"] > 0:
            healthy_by_crop[row["crop"]].append(row["class"])
    for crop in CROPS:
        total = sum(int(row["total"]) for row in by_crop[crop])
        readiness += [f"### {crop}", f"status: {statuses[crop]}", f"disease classes: {', '.join(disease_by_crop[crop]) if disease_by_crop[crop] else 'None currently staged'}", f"healthy: {', '.join(healthy_by_crop[crop]) if healthy_by_crop[crop] else 'MISSING - NEEDS_HEALTHY_DATA'}", f"image count: {total}", f"notes: {notes_by_crop[crop]}", ""]
    readiness += [
        "## Missing Healthy Data",
        "",
        "- Chickpea___healthy: NEEDS_HEALTHY_DATA - 300 minimum / 500 preferred genuine healthy images.",
        "- Rice___healthy: NEEDS_HEALTHY_DATA - 300 minimum / 500 preferred genuine healthy images.",
        "- Soybean___healthy: NEEDS_HEALTHY_DATA - 300 minimum / 500 preferred genuine healthy images.",
        "",
        "The 11-crop model should not be considered production-ready until these verified healthy classes are added.",
        "",
        "## Leakage",
        "",
        "- train/validation = 0 exact duplicates in the final manifest",
        "- train/test = 0 exact duplicates in the final manifest",
        "- validation/test = 0 exact duplicates in the final manifest",
        "- Perceptual duplicates were processed through `perceptual_duplicate_review.csv`; obvious exact perceptual copies were excluded and ambiguous/conflicting groups are marked REVIEW.",
        "",
        "## Final Dataset",
        "",
        f"- crops: {len(CROPS)} ({', '.join(CROPS)})",
        f"- disease classes: {len(disease_classes)}",
        f"- healthy classes: {len(healthy_classes)}",
        "- excluded pest classes: 15",
        f"- total images: {len(manifest)}",
        f"- train: {final_counts['train']}",
        f"- validation: {final_counts['validation']}",
        f"- test: {final_counts['test']}",
        f"- low-data classes: {', '.join(low_classes) if low_classes else 'None'}",
        "- excluded/conflicting classes: Rice___Brown_spot, Rice___Leaf_smut; all pest classes",
        "",
        "## Training Readiness",
        "",
        "1. READY FOR PRELIMINARY TRAINING?",
        "",
        "Preliminary training may be possible using currently available disease and healthy classes, with class weights, augmentation, and the missing-healthy gaps clearly documented.",
        "",
        "2. READY FOR FINAL 11-CROP TRAINING?",
        "",
        "Final 11-crop training should wait until verified healthy images are obtained for Chickpea, Rice, and Soybean. The final manifest preserves all 11 crops in the plan, but the three missing healthy classes are intentionally empty.",
    ]
    (DATA / "FINAL_11_CROP_READINESS.md").write_text("\n".join(readiness) + "\n", encoding="utf-8")
    print({"final_images": len(manifest), "train": final_counts["train"], "validation": final_counts["validation"], "test": final_counts["test"], "disease_classes": len(disease_classes), "healthy_classes": len(healthy_classes), "perceptual_review_rows": len(duplicate_review), "final_path": str(FINAL)})


if __name__ == "__main__":
    main()
