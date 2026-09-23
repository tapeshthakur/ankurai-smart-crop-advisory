import os
import json
import random
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf
from PIL import Image

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)

import matplotlib.pyplot as plt


# ============================================================
# AGROINTEL - PRELIMINARY UNIFIED MOBILENETV2 TRAINING
# ============================================================

# ------------------------------------------------------------
# 1. PATHS
# ------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_DIR = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "leaf_disease_final"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "ml"
    / "models"
    / "preliminary_unified"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# 2. TRAINING CONFIG
# ------------------------------------------------------------

IMAGE_SIZE = (224, 224)
BATCH_SIZE = 16

PHASE1_EPOCHS = 10
PHASE2_EPOCHS = 15

PHASE1_LR = 1e-3
PHASE2_LR = 1e-5

SEED = 42
REPORT_ONLY = "--report-only" in sys.argv

AUTOTUNE = tf.data.AUTOTUNE

# Keep TensorFlow from trying to allocate excessive memory.
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "1"


# ------------------------------------------------------------
# 3. REPRODUCIBILITY
# ------------------------------------------------------------

random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)


# ------------------------------------------------------------
# 4. STARTUP INFO
# ------------------------------------------------------------

print("=" * 75)
print("AGROINTEL UNIFIED MOBILENETV2 - PRELIMINARY TRAINING")
print("=" * 75)

print(f"TensorFlow version : {tf.__version__}")
print(f"Dataset            : {DATASET_DIR}")
print(f"Output directory   : {OUTPUT_DIR}")
print(f"Image size         : {IMAGE_SIZE}")
print(f"Batch size         : {BATCH_SIZE}")
print(f"Phase 1 epochs     : {PHASE1_EPOCHS}")
print(f"Phase 2 epochs     : {PHASE2_EPOCHS}")
print("=" * 75)


# ------------------------------------------------------------
# 5. VERIFY DATASET
# ------------------------------------------------------------

for split in ["train", "validation", "test"]:
    split_dir = DATASET_DIR / split

    if not split_dir.exists():
        raise FileNotFoundError(
            f"Missing dataset directory:\n{split_dir}"
        )

print("\nDataset directories verified.")


# ------------------------------------------------------------
# 6. LOAD DATASETS
# ------------------------------------------------------------

print("\nLoading training dataset...")

train_ds = tf.keras.utils.image_dataset_from_directory(
    DATASET_DIR / "train",
    labels="inferred",
    label_mode="int",
    image_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    shuffle=True,
    seed=SEED,
)

print("\nLoading validation dataset...")

val_ds = tf.keras.utils.image_dataset_from_directory(
    DATASET_DIR / "validation",
    labels="inferred",
    label_mode="int",
    image_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    shuffle=False,
)

print("\nLoading test dataset...")

test_ds = tf.keras.utils.image_dataset_from_directory(
    DATASET_DIR / "test",
    labels="inferred",
    label_mode="int",
    image_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    shuffle=False,
)


# ------------------------------------------------------------
# 7. CLASS INFORMATION
# ------------------------------------------------------------

class_names = train_ds.class_names
num_classes = len(class_names)

print("\n" + "=" * 75)
print(f"NUMBER OF CLASSES: {num_classes}")
print("=" * 75)

for i, class_name in enumerate(class_names):
    print(f"{i:02d}  {class_name}")

if num_classes != 44:
    print(
        f"\nWARNING: Expected approximately 44 classes, "
        f"but found {num_classes}."
    )


