# Interactive Quiz Backend for Perk

This backend server handles interactive quizzes embedded in Perk challenges and awards points via the Perk API.

## Features

- Multi-step quiz validation
- Automatic point awards via Perk API
- CORS support for cross-origin requests
- Quiz completion tracking
- Session management
- Multiple quiz configurations

## Quick Deployment

### Deploy to Heroku:

1. Install Heroku CLI
2. Create new Heroku app:
   ```bash
   heroku create your-quiz-backend
   ```

3. Set environment variables:
   ```bash
   heroku config:set PERK_API_KEY=bdaps0_BtUknvFg5uAlEnQj1LkXBA
   ```

4. Deploy:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   heroku git:remote -a your-quiz-backend
   git push heroku main
   ```

### Deploy to Railway:

1. Connect your GitHub repo to Railway
2. Set environment variable: `PERK_API_KEY=bdaps0_BtUknvFg5uAlEnQj1LkXBA`
3. Deploy automatically

## API Endpoints

### POST /api/quiz/start
Start a new quiz session
```json
{
  "quiz_id": "grooming_mastery",
  "email": "user@example.com"
}
```

### POST /api/quiz/submit
Submit quiz answers
```json
{
  "session_id": "session123",
  "quiz_id": "grooming_mastery", 
  "score": 4,
  "answers": {"0": 2, "1": 1, "2": 2}
}
```

### GET /api/quiz/status
Check completion status
```
GET /api/quiz/status?email=user@example.com&quiz_id=grooming_mastery
```

## Quiz Configurations

- **grooming_mastery**: 5 questions, 50 points, need 3 correct
- **product_knowledge**: 4 questions, 40 points, need 3 correct  
- **skin_type**: 6 questions, 30 points, need all correct

## Integration with Perk

The backend automatically awards points to users via the Perk API:
- Uses `PUT /api/v2/participants/points`
- Custom action titles for tracking
- Completion limits to prevent abuse
- Email-based user identification

## Security

- Session validation
- Completion tracking
- Score validation
- CORS configured for your domain
- Environment-based API keys