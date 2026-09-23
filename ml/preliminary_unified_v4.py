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
# AGROINTEL - UNIFIED MOBILENETV2 V4
# ============================================================
#
# V4 strategy:
#
# 1. Start from the trained V2 model.
# 2. Use the V3 dataset.
# 3. Preserve V2 learned weights for existing 46 classes.
# 4. Add 2 new healthy classes:
#       Rice___healthy
#       Soybean___healthy
# 5. Train the new 48-class head gently.
# 6. Fine-tune only the upper MobileNetV2 layers.
#
# V2 is NOT modified.
# Raw datasets are NOT modified.
# ============================================================


# ------------------------------------------------------------
# 1. PROJECT PATHS
# ------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

V3_DATASET_DIR = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "leaf_disease_final_v3"
)

V2_MODEL_DIR = (
    PROJECT_ROOT
    / "ml"
    / "models"
    / "preliminary_unified_v2"
)

V2_MODEL_PATH = (
    V2_MODEL_DIR
    / "agrointel_unified_mobilenetv2_v2.keras"
)

V2_CLASS_NAMES_PATH = (
    V2_MODEL_DIR
    / "class_names.json"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "ml"
    / "models"
    / "preliminary_unified_v4"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ------------------------------------------------------------
# 2. CONFIGURATION
# ------------------------------------------------------------

IMAGE_SIZE = (224, 224)

BATCH_SIZE = 16

# Gentle warm-start phase.
PHASE1_EPOCHS = 5
PHASE1_LR = 1e-4

# Upper-layer fine tuning.
PHASE2_EPOCHS = 12
PHASE2_LR = 2e-6

SEED = 42

AUTOTUNE = tf.data.AUTOTUNE

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
}

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

print("=" * 80)
print("AGROINTEL UNIFIED MOBILENETV2 V4")
print("=" * 80)

print(f"TensorFlow version : {tf.__version__}")
print(f"V3 dataset         : {V3_DATASET_DIR}")
print(f"V2 model           : {V2_MODEL_PATH}")
print(f"V4 output          : {OUTPUT_DIR}")
print(f"Image size         : {IMAGE_SIZE}")
print(f"Batch size         : {BATCH_SIZE}")

print()
print("Phase 1:")
print(f"  Epochs           : {PHASE1_EPOCHS}")
print(f"  Learning rate    : {PHASE1_LR}")

print()
print("Phase 2:")
print(f"  Epochs           : {PHASE2_EPOCHS}")
print(f"  Learning rate    : {PHASE2_LR}")

print("=" * 80)


# ------------------------------------------------------------
# 5. VERIFY PATHS
# ------------------------------------------------------------

if not V3_DATASET_DIR.exists():
    raise FileNotFoundError(
        f"V3 dataset not found:\n{V3_DATASET_DIR}"
    )

if not V2_MODEL_PATH.exists():
    raise FileNotFoundError(
        f"V2 model not found:\n{V2_MODEL_PATH}"
    )

if not V2_CLASS_NAMES_PATH.exists():
    raise FileNotFoundError(
        f"V2 class_names.json not found:\n"
        f"{V2_CLASS_NAMES_PATH}"
    )


for split in ["train", "validation", "test"]:

    split_dir = V3_DATASET_DIR / split

    if not split_dir.exists():

        raise FileNotFoundError(
            f"Missing V3 split:\n{split_dir}"
        )


# ------------------------------------------------------------
# 6. CLASS FOLDERS
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
    V3_DATASET_DIR / "train"
)

validation_classes = get_class_folders(
    V3_DATASET_DIR / "validation"
)

test_classes = get_class_folders(
    V3_DATASET_DIR / "test"
)


if (
    train_classes != validation_classes
    or train_classes != test_classes
):

    raise RuntimeError(
        "V3 train/validation/test class vocabularies "
        "are not identical."
    )


class_names = train_classes
num_classes = len(class_names)