def run_reporting_only():
    """Regenerate post-training artifacts without fitting or saving a model."""
    checkpoint_path = OUTPUT_DIR / "best_preliminary_mobilenetv2.keras"
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Saved best model not found: {checkpoint_path}")

    print("\nREPORT-ONLY MODE: loading saved best model; no training will run.")
    try:
        reporting_model = tf.keras.models.load_model(
            checkpoint_path,
            compile=False,
        )
    except (TypeError, ValueError) as error:
        # The checkpoint was serialized by a Keras version that included
        # initializer fields no longer accepted by this environment. Build
        # the same topology and load the checkpoint's existing weights.
        print(f"Direct checkpoint deserialization unavailable: {error}")
        compatibility_augmentation = tf.keras.Sequential(
            [
                tf.keras.layers.RandomFlip("horizontal"),
                tf.keras.layers.RandomRotation(0.08),
                tf.keras.layers.RandomZoom(0.10),
                tf.keras.layers.RandomTranslation(
                    height_factor=0.05,
                    width_factor=0.05,
                ),
                tf.keras.layers.RandomContrast(0.10),
            ],
            name="data_augmentation",
        )
        compatibility_base = tf.keras.applications.MobileNetV2(
            input_shape=(IMAGE_SIZE[0], IMAGE_SIZE[1], 3),
            include_top=False,
            weights=None,
        )
        compatibility_inputs = tf.keras.Input(
            shape=(IMAGE_SIZE[0], IMAGE_SIZE[1], 3)
        )
        compatibility_x = compatibility_augmentation(compatibility_inputs)
        compatibility_x = tf.keras.applications.mobilenet_v2.preprocess_input(
            compatibility_x
        )
        compatibility_x = compatibility_base(compatibility_x, training=False)
        compatibility_x = tf.keras.layers.GlobalAveragePooling2D()(compatibility_x)
        compatibility_x = tf.keras.layers.Dropout(0.30)(compatibility_x)
        compatibility_outputs = tf.keras.layers.Dense(
            num_classes,
            activation="softmax",
            name="predictions",
        )(compatibility_x)
        reporting_model = tf.keras.Model(
            compatibility_inputs,
            compatibility_outputs,
            name="AgroIntel_MobileNetV2",
        )
        reporting_model.load_weights(checkpoint_path)

    # Use Pillow for report-only loading so valid WebP test images are not
    # rejected by TensorFlow's directory decoder. The dataset is not changed.
    test_images = []
    test_labels = []
    for class_index, class_name in enumerate(class_names):
        class_dir = DATASET_DIR / "test" / class_name
        for image_path in sorted(class_dir.iterdir()):
            if not image_path.is_file():
                continue
            try:
                with Image.open(image_path) as image:
                    test_images.append(
                        np.asarray(
                            image.convert("RGB").resize(IMAGE_SIZE),
                            dtype=np.float32,
                        )
                    )
                test_labels.append(class_index)
            except (OSError, ValueError) as error:
                print(f"Skipping unreadable test image {image_path}: {error}")

    y_true = np.asarray(test_labels)
    y_pred = []
    for start in range(0, len(test_images), BATCH_SIZE):
        batch = np.asarray(test_images[start : start + BATCH_SIZE])
        predictions = reporting_model.predict(batch, verbose=0)
        y_pred.extend(np.argmax(predictions, axis=1).tolist())

    y_true_array = y_true
    y_pred_array = np.asarray(y_pred)
    labels = np.arange(num_classes)

    report = classification_report(
        y_true_array,
        y_pred_array,
        labels=labels,
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )

    class_metrics = []
    for i, class_name in enumerate(class_names):
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true_array,
            y_pred_array,
            labels=[i],
            average="macro",
            zero_division=0,
        )
        support = int(np.sum(y_true_array == i))
        class_metrics.append(
            {
                "class": class_name,
                "precision": float(precision),
                "recall": float(recall),
                "f1": float(f1),
                "support": support,
            }
        )

    best_classes = sorted(class_metrics, key=lambda item: item["f1"], reverse=True)
    worst_classes = sorted(class_metrics, key=lambda item: item["f1"])

    cm = confusion_matrix(y_true_array, y_pred_array, labels=labels)
    np.save(OUTPUT_DIR / "confusion_matrix.npy", cm)
    plt.figure(figsize=(22, 20))
    plt.imshow(cm, interpolation="nearest")
    plt.title("AgroIntel Unified MobileNetV2 - Confusion Matrix")
    plt.colorbar()
    tick_marks = np.arange(num_classes)
    plt.xticks(tick_marks, class_names, rotation=90, fontsize=7)
    plt.yticks(tick_marks, class_names, fontsize=7)
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "confusion_matrix.png", dpi=200, bbox_inches="tight")
    plt.close()

    row_sums = cm.sum(axis=1, keepdims=True)
    normalized_cm = np.divide(
        cm,
        row_sums,
        out=np.zeros_like(cm, dtype=float),
        where=row_sums != 0,
    )
    np.save(OUTPUT_DIR / "normalized_confusion_matrix.npy", normalized_cm)
    plt.figure(figsize=(22, 20))
    plt.imshow(normalized_cm, interpolation="nearest")
    plt.title("AgroIntel Unified MobileNetV2 - Normalized Confusion Matrix")
    plt.colorbar()
    plt.xticks(tick_marks, class_names, rotation=90, fontsize=7)
    plt.yticks(tick_marks, class_names, fontsize=7)
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "normalized_confusion_matrix.png",
        dpi=200,
        bbox_inches="tight",
    )
    plt.close()

    crop_results = {}
    for index, class_name in enumerate(class_names):
        crop = class_name.split("___", 1)[0] if "___" in class_name else "Unknown"
        crop_results.setdefault(crop, {"classes": [], "true": [], "pred": []})
        mask = y_true_array == index
        crop_results[crop]["classes"].append(class_name)
        crop_results[crop]["true"].extend(y_true_array[mask].tolist())
        crop_results[crop]["pred"].extend(y_pred_array[mask].tolist())

    crop_summary = {}
    for crop, data in crop_results.items():
        true_values = np.asarray(data["true"])
        pred_values = np.asarray(data["pred"])
        accuracy = float(np.mean(true_values == pred_values)) if len(true_values) else 0.0
        valid_labels = sorted(set(true_values.tolist()))
        if valid_labels:
            _, _, f1_values, _ = precision_recall_fscore_support(
                true_values,
                pred_values,
                labels=valid_labels,
                average=None,
                zero_division=0,
            )
            macro_f1 = float(np.mean(f1_values))
        else:
            macro_f1 = 0.0
        crop_summary[crop] = {
            "num_classes": len(data["classes"]),
            "test_images": len(true_values),
            "accuracy": accuracy,
            "macro_f1": macro_f1,
            "classes": sorted(data["classes"]),
        }

    report["class_metrics"] = class_metrics
    report["best_classes"] = best_classes[:10]
    report["worst_classes"] = worst_classes[:10]
    report["crop_summary"] = crop_summary
    with open(OUTPUT_DIR / "classification_report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    history_path = OUTPUT_DIR / "training_history.json"
    if history_path.exists():
        history = json.loads(history_path.read_text(encoding="utf-8"))
    else:
        history = {}
    history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")

    config_path = OUTPUT_DIR / "training_config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
    else:
        config = {
            "dataset": str(DATASET_DIR),
            "output_directory": str(OUTPUT_DIR),
            "image_size": list(IMAGE_SIZE),
            "batch_size": BATCH_SIZE,
            "num_classes": num_classes,
            "architecture": "MobileNetV2",
        }
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    macro_precision = float(report["macro avg"]["precision"])
    macro_recall = float(report["macro avg"]["recall"])
    macro_f1 = float(report["macro avg"]["f1-score"])
    weighted_f1 = float(report["weighted avg"]["f1-score"])
    report_lines = [
        "# AgroIntel Unified MobileNetV2 - Preliminary Training Report",
        "",
        "## Reporting Run",
        "- Existing best checkpoint loaded; no training was performed.",
        f"- Test images: {len(y_true_array)}",
        "",
        "## Test Performance",
        f"- Test accuracy: {report['accuracy']:.4f}",
        f"- Macro precision: {macro_precision:.4f}",
        f"- Macro recall: {macro_recall:.4f}",
        f"- Macro F1: {macro_f1:.4f}",
        f"- Weighted F1: {weighted_f1:.4f}",
        "",
        "## Best Classes",
        "",
    ]
    report_lines.extend(
        f"- {item['class']}: F1={item['f1']:.4f}, precision={item['precision']:.4f}, recall={item['recall']:.4f}, support={item['support']}"
        for item in best_classes[:5]
    )
    report_lines.extend(["", "## Worst Classes", ""])
    report_lines.extend(
        f"- {item['class']}: F1={item['f1']:.4f}, precision={item['precision']:.4f}, recall={item['recall']:.4f}, support={item['support']}"
        for item in worst_classes[:10]
    )
    report_lines.extend(["", "## Crop-Level Performance", ""])
    report_lines.extend(
        f"- {crop}: accuracy={result['accuracy']:.4f}, macro F1={result['macro_f1']:.4f}, test images={result['test_images']}"
        for crop, result in sorted(crop_summary.items())
    )
    (OUTPUT_DIR / "TRAINING_REPORT.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print("NO TRAINING PERFORMED: existing best model was evaluated.")
    print(f"Test accuracy: {report['accuracy']:.4f}")
    print(f"Macro F1: {macro_f1:.4f}")
    print(f"Weighted F1: {weighted_f1:.4f}")
    print("Best 5 classes:")
    for item in best_classes[:5]:
        print(f"  {item['class']}: F1={item['f1']:.4f}")
    print("Worst 10 classes:")
    for item in worst_classes[:10]:
        print(f"  {item['class']}: F1={item['f1']:.4f}")
    print("Crop-level results:")
    for crop, result in sorted(crop_summary.items()):
        print(
            f"  {crop}: accuracy={result['accuracy']:.4f}, "
            f"macro F1={result['macro_f1']:.4f}, test_images={result['test_images']}"
        )
    print("Generated reports:")
    for name in (
        "classification_report.json",
        "confusion_matrix.npy",
        "confusion_matrix.png",
        "normalized_confusion_matrix.npy",
        "normalized_confusion_matrix.png",
        "training_history.json",
        "training_config.json",
        "TRAINING_REPORT.md",
    ):
        print(OUTPUT_DIR / name)


if REPORT_ONLY:
    run_reporting_only()
    raise SystemExit(0)


# ------------------------------------------------------------
# 8. SAVE CLASS NAMES
# ------------------------------------------------------------

with open(
    OUTPUT_DIR / "class_names.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump(
        class_names,
        f,
        indent=2,
        ensure_ascii=False,
    )


# ------------------------------------------------------------
# 9. COUNT IMAGES PER CLASS
# ------------------------------------------------------------

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
}


def count_images(split_dir):
    counts = {}

    for class_dir in sorted(split_dir.iterdir()):
        if not class_dir.is_dir():
            continue

        count = 0

        for file_path in class_dir.rglob("*"):
            if (
                file_path.is_file()
                and file_path.suffix.lower() in IMAGE_EXTENSIONS
            ):
                count += 1

        counts[class_dir.name] = count

    return counts


train_counts = count_images(DATASET_DIR / "train")
val_counts = count_images(DATASET_DIR / "validation")
test_counts = count_images(DATASET_DIR / "test")


print("\n" + "=" * 75)
print("CLASS DISTRIBUTION")
print("=" * 75)

for class_name in class_names:
    print(
        f"{class_name:55s} "
        f"Train={train_counts.get(class_name, 0):4d} "
        f"Val={val_counts.get(class_name, 0):4d} "
        f"Test={test_counts.get(class_name, 0):4d}"
    )


# ------------------------------------------------------------
# 10. CLASS WEIGHTS
# ------------------------------------------------------------

total_train = sum(
    train_counts.get(name, 0)
    for name in class_names
)

class_weights = {}

for index, class_name in enumerate(class_names):
    count = train_counts.get(class_name, 0)

    if count > 0:
        # Standard balanced-class weighting:
        # total_samples / (num_classes * samples_in_class)
        weight = total_train / (num_classes * count)
    else:
        weight = 1.0

    class_weights[index] = float(weight)


print("\n" + "=" * 75)
print("CLASS WEIGHTS")
print("=" * 75)

for index, class_name in enumerate(class_names):
    print(
        f"{class_name:55s} "
        f"weight={class_weights[index]:.4f}"
    )


with open(
    OUTPUT_DIR / "class_weights.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump(
        {
            class_names[index]: class_weights[index]
            for index in range(num_classes)
        },
        f,
        indent=2,
        ensure_ascii=False,
    )


# ------------------------------------------------------------
# 11. PREFETCH
# ------------------------------------------------------------

train_ds = train_ds.prefetch(AUTOTUNE)
val_ds = val_ds.prefetch(AUTOTUNE)
test_ds = test_ds.prefetch(AUTOTUNE)


# ------------------------------------------------------------
# 12. DATA AUGMENTATION
# ------------------------------------------------------------

data_augmentation = tf.keras.Sequential(
    [
        tf.keras.layers.RandomFlip("horizontal"),
        tf.keras.layers.RandomRotation(0.08),
        tf.keras.layers.RandomZoom(0.10),
        tf.keras.layers.RandomTranslation(
            height_factor=0.05,
            width_factor=0.05,
        ),
        tf.keras.layers.RandomContrast(0.10),
    ],
    name="data_augmentation",
)


# ------------------------------------------------------------
# 13. BASE MOBILENETV2
# ------------------------------------------------------------

print("\nLoading ImageNet-pretrained MobileNetV2...")

base_model = tf.keras.applications.MobileNetV2(
    input_shape=(
        IMAGE_SIZE[0],
        IMAGE_SIZE[1],
        3,
    ),
    include_top=False,
    weights="imagenet",
)

base_model.trainable = False


# ------------------------------------------------------------
# 14. MODEL
# ------------------------------------------------------------

inputs = tf.keras.Input(
    shape=(
        IMAGE_SIZE[0],
        IMAGE_SIZE[1],
        3,
    )
)

x = data_augmentation(inputs)

x = tf.keras.applications.mobilenet_v2.preprocess_input(x)

x = base_model(
    x,
    training=False,
)

x = tf.keras.layers.GlobalAveragePooling2D()(x)

x = tf.keras.layers.Dropout(0.30)(x)

outputs = tf.keras.layers.Dense(
    num_classes,
    activation="softmax",
    name="predictions",
)(x)

model = tf.keras.Model(
    inputs=inputs,
    outputs=outputs,
    name="AgroIntel_MobileNetV2",
)


# ------------------------------------------------------------
# 15. MODEL SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("MODEL SUMMARY")
print("=" * 75)

model.summary()


# ------------------------------------------------------------
# 16. CALLBACKS
# ------------------------------------------------------------

checkpoint_path = (
    OUTPUT_DIR
    / "best_preliminary_mobilenetv2.keras"
)

callbacks = [
    tf.keras.callbacks.ModelCheckpoint(
        filepath=str(checkpoint_path),
        monitor="val_loss",
        save_best_only=True,
        mode="min",
        verbose=1,
    ),

    tf.keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=4,
        restore_best_weights=True,
        mode="min",
        verbose=1,
    ),

    tf.keras.callbacks.ReduceLROnPlateau(
        monitor="val_loss",
        factor=0.2,
        patience=2,
        min_lr=1e-7,
        mode="min",
        verbose=1,
    ),
]


