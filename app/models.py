from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    surveys = relationship("Survey", back_populates="creator")
    answers = relationship("Answer", back_populates="user")
    results = relationship("Result", back_populates="user")

class Survey(Base):
    __tablename__ = "surveys"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    
    creator = relationship("User", back_populates="surveys")
    category = relationship("Category", back_populates="surveys")
    questions = relationship("Question", back_populates="survey", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="survey")

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    survey_id = Column(Integer, ForeignKey("surveys.id"))
    text = Column(Text)
    question_type = Column(String)  # multiple_choice, open_ended, yes_no
    order_number = Column(Integer)
    
    survey = relationship("Survey", back_populates="questions")
    answers = relationship("Answer", back_populates="question", cascade="all, delete-orphan")
    result_answers = relationship("ResultAnswer", back_populates="question")

class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    text = Column(Text)
    is_correct = Column(Boolean, default=False)
    
    question = relationship("Question", back_populates="answers")
    user = relationship("User", back_populates="answers")
    result_answers = relationship("ResultAnswer", back_populates="answer")

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(Text)
    
    surveys = relationship("Survey", back_populates="category")

class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    survey_id = Column(Integer, ForeignKey("surveys.id"))
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    responses_number = Column(Integer, default=0)
    
    user = relationship("User", back_populates="results")
    survey = relationship("Survey", back_populates="results")
    result_answers = relationship("ResultAnswer", back_populates="result", cascade="all, delete-orphan")

class ResultAnswer(Base):
    __tablename__ = "result_answers"

    id = Column(Integer, primary_key=True, index=True)
    result_id = Column(Integer, ForeignKey("results.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    answer_id = Column(Integer, ForeignKey("answers.id"))
    answer_text = Column(Text)
    
    result = relationship("Result", back_populates="result_answers")
    question = relationship("Question", back_populates="result_answers")
    answer = relationship("Answer", back_populates="result_answers") 