import os
import json
import random
from pathlib import Path

import numpy as np
import tensorflow as tf

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)

import matplotlib.pyplot as plt


# ============================================================
# AGROINTEL - PRELIMINARY UNIFIED MOBILENETV2 V2
# ============================================================

# ------------------------------------------------------------
# 1. PROJECT PATHS
# ------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_DIR = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "leaf_disease_final_v2"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "ml"
    / "models"
    / "preliminary_unified_v2"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# 2. TRAINING CONFIGURATION
# ------------------------------------------------------------

IMAGE_SIZE = (224, 224)

BATCH_SIZE = 16

PHASE1_EPOCHS = 10
PHASE2_EPOCHS = 15

PHASE1_LR = 1e-3
PHASE2_LR = 1e-5

SEED = 42

AUTOTUNE = tf.data.AUTOTUNE

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
}

# Reduce unnecessary TensorFlow console output.
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "1"


# ------------------------------------------------------------
# 3. REPRODUCIBILITY
# ------------------------------------------------------------

random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)


# ------------------------------------------------------------
# 4. STARTUP
# ------------------------------------------------------------

print("=" * 75)
print("AGROINTEL UNIFIED MOBILENETV2 V2 - PRELIMINARY TRAINING")
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
# 5. VERIFY DATASET DIRECTORIES
# ------------------------------------------------------------

required_splits = [
    "train",
    "validation",
    "test",
]

for split in required_splits:

    split_dir = DATASET_DIR / split

    if not split_dir.exists():
        raise FileNotFoundError(
            f"Missing dataset split:\n{split_dir}"
        )

print("\nDataset directories verified.")


# ------------------------------------------------------------
# 6. GET CLASS FOLDERS
# ------------------------------------------------------------

def get_class_folders(split_dir):
    return sorted(
        [
            folder.name
            for folder in split_dir.iterdir()
            if folder.is_dir()
        ]
    )


train_classes = get_class_folders(
    DATASET_DIR / "train"
)

validation_classes = get_class_folders(
    DATASET_DIR / "validation"
)

test_classes = get_class_folders(
    DATASET_DIR / "test"
)


print("\nChecking class vocabulary...")

if (
    train_classes
    != validation_classes
    or train_classes
    != test_classes
):
    print("\nERROR: Dataset splits do not have identical classes.")

    print("\nTrain-only:")
    print(
        sorted(
            set(train_classes)
            - set(validation_classes)
            - set(test_classes)
        )
    )

    print("\nValidation-only:")
    print(
        sorted(
            set(validation_classes)
            - set(train_classes)
            - set(test_classes)
        )
    )

    print("\nTest-only:")
    print(
        sorted(
            set(test_classes)
            - set(train_classes)
            - set(validation_classes)
        )
    )

    raise RuntimeError(
        "Train, validation and test class vocabularies must be identical."
    )

print(
    f"Class vocabulary verified: "
    f"{len(train_classes)} classes"
)


# ------------------------------------------------------------
# 7. LOAD DATASETS
# ------------------------------------------------------------

print("\nLoading training dataset...")

train_ds = tf.keras.utils.image_dataset_from_directory(
    DATASET_DIR / "train",
    labels="inferred",
    label_mode="int",
    class_names=train_classes,
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
    class_names=train_classes,
    image_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    shuffle=False,
)

print("\nLoading test dataset...")

test_ds = tf.keras.utils.image_dataset_from_directory(
    DATASET_DIR / "test",
    labels="inferred",
    label_mode="int",
    class_names=train_classes,
    image_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
    shuffle=False,
)


# ------------------------------------------------------------
# 8. CLASS INFORMATION
# ------------------------------------------------------------

class_names = train_ds.class_names
num_classes = len(class_names)

print("\n" + "=" * 75)
print(f"NUMBER OF CLASSES: {num_classes}")
print("=" * 75)

for index, class_name in enumerate(class_names):
    print(
        f"{index:02d}  {class_name}"
    )