# ------------------------------------------------------------
# 17. PHASE 1 - FROZEN BASE
# ------------------------------------------------------------

print("\n")
print("=" * 75)
print("PHASE 1 - TRAIN CLASSIFICATION HEAD")
print("=" * 75)

model.compile(
    optimizer=tf.keras.optimizers.Adam(
        learning_rate=PHASE1_LR
    ),
    loss="sparse_categorical_crossentropy",
    metrics=[
        tf.keras.metrics.SparseCategoricalAccuracy(
            name="accuracy"
        )
    ],
)

history1 = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=PHASE1_EPOCHS,
    class_weight=class_weights,
    callbacks=callbacks,
    verbose=1,
)


# ------------------------------------------------------------
# 18. PHASE 2 - FINE TUNING
# ------------------------------------------------------------

print("\n")
print("=" * 75)
print("PHASE 2 - FINE TUNING UPPER MOBILENETV2 LAYERS")
print("=" * 75)

base_model.trainable = True

# Unfreeze approximately the top 30%.
fine_tune_from = int(
    len(base_model.layers) * 0.70
)

for layer in base_model.layers[:fine_tune_from]:
    layer.trainable = False

# Keep BatchNormalization layers frozen.
for layer in base_model.layers:
    if isinstance(
        layer,
        tf.keras.layers.BatchNormalization,
    ):
        layer.trainable = False


