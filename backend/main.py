from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import json

from backend.database import engine, Base, get_db
from backend.users import User
from backend.job_analysis import JobAnalysis
from backend.schemas import JobAnalysisRequest, UserCreate
from .fake_job_ml.predict import predict
from .fake_job_ml.cleaner import clean_job_text


# Create database tables
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Hirely Fake Job Detection API",
    description="Backend API for AI-based fake job detection system",
    version="1.0"
)


# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# HOME
# =========================

@app.get("/")
def home():
    return {
        "message": "Hirely FastAPI Backend is running"
    }


# =========================
# SAVE USER
# =========================

@app.post("/users")
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):

    existing_user = db.query(User).filter(
        User.firebase_uid == user.firebase_uid
    ).first()

    if existing_user:
        return {
            "message": "User already exists",
            "id": existing_user.id,
            "firebase_uid": existing_user.firebase_uid,
            "name": existing_user.name,
            "email": existing_user.email
        }

    new_user = User(
        firebase_uid=user.firebase_uid,
        name=user.name,
        email=user.email
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User saved successfully",
        "id": new_user.id,
        "firebase_uid": new_user.firebase_uid,
        "name": new_user.name,
        "email": new_user.email
    }


# =========================
# ANALYZE JOB
# =========================

@app.post("/analyze")
def analyze_job(
    job: JobAnalysisRequest,
    db: Session = Depends(get_db)
):

    # =========================
    # CLEAN JOB TEXT
    # =========================

    clean_text = clean_job_text(job.text)

    # Combine title and cleaned job text
    job_text = f"{job.title} {clean_text}"


    # =========================
    # CALL ML MODEL
    # =========================

    result = predict(job_text)


    # =========================
    # GET MODEL RESULT
    # =========================

    prediction = result["final_prediction"]

    risk_score = result["risk_score"]

    risk_level = result["risk_level"]

    best_model = result["best_model"]

    model_score = result["best_model_score"]

    rule_bonus = result["rule_bonus"]

    suspicious_factors = result["suspicious_factors"]

    models = result["models"]

    # NOTE: this was computed by predict() all along but never
    # made it into the API response, so the frontend's "words
    # the model weighted toward Fraudulent" section always had
    # nothing to show.
    top_contributing_words = result.get("top_contributing_words", [])


    # =========================
    # SAVE ANALYSIS
    # =========================

    new_job = JobAnalysis(
        job_title=job.title,
        job_url=job.url,
        job_text=job.text,
        prediction=prediction,
        risk_score=risk_score,
        reasons=json.dumps(suspicious_factors)
    )

    db.add(new_job)

    db.commit()

    db.refresh(new_job)


    # =========================
    # SEND RESPONSE
    # =========================

    return {

        "success": True,

        "id": new_job.id,

        # NOTE: the frontend expects "extracted_title" /
        # "extracted_company" (used to let the user visually
        # confirm the correct job was analyzed). Previously
        # this only sent "title", so that check silently never
        # matched anything.
        #
        # "company" isn't currently extracted anywhere in the
        # pipeline (not in JobAnalysisRequest, not in the
        # content script) — this passes through job.company if
        # you add that field, and safely returns None if you
        # haven't yet. See note below the code.
        "title": job.title,

        "extracted_title": job.title,

        "extracted_company": getattr(job, "company", None),

        "url": job.url,

        "prediction": prediction,

        "final_prediction": prediction,

        "risk_score": risk_score,

        "risk_level": risk_level,

        "best_model": best_model,

        "model_score": model_score,

        "best_model_score": model_score,

        "rule_bonus": rule_bonus,

        "suspicious_factors": suspicious_factors,

        "top_contributing_words": top_contributing_words,

        "models": models
    }