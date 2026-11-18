import os
import re
import joblib
import numpy as np


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):
    """
    Clean job posting text before prediction.
    """

    text = str(text).lower()

    # Remove URLs
    text = re.sub(r"http\S+|www\S+", " ", text)

    # Remove HTML
    text = re.sub(r"<.*?>", " ", text)

    # Keep letters and numbers
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Remove extra spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ============================================================
# SUSPICIOUS JOB PATTERNS
#
# NOTE: ".*" in the old version was unbounded, so re.search
# could match huge spans of text between two keywords and
# return an ugly, meaningless "matched phrase". Every loose
# pattern below is now bounded (".{0,N}") so matches stay
# short and readable. The pattern list is also expanded to
# catch more common fake-job phrasing.
# ============================================================

SUSPICIOUS_PATTERNS = {

    "Payment/fee request": [
        r"registration fee",
        r"processing fee",
        r"joining fee",
        r"training fee",
        r"document(ation)? fee",
        r"verification fee",
        r"security deposit",
        r"refundable deposit",
        r"pay.{0,20}fee",
        r"pay.{0,20}(amount|money)",
        r"send.{0,20}money",
        r"transfer.{0,20}(amount|fee|money)",
        r"deposit.{0,20}(account|amount)",
        r"payment required",
        r"advance payment",
    ],

    "Unrealistic earning language": [
        r"guaranteed.{0,20}(high )?salary",
        r"(high )?salary.{0,20}guaranteed",
        r"earn.{0,15}(per day|per week|per month|daily|weekly|monthly)",
        r"make money.{0,15}(quickly|fast|instantly)",
        r"easy money",
        r"huge income",
        r"unlimited income",
        r"double your income",
        r"work.{0,10}hours?.{0,15}earn",
        r"100% job guarantee",
    ],

    "Urgency language": [
        r"apply immediately",
        r"apply now",
        r"urgent hiring",
        r"urgent requirement",
        r"join immediately",
        r"limited seats",
        r"limited vacan(cy|cies)",
        r"act now",
        r"immediate joining",
        r"hurry up",
    ],

    "Personal information request": [
        r"send.{0,20}bank details",
        r"bank account number",
        r"share.{0,20}otp",
        r"send.{0,20}otp",
        r"aadhar(\s?card)?.{0,15}number",
        r"pan\s?card.{0,15}number",
        r"debit card.{0,15}pin",
        r"credit card.{0,15}(number|cvv)",
        r"\bcvv\b",
    ],

    "Suspicious communication": [
        r"contact.{0,15}(telegram|whatsapp|signal)",
        r"message.{0,15}(telegram|whatsapp|signal)",
        r"whatsapp\s?number",
        r"telegram\s?(channel|group|id)",
        r"personal gmail",
    ],

    "Suspicious job claims": [
        r"no experience required.{0,30}(guaranteed )?salary",
        r"no experience.{0,15}high salary",
        r"no interview required",
        r"no skills required",
        r"work from home.{0,15}guaranteed",
        r"sitting job.{0,15}high salary",
        r"data entry.{0,15}unlimited earning",
        r"easy job.{0,15}high salary",
    ]
}


# ============================================================
# FIND RISK FACTORS (rule-based "why")
# ============================================================

def find_risk_factors(text):

    factors = []

    for category, patterns in SUSPICIOUS_PATTERNS.items():

        matches = []

        for pattern in patterns:

            match = re.search(pattern, text, re.IGNORECASE)

            if match:
                matches.append(match.group().strip())

        if matches:

            # Remove duplicate matches
            matches = list(dict.fromkeys(matches))

            factors.append({
                "category": category,
                "matches": matches
            })

    return factors


# ============================================================
# LOAD ALL MODELS
# ============================================================

def load_models():

    models = {}

    lr_path = os.path.join(MODEL_DIR, "logistic_regression.pkl")
    if os.path.exists(lr_path):
        models["Logistic Regression"] = joblib.load(lr_path)

    svm_path = os.path.join(MODEL_DIR, "linear_svm.pkl")
    if os.path.exists(svm_path):
        models["Linear SVM"] = joblib.load(svm_path)

    rf_path = os.path.join(MODEL_DIR, "random_forest.pkl")
    if os.path.exists(rf_path):
        models["Random Forest"] = joblib.load(rf_path)

    if not models:
        raise FileNotFoundError(
            "No trained models found inside the models folder."
        )

    return models


# ============================================================
# LOAD BEST MODEL
# ============================================================

