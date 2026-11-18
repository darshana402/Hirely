from pathlib import Path
import re
import warnings

import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

warnings.filterwarnings("ignore")


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "results"

DATA_FILE = DATA_DIR / "fake_job_postings.csv"

MODELS_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):

    if pd.isna(text):
        return ""

    text = str(text).lower()

    # Remove URLs
    text = re.sub(r"http\S+|www\S+|https\S+", " ", text)

    # Remove HTML
    text = re.sub(r"<.*?>", " ", text)

    # Remove special characters
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)

    # Remove extra spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# LOAD DATA
# ============================================================

def load_data():

    print("\nLoading dataset from:")
    print(DATA_FILE)

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"\nDataset not found:\n{DATA_FILE}"
        )

    df = pd.read_csv(DATA_FILE)

    print(f"\nRaw dataset shape: {df.shape}")

    print("\nColumns found:")
    print(df.columns.tolist())

    # --------------------------------------------------------
    # Check target column
    # --------------------------------------------------------

    if "fraudulent" not in df.columns:
        raise ValueError(
            "\nThe dataset does not contain a 'fraudulent' column."
        )

    # --------------------------------------------------------
    # Raw target information
    # --------------------------------------------------------

    print("\nRaw target values:")
    print(df["fraudulent"].value_counts(dropna=False))

    print("\nRaw target data type:")
    print(df["fraudulent"].dtype)

    # --------------------------------------------------------
    # Convert target
    # --------------------------------------------------------

    target = (
        df["fraudulent"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    target = target.replace({

        # Original dataset format
        "f": 0,
        "t": 1,

        # Other possible formats
        "false": 0,
        "true": 1,

        "no": 0,
        "yes": 1,

        "real": 0,
        "fake": 1,

        "legitimate": 0,
        "fraudulent": 1,

        # Numeric strings
        "0": 0,
        "1": 1,

        "0.0": 0,
        "1.0": 1,
    })

    target = pd.to_numeric(
        target,
        errors="coerce"
    )

    # --------------------------------------------------------
    # Show converted target
    # --------------------------------------------------------

    print("\nTarget after conversion:")
    print(target.value_counts(dropna=False))

    # --------------------------------------------------------
    # Remove invalid labels
    # --------------------------------------------------------

    invalid_count = target.isna().sum()

    if invalid_count > 0:

        print(
            f"\nWarning: {invalid_count} rows have "
            "an invalid/missing target and will be removed."
        )

    valid_mask = target.notna()

    df = df.loc[valid_mask].copy()

    target = target.loc[valid_mask].astype(int)

    # --------------------------------------------------------
    # Validate labels
    # --------------------------------------------------------

    valid_labels = sorted(
        target.unique().tolist()
    )

    print("\nValid target labels:")
    print(valid_labels)

    if len(df) == 0:

        raise ValueError(
            "\nNO VALID ROWS REMAIN AFTER TARGET CLEANING."
        )

    if not set(valid_labels).issubset({0, 1}):

        raise ValueError(
            f"\nUnexpected target labels found: {valid_labels}\n"
            "Expected labels are 0 and 1."
        )

    if len(valid_labels) < 2:

        raise ValueError(
            "\nOnly one target class exists."
            "\nBoth legitimate and fraudulent jobs are required."
        )

    # --------------------------------------------------------
    # Final dataset information
    # --------------------------------------------------------

    print(f"\nClean dataset shape: {df.shape}")

    print("\nFinal training information:")
    print(f"Total samples : {len(df)}")
    print(f"Total labels  : {len(target)}")
    print(f"Fraudulent    : {(target == 1).sum()}")
    print(f"Legitimate    : {(target == 0).sum()}")

    return df, target


# ============================================================
# BUILD TEXT FEATURES
# ============================================================

def build_text(df):

    print("\nBuilding combined text features...")

    text_columns = [
        "title",
        "location",
        "department",
        "salary_range",
        "company_profile",
        "description",
        "requirements",
        "benefits",
        "employment_type",
        "required_experience",
        "required_education",
        "industry",
        "function",
    ]

    # Use only columns that exist
    available_columns = [
        column
        for column in text_columns
        if column in df.columns
    ]

    print("\nText columns being used:")
    print(available_columns)

    if not available_columns:
        raise ValueError(
            "\nNo usable text columns were found in the dataset."
        )

    text = (
        df[available_columns]
        .fillna("")
        .astype(str)
        .agg(" ".join, axis=1)
    )

    text = text.apply(clean_text)

    print("\nText features created.")

    return text


# ============================================================
# EVALUATE MODEL
# ============================================================

def evaluate_model(
    model_name,
    model,
    X_test,
    y_test
):

    print("\n" + "=" * 60)
    print(f"Evaluating {model_name}")
    print("=" * 60)

    predictions = model.predict(X_test)

    accuracy = accuracy_score(
        y_test,
        predictions
    )

    precision = precision_score(
        y_test,
        predictions,
        zero_division=0
    )

    recall = recall_score(
        y_test,
        predictions,
        zero_division=0
    )

    f1 = f1_score(
        y_test,
        predictions,
        zero_division=0
    )

    print(f"\nAccuracy  : {accuracy:.4f}")
    print(f"Precision : {precision:.4f}")
    print(f"Recall    : {recall:.4f}")
    print(f"F1 Score  : {f1:.4f}")

    print("\nClassification Report:")

    print(
        classification_report(
            y_test,
            predictions,
            target_names=[
                "Legitimate",
                "Fraudulent"
            ],
            zero_division=0
        )
    )

    print("Confusion Matrix:")

    print(
        confusion_matrix(
            y_test,
            predictions
        )
    )

    return {
        "model": model_name,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
    }


# ============================================================
# CREATE STANDARD MODEL BUNDLE
# ============================================================

def create_model_bundle(model_name, model):

    """
    Creates the same model structure for all algorithms.

    Final structure:

    {
        "model": trained classifier,
        "tfidf": fitted TF-IDF vectorizer,
        "model_name": model name
    }
    """

    if model_name == "Logistic Regression":

        tfidf = model.named_steps["tfidf"]
        classifier = model.named_steps["classifier"]

    elif model_name == "Linear SVM":

        tfidf = model.named_steps["tfidf"]
        classifier = model.named_steps["classifier"]

    elif model_name == "Random Forest":

        # Random Forest is already handled separately
        # in the training section.
        return model

    else:

        raise ValueError(
            f"Unknown model: {model_name}"
        )

    return {
        "model": classifier,
        "tfidf": tfidf,
        "model_name": model_name
    }


# ============================================================
# TRAIN MODELS
# ============================================================

def train():

    print("\n==========================================")
    print("     FAKE JOB DETECTION ML TRAINING")
    print("==========================================")

    # --------------------------------------------------------
    # Load dataset
    # --------------------------------------------------------

    df, y = load_data()

    # --------------------------------------------------------
    # Build combined text
    # --------------------------------------------------------

    X = build_text(df)

    # --------------------------------------------------------
    # Remove rows with empty text
    # --------------------------------------------------------

    non_empty_mask = X.str.strip().ne("")

    removed = (~non_empty_mask).sum()

    if removed > 0:

        print(
            f"\nWarning: Removing {removed} rows "
            "with empty text."
        )

    X = X.loc[non_empty_mask]
    y = y.loc[non_empty_mask]

    print(
        f"\nFinal usable samples: {len(X)}"
    )

    # --------------------------------------------------------
    # Train/Test split
    # --------------------------------------------------------

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y
    )

    print("\nTrain/Test split:")
    print(f"Training samples : {len(X_train)}")
    print(f"Testing samples  : {len(X_test)}")

    print("\nTraining class distribution:")
    print(y_train.value_counts())

    print("\nTesting class distribution:")
    print(y_test.value_counts())

    # ========================================================
    # LOGISTIC REGRESSION
    # ========================================================

    print("\n\nTraining Logistic Regression...")

    logistic_model = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                max_features=50000,
                ngram_range=(1, 2),
                min_df=2,
                sublinear_tf=True
            )
        ),

        (
            "classifier",
            LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                random_state=42
            )
        )
    ])

    logistic_model.fit(
        X_train,
        y_train
    )

    logistic_results = evaluate_model(
        "Logistic Regression",
        logistic_model,
        X_test,
        y_test
    )

    logistic_path = (
        MODELS_DIR /
        "logistic_regression.pkl"
    )

    joblib.dump(
        logistic_model,
        logistic_path
    )

    print(f"\nSaved: {logistic_path}")

    # ========================================================
    # LINEAR SVM
    # ========================================================

    print("\n\nTraining Linear SVM...")

    svm_model = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                max_features=50000,
                ngram_range=(1, 2),
                min_df=2,
                sublinear_tf=True
            )
        ),

        (
            "classifier",
            LinearSVC(
                class_weight="balanced",
                random_state=42
            )
        )
    ])

    svm_model.fit(
        X_train,
        y_train
    )

    svm_results = evaluate_model(
        "Linear SVM",
        svm_model,
        X_test,
        y_test
    )

    svm_path = (
        MODELS_DIR /
        "linear_svm.pkl"
    )

    joblib.dump(
        svm_model,
        svm_path
    )

    print(f"\nSaved: {svm_path}")

    # ========================================================
    # RANDOM FOREST
    # ========================================================

    print("\n\nTraining Random Forest...")

    rf_tfidf = TfidfVectorizer(
        max_features=20000,
        ngram_range=(1, 2),
        min_df=2,
        sublinear_tf=True
    )

    X_train_rf = rf_tfidf.fit_transform(
        X_train
    )

    X_test_rf = rf_tfidf.transform(
        X_test
    )

    print(
        f"\nRandom Forest feature count: "
        f"{X_train_rf.shape[1]}"
    )

    rf_model = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_split=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )

    rf_model.fit(
        X_train_rf,
        y_train
    )

    # --------------------------------------------------------
    # Evaluate RF
    # --------------------------------------------------------

    rf_results = evaluate_model(
        "Random Forest",
        rf_model,
        X_test_rf,
        y_test
    )

    rf_path = (
        MODELS_DIR /
        "random_forest.pkl"
    )

    joblib.dump(
        {
            "model": rf_model,
            "tfidf": rf_tfidf,
            "model_name": "Random Forest"
        },
        rf_path
    )

    print(f"\nSaved: {rf_path}")

    # ========================================================
    # MODEL COMPARISON
    # ========================================================

    results = [
        logistic_results,
        svm_results,
        rf_results
    ]

    results_df = pd.DataFrame(
        results
    )

    results_df = results_df.sort_values(
        by="f1_score",
        ascending=False
    )

    print("\n\n==========================================")
    print("           MODEL COMPARISON")
    print("==========================================")

    print(
        results_df.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # Save results
    # --------------------------------------------------------

    results_file = (
        RESULTS_DIR /
        "model_results.csv"
    )

    results_df.to_csv(
        results_file,
        index=False
    )

    print(
        f"\nResults saved to:\n"
        f"{results_file}"
    )

    # ========================================================
    # SAVE BEST MODEL
    # ========================================================

    best_model_name = (
        results_df.iloc[0]["model"]
    )

    best_f1 = (
        results_df.iloc[0]["f1_score"]
    )

    print(
        f"\nBest model based on F1 score: "
        f"{best_model_name}"
    )

    print(
        f"Best F1 Score: {best_f1:.4f}"
    )

    best_model_path = (
        MODELS_DIR /
        "best_model.pkl"
    )

    # --------------------------------------------------------
    # Create standard bundle
    # --------------------------------------------------------

    if best_model_name == "Logistic Regression":

        best_bundle = {
            "model": logistic_model.named_steps["classifier"],
            "tfidf": logistic_model.named_steps["tfidf"],
            "model_name": "Logistic Regression"
        }

    elif best_model_name == "Linear SVM":

        best_bundle = {
            "model": svm_model.named_steps["classifier"],
            "tfidf": svm_model.named_steps["tfidf"],
            "model_name": "Linear SVM"
        }

    else:

        best_bundle = {
            "model": rf_model,
            "tfidf": rf_tfidf,
            "model_name": "Random Forest"
        }

    joblib.dump(
        best_bundle,
        best_model_path
    )

    print(
        f"\nBest model saved to:\n"
        f"{best_model_path}"
    )

    # ========================================================
    # FINISHED
    # ========================================================

    print("\n==========================================")
    print("        TRAINING COMPLETED")
    print("==========================================\n")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    train()