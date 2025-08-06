# 🚀 Deploy Quiz Backend to Vercel + GitHub

This guide shows you how to deploy your interactive quiz backend using GitHub and Vercel.

## Step 1: Push to GitHub

1. **Create a new GitHub repository**:
   - Go to GitHub.com → New Repository
   - Name: `game-face-quiz-backend` (or any name you prefer)
   - Make it Public or Private
   - Don't initialize with README (we have files already)

2. **Push your code**:
   ```bash
   cd quiz_backend
   git init
   git add .
   git commit -m "Initial commit - Game Face interactive quiz backend"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/game-face-quiz-backend.git
   git push -u origin main
   ```

## Step 2: Deploy to Vercel

1. **Connect GitHub to Vercel**:
   - Go to [vercel.com](https://vercel.com)
   - Sign in with GitHub
   - Click "New Project"
   - Import your `game-face-quiz-backend` repository

2. **Configure the deployment**:
   - **Framework Preset**: Other
   - **Root Directory**: `./` (leave as default)
   - **Build Command**: Leave empty
   - **Output Directory**: Leave empty
   - **Install Command**: `pip install -r requirements.txt`

3. **Set Environment Variables**:
   - Click "Environment Variables"
   - Add: `PERK_API_KEY` = `bdaps0_BtUknvFg5uAlEnQj1LkXBA`
   - Click "Add"

4. **Deploy**:
   - Click "Deploy"
   - Wait 1-2 minutes for deployment
   - You'll get a URL like: `https://game-face-quiz-backend.vercel.app`

## Step 3: Test Your Backend

Test your deployed backend:

```bash
# Health check
curl https://your-app.vercel.app/health

# Start quiz test
curl -X POST https://your-app.vercel.app/api/quiz/start \
  -H "Content-Type: application/json" \
  -d '{"quiz_id":"grooming_mastery","email":"test@example.com"}'
```

## Step 4: Update Quiz Challenge

1. **Update the quiz HTML** in `create_custom_quiz_challenge.py`:
   ```javascript
   const QUIZ_API_URL = 'https://your-app.vercel.app/api';
   ```

2. **Uncomment the API calls** in the JavaScript:
   - Remove the `/*` and `*/` around the fetch calls
   - Comment out the "Demo mode" sections

3. **Recreate the Perk challenge**:
   ```bash
   python3 create_custom_quiz_challenge.py
   ```

## Step 5: Automatic Deployments

Every time you push to GitHub, Vercel will automatically redeploy:

```bash
# Make changes to your code
git add .
git commit -m "Updated quiz questions"
git push
# Vercel automatically deploys the changes!
```

## 🔧 Vercel-Specific Files Created:

- **`vercel.json`** - Vercel configuration
- **`.gitignore`** - Git ignore rules
- **`requirements.txt`** - Python dependencies
- **This deployment guide**

## 📋 Your Vercel URL Structure:

- **Health**: `https://your-app.vercel.app/health`
- **Start Quiz**: `https://your-app.vercel.app/api/quiz/start`
- **Submit Quiz**: `https://your-app.vercel.app/api/quiz/submit`
- **Quiz Status**: `https://your-app.vercel.app/api/quiz/status`

## 🎯 Next Steps After Deployment:

1. **Test all endpoints** work correctly
2. **Update quiz challenge** with your Vercel URL
3. **Create more quiz types** by adding to QUIZ_CONFIG
4. **Monitor usage** in Vercel dashboard
5. **Scale up** if needed (Vercel handles this automatically)

## 💡 Advanced Features You Can Add:

- **Database integration** (Vercel + PlanetScale)
- **Analytics tracking** (quiz completion rates)
- **A/B testing** (different quiz versions)
- **Admin dashboard** (manage quizzes)
- **Email notifications** (quiz completion alerts)

Your backend will be live at a URL like:
`https://game-face-quiz-backend-your-username.vercel.app`