# ------------------------------------------------------------
# 9. SAVE CLASS NAMES
# ------------------------------------------------------------

with open(
    OUTPUT_DIR / "class_names.json",
    "w",
    encoding="utf-8",
) as file:

    json.dump(
        class_names,
        file,
        indent=2,
        ensure_ascii=False,
    )


# ------------------------------------------------------------
# 10. COUNT IMAGES
# ------------------------------------------------------------

def count_images(split_dir):

    counts = {}

    for class_dir in sorted(
        split_dir.iterdir()
    ):

        if not class_dir.is_dir():
            continue

        count = 0

        for file_path in class_dir.rglob("*"):

            if (
                file_path.is_file()
                and file_path.suffix.lower()
                in IMAGE_EXTENSIONS
            ):
                count += 1

        counts[class_dir.name] = count

    return counts


train_counts = count_images(
    DATASET_DIR / "train"
)

validation_counts = count_images(
    DATASET_DIR / "validation"
)

test_counts = count_images(
    DATASET_DIR / "test"
)


# ------------------------------------------------------------
# 11. PRINT CLASS DISTRIBUTION
# ------------------------------------------------------------

print("\n" + "=" * 75)
print("CLASS DISTRIBUTION")
print("=" * 75)

for class_name in class_names:

    print(
        f"{class_name:55s}"
        f"Train={train_counts.get(class_name, 0):4d} "
        f"Val={validation_counts.get(class_name, 0):4d} "
        f"Test={test_counts.get(class_name, 0):4d}"
    )


total_train = sum(
    train_counts.values()
)

total_validation = sum(
    validation_counts.values()
)

total_test = sum(
    test_counts.values()
)

print("\nTotal training images   :", total_train)
print("Total validation images :", total_validation)
print("Total test images       :", total_test)


# ------------------------------------------------------------
# 12. CLASS WEIGHTS
# ------------------------------------------------------------

class_weights = {}

for index, class_name in enumerate(class_names):

    count = train_counts.get(
        class_name,
        0,
    )

    if count > 0:

        weight = (
            total_train
            / (num_classes * count)
        )

    else:

        weight = 1.0

    class_weights[index] = float(
        weight
    )


print("\n" + "=" * 75)
print("CLASS WEIGHTS")
print("=" * 75)

for index, class_name in enumerate(
    class_names
):

    print(
        f"{class_name:55s}"
        f"weight={class_weights[index]:.4f}"
    )


with open(
    OUTPUT_DIR / "class_weights.json",
    "w",
    encoding="utf-8",
) as file:

    json.dump(
        {
            class_names[index]:
            class_weights[index]
            for index in range(num_classes)
        },
        file,
        indent=2,
        ensure_ascii=False,
    )


# ------------------------------------------------------------
# 13. PREFETCH
# ------------------------------------------------------------

train_ds = train_ds.prefetch(
    AUTOTUNE
)

val_ds = val_ds.prefetch(
    AUTOTUNE
)

test_ds = test_ds.prefetch(
    AUTOTUNE
)


# ------------------------------------------------------------
# 14. DATA AUGMENTATION
# ------------------------------------------------------------

data_augmentation = tf.keras.Sequential(
    [
        tf.keras.layers.RandomFlip(
            "horizontal"
        ),

        tf.keras.layers.RandomRotation(
            0.08
        ),

        tf.keras.layers.RandomZoom(
            0.10
        ),

        tf.keras.layers.RandomTranslation(
            height_factor=0.05,
            width_factor=0.05,
        ),

        tf.keras.layers.RandomContrast(
            0.10
        ),
    ],
    name="data_augmentation",
)


# ------------------------------------------------------------
# 15. LOAD MOBILENETV2
# ------------------------------------------------------------

print("\n")
print("=" * 75)
print("LOADING IMAGENET-PRETRAINED MOBILENETV2")
print("=" * 75)

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
# 16. BUILD MODEL
# ------------------------------------------------------------