trainable_count = sum(
    1
    for layer in base_model.layers
    if layer.trainable
)

print(
    f"Trainable MobileNetV2 layers: "
    f"{trainable_count}/{len(base_model.layers)}"
)

model.compile(
    optimizer=tf.keras.optimizers.Adam(
        learning_rate=PHASE2_LR
    ),
    loss="sparse_categorical_crossentropy",
    metrics=[
        tf.keras.metrics.SparseCategoricalAccuracy(
            name="accuracy"
        )
    ],
)

history2 = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=PHASE2_EPOCHS,
    class_weight=class_weights,
    callbacks=callbacks,
    verbose=1,
)


# ------------------------------------------------------------
# 19. LOAD BEST CHECKPOINT
# ------------------------------------------------------------

print("\nLoading best model checkpoint...")

if not checkpoint_path.exists():
    raise FileNotFoundError(
        "Best checkpoint was not created."
    )

model = tf.keras.models.load_model(
    checkpoint_path
)


# ------------------------------------------------------------
# 20. TEST EVALUATION
# ------------------------------------------------------------

print("\n")
print("=" * 75)
print("FINAL TEST EVALUATION")
print("=" * 75)

test_loss, test_accuracy = model.evaluate(
    test_ds,
    verbose=1,
)

print(f"\nTest Loss     : {test_loss:.4f}")
print(f"Test Accuracy : {test_accuracy:.4f}")