print()
print(
    f"V3 class vocabulary: "
    f"{num_classes} classes"
)


# ------------------------------------------------------------
# 7. LOAD V2 CLASS NAMES
# ------------------------------------------------------------

with open(
    V2_CLASS_NAMES_PATH,
    "r",
    encoding="utf-8",
) as file:

    v2_class_names = json.load(file)


print(
    f"V2 class vocabulary: "
    f"{len(v2_class_names)} classes"
)


# ------------------------------------------------------------
# 8. VERIFY CLASS RELATIONSHIP
# ------------------------------------------------------------

v2_set = set(v2_class_names)
v4_set = set(class_names)

new_classes = sorted(
    v4_set - v2_set
)

removed_classes = sorted(
    v2_set - v4_set
)

print()
print("=" * 80)
print("V2 → V4 CLASS TRANSFER")
print("=" * 80)

print(
    f"Classes shared with V2 : "
    f"{len(v2_set & v4_set)}"
)

print(
    f"New classes            : "
    f"{new_classes}"
)

print(
    f"Removed classes        : "
    f"{removed_classes}"
)


# We expect the V3 dataset to add only these two healthy classes.
expected_new_classes = {
    "Rice___healthy",
    "Soybean___healthy",
}

if not expected_new_classes.issubset(
    set(new_classes)
):

    raise RuntimeError(
        "Expected Rice___healthy and "
        "Soybean___healthy to be new V3 classes."
    )

if removed_classes:

    raise RuntimeError(
        "V3 removed classes that existed in V2:\n"
        + "\n".join(removed_classes)
    )


# ------------------------------------------------------------
# 9. LOAD V3 DATASETS
# ------------------------------------------------------------

print()
print("Loading V3 training dataset...")

train_ds = (
    tf.keras.utils.image_dataset_from_directory(

        V3_DATASET_DIR / "train",

        labels="inferred",

        label_mode="int",

        class_names=class_names,

        image_size=IMAGE_SIZE,

        batch_size=BATCH_SIZE,

        shuffle=True,

        seed=SEED,
    )
)


print()
print("Loading V3 validation dataset...")

val_ds = (
    tf.keras.utils.image_dataset_from_directory(

        V3_DATASET_DIR / "validation",

        labels="inferred",

        label_mode="int",

        class_names=class_names,

        image_size=IMAGE_SIZE,

        batch_size=BATCH_SIZE,

        shuffle=False,
    )
)


print()
print("Loading V3 test dataset...")

test_ds = (
    tf.keras.utils.image_dataset_from_directory(

        V3_DATASET_DIR / "test",

        labels="inferred",

        label_mode="int",

        class_names=class_names,

        image_size=IMAGE_SIZE,

        batch_size=BATCH_SIZE,

        shuffle=False,
    )
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

        count = sum(

            1

            for path
            in class_dir.rglob("*")

            if (

                path.is_file()

                and path.suffix.lower()
                in IMAGE_EXTENSIONS
            )
        )

        counts[
            class_dir.name
        ] = count

    return counts


train_counts = count_images(
    V3_DATASET_DIR / "train"
)

val_counts = count_images(
    V3_DATASET_DIR / "validation"
)

test_counts = count_images(
    V3_DATASET_DIR / "test"
)


total_train = sum(
    train_counts.values()
)

total_val = sum(
    val_counts.values()
)

total_test = sum(
    test_counts.values()
)


print()
print("=" * 80)
print("DATASET SIZE")
print("=" * 80)

print(
    f"Train       : {total_train}"
)

print(
    f"Validation  : {total_val}"
)

print(
    f"Test        : {total_test}"
)

print(
    f"Total       : "
    f"{total_train + total_val + total_test}"
)


# ------------------------------------------------------------
# 11. CLASS WEIGHTS
# ------------------------------------------------------------
#
# Use moderate balanced weights.
# Cap extreme values at 3.0.
#
# This avoids allowing 3-14 image classes to dominate
# training.
# ------------------------------------------------------------

MAX_CLASS_WEIGHT = 3.0

class_weights = {}


print()
print("=" * 80)
print("CLASS WEIGHTS")
print("=" * 80)


for index, class_name in enumerate(
    class_names
):

    count = train_counts.get(
        class_name,
        0,
    )

    if count <= 0:

        raw_weight = 1.0

    else:

        raw_weight = (
            total_train
            / (
                num_classes
                * count
            )
        )

    used_weight = min(
        float(raw_weight),
        MAX_CLASS_WEIGHT,
    )

    class_weights[index] = (
        used_weight
    )

    print(
        f"{class_name:55s}"
        f"count={count:4d} "
        f"weight={used_weight:6.3f}"
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

            for index
            in range(num_classes)
        },

        file,

        indent=2,

        ensure_ascii=False,
    )


