from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List
from . import models, schemas, auth, tasks
from .database import engine, get_db
from .cache import cache, CacheManager

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Survey API", description="API for creating and managing surveys")

# Authentication endpoints
@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# User endpoints
@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = auth.get_user(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/me/", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(auth.get_current_active_user)):
    return current_user

# Survey endpoints
@app.post("/surveys/", response_model=schemas.Survey)
async def create_survey(
    survey: schemas.SurveyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_survey = models.Survey(
        title=survey.title,
        description=survey.description,
        user_id=current_user.id,
        category_id=survey.category_id
    )
    db.add(db_survey)
    db.commit()
    db.refresh(db_survey)
    
    # Add questions
    for question in survey.questions:
        db_question = models.Question(
            text=question.text,
            question_type=question.question_type,
            order_number=question.order_number,
            survey_id=db_survey.id
        )
        db.add(db_question)
    
    db.commit()
    db.refresh(db_survey)
    
    # Invalidate cache
    await CacheManager.invalidate_survey(db_survey.id)
    
    return db_survey

@app.get("/surveys/", response_model=List[schemas.Survey])
@cache(expire=300)
async def read_surveys(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    surveys = db.query(models.Survey).offset(skip).limit(limit).all()
    return surveys

@app.get("/surveys/{survey_id}", response_model=schemas.Survey)
@cache(expire=300)
async def read_survey(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    # Try to get from cache first
    cached_survey = await CacheManager.get_survey(survey_id)
    if cached_survey:
        return cached_survey

    survey = db.query(models.Survey).filter(models.Survey.id == survey_id).first()
    if survey is None:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    # Cache the survey
    await CacheManager.set_survey(survey_id, survey)
    return survey

# Category endpoints
@app.post("/categories/", response_model=schemas.Category)
def create_category(
    category: schemas.CategoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_category = models.Category(**category.dict())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@app.get("/categories/", response_model=List[schemas.Category])
@cache(expire=300)
async def read_categories(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    categories = db.query(models.Category).offset(skip).limit(limit).all()
    return categories

# Answer endpoints
@app.post("/answers/", response_model=schemas.Answer)
async def create_answer(
    answer: schemas.AnswerCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_answer = models.Answer(
        text=answer.text,
        is_correct=answer.is_correct,
        question_id=answer.question_id,
        user_id=current_user.id
    )
    db.add(db_answer)
    db.commit()
    db.refresh(db_answer)
    
    # Invalidate cache for the survey
    question = db.query(models.Question).filter(models.Question.id == answer.question_id).first()
    if question:
        await CacheManager.invalidate_survey(question.survey_id)
        await CacheManager.invalidate_survey_results(question.survey_id)
        
        # Schedule background tasks
        background_tasks.add_task(tasks.send_survey_notification, question.survey_id, current_user.id)
    
    return db_answer

@app.get("/answers/", response_model=List[schemas.Answer])
@cache(expire=300)
async def read_answers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    answers = db.query(models.Answer).filter(
        models.Answer.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    return answers

# Result endpoints
@app.post("/results/", response_model=schemas.Result)
async def create_result(
    result: schemas.ResultCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_result = models.Result(
        survey_id=result.survey_id,
        user_id=current_user.id,
        responses_number=result.responses_number
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    
    # Add result answers
    for answer in result.result_answers:
        db_result_answer = models.ResultAnswer(
            result_id=db_result.id,
            question_id=answer.question_id,
            answer_id=answer.answer_id,
            answer_text=answer.answer_text
        )
        db.add(db_result_answer)
    
    db.commit()
    db.refresh(db_result)
    
    # Invalidate cache
    await CacheManager.invalidate_survey_results(result.survey_id)
    
    # Schedule background tasks
    background_tasks.add_task(tasks.generate_survey_report, result.survey_id)
    background_tasks.add_task(tasks.send_survey_notification, result.survey_id, current_user.id)
    
    return db_result

@app.get("/results/", response_model=List[schemas.Result])
@cache(expire=300)
async def read_results(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    results = db.query(models.Result).filter(
        models.Result.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    return results

@app.get("/results/{result_id}", response_model=schemas.Result)
@cache(expire=300)
async def read_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    result = db.query(models.Result).filter(
        models.Result.id == result_id,
        models.Result.user_id == current_user.id
    ).first()
    if result is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return result

# Export endpoints
@app.post("/surveys/{survey_id}/export")
async def export_survey(
    survey_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    # Check if survey exists and user has access
    survey = db.query(models.Survey).filter(models.Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    # Schedule export task
    task = tasks.export_survey_data.delay(survey_id)
    
    return {
        "message": "Export started",
        "task_id": task.id
    }

@app.get("/surveys/{survey_id}/report")
async def get_survey_report(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    # Check if survey exists and user has access
    survey = db.query(models.Survey).filter(models.Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    # Generate report
    task = tasks.generate_survey_report.delay(survey_id)
    
    return {
        "message": "Report generation started",
        "task_id": task.id
    } 