# ------------------------------------------------------------
# 21. TEST PREDICTIONS
# ------------------------------------------------------------

print("\nGenerating test predictions...")

y_true = []
y_pred = []

for images, labels in test_ds:

    predictions = model.predict(
        images,
        verbose=0,
    )

    predicted_labels = np.argmax(
        predictions,
        axis=1,
    )

    y_true.extend(labels.numpy().tolist())
    y_pred.extend(predicted_labels.tolist())

y_true = np.asarray(y_true)
y_pred = np.asarray(y_pred)


# ------------------------------------------------------------
# 22. CLASSIFICATION REPORT
# ------------------------------------------------------------

report = classification_report(
    y_true,
    y_pred,
    labels=np.arange(num_classes),
    target_names=class_names,
    output_dict=True,
    zero_division=0,
)

print("\n" + "=" * 75)
print("CLASSIFICATION REPORT")
print("=" * 75)

print(
    classification_report(
        y_true,
        y_pred,
        labels=np.arange(num_classes),
        target_names=class_names,
        zero_division=0,
    )
)

with open(
    OUTPUT_DIR / "classification_report.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump(
        report,
        f,
        indent=2,
        ensure_ascii=False,
    )


# ------------------------------------------------------------
# 23. CONFUSION MATRIX
# ------------------------------------------------------------