inputs = tf.keras.Input(
    shape=(
        IMAGE_SIZE[0],
        IMAGE_SIZE[1],
        3,
    )
)

x = data_augmentation(
    inputs
)

x = tf.keras.applications.mobilenet_v2.preprocess_input(
    x
)

x = base_model(
    x,
    training=False,
)

x = tf.keras.layers.GlobalAveragePooling2D()(
    x
)

x = tf.keras.layers.Dropout(
    0.30
)(
    x
)

outputs = tf.keras.layers.Dense(
    num_classes,
    activation="softmax",
    name="predictions",
)(
    x
)

model = tf.keras.Model(
    inputs=inputs,
    outputs=outputs,
    name="AgroIntel_MobileNetV2_V2",
)


# ------------------------------------------------------------
# 17. MODEL SUMMARY
# ------------------------------------------------------------

print("\n")
print("=" * 75)
print("MODEL SUMMARY")
print("=" * 75)

model.summary()


# ------------------------------------------------------------
# 18. CALLBACKS
# ------------------------------------------------------------

checkpoint_path = (
    OUTPUT_DIR
    / "best_preliminary_mobilenetv2_v2.keras"
)

callbacks = [

    tf.keras.callbacks.ModelCheckpoint(
        filepath=str(
            checkpoint_path
        ),
        monitor="val_loss",
        mode="min",
        save_best_only=True,
        verbose=1,
    ),

    tf.keras.callbacks.EarlyStopping(
        monitor="val_loss",
        mode="min",
        patience=4,
        restore_best_weights=True,
        verbose=1,
    ),

    tf.keras.callbacks.ReduceLROnPlateau(
        monitor="val_loss",
        mode="min",
        factor=0.2,
        patience=2,
        min_lr=1e-7,
        verbose=1,
    ),
]


# ------------------------------------------------------------
# 19. PHASE 1
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
# 20. PHASE 2
# ------------------------------------------------------------

print("\n")
print("=" * 75)
print("PHASE 2 - FINE TUNING UPPER MOBILENETV2 LAYERS")
print("=" * 75)

base_model.trainable = True

# Unfreeze approximately the final 30%.
fine_tune_from = int(
    len(base_model.layers)
    * 0.70
)

for layer in base_model.layers[
    :fine_tune_from
]:

    layer.trainable = False


# Keep BatchNorm frozen.
for layer in base_model.layers:

    if isinstance(
        layer,
        tf.keras.layers.BatchNormalization,
    ):

        layer.trainable = False


trainable_layers = sum(
    1
    for layer in base_model.layers
    if layer.trainable
)