# ------------------------------------------------------------
# 12. PREFETCH
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
# 13. LOAD V2 MODEL
# ------------------------------------------------------------

print()
print("=" * 80)
print("LOADING V2 MODEL")
print("=" * 80)


v2_model = tf.keras.models.load_model(
    V2_MODEL_PATH
)


print(
    "V2 model loaded successfully."
)


# ------------------------------------------------------------
# 14. LOCATE V2 BACKBONE + HEAD
# ------------------------------------------------------------

# Find the MobileNetV2 backbone.
v2_base = None

for layer in v2_model.layers:

    if (
        isinstance(
            layer,
            tf.keras.Model,
        )
        and
        "mobilenetv2"
        in layer.name.lower()
    ):

        v2_base = layer

        break


if v2_base is None:

    raise RuntimeError(
        "Could not locate MobileNetV2 backbone "
        "inside the V2 model."
    )


# Find the old Dense classification layer.
v2_head = None

for layer in reversed(
    v2_model.layers
):

    if isinstance(
        layer,
        tf.keras.layers.Dense,
    ):

        v2_head = layer

        break


if v2_head is None:

    raise RuntimeError(
        "Could not locate V2 Dense classification head."
    )


print(
    f"V2 backbone: {v2_base.name}"
)

print(
    f"V2 classification head: {v2_head.name}"
)

print(
    f"V2 head output units: "
    f"{v2_head.units}"
)


if v2_head.units != len(
    v2_class_names
):

    raise RuntimeError(
        "V2 model output size does not match "
        "V2 class_names.json."
    )


# ------------------------------------------------------------
# 15. BUILD V4 MODEL
# ------------------------------------------------------------

print()
print("=" * 80)
print("BUILDING V4 MODEL FROM V2")
print("=" * 80)


# Important:
# Reuse the COMPLETE V2 feature pipeline up to
# the dropout layer, then create a new Dense(48) layer.
#
# V2 already contains:
# Input
# Augmentation
# MobileNet preprocessing
# MobileNetV2 backbone
# GlobalAveragePooling
# Dropout


# Identify all layers before the old Dense head.
head_index = None

for i, layer in enumerate(
    v2_model.layers
):

    if layer is v2_head:

        head_index = i

        break


if head_index is None:

    raise RuntimeError(
        "Could not determine V2 head position."
    )


# The layer immediately before the old Dense head
# should be Dropout.
feature_layer = v2_model.layers[
    head_index - 1
]


print(
    f"V2 feature layer: "
    f"{feature_layer.name}"
)


feature_model = tf.keras.Model(

    inputs=v2_model.input,

    outputs=feature_layer.output,

    name="V2_feature_extractor",
)


# Create V4 input using the original V2 input shape.
inputs = tf.keras.Input(

    shape=(

        IMAGE_SIZE[0],

        IMAGE_SIZE[1],

        3,
    )
)


features = feature_model(
    inputs
)


new_head = tf.keras.layers.Dense(

    num_classes,

    activation="softmax",

    name="predictions",
)


