# AI-Based Fake Job Detection - ML Module

This folder contains the Machine Learning/NLP part of the project.
It does NOT contain the Flask backend or React/browser-extension frontend.

## Dataset

Use the EMSCAD / Fake Job Postings dataset. Put the CSV here:

    data/fake_job_postings.csv

The target column should be:

    fraudulent

where:
- 0 = legitimate
- 1 = fraudulent

## Setup

Create a virtual environment if desired, then:

    pip install -r requirements.txt

## Train

    python train_models.py

The script compares:
- Logistic Regression
- Linear SVM
- Random Forest

Metrics:
- Accuracy
- Precision
- Recall
- F1-score
- Confusion matrix

The model with the best F1-score is saved in `models/`.

## Test a single job

After training:

    python predict.py "Paste the job title and description here"

The prediction module returns:
- model used
- legitimate/fraudulent prediction
- fraud probability
- risk score
- risk level
- suspicious factors

## How backend will use it later

The Flask backend can import:

    from predict import predict

and call:

    result = predict(job_text)

The result can then be returned to the browser extension as JSON.

## Important

The rule-based suspicious indicators are supporting signals, not proof that a job is fraudulent. The ML model should remain the main prediction component.