print(
    f"Trainable MobileNetV2 layers: "
    f"{trainable_layers}/{len(base_model.layers)}"
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
# 21. LOAD BEST MODEL
# ------------------------------------------------------------

print("\n")
print("=" * 75)
print("LOADING BEST V2 CHECKPOINT")
print("=" * 75)

if not checkpoint_path.exists():

    raise FileNotFoundError(
        f"Checkpoint was not created:\n"
        f"{checkpoint_path}"
    )

model = tf.keras.models.load_model(
    checkpoint_path
)


# ------------------------------------------------------------
# 22. TEST EVALUATION
# ------------------------------------------------------------

print("\n")
print("=" * 75)
print("FINAL V2 TEST EVALUATION")
print("=" * 75)

test_loss, test_accuracy = model.evaluate(
    test_ds,
    verbose=1,
)

print(
    f"\nTest loss     : "
    f"{test_loss:.4f}"
)

print(
    f"Test accuracy : "
    f"{test_accuracy:.4f}"
)


# ------------------------------------------------------------
# 23. GENERATE TEST PREDICTIONS
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

    y_true.extend(
        labels.numpy().tolist()
    )

    y_pred.extend(
        predicted_labels.tolist()
    )


y_true = np.asarray(
    y_true
)

y_pred = np.asarray(
    y_pred
)


# ------------------------------------------------------------
# 24. CLASSIFICATION REPORT
# ------------------------------------------------------------

report = classification_report(

    y_true,

    y_pred,

    labels=np.arange(
        num_classes
    ),

    target_names=class_names,

    output_dict=True,

    zero_division=0,
)


print("\n")
print("=" * 75)
print("CLASSIFICATION REPORT")
print("=" * 75)

print(

    classification_report(

        y_true,

        y_pred,

        labels=np.arange(
            num_classes
        ),

        target_names=class_names,

        zero_division=0,
    )
)


with open(

    OUTPUT_DIR
    / "classification_report.json",

    "w",

    encoding="utf-8",

) as file:

    json.dump(

        report,

        file,

        indent=2,

        ensure_ascii=False,
    )


# ------------------------------------------------------------
# 25. CONFUSION MATRIX
# ------------------------------------------------------------

cm = confusion_matrix(

    y_true,

    y_pred,

    labels=np.arange(
        num_classes
    ),
)


np.save(

    OUTPUT_DIR
    / "confusion_matrix.npy",

    cm,
)


plt.figure(
    figsize=(22, 20)
)

plt.imshow(
    cm,
    interpolation="nearest",
)

plt.title(
    "AgroIntel Unified MobileNetV2 V2 - Confusion Matrix"
)

plt.colorbar()

tick_marks = np.arange(
    num_classes
)

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

plt.xlabel(
    "Predicted"
)

plt.ylabel(
    "True"
)

plt.tight_layout()


plt.savefig(

    OUTPUT_DIR
    / "confusion_matrix.png",

    dpi=200,

    bbox_inches="tight",
)


plt.close()


# ------------------------------------------------------------
# 26. NORMALIZED CONFUSION MATRIX
# ------------------------------------------------------------

row_sums = cm.sum(
    axis=1,
    keepdims=True,
)


normalized_cm = np.divide(

    cm,

    row_sums,

    out=np.zeros_like(
        cm,
        dtype=float,
    ),

    where=row_sums != 0,
)


np.save(

    OUTPUT_DIR
    / "normalized_confusion_matrix.npy",

    normalized_cm,
)


plt.figure(
    figsize=(22, 20)
)

plt.imshow(

    normalized_cm,

    interpolation="nearest",
)

plt.title(
    "AgroIntel Unified MobileNetV2 V2 - Normalized Confusion Matrix"
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

plt.xlabel(
    "Predicted"
)

plt.ylabel(
    "True"
)

plt.tight_layout()


plt.savefig(

    OUTPUT_DIR
    / "normalized_confusion_matrix.png",

    dpi=200,

    bbox_inches="tight",
)


plt.close()


# ------------------------------------------------------------
# 27. PER-CLASS METRICS
# ------------------------------------------------------------

class_metrics = []

for index, class_name in enumerate(
    class_names
):

    precision, recall, f1, _ = (
        precision_recall_fscore_support(

            y_true,

            y_pred,

            labels=[index],

            average="macro",

            zero_division=0,
        )
    )

    # Reliable support calculation.
    support = int(
        np.sum(
            y_true == index
        )
    )

    class_metrics.append(

        {
            "class": class_name,

            "precision": float(
                precision
            ),

            "recall": float(
                recall
            ),

            "f1": float(
                f1
            ),

            "support": support,
        }
    )


best_classes = sorted(

    class_metrics,

    key=lambda item:
    item["f1"],

    reverse=True,
)


worst_classes = sorted(

    class_metrics,

    key=lambda item:
    item["f1"],
)


# ------------------------------------------------------------
# 28. CROP-LEVEL METRICS
# ------------------------------------------------------------

def get_crop(class_name):

    if "___" in class_name:

        return class_name.split(
            "___",
            1
        )[0]

    return "Unknown"


crop_to_indices = {}

for index, class_name in enumerate(
    class_names
):

    crop = get_crop(
        class_name
    )

    crop_to_indices.setdefault(
        crop,
        []
    ).append(
        index
    )


crop_results = {}

for crop, indices in sorted(
    crop_to_indices.items()
):

    mask = np.isin(
        y_true,
        indices
    )

    crop_true = y_true[mask]
    crop_pred = y_pred[mask]

    if len(crop_true) == 0:

        crop_accuracy = 0.0
        crop_macro_f1 = 0.0

    else:

        crop_accuracy = float(
            np.mean(
                crop_true ==
                crop_pred
            )
        )

        crop_f1_values = []

        for class_index in indices:

            class_mask = (
                crop_true
                == class_index
            )

            if np.sum(
                class_mask
            ) == 0:

                continue

            _, _, class_f1, _ = (
                precision_recall_fscore_support(

                    crop_true,

                    crop_pred,

                    labels=[class_index],

                    average="macro",

                    zero_division=0,
                )
            )

            crop_f1_values.append(
                float(class_f1)
            )

        if crop_f1_values:

            crop_macro_f1 = float(
                np.mean(
                    crop_f1_values
                )
            )

        else:

            crop_macro_f1 = 0.0


    crop_results[crop] = {

        "test_images": int(
            len(crop_true)
        ),

        "num_classes": len(
            indices
        ),

        "accuracy": crop_accuracy,

        "macro_f1": crop_macro_f1,

        "classes": [
            class_names[i]
            for i in indices
        ],
    }


print("\n")
print("=" * 75)
print("CROP-LEVEL PERFORMANCE")
print("=" * 75)

for crop, result in sorted(
    crop_results.items()
):

    print(

        f"{crop:20s}"

        f"classes={result['num_classes']:2d} "

        f"test={result['test_images']:4d} "

        f"accuracy={result['accuracy']:.4f} "

        f"macro_F1={result['macro_f1']:.4f}"
    )


# ------------------------------------------------------------
# 29. SAVE TRAINING HISTORY
# ------------------------------------------------------------

training_history = {

    "phase1": {

        key: [
            float(value)
            for value in values
        ]

        for key, values
        in history1.history.items()
    },

    "phase2": {

        key: [
            float(value)
            for value in values
        ]

        for key, values
        in history2.history.items()
    },
}


with open(

    OUTPUT_DIR
    / "training_history.json",

    "w",

    encoding="utf-8",

) as file:

    json.dump(

        training_history,

        file,

        indent=2,
    )


# ------------------------------------------------------------
# 30. SAVE TRAINING CONFIG
# ------------------------------------------------------------

training_config = {

    "dataset":
        str(DATASET_DIR),

    "output_directory":
        str(OUTPUT_DIR),

    "image_size":
        list(IMAGE_SIZE),

    "batch_size":
        BATCH_SIZE,

    "num_classes":
        num_classes,

    "phase1_epochs":
        PHASE1_EPOCHS,

    "phase2_epochs":
        PHASE2_EPOCHS,

    "phase1_learning_rate":
        PHASE1_LR,

    "phase2_learning_rate":
        PHASE2_LR,

    "seed":
        SEED,

    "architecture":
        "MobileNetV2",

    "pretrained_weights":
        "ImageNet",

    "optimizer":
        "Adam",

    "loss":
        "sparse_categorical_crossentropy",

    "class_weights":
        True,

    "augmentation":
        True,

    "input_size":
        "224x224x3",
}


with open(

    OUTPUT_DIR
    / "training_config.json",

    "w",

    encoding="utf-8",

) as file:

    json.dump(

        training_config,

        file,

        indent=2,
    )


# ------------------------------------------------------------
# 31. SAVE FINAL V2 MODEL
# ------------------------------------------------------------

final_model_path = (

    OUTPUT_DIR
    / "agrointel_unified_mobilenetv2_v2.keras"
)


model.save(
    final_model_path
)


# ------------------------------------------------------------
# 32. BUILD TRAINING REPORT
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


if macro_f1 >= 0.85:

    status = "EXCELLENT_PRELIMINARY"

elif macro_f1 >= 0.75:

    status = "GOOD_PRELIMINARY"

elif macro_f1 >= 0.65:

    status = "USABLE_WITH_LIMITATIONS"

else:

    status = "NEEDS_MORE_TRAINING_OR_DATA"


report_lines = []


report_lines.append(
    "# AgroIntel Unified MobileNetV2 V2 - Training Report"
)

report_lines.append("")

report_lines.append(
    "## Dataset"
)

report_lines.append(

    f"- Dataset: `{DATASET_DIR}`"
)

report_lines.append(
    f"- Classes: {num_classes}"
)

report_lines.append(
    "- Target crops: 11"
)

report_lines.append(
    f"- Train images: {total_train}"
)

report_lines.append(
    f"- Validation images: "
    f"{total_validation}"
)

report_lines.append(
    f"- Test images: "
    f"{total_test}"
)


report_lines.append("")

report_lines.append(
    "## Model"
)

report_lines.append(
    "- Architecture: MobileNetV2"
)

report_lines.append(
    "- Pretrained weights: ImageNet"
)

report_lines.append(
    "- Input size: 224x224"
)

report_lines.append(
    "- Batch size: 16"
)

report_lines.append(
    "- Class weighting: enabled"
)

report_lines.append(
    "- Data augmentation: enabled"
)


report_lines.append("")

report_lines.append(
    "## Test Performance"
)

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

report_lines.append(
    "## Best 10 Classes"
)

for item in best_classes[:10]:

    report_lines.append(

        f"- {item['class']}: "

        f"F1={item['f1']:.4f}, "

        f"precision={item['precision']:.4f}, "

        f"recall={item['recall']:.4f}, "

        f"support={item['support']}"
    )


report_lines.append("")

report_lines.append(
    "## Worst 10 Classes"
)

for item in worst_classes[:10]:

    report_lines.append(

        f"- {item['class']}: "

        f"F1={item['f1']:.4f}, "

        f"precision={item['precision']:.4f}, "

        f"recall={item['recall']:.4f}, "

        f"support={item['support']}"
    )


report_lines.append("")

report_lines.append(
    "## Crop-Level Performance"
)

for crop, result in sorted(
    crop_results.items()
):

    report_lines.append(

        f"- {crop}: "

        f"accuracy={result['accuracy']:.4f}, "

        f"macro F1={result['macro_f1']:.4f}, "

        f"test images={result['test_images']}"
    )


report_lines.append("")

report_lines.append(
    "## Missing Healthy Classes"
)

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
    "These classes were not present in V2. "
    "The model therefore cannot reliably identify healthy "
    "examples for these three crops."
)

report_lines.append("")

report_lines.append(
    f"## Preliminary Status: **{status}**"
)

report_lines.append("")

report_lines.append(
    "This V2 model is a preliminary experiment and should "
    "not automatically replace the existing production model."
)


with open(

    OUTPUT_DIR
    / "TRAINING_REPORT.md",

    "w",

    encoding="utf-8",

) as file:

    file.write(
        "\n".join(
            report_lines
        )
    )


# ------------------------------------------------------------
# 33. FINAL OUTPUT
# ------------------------------------------------------------

print("\n")
print("=" * 75)
print("V2 TRAINING COMPLETE")
print("=" * 75)

print(
    f"Classes       : {num_classes}"
)

print(
    f"Test accuracy : {test_accuracy:.4f}"
)

print(
    f"Macro F1      : {macro_f1:.4f}"
)

print(
    f"Weighted F1   : {weighted_f1:.4f}"
)

print(
    f"Status        : {status}"
)

print("\nBest checkpoint:")
print(
    checkpoint_path
)

print("\nFinal V2 model:")
print(
    final_model_path
)

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

print("\n")
print("=" * 75)
print("IMPORTANT")
print("=" * 75)

print(
    "This is the V2 preliminary model."
)

print(
    "The V1 model remains untouched."
)

print(
    "The application has not been modified."
)