cm = confusion_matrix(
    y_true,
    y_pred,
    labels=np.arange(num_classes),
)

np.save(
    OUTPUT_DIR / "confusion_matrix.npy",
    cm,
)

plt.figure(figsize=(22, 20))

plt.imshow(
    cm,
    interpolation="nearest",
)

plt.title(
    "AgroIntel Unified MobileNetV2 - Confusion Matrix"
)

plt.colorbar()

tick_marks = np.arange(num_classes)

plt.xticks(
    tick_marks,
    class_names,
    rotation=90,
    fontsize=7,
)

plt.yticks(
    tick_marks,
    class_names,
    fontsize=7,
)

plt.xlabel("Predicted")
plt.ylabel("True")

plt.tight_layout()

plt.savefig(
    OUTPUT_DIR / "confusion_matrix.png",
    dpi=200,
    bbox_inches="tight",
)

plt.close()


# ------------------------------------------------------------
# 24. NORMALIZED CONFUSION MATRIX
# ------------------------------------------------------------

row_sums = cm.sum(axis=1, keepdims=True)

normalized_cm = np.divide(
    cm,
    row_sums,
    out=np.zeros_like(cm, dtype=float),
    where=row_sums != 0,
)

np.save(
    OUTPUT_DIR / "normalized_confusion_matrix.npy",
    normalized_cm,
)

plt.figure(figsize=(22, 20))

plt.imshow(
    normalized_cm,
    interpolation="nearest",
)

plt.title(
    "AgroIntel Unified MobileNetV2 - Normalized Confusion Matrix"
)

plt.colorbar()

plt.xticks(
    tick_marks,
    class_names,
    rotation=90,
    fontsize=7,
)

plt.yticks(
    tick_marks,
    class_names,
    fontsize=7,
)

plt.xlabel("Predicted")
plt.ylabel("True")

plt.tight_layout()

plt.savefig(
    OUTPUT_DIR / "normalized_confusion_matrix.png",
    dpi=200,
    bbox_inches="tight",
)

plt.close()


# ------------------------------------------------------------
# 25. WORST / BEST CLASSES
# ------------------------------------------------------------

class_metrics = []

for i, class_name in enumerate(class_names):

    precision, recall, f1, support = (
        precision_recall_fscore_support(
            y_true,
            y_pred,
            labels=[i],
            average="macro",
            zero_division=0,
        )
    )
    support = int(np.sum(y_true == i))

    class_metrics.append(
        {
            "class": class_name,
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "support": support,
        }
    )

best_classes = sorted(
    class_metrics,
    key=lambda x: x["f1"],
    reverse=True,
)

worst_classes = sorted(
    class_metrics,
    key=lambda x: x["f1"],
)


# ------------------------------------------------------------
# 26. CROP-LEVEL EVALUATION
# ------------------------------------------------------------

def get_crop(class_name):
    """
    Standardized class names are expected to use:
    Crop___Condition
    """
    if "___" in class_name:
        return class_name.split("___", 1)[0]

    # Fallback for unexpected names.
    if "__" in class_name:
        return class_name.split("__", 1)[0]

    return "Unknown"


crop_results = {}

