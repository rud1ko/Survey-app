from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Category schemas
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int

    class Config:
        from_attributes = True

# Question schemas
class QuestionBase(BaseModel):
    text: str
    question_type: str
    order_number: int

class QuestionCreate(QuestionBase):
    pass

class Question(QuestionBase):
    id: int
    survey_id: int

    class Config:
        from_attributes = True

# Answer schemas
class AnswerBase(BaseModel):
    text: str
    is_correct: bool = False

class AnswerCreate(AnswerBase):
    question_id: int

class Answer(AnswerBase):
    id: int
    question_id: int
    user_id: int

    class Config:
        from_attributes = True

# Survey schemas
class SurveyBase(BaseModel):
    title: str
    description: Optional[str] = None

class SurveyCreate(SurveyBase):
    questions: List[QuestionCreate]
    category_id: int

class Survey(SurveyBase):
    id: int
    created_at: datetime
    user_id: int
    category_id: int
    questions: List[Question]
    category: Category

    class Config:
        from_attributes = True

# Result schemas
class ResultAnswerBase(BaseModel):
    question_id: int
    answer_id: int
    answer_text: str

class ResultAnswerCreate(ResultAnswerBase):
    pass

class ResultAnswer(ResultAnswerBase):
    id: int
    result_id: int

    class Config:
        from_attributes = True

class ResultBase(BaseModel):
    survey_id: int
    responses_number: int = 0

class ResultCreate(ResultBase):
    result_answers: List[ResultAnswerCreate]

class Result(ResultBase):
    id: int
    user_id: int
    submitted_at: datetime
    result_answers: List[ResultAnswer]

    class Config:
        from_attributes = True

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None 