def load_best_model():

    best_path = os.path.join(MODEL_DIR, "best_model.pkl")

    if not os.path.exists(best_path):
        return None

    return joblib.load(best_path)


# ============================================================
# HELPERS TO PULL (vectorizer, classifier) OUT OF A MODEL OBJECT
# ============================================================

def _extract_vectorizer_and_classifier(model_object):
    """
    Works for:
      - dict bundles: {"model": ..., "tfidf": ...}
      - sklearn Pipeline objects with a vectorizer step and a
        classifier step (found by duck-typing, not by name)
    Returns (vectorizer, classifier) or (None, None) if it
    can't figure them out.
    """

    if isinstance(model_object, dict):
        return model_object.get("tfidf"), model_object.get("model")

    # sklearn Pipeline (or anything with .named_steps / .steps)
    steps = None

    if hasattr(model_object, "named_steps"):
        steps = list(model_object.named_steps.values())
    elif hasattr(model_object, "steps"):
        steps = [s[1] for s in model_object.steps]

    if steps:

        vectorizer = None
        classifier = None

        for step in steps:
            if hasattr(step, "get_feature_names_out") and hasattr(step, "transform"):
                vectorizer = step
            if hasattr(step, "coef_") or hasattr(step, "feature_importances_"):
                classifier = step

        return vectorizer, classifier

    return None, None


def explain_prediction(model_object, cleaned_text, top_n=8):
    """
    Returns the words/tokens from the input text that most
    pushed the model toward the "Fraudulent" class.

    - Logistic Regression / Linear SVM: uses coef_ (weight of
      each word) times its TF-IDF value in this document.
    - Random Forest: uses feature_importances_ times TF-IDF
      value (importances are always positive, so presence +
      importance is used as the contribution signal).

    Returns a list of {"word": str, "weight": float}, sorted
    by contribution, largest first. Empty list if it can't be
    computed (e.g. model type not recognised).
    """

    vectorizer, classifier = _extract_vectorizer_and_classifier(model_object)

    if vectorizer is None or classifier is None:
        return []

    try:
        X = vectorizer.transform([cleaned_text])
    except Exception:
        return []

    feature_names = vectorizer.get_feature_names_out()
    row = X.tocoo()

    if row.nnz == 0:
        return []

    contributions = []

    if hasattr(classifier, "coef_"):

        classes = list(getattr(classifier, "classes_", [0, 1]))
        fraud_idx = classes.index(1) if 1 in classes else 0
        coefs = classifier.coef_[0] if classifier.coef_.shape[0] == 1 else classifier.coef_[fraud_idx]

        for col, tfidf_value in zip(row.col, row.data):
            weight = coefs[col] * tfidf_value
            contributions.append((feature_names[col], weight))

    elif hasattr(classifier, "feature_importances_"):

        importances = classifier.feature_importances_

        for col, tfidf_value in zip(row.col, row.data):
            weight = importances[col] * tfidf_value
            contributions.append((feature_names[col], weight))

    else:
        return []

    # Keep only words pushing toward "Fraudulent" (positive weight),
    # sorted strongest first
    contributions = [c for c in contributions if c[1] > 0]
    contributions.sort(key=lambda item: item[1], reverse=True)

    # --------------------------------------------------------
    # Clean up for readability:
    #  1. Drop tokens/n-grams that are purely numeric fragments
    #     (e.g. "000", "10", "10 000") — these come from things
    #     like "10,000" getting split apart and don't read as
    #     meaningful "reasons" on their own.
    #  2. Drop n-grams that are redundant with an already-kept,
    #     higher-weight phrase (e.g. skip "earn" if "can earn"
    #     already made the list, since it's the same signal).
    # --------------------------------------------------------

    def is_informative(phrase):
        tokens = phrase.split()
        return any(not t.isdigit() for t in tokens)

    def tokens_of(phrase):
        return set(phrase.split())

    cleaned = []

    for word, weight in contributions:

        if not is_informative(word):
            continue

        word_tokens = tokens_of(word)

        is_redundant = any(
            word_tokens <= tokens_of(kept["word"]) or tokens_of(kept["word"]) <= word_tokens
            for kept in cleaned
        )

        if is_redundant:
            continue

        cleaned.append({"word": word, "weight": round(float(weight), 4)})

        if len(cleaned) >= top_n:
            break

    return cleaned


# ============================================================
# MODEL PREDICTION
# ============================================================