outputs = new_head(
    features
)


model = tf.keras.Model(

    inputs=inputs,

    outputs=outputs,

    name="AgroIntel_MobileNetV2_V4",
)


# ------------------------------------------------------------
# 16. COPY V2 HEAD WEIGHTS INTO V4 HEAD
# ------------------------------------------------------------
#
# This is the key V4 improvement.
#
# Existing 46 classes retain their learned V2 classifier weights.
# Only the two new healthy classes start from new/random weights.
# ------------------------------------------------------------

old_kernel, old_bias = (
    v2_head.get_weights()
)


feature_dim = old_kernel.shape[0]


new_kernel = np.zeros(
    (
        feature_dim,
        num_classes,
    ),
    dtype=np.float32,
)

new_bias = np.zeros(
    (
        num_classes,
    ),
    dtype=np.float32,
)


# Initialize the entire new head with small random values.
initializer = tf.keras.initializers.GlorotUniform(
    seed=SEED
)

new_kernel = initializer(

    shape=(
        feature_dim,
        num_classes,
    )
).numpy()


new_bias = np.zeros(
    num_classes,
    dtype=np.float32,
)


# Map V2 weights by class name.
for old_index, old_class in enumerate(
    v2_class_names
):

    if old_class not in class_names:
        continue

    new_index = class_names.index(
        old_class
    )

    new_kernel[:, new_index] = (
        old_kernel[:, old_index]
    )

    new_bias[new_index] = (
        old_bias[old_index]
    )


new_head.set_weights(
    [
        new_kernel,
        new_bias,
    ]
)


print()
print(
    "Transferred V2 classifier weights "
    f"for {len(v2_set & v4_set)} classes."
)

print(
    "New classes initialized:"
)

for new_class in new_classes:

    print(
        f"  - {new_class}"
    )


# ------------------------------------------------------------
# 17. PHASE 1 - WARM START
# ------------------------------------------------------------

print()
print("=" * 80)
print("PHASE 1 - WARM START FROM V2")
print("=" * 80)


# Keep the V2 feature extractor frozen.
feature_model.trainable = False


# Use the new head only.
model.compile(

    optimizer=tf.keras.optimizers.Adam(

        learning_rate=PHASE1_LR
    ),

    loss=(
        "sparse_categorical_crossentropy"
    ),

    metrics=[

        tf.keras.metrics
        .SparseCategoricalAccuracy(
            name="accuracy"
        )
    ],
)


phase1_checkpoint = (

    OUTPUT_DIR
    / "best_v4_phase1.keras"
)


phase1_callbacks = [

    tf.keras.callbacks.ModelCheckpoint(

        filepath=str(
            phase1_checkpoint
        ),

        monitor="val_loss",

        mode="min",

        save_best_only=True,

        verbose=1,
    ),

    tf.keras.callbacks.EarlyStopping(

        monitor="val_loss",

        mode="min",

        patience=2,

        restore_best_weights=True,

        verbose=1,
    ),

    tf.keras.callbacks.ReduceLROnPlateau(

        monitor="val_loss",

        mode="min",

        factor=0.5,

        patience=1,

        min_lr=1e-6,

        verbose=1,
    ),
]


history1 = model.fit(

    train_ds,

    validation_data=val_ds,

    epochs=PHASE1_EPOCHS,

    class_weight=class_weights,

    callbacks=phase1_callbacks,

    verbose=1,
)


# ------------------------------------------------------------
# 18. PHASE 2 - FINE TUNE UPPER 20%
# ------------------------------------------------------------

print()
print("=" * 80)
print("PHASE 2 - FINE TUNE UPPER 20% OF MOBILENETV2")
print("=" * 80)


# Re-enable backbone.
feature_model.trainable = True

# Locate MobileNetV2 layers.
mobile_layers = v2_base.layers

fine_tune_from = int(
    len(mobile_layers) * 0.80
)


