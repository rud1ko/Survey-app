from celery import Celery
from .config import settings
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from . import models
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import boto3
from datetime import datetime

celery_app = Celery(
    "survey_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Database session
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@celery_app.task
def generate_survey_report(survey_id: int):
    """Generate a detailed report for a survey."""
    db = SessionLocal()
    try:
        # Get survey data
        survey = db.query(models.Survey).filter(models.Survey.id == survey_id).first()
        if not survey:
            return {"error": "Survey not found"}

        # Get all answers for the survey
        answers = db.query(models.Answer).join(models.Question).filter(
            models.Question.survey_id == survey_id
        ).all()

        # Create DataFrame for analysis
        data = []
        for answer in answers:
            data.append({
                "question_id": answer.question_id,
                "question_text": answer.question.text,
                "answer_text": answer.text,
                "is_correct": answer.is_correct,
                "user_id": answer.user_id
            })
        
        df = pd.DataFrame(data)
        
        # Generate statistics
        stats = {
            "total_responses": len(df["user_id"].unique()),
            "questions": {}
        }
        
        for question_id in df["question_id"].unique():
            question_data = df[df["question_id"] == question_id]
            stats["questions"][question_id] = {
                "total_answers": len(question_data),
                "correct_answers": len(question_data[question_data["is_correct"] == True]),
                "answer_distribution": question_data["answer_text"].value_counts().to_dict()
            }
        
        return stats
    finally:
        db.close()

@celery_app.task
def send_survey_notification(survey_id: int, user_id: int):
    """Send email notification about survey completion."""
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        survey = db.query(models.Survey).filter(models.Survey.id == survey_id).first()
        
        if not user or not survey:
            return {"error": "User or survey not found"}

        # Create email message
        msg = MIMEMultipart()
        msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        msg["To"] = user.email
        msg["Subject"] = f"Survey Completion: {survey.title}"

        body = f"""
        Dear {user.username},

        Thank you for completing the survey "{survey.title}".
        Your responses have been recorded successfully.

        Best regards,
        Survey Team
        """
        
        msg.attach(MIMEText(body, "plain"))

        # Send email
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        return {"status": "Email sent successfully"}
    finally:
        db.close()

@celery_app.task
def export_survey_data(survey_id: int):
    """Export survey data to S3 as CSV."""
    db = SessionLocal()
    try:
        # Get survey data
        survey = db.query(models.Survey).filter(models.Survey.id == survey_id).first()
        if not survey:
            return {"error": "Survey not found"}

        # Get all answers
        answers = db.query(models.Answer).join(models.Question).filter(
            models.Question.survey_id == survey_id
        ).all()

        # Create DataFrame
        data = []
        for answer in answers:
            data.append({
                "question_id": answer.question_id,
                "question_text": answer.question.text,
                "answer_text": answer.text,
                "is_correct": answer.is_correct,
                "user_id": answer.user_id,
                "timestamp": answer.created_at
            })
        
        df = pd.DataFrame(data)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"survey_{survey_id}_{timestamp}.csv"
        
        # Upload to S3
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        csv_buffer = df.to_csv(index=False)
        s3_client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=f"survey_exports/{filename}",
            Body=csv_buffer
        )
        
        return {
            "status": "Export completed",
            "filename": filename,
            "s3_path": f"survey_exports/{filename}"
        }
    finally:
        db.close() 