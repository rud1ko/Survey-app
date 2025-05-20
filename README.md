# Survey API

A FastAPI-based web service for creating and managing surveys.

## Features

- User authentication and authorization
- Create and manage surveys
- Add questions to surveys
- Categorize surveys
- Submit and view answers
- Track survey results
- RESTful API design

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a PostgreSQL database and update the `.env` file in the root directory with the following content:
```
DATABASE_URL=postgresql://user:password@localhost/survey_db
SECRET_KEY=your-secret-key-here
```

4. Run the application:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the application is running, you can access:
- Interactive API documentation (Swagger UI): `http://localhost:8000/docs`
- Alternative API documentation (ReDoc): `http://localhost:8000/redoc`

## API Endpoints

### Authentication
- `POST /token` - Get access token

### Users
- `POST /users/` - Create new user
- `GET /users/me/` - Get current user info

### Surveys
- `POST /surveys/` - Create new survey
- `GET /surveys/` - List all surveys
- `GET /surveys/{survey_id}` - Get survey details

### Categories
- `POST /categories/` - Create new category
- `GET /categories/` - List all categories

### Answers
- `POST /answers/` - Submit answer
- `GET /answers/` - List user's answers

### Results
- `POST /results/` - Submit survey results
- `GET /results/` - List user's results
- `GET /results/{result_id}` - Get specific result details

## Database Schema

The application uses PostgreSQL with the following main tables:
- users: User information and authentication
- surveys: Survey details and metadata
- questions: Survey questions with order and type
- answers: User responses to questions
- categories: Survey categories
- results: Survey completion records
- result_answers: Detailed answer records for each result

## Security

- All endpoints except user creation and token generation require authentication
- Passwords are hashed using bcrypt
- JWT tokens are used for authentication
- SQL injection protection through SQLAlchemy
- Input validation through Pydantic models 