def predict_with_model(model_object, text):

    if isinstance(model_object, dict):

        model = model_object.get("model")
        tfidf = model_object.get("tfidf")

        if model is None or tfidf is None:
            raise ValueError("Invalid model bundle. Model or TF-IDF missing.")

        X = tfidf.transform([text])
        prediction = model.predict(X)[0]

        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(X)[0]
            classes = list(model.classes_)
            if 1 in classes:
                fraud_index = classes.index(1)
                score = probabilities[fraud_index] * 100
            else:
                score = 0.0
        else:
            score = 100.0 if prediction == 1 else 0.0

        return int(prediction), float(score)

    prediction = model_object.predict([text])[0]

    if hasattr(model_object, "predict_proba"):
        probabilities = model_object.predict_proba([text])[0]
        classes = list(model_object.classes_)
        if 1 in classes:
            fraud_index = classes.index(1)
            score = probabilities[fraud_index] * 100
        else:
            score = 0.0
        return int(prediction), float(score)

    if hasattr(model_object, "decision_function"):
        decision = model_object.decision_function([text])
        decision = float(np.asarray(decision).ravel()[0])
        score = 100 / (1 + np.exp(-decision))
        return int(prediction), float(score)

    score = 100.0 if prediction == 1 else 0.0
    return int(prediction), float(score)


# ============================================================
# BEST MODEL PREDICTION
# ============================================================

def predict_best_model(best_model, text):

    if best_model is None:
        return None, None, None

    if isinstance(best_model, dict):

        model = best_model.get("model")
        tfidf = best_model.get("tfidf")
        model_name = best_model.get("model_name", "Best Model")

        if model is None or tfidf is None:
            return None, None, model_name

        X = tfidf.transform([text])
        prediction = model.predict(X)[0]

        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(X)[0]
            classes = list(model.classes_)
            if 1 in classes:
                fraud_index = classes.index(1)
                score = probabilities[fraud_index] * 100
            else:
                score = 0.0
        elif hasattr(model, "decision_function"):
            decision = model.decision_function(X)
            decision = float(np.asarray(decision).ravel()[0])
            score = 100 / (1 + np.exp(-decision))
        else:
            score = 100.0 if prediction == 1 else 0.0

        return int(prediction), float(score), model_name

    prediction = best_model.predict([text])[0]

    if hasattr(best_model, "predict_proba"):
        probabilities = best_model.predict_proba([text])[0]
        classes = list(best_model.classes_)
        if 1 in classes:
            fraud_index = classes.index(1)
            score = probabilities[fraud_index] * 100
        else:
            score = 0.0
    elif hasattr(best_model, "decision_function"):
        decision = best_model.decision_function([text])
        decision = float(np.asarray(decision).ravel()[0])
        score = 100 / (1 + np.exp(-decision))
    else:
        score = 100.0 if prediction == 1 else 0.0

    return int(prediction), float(score), "Best Model"


# ============================================================
# MAIN PREDICTION FUNCTION
# ============================================================