for index, class_name in enumerate(class_names):

    crop = get_crop(class_name)

    if crop not in crop_results:
        crop_results[crop] = {
            "classes": [],
            "true": [],
            "pred": [],
        }

    mask = y_true == index

    crop_results[crop]["classes"].append(
        class_name
    )

    crop_results[crop]["true"].extend(
        y_true[mask].tolist()
    )

    crop_results[crop]["pred"].extend(
        y_pred[mask].tolist()
    )


crop_summary = {}

for crop, data in crop_results.items():

    true_values = np.asarray(data["true"])
    pred_values = np.asarray(data["pred"])

    if len(true_values) == 0:
        crop_accuracy = 0.0
        crop_f1 = 0.0
    else:

        crop_accuracy = float(
            np.mean(
                true_values == pred_values
            )
        )

        valid_labels = sorted(
            set(true_values.tolist())
        )

        if valid_labels:

            _, _, f1_values, _ = (
                precision_recall_fscore_support(
                    true_values,
                    pred_values,
                    labels=valid_labels,
                    average=None,
                    zero_division=0,
                )
            )

            crop_f1 = float(
                np.mean(f1_values)
            )

        else:
            crop_f1 = 0.0

    crop_summary[crop] = {
        "num_classes": len(
            data["classes"]
        ),
        "test_images": len(true_values),
        "accuracy": crop_accuracy,
        "macro_f1": crop_f1,
        "classes": sorted(
            data["classes"]
        ),
    }


print("\n" + "=" * 75)
print("CROP-LEVEL PERFORMANCE")
print("=" * 75)

for crop in sorted(crop_summary):

    result = crop_summary[crop]

    print(
        f"{crop:20s} "
        f"classes={result['num_classes']:2d} "
        f"test={result['test_images']:4d} "
        f"accuracy={result['accuracy']:.4f} "
        f"macro_F1={result['macro_f1']:.4f}"
    )


# ------------------------------------------------------------
# 27. SAVE TRAINING HISTORY
# ------------------------------------------------------------

training_history = {
    "phase1": {
        key: [
            float(value)
            for value in values
        ]
        for key, values in history1.history.items()
    },
    "phase2": {
        key: [
            float(value)
            for value in values
        ]
        for key, values in history2.history.items()
    },
}

with open(
    OUTPUT_DIR / "training_history.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump(
        training_history,
        f,
        indent=2,
    )


# ------------------------------------------------------------
# 28. SAVE CONFIG
# ------------------------------------------------------------

training_config = {
    "dataset": str(DATASET_DIR),
    "output_directory": str(OUTPUT_DIR),
    "image_size": list(IMAGE_SIZE),
    "batch_size": BATCH_SIZE,
    "num_classes": num_classes,
    "phase1_epochs": PHASE1_EPOCHS,
    "phase2_epochs": PHASE2_EPOCHS,
    "phase1_learning_rate": PHASE1_LR,
    "phase2_learning_rate": PHASE2_LR,
    "seed": SEED,
    "architecture": "MobileNetV2",
    "pretrained_weights": "ImageNet",
    "loss": "sparse_categorical_crossentropy",
    "optimizer": "Adam",
    "class_weights": True,
    "augmentation": True,
    "input_size": "224x224x3",
}

with open(
    OUTPUT_DIR / "training_config.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump(
        training_config,
        f,
        indent=2,
    )


# ------------------------------------------------------------
# 29. SAVE MODEL
# ------------------------------------------------------------

final_model_path = (
    OUTPUT_DIR
    / "agrointel_unified_mobilenetv2_preliminary.keras"
)

model.save(
    final_model_path
)


# ------------------------------------------------------------
# 30. SAVE PRELIMINARY TRAINING REPORT
# ------------------------------------------------------------

macro_precision = float(
    report["macro avg"]["precision"]
)

macro_recall = float(
    report["macro avg"]["recall"]
)

macro_f1 = float(
    report["macro avg"]["f1-score"]
)

weighted_f1 = float(
    report["weighted avg"]["f1-score"]
)

report_lines = []

report_lines.append(
    "# AgroIntel Unified MobileNetV2 - Preliminary Training Report"
)

report_lines.append("")
report_lines.append("## Dataset")
report_lines.append(
    f"- Dataset: `{DATASET_DIR}`"
)
report_lines.append(
    f"- Classes: {num_classes}"
)
report_lines.append(
    "- Crops: 11"
)
report_lines.append(
    f"- Train images: {total_train}"
)
report_lines.append(
    f"- Validation images: "
    f"{sum(val_counts.values())}"
)
report_lines.append(
    f"- Test images: "
    f"{sum(test_counts.values())}"
)

