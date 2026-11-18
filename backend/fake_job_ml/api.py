from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from predict import predict


# ============================================================
# CREATE FASTAPI APP
# ============================================================

app = FastAPI(
    title="Hirely Fake Job Detection API",
    description="AI-based fake job detection backend",
    version="1.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ============================================================
# JOB DATA MODEL
# ============================================================

class JobData(BaseModel):

    title: str = ""

    url: str = ""

    text: str = ""


# ============================================================
# HOME API
# ============================================================

@app.get("/")
def home():

    return {
        "message": "Hirely Fake Job Detection API is running"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "OK"
    }


# ============================================================
# ANALYZE JOB
# ============================================================

@app.post("/analyze")
def analyze_job(job: JobData):

    # Combine job title and webpage text
    job_text = job.title + " " + job.text


    # Run prediction
    result = predict(job_text)


    # Return result to React
    return {

        "success": True,

        "title": job.title,

        "url": job.url,

        # Results of all 3 models
        "models": result["models"],

        # Best model selected during training
        "best_model": result["best_model"],

        "prediction": result["final_prediction"],

        "model_score": result["best_model_score"],

        # Final risk result
        "risk_score": result["risk_score"],

        "risk_level": result["risk_level"],

        # Rule-based risk
        "rule_bonus": result["rule_bonus"],

        # Why the job was considered suspicious
        "suspicious_factors": result[
            "suspicious_factors"
        ]
    }