def predict(text):

    cleaned_text = clean_text(text)

    models = load_models()

    model_results = {}

    for model_name, model_object in models.items():

        try:
            prediction, score = predict_with_model(model_object, cleaned_text)

            model_results[model_name] = {
                "prediction": "Fraudulent" if prediction == 1 else "Legitimate",
                "prediction_value": int(prediction),
                "score": round(score, 2)
            }

        except Exception as error:
            model_results[model_name] = {
                "prediction": "Error",
                "prediction_value": None,
                "score": None,
                "error": str(error)
            }

    best_model = load_best_model()

    best_model_name = None
    best_prediction = None
    best_score = None
    best_model_object = best_model  # kept for explanation step

    if best_model is not None:
        try:
            best_prediction, best_score, best_model_name = predict_best_model(
                best_model, cleaned_text
            )
        except Exception as error:
            print("Best model prediction error:", error)

    if best_model_name is None:

        valid_models = [
            (name, result)
            for name, result in model_results.items()
            if result["score"] is not None
        ]

        if valid_models:
            best_model_name, best_result = max(
                valid_models, key=lambda item: item[1]["score"]
            )
            best_prediction = best_result["prediction_value"]
            best_score = best_result["score"]
            best_model_object = models.get(best_model_name)

    # --------------------------------------------------------
    # Rule-based fraud detection ("why" #1)
    # --------------------------------------------------------

    suspicious_factors = find_risk_factors(cleaned_text)

    rule_bonus = 0
    categories = [factor["category"] for factor in suspicious_factors]

    if "Payment/fee request" in categories:
        rule_bonus += 15
    if "Unrealistic earning language" in categories:
        rule_bonus += 10
    if "Urgency language" in categories:
        rule_bonus += 5
    if "Personal information request" in categories:
        rule_bonus += 15
    if "Suspicious communication" in categories:
        rule_bonus += 5
    if "Suspicious job claims" in categories:
        rule_bonus += 10

    # --------------------------------------------------------
    # Model-based word explanation ("why" #2 — this is new)
    # --------------------------------------------------------

    top_contributing_words = []

    if best_model_object is not None:
        try:
            top_contributing_words = explain_prediction(
                best_model_object, cleaned_text
            )
        except Exception as error:
            print("Explanation error:", error)

    if best_score is None:
        best_score = 0

    risk_score = round(best_score + rule_bonus)
    risk_score = max(0, min(100, risk_score))

    if risk_score >= 70:
        risk_level = "HIGH"
    elif risk_score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # --------------------------------------------------------
    # Final verdict — derived from risk_level, NOT from the raw
    # model's own 0.5 cutoff.
    #
    # Previously this used `best_prediction` directly, which is
    # just the classifier's internal >=50% decision. That meant
    # a posting could score 43/100 ("MEDIUM" risk, with several
    # model-flagged fraud words) and still be labeled
    # "Legitimate" simply because 42.73% < 50%. The label and
    # the risk meter were answering different questions and
    # could contradict each other.
    #
    # Now the label is tied to the same blended risk_score the
    # user actually sees, so it can't disagree with it.
    # --------------------------------------------------------

    if risk_level == "HIGH":
        final_prediction = "Fraudulent"
    elif risk_level == "MEDIUM":
        final_prediction = "Suspicious – Needs Review"
    else:
        final_prediction = "Legitimate"

    return {
        "models": model_results,
        "best_model": best_model_name,
        "best_model_prediction": "Fraudulent" if best_prediction == 1 else "Legitimate",
        "best_model_score": round(best_score, 2),
        "final_prediction": final_prediction,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "rule_bonus": rule_bonus,
        "suspicious_factors": suspicious_factors,
        "top_contributing_words": top_contributing_words,
    }


# ============================================================
# COMMAND LINE TEST
# ============================================================

if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:
        print("\nUsage:")
        print('python predict.py "job description"')
        sys.exit(1)

    input_text = " ".join(sys.argv[1:])

    result = predict(input_text)

    print("\n============================================================")
    print("              HIRELY FAKE JOB DETECTION")
    print("============================================================")

    print("\nMODEL PREDICTIONS")
    print("------------------------------------------------------------")

    for model_name, model_result in result["models"].items():
        print(f"\n{model_name}")
        print(f"Prediction : {model_result['prediction']}")
        if model_result["score"] is not None:
            print(f"Score      : {model_result['score']:.2f}%")
        else:
            print("Score      : Error")

    print("\n------------------------------------------------------------")
    print("BEST MODEL")
    print("------------------------------------------------------------")
    print(f"Selected Model   : {result['best_model']}")
    print(f"Model Prediction : {result['best_model_prediction']}")
    print(f"Model Score      : {result['best_model_score']:.2f}%")

    print("\n------------------------------------------------------------")
    print("FINAL RISK ANALYSIS")
    print("------------------------------------------------------------")
    print(f"Rule-based Risk Bonus : +{result['rule_bonus']}")
    print(f"Final Risk Score      : {result['risk_score']}/100")
    print(f"Risk Level            : {result['risk_level']}")
    print(f"Final Verdict         : {result['final_prediction']}")

    print("\nWHY THIS PREDICTION?")

    if result["suspicious_factors"]:
        print("\n  Rule-based red flags:")
        for factor in result["suspicious_factors"]:
            print(f"\n  [{factor['category']}]")
            for match in factor["matches"]:
                print(f'    • Matched phrase: "{match}"')
    else:
        print("\n  No rule-based red flags detected.")

    if result["top_contributing_words"]:

        print("\n  Words the model itself weighted most heavily toward 'Fraudulent':")

        max_weight = result["top_contributing_words"][0]["weight"]

        for item in result["top_contributing_words"]:

            phrase = item["word"].capitalize()

            # Simple relative strength bar (out of the top signal in this list)
            strength = round((item["weight"] / max_weight) * 100) if max_weight else 0

            print(f'    • "{phrase}"  ({strength}% relative strength)')

    else:
        print("\n  No model-level word explanation available for this model type.")

    print("\n============================================================")