report_lines.append("")
report_lines.append("## Model")
report_lines.append(
    "- Architecture: MobileNetV2"
)
report_lines.append(
    "- Pretrained weights: ImageNet"
)
report_lines.append(
    "- Input size: 224x224x3"
)
report_lines.append(
    "- Batch size: 16"
)

report_lines.append("")
report_lines.append("## Test Performance")
report_lines.append(
    f"- Test loss: {test_loss:.4f}"
)
report_lines.append(
    f"- Test accuracy: {test_accuracy:.4f}"
)
report_lines.append(
    f"- Macro precision: {macro_precision:.4f}"
)
report_lines.append(
    f"- Macro recall: {macro_recall:.4f}"
)
report_lines.append(
    f"- Macro F1: {macro_f1:.4f}"
)
report_lines.append(
    f"- Weighted F1: {weighted_f1:.4f}"
)

report_lines.append("")
report_lines.append("## Best Classes")
report_lines.append("")

for item in best_classes[:10]:
    report_lines.append(
        f"- {item['class']}: "
        f"F1={item['f1']:.4f}, "
        f"precision={item['precision']:.4f}, "
        f"recall={item['recall']:.4f}, "
        f"support={item['support']}"
    )

report_lines.append("")
report_lines.append("## Worst Classes")
report_lines.append("")

for item in worst_classes[:10]:
    report_lines.append(
        f"- {item['class']}: "
        f"F1={item['f1']:.4f}, "
        f"precision={item['precision']:.4f}, "
        f"recall={item['recall']:.4f}, "
        f"support={item['support']}"
    )

report_lines.append("")
report_lines.append("## Crop-Level Performance")
report_lines.append("")

for crop in sorted(crop_summary):

    result = crop_summary[crop]

    report_lines.append(
        f"- {crop}: "
        f"accuracy={result['accuracy']:.4f}, "
        f"macro F1={result['macro_f1']:.4f}, "
        f"test images={result['test_images']}"
    )

report_lines.append("")
report_lines.append("## Missing Healthy Classes")
report_lines.append("")
report_lines.append(
    "- Chickpea___healthy"
)
report_lines.append(
    "- Rice___healthy"
)
report_lines.append(
    "- Soybean___healthy"
)

report_lines.append("")
report_lines.append(
    "These three classes are not present in the preliminary "
    "training dataset and therefore the preliminary model cannot "
    "reliably classify healthy examples for those crops."
)

report_lines.append("")
report_lines.append("## Model Status")
report_lines.append("")

if macro_f1 >= 0.85:
    status = "EXCELLENT_PRELIMINARY"
elif macro_f1 >= 0.75:
    status = "GOOD_PRELIMINARY"
elif macro_f1 >= 0.65:
    status = "USABLE_WITH_LIMITATIONS"
else:
    status = "NEEDS_MORE_TRAINING_OR_DATA"

report_lines.append(
    f"Preliminary status: **{status}**"
)

report_lines.append("")
report_lines.append(
    "Do not replace the existing production disease model "
    "until this preliminary model has been reviewed."
)

with open(
    OUTPUT_DIR / "TRAINING_REPORT.md",
    "w",
    encoding="utf-8",
) as f:
    f.write("\n".join(report_lines))


# ------------------------------------------------------------
# 31. FINAL OUTPUT
# ------------------------------------------------------------

print("\n")
print("=" * 75)
print("TRAINING COMPLETE")
print("=" * 75)

print(f"Classes              : {num_classes}")
print(f"Test accuracy        : {test_accuracy:.4f}")
print(f"Macro F1             : {macro_f1:.4f}")
print(f"Weighted F1          : {weighted_f1:.4f}")
print(f"Status               : {status}")

print("\nBest model:")
print(checkpoint_path)

print("\nFinal model:")
print(final_model_path)

print("\nClassification report:")
print(
    OUTPUT_DIR
    / "classification_report.json"
)

print("\nConfusion matrix:")
print(
    OUTPUT_DIR
    / "confusion_matrix.png"
)

print("\nTraining report:")
print(
    OUTPUT_DIR
    / "TRAINING_REPORT.md"
)

print("\n" + "=" * 75)
print("IMPORTANT")
print("=" * 75)

print(
    "This is a PRELIMINARY model."
)
print(
    "The existing production model has NOT been modified."
)
print(
    "Do NOT integrate this model into the application yet."
)