for layer in mobile_layers[
    :fine_tune_from
]:

    layer.trainable = False


for layer in mobile_layers:

    if isinstance(
        layer,
        tf.keras.layers.BatchNormalization,
    ):

        layer.trainable = False


trainable_mobile_layers = sum(

    1

    for layer
    in mobile_layers

    if layer.trainable
)


print(

    "Trainable MobileNetV2 layers: "

    f"{trainable_mobile_layers}/"
    f"{len(mobile_layers)}"
)


model.compile(

    optimizer=tf.keras.optimizers.Adam(

        learning_rate=PHASE2_LR
    ),

    loss=(
        "sparse_categorical_crossentropy"
    ),

    metrics=[

        tf.keras.metrics
        .SparseCategoricalAccuracy(
            name="accuracy"
        )
    ],
)


phase2_checkpoint = (

    OUTPUT_DIR
    / "best_v4_phase2.keras"
)


phase2_callbacks = [

    tf.keras.callbacks.ModelCheckpoint(

        filepath=str(
            phase2_checkpoint
        ),

        monitor="val_loss",

        mode="min",

        save_best_only=True,

        verbose=1,
    ),

    tf.keras.callbacks.EarlyStopping(

        monitor="val_loss",

        mode="min",

        patience=3,

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


history2 = model.fit(

    train_ds,

    validation_data=val_ds,

    epochs=PHASE2_EPOCHS,

    class_weight=class_weights,

    callbacks=phase2_callbacks,

    verbose=1,
)


# ------------------------------------------------------------
# 19. LOAD BEST MODEL
# ------------------------------------------------------------

if not phase2_checkpoint.exists():

    raise FileNotFoundError(
        "V4 Phase 2 best checkpoint not found."
    )


best_model = tf.keras.models.load_model(
    phase2_checkpoint
)


# ------------------------------------------------------------
# 20. FINAL TEST EVALUATION
# ------------------------------------------------------------

print()
print("=" * 80)
print("FINAL V4 TEST EVALUATION")
print("=" * 80)


test_loss, test_accuracy = (
    best_model.evaluate(
        test_ds,
        verbose=1,
    )
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
# 21. TEST PREDICTIONS
# ------------------------------------------------------------

print(
    "\nGenerating predictions..."
)


y_true = []

y_pred = []


for images, labels in test_ds:

    predictions = (
        best_model.predict(
            images,
            verbose=0,
        )
    )


    predicted_labels = (
        np.argmax(
            predictions,
            axis=1,
        )
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
# 22. CLASSIFICATION REPORT
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


print()
print("=" * 80)
print("CLASSIFICATION REPORT")
print("=" * 80)


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
# 23. CONFUSION MATRIX
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
    figsize=(24, 22)
)


plt.imshow(

    cm,

    interpolation="nearest",
)


plt.title(
    "AgroIntel MobileNetV2 V4 - Confusion Matrix"
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
# 24. NORMALIZED CONFUSION MATRIX
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
    figsize=(24, 22)
)


plt.imshow(

    normalized_cm,

    interpolation="nearest",
)


plt.title(
    "AgroIntel MobileNetV2 V4 - "
    "Normalized Confusion Matrix"
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
# 25. PER-CLASS METRICS
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


    support = int(
        np.sum(
            y_true == index
        )
    )


    class_metrics.append(

        {
            "class":
                class_name,

            "precision":
                float(
                    precision
                ),

            "recall":
                float(
                    recall
                ),

            "f1":
                float(
                    f1
                ),

            "support":
                support,
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
# 26. CROP METRICS
# ------------------------------------------------------------

def get_crop(
    class_name
):

    if "___" in class_name:

        return class_name.split(
            "___",
            1,
        )[0]

    return "Unknown"


crop_indices = {}


for index, class_name in enumerate(
    class_names
):

    crop = get_crop(
        class_name
    )

    crop_indices.setdefault(
        crop,
        []
    ).append(
        index
    )


crop_results = {}


for crop, indices in sorted(
    crop_indices.items()
):

    mask = np.isin(

        y_true,

        indices,
    )


    crop_true = y_true[mask]

    crop_pred = y_pred[mask]


    if len(crop_true) == 0:

        accuracy = 0.0

        macro_f1 = 0.0

    else:

        accuracy = float(

            np.mean(

                crop_true
                == crop_pred
            )
        )


        f1_values = []


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


            f1_values.append(
                float(
                    class_f1
                )
            )


        macro_f1 = (

            float(
                np.mean(
                    f1_values
                )
            )

            if f1_values

            else 0.0
        )


    crop_results[crop] = {

        "test_images":
            int(
                len(crop_true)
            ),

        "classes":
            len(indices),

        "accuracy":
            accuracy,

        "macro_f1":
            macro_f1,
    }


print()
print("=" * 80)
print("CROP-LEVEL PERFORMANCE")
print("=" * 80)


for crop, result in sorted(
    crop_results.items()
):

    print(

        f"{crop:20s}"

        f"classes={result['classes']:2d} "

        f"test={result['test_images']:4d} "

        f"accuracy="
        f"{result['accuracy']:.4f} "

        f"macro_F1="
        f"{result['macro_f1']:.4f}"
    )


# ------------------------------------------------------------
# 27. SAVE HISTORY
# ------------------------------------------------------------

history = {

    "phase1": {

        key: [

            float(value)

            for value
            in values

        ]

        for key, values
        in history1.history.items()
    },


    "phase2": {

        key: [

            float(value)

            for value
            in values

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

        history,

        file,

        indent=2,
    )


# ------------------------------------------------------------
# 28. SAVE CONFIG
# ------------------------------------------------------------

config = {

    "base_model":
        "V2 trained MobileNetV2",

    "v2_model":
        str(V2_MODEL_PATH),

    "dataset":
        str(V3_DATASET_DIR),

    "output":
        str(OUTPUT_DIR),

    "num_classes":
        num_classes,

    "image_size":
        list(IMAGE_SIZE),

    "batch_size":
        BATCH_SIZE,

    "phase1_epochs":
        PHASE1_EPOCHS,

    "phase1_learning_rate":
        PHASE1_LR,

    "phase2_epochs":
        PHASE2_EPOCHS,

    "phase2_learning_rate":
        PHASE2_LR,

    "max_class_weight":
        MAX_CLASS_WEIGHT,

    "seed":
        SEED,

    "strategy":
        "transfer_from_V2",
}


with open(

    OUTPUT_DIR
    / "training_config.json",

    "w",

    encoding="utf-8",

) as file:

    json.dump(

        config,

        file,

        indent=2,
    )


# ------------------------------------------------------------
# 29. SAVE FINAL V4 MODEL
# ------------------------------------------------------------

final_model_path = (

    OUTPUT_DIR
    / "agrointel_unified_mobilenetv2_v4.keras"
)


best_model.save(
    final_model_path
)


# ------------------------------------------------------------
# 30. OVERALL METRICS
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


# ------------------------------------------------------------
# 31. STATUS
# ------------------------------------------------------------

if (

    test_accuracy >= 0.93

    and macro_f1 >= 0.90
):

    status = (
        "EXCELLENT_PRELIMINARY"
    )

elif (

    test_accuracy >= 0.90

    and macro_f1 >= 0.85
):

    status = (
        "GOOD_PRELIMINARY"
    )

elif (

    test_accuracy >= 0.80

    and macro_f1 >= 0.75
):

    status = (
        "USABLE_WITH_LIMITATIONS"
    )

else:

    status = (
        "NEEDS_MORE_TRAINING_OR_DATA"
    )


# ------------------------------------------------------------
# 32. TRAINING REPORT
# ------------------------------------------------------------

lines = []


lines.append(
    "# AgroIntel Unified MobileNetV2 V4"
)


lines.append("")


lines.append(
    "## Dataset"
)

lines.append(
    f"- Dataset: `{V3_DATASET_DIR}`"
)

lines.append(
    f"- Classes: {num_classes}"
)

lines.append(
    f"- Train: {total_train}"
)

lines.append(
    f"- Validation: {total_val}"
)

lines.append(
    f"- Test: {total_test}"
)


lines.append("")


lines.append(
    "## Transfer Learning"
)

lines.append(
    f"- Starting model: `{V2_MODEL_PATH}`"
)

lines.append(
    "- Existing V2 classifier weights transferred "
    "to matching classes."
)

lines.append(
    f"- New classes: {', '.join(new_classes)}"
)


lines.append("")


lines.append(
    "## Training"
)

lines.append(
    f"- Phase 1: V2 warm start, "
    f"{PHASE1_EPOCHS} epochs, LR={PHASE1_LR}"
)

lines.append(
    f"- Phase 2: upper ~20% fine-tuning, "
    f"{PHASE2_EPOCHS} epochs, LR={PHASE2_LR}"
)

lines.append(
    f"- Maximum class weight: "
    f"{MAX_CLASS_WEIGHT}"
)


lines.append("")


lines.append(
    "## Test Performance"
)

lines.append(
    f"- Test accuracy: {test_accuracy:.4f}"
)

lines.append(
    f"- Macro precision: {macro_precision:.4f}"
)

lines.append(
    f"- Macro recall: {macro_recall:.4f}"
)

lines.append(
    f"- Macro F1: {macro_f1:.4f}"
)

lines.append(
    f"- Weighted F1: {weighted_f1:.4f}"
)


lines.append("")


lines.append(
    "## Best 10 Classes"
)

for item in best_classes[:10]:

    lines.append(

        f"- {item['class']}: "
        f"F1={item['f1']:.4f}, "
        f"support={item['support']}"
    )


lines.append("")


lines.append(
    "## Worst 10 Classes"
)

for item in worst_classes[:10]:

    lines.append(

        f"- {item['class']}: "
        f"F1={item['f1']:.4f}, "
        f"support={item['support']}"
    )


lines.append("")


lines.append(
    "## Crop-Level Performance"
)

for crop, result in sorted(
    crop_results.items()
):

    lines.append(

        f"- {crop}: "
        f"accuracy={result['accuracy']:.4f}, "
        f"macro F1={result['macro_f1']:.4f}, "
        f"test={result['test_images']}"
    )


lines.append("")


lines.append(
    "## Healthy Coverage"
)

healthy_present = [

    name

    for name in class_names

    if name.endswith(
        "___healthy"
    )
]


for name in healthy_present:

    lines.append(
        f"- {name}"
    )


lines.append(
    "- Chickpea___healthy remains unavailable."
)


lines.append("")


lines.append(
    f"## Status: **{status}**"
)


lines.append("")


lines.append(
    "V2 remains untouched and should remain the "
    "current application model until V4 is validated."
)


with open(

    OUTPUT_DIR
    / "TRAINING_REPORT.md",

    "w",

    encoding="utf-8",

) as file:

    file.write(
        "\n".join(lines)
    )


# ------------------------------------------------------------
# 33. FINAL
# ------------------------------------------------------------

print()
print("=" * 80)
print("V4 TRAINING COMPLETE")
print("=" * 80)

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

print()
print("V4 model:")
print(
    final_model_path
)

print()
print("Classification report:")
print(
    OUTPUT_DIR
    / "classification_report.json"
)

print()
print("Confusion matrix:")
print(
    OUTPUT_DIR
    / "confusion_matrix.png"
)

print()
print("Training report:")
print(
    OUTPUT_DIR
    / "TRAINING_REPORT.md"
)

print()
print("=" * 80)
print("V2 WAS NOT MODIFIED")
print("=" * 80)