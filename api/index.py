#!/usr/bin/env python3
"""
Vercel Serverless API for Interactive Perk Quizzes
Simplified structure to avoid crashes
"""

from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import requests
import hashlib
import time
from datetime import datetime
import os

# Configuration
PERK_API_KEY = os.getenv("PERK_API_KEY", "bdaps0_BtUknvFg5uAlEnQj1LkXBA")
PERK_BASE_URL = "https://perk.studio/api/v2"

# In-memory storage (replace with database in production)
completed_quizzes = {}

# Quiz configurations
QUIZ_CONFIG = {
    "grooming_mastery": {
        "name": "Grooming Mastery Quiz",
        "total_questions": 5,
        "passing_score": 3,
        "points": 50,
        "action_title": "Completed Grooming Mastery Quiz",
        "completion_limit": 1
    }
}

def get_user_email_from_session(session_id):
    """Extract email from session ID"""
    try:
        parts = session_id.split('_')
        if len(parts) >= 2:
            return parts[0]
    except:
        pass
    return None

def has_completed_quiz(email, quiz_id):
    """Check if user has already completed this quiz"""
    key = f"{email}_{quiz_id}"
    return key in completed_quizzes

def award_points(email, points, action_title, completion_limit=1):
    """Award points to a user via Perk API"""
    
    headers = {
        "X-API-Key": PERK_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    data = {
        "email": email,
        "points": points,
        "action_title": action_title,
        "action_source": "Interactive Quiz",
        "action_completion_limit": completion_limit
    }
    
    try:
        response = requests.put(
            f"{PERK_BASE_URL}/participants/points",
            headers=headers,
            json=data
        )
        
        if response.status_code in [200, 201]:
            return True, "Points awarded successfully"
        else:
            return False, f"Failed to award points: {response.status_code}"
            
    except Exception as e:
        return False, f"Error awarding points: {str(e)}"

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests"""
        path = self.path
        
        if path.startswith('/quiz'):
            # Serve the quiz HTML page with Perk ID handling
            self.serve_quiz_page(path)
            return
            
        # Set CORS headers for API endpoints
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        if path == '/':
            response = {
                "message": "Game Face Quiz Backend API",
                "version": "1.0.0",
                "platform": "Vercel Serverless",
                "endpoints": {
                    "health": "/health",
                    "quiz": "/quiz (HTML page)",
                    "start_quiz": "/api/quiz/start",
                    "submit_quiz": "/api/quiz/submit",
                    "quiz_status": "/api/quiz/status"
                }
            }
        elif path == '/health':
            response = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "quizzes_available": list(QUIZ_CONFIG.keys()),
                "platform": "Vercel Serverless"
            }
        elif path.startswith('/api/quiz/status'):
            # Parse query parameters
            parsed = urllib.parse.urlparse(path)
            params = urllib.parse.parse_qs(parsed.query)
            
            email = params.get('email', [None])[0]
            quiz_id = params.get('quiz_id', [None])[0]
            
            if not email:
                response = {"error": "Email required"}
            elif quiz_id:
                completed = has_completed_quiz(email, quiz_id)
                response = {
                    "quiz_id": quiz_id,
                    "completed": completed
                }
            else:
                status = {}
                for qid in QUIZ_CONFIG:
                    status[qid] = has_completed_quiz(email, qid)
                response = status
        else:
            response = {"error": "Not found"}
        
        self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        """Handle POST requests"""
        path = self.path
        
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode())
            except:
                self.send_error_response(400, "Invalid JSON")
                return
            
            if path == '/api/quiz/start':
                response = self.handle_quiz_start(data)
            elif path == '/api/quiz/submit':
                response = self.handle_quiz_submit(data)
            else:
                self.send_error_response(404, "Not found")
                return
            
            # Send response
            status_code = response.get('_status', 200)
            if '_status' in response:
                del response['_status']
                
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_error_response(500, f"Server error: {str(e)}")
    
    def handle_quiz_start(self, data):
        """Handle quiz start request"""
        quiz_id = data.get('quiz_id')
        email = data.get('email')
        
        if not quiz_id or quiz_id not in QUIZ_CONFIG:
            return {"error": "Invalid quiz ID", "_status": 400}
        
        if not email:
            return {"error": "Email required", "_status": 400}
        
        # Create session ID
        timestamp = int(time.time())
        session_data = f"{email}_{timestamp}_{quiz_id}"
        session_id = hashlib.sha256(session_data.encode()).hexdigest()[:16]
        
        # Check if already completed
        if has_completed_quiz(email, quiz_id):
            return {
                "error": "Quiz already completed",
                "message": "You have already completed this quiz and received your points.",
                "_status": 400
            }
        
        return {
            "session_id": f"{email}_{timestamp}_{session_id}",
            "quiz_config": QUIZ_CONFIG[quiz_id],
            "message": "Quiz started successfully"
        }
    
    def handle_quiz_submit(self, data):
        """Handle quiz submission"""
        session_id = data.get('session_id')
        quiz_id = data.get('quiz_id')
        score = data.get('score')
        answers = data.get('answers', {})
        
        if not all([session_id, quiz_id, score is not None]):
            return {"error": "Missing required fields", "_status": 400}
        
        # Validate quiz exists
        if quiz_id not in QUIZ_CONFIG:
            return {"error": "Invalid quiz ID", "_status": 400}
        
        # Get user email from session
        email = get_user_email_from_session(session_id)
        if not email:
            return {"error": "Invalid session", "_status": 401}
        
        # Check if already completed
        if has_completed_quiz(email, quiz_id):
            return {
                "error": "Quiz already completed",
                "message": "You have already completed this quiz.",
                "_status": 400
            }
        
        quiz_config = QUIZ_CONFIG[quiz_id]
        passing_score = quiz_config['passing_score']
        
        # Validate score
        if score > quiz_config['total_questions']:
            return {"error": "Invalid score", "_status": 400}
        
        # Check if passed
        if score >= passing_score:
            # Award points
            success, message = award_points(
                email,
                quiz_config['points'],
                quiz_config['action_title'],
                quiz_config['completion_limit']
            )
            
            if success:
                # Mark as completed
                completed_quizzes[f"{email}_{quiz_id}"] = {
                    "timestamp": datetime.now().isoformat(),
                    "score": score,
                    "answers": answers
                }
                
                return {
                    "success": True,
                    "passed": True,
                    "message": f"Congratulations! You earned {quiz_config['points']} points!",
                    "score": score,
                    "passing_score": passing_score,
                    "points_awarded": quiz_config['points']
                }
            else:
                return {
                    "success": False,
                    "error": message,
                    "_status": 500
                }
        else:
            return {
                "success": True,
                "passed": False,
                "message": f"You scored {score}/{quiz_config['total_questions']}. You need {passing_score} to pass. Try again!",
                "score": score,
                "passing_score": passing_score
            }
    
    def send_error_response(self, code, message):
        """Send error response"""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        response = {"error": message}
        self.wfile.write(json.dumps(response).encode())
    
    def serve_quiz_page(self, path):
        """Serve the quiz HTML page with Perk ID handling"""
        # Parse query parameters to get Perk ID
        parsed = urllib.parse.urlparse(path)
        params = urllib.parse.parse_qs(parsed.query)
        perk_id = params.get('pid', [None])[0]
        
        # Quiz HTML page
        quiz_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Game Face Grooming Quiz</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .quiz-container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .quiz-header {{
            background: linear-gradient(135deg, #1a1a1a 0%, #333 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .quiz-header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .quiz-header p {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        
        .quiz-content {{
            padding: 40px;
        }}
        
        .progress-bar {{
            background: #f0f0f0;
            border-radius: 10px;
            height: 12px;
            margin-bottom: 30px;
            overflow: hidden;
        }}
        
        .progress-fill {{
            background: linear-gradient(90deg, #4CAF50 0%, #45a049 100%);
            height: 100%;
            width: 0%;
            transition: width 0.5s ease;
        }}
        
        .question-container {{
            background: #f8f9fa;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            border-left: 5px solid #4CAF50;
        }}
        
        .question {{
            font-size: 1.4em;
            color: #1a1a1a;
            margin-bottom: 25px;
            font-weight: 600;
            line-height: 1.4;
        }}
        
        .options {{
            display: grid;
            gap: 15px;
        }}
        
        .option {{
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            padding: 20px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 1.1em;
            position: relative;
        }}
        
        .option:hover {{
            border-color: #4CAF50;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(76, 175, 80, 0.2);
        }}
        
        .option.selected {{
            background: #e8f5e8;
            border-color: #4CAF50;
            color: #2e7d32;
            font-weight: 600;
        }}
        
        .controls {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 30px;
        }}
        
        .btn {{
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            font-size: 1.1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        
        .btn-primary {{
            background: #1a1a1a;
            color: white;
        }}
        
        .btn-primary:hover {{
            background: #333;
            transform: translateY(-2px);
        }}
        
        .btn-secondary {{
            background: #e0e0e0;
            color: #666;
        }}
        
        .btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }}
        
        .start-screen, .result-screen {{
            text-align: center;
            padding: 40px 20px;
        }}
        
        .email-input {{
            width: 100%;
            max-width: 350px;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 1.1em;
            margin: 20px 0;
        }}
        
        .score-display {{
            font-size: 4em;
            font-weight: 700;
            color: #4CAF50;
            margin: 20px 0;
        }}
        
        .loading {{
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #1a1a1a;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-left: 10px;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        .error-message {{
            color: #f44336;
            margin: 15px 0;
            padding: 10px;
            background: #ffebee;
            border-radius: 8px;
            border: 1px solid #ffcdd2;
        }}
        
        .success-message {{
            color: #4CAF50;
            font-size: 1.3em;
            font-weight: 600;
            margin: 20px 0;
        }}
        
        .perk-info {{
            background: #e3f2fd;
            border: 1px solid #90caf9;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
        }}
        
        .back-to-perk {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            font-size: 1.1em;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            margin-top: 20px;
            transition: transform 0.3s ease;
        }}
        
        .back-to-perk:hover {{
            transform: translateY(-2px);
            text-decoration: none;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="quiz-container">
        <div class="quiz-header">
            <h1>🎯 Grooming Mastery Quiz</h1>
            <p>Test your knowledge and earn 50 points!</p>
            {"<p style='font-size: 0.9em; margin-top: 10px;'>Perk ID: " + str(perk_id) + "</p>" if perk_id else ""}
        </div>
        
        <div class="quiz-content">
            <div id="quizContent">
                <!-- Quiz content will be dynamically inserted here -->
            </div>
        </div>
    </div>

    <script>
        // Configuration
        const QUIZ_API_URL = '/api';
        const QUIZ_ID = 'grooming_mastery';
        const PERK_ID = '{perk_id}';
        const PERK_RETURN_URL = 'https://championsclub.perk.studio/';
        
        console.log('Quiz loaded with Perk ID:', PERK_ID);
        
        // Quiz questions
        const questions = [
            {{
                question: "How often should you replace your razor blade for optimal performance?",
                options: [
                    "After every shave",
                    "Once a month", 
                    "Every 5-7 shaves",
                    "When it starts to rust"
                ],
                correct: 2
            }},
            {{
                question: "What's the best time to apply moisturizer for maximum effectiveness?",
                options: [
                    "Before bed",
                    "Right after showering while skin is damp",
                    "First thing in the morning",
                    "Whenever skin feels dry"
                ],
                correct: 1
            }},
            {{
                question: "Which Game Face product is best for on-the-go freshness?",
                options: [
                    "The Lotion",
                    "Shower Mist",
                    "All The Wipes", 
                    "Foot Spray Serum"
                ],
                correct: 2
            }},
            {{
                question: "What's the ideal water temperature for washing your face?",
                options: [
                    "As hot as you can stand",
                    "Ice cold",
                    "Lukewarm",
                    "Room temperature"
                ],
                correct: 2
            }},
            {{
                question: "How long should you wait after shaving before applying aftershave?",
                options: [
                    "Apply immediately",
                    "Wait 5-10 minutes", 
                    "Wait 30 minutes",
                    "Wait 2-3 minutes"
                ],
                correct: 3
            }}
        ];

        // Quiz state
        let currentQuestion = 0;
        let score = 0;
        let userAnswers = {{}};
        let sessionId = null;
        let userEmail = null;

        // Initialize quiz
        function initQuiz() {{
            showStartScreen();
        }}

        // Show start screen
        function showStartScreen() {{
            const content = `
                <div class="start-screen">
                    <h2>Ready to Test Your Grooming Knowledge?</h2>
                    <p>Answer 5 questions correctly to earn 50 points!</p>
                    <p>You need at least 3 correct answers to pass.</p>
                    
                    ${{PERK_ID ? `
                        <div class="perk-info">
                            <p><strong>Connected to your Perk account!</strong></p>
                            <p>Points will be automatically added after completion.</p>
                        </div>
                    ` : ''}}
                    
                    <input type="email" 
                           id="emailInput" 
                           class="email-input" 
                           placeholder="Enter your email to start"
                           required>
                    
                    <div id="errorMessage" class="error-message" style="display: none;"></div>
                    
                    <br>
                    <button class="btn btn-primary" onclick="startQuiz()">
                        Start Quiz
                    </button>
                </div>
            `;
            document.getElementById('quizContent').innerHTML = content;
        }}

        // Start quiz
        async function startQuiz() {{
            const emailInput = document.getElementById('emailInput');
            const email = emailInput.value.trim();
            
            if (!email || !email.includes('@')) {{
                showError('Please enter a valid email address');
                return;
            }}
            
            userEmail = email;
            
            // Show loading
            const startBtn = document.querySelector('.btn-primary');
            const originalText = startBtn.innerHTML;
            startBtn.innerHTML = 'Starting Quiz... <span class="loading"></span>';
            startBtn.disabled = true;
            
            try {{
                const response = await fetch(`${{QUIZ_API_URL}}/quiz/start`, {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{
                        quiz_id: QUIZ_ID,
                        email: userEmail,
                        perk_id: PERK_ID
                    }})
                }});
                
                const data = await response.json();
                
                if (!response.ok) {{
                    showError(data.message || 'Failed to start quiz');
                    startBtn.innerHTML = originalText;
                    startBtn.disabled = false;
                    return;
                }}
                
                sessionId = data.session_id;
                showQuestion();
                
            }} catch (error) {{
                console.error('Quiz start error:', error);
                showError('Failed to connect to quiz server. Please try again.');
                startBtn.innerHTML = originalText;
                startBtn.disabled = false;
            }}
        }}

        // Show current question
        function showQuestion() {{
            const question = questions[currentQuestion];
            const progress = ((currentQuestion + 1) / questions.length) * 100;
            
            const content = `
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${{progress}}%"></div>
                </div>
                
                <div class="question-container">
                    <div class="question">
                        Question ${{currentQuestion + 1}} of ${{questions.length}}: ${{question.question}}
                    </div>
                    
                    <div class="options">
                        ${{question.options.map((option, index) => `
                            <div class="option" onclick="selectOption(${{index}})" data-index="${{index}}">
                                ${{option}}
                            </div>
                        `).join('')}}
                    </div>
                </div>
                
                <div class="controls">
                    <button class="btn btn-secondary" 
                            onclick="previousQuestion()" 
                            ${{currentQuestion === 0 ? 'disabled' : ''}}>
                        Previous
                    </button>
                    
                    <button class="btn btn-primary" 
                            onclick="nextQuestion()"
                            id="nextBtn"
                            disabled>
                        ${{currentQuestion === questions.length - 1 ? 'Submit Quiz' : 'Next'}}
                    </button>
                </div>
            `;
            
            document.getElementById('quizContent').innerHTML = content;
            
            // Restore previous answer if any
            if (userAnswers[currentQuestion] !== undefined) {{
                const options = document.querySelectorAll('.option');
                options[userAnswers[currentQuestion]].classList.add('selected');
                document.getElementById('nextBtn').disabled = false;
            }}
        }}

        // Select an option
        function selectOption(index) {{
            document.querySelectorAll('.option').forEach(opt => {{
                opt.classList.remove('selected');
            }});
            
            document.querySelector(`[data-index="${{index}}"]`).classList.add('selected');
            userAnswers[currentQuestion] = index;
            document.getElementById('nextBtn').disabled = false;
        }}

        // Previous question
        function previousQuestion() {{
            if (currentQuestion > 0) {{
                currentQuestion--;
                showQuestion();
            }}
        }}

        // Next question or submit
        async function nextQuestion() {{
            if (currentQuestion < questions.length - 1) {{
                currentQuestion++;
                showQuestion();
            }} else {{
                await submitQuiz();
            }}
        }}

        // Calculate score
        function calculateScore() {{
            score = 0;
            questions.forEach((question, index) => {{
                if (userAnswers[index] === question.correct) {{
                    score++;
                }}
            }});
            return score;
        }}

        // Submit quiz
        async function submitQuiz() {{
            const finalScore = calculateScore();
            
            // Show loading
            const submitBtn = document.getElementById('nextBtn');
            submitBtn.innerHTML = 'Submitting... <span class="loading"></span>';
            submitBtn.disabled = true;
            
            try {{
                const response = await fetch(`${{QUIZ_API_URL}}/quiz/submit`, {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{
                        session_id: sessionId,
                        quiz_id: QUIZ_ID,
                        score: finalScore,
                        answers: userAnswers,
                        perk_id: PERK_ID
                    }})
                }});
                
                const data = await response.json();
                
                if (response.ok) {{
                    showResult(data);
                }} else {{
                    showError(data.message || 'Failed to submit quiz');
                    submitBtn.innerHTML = 'Submit Quiz';
                    submitBtn.disabled = false;
                }}
                
            }} catch (error) {{
                console.error('Quiz submit error:', error);
                showError('Failed to submit quiz. Please try again.');
                submitBtn.innerHTML = 'Submit Quiz';
                submitBtn.disabled = false;
            }}
        }}

        // Show result
        function showResult(data) {{
            const isPassed = data.passed;
            const content = `
                <div class="result-screen">
                    <h2>${{isPassed ? '🎉 Congratulations!' : '😔 Not Quite!'}}</h2>
                    
                    <div class="score-display">
                        ${{data.score}} / ${{questions.length}}
                    </div>
                    
                    ${{isPassed ? 
                        `<div class="success-message">${{data.message}}</div>` :
                        `<p style="font-size: 1.1em;">${{data.message}}</p>`
                    }}
                    
                    ${{PERK_ID && isPassed ? `
                        <div class="perk-info">
                            <p><strong>✅ Points Added to Your Perk Account!</strong></p>
                            <p>Your 50 points have been automatically credited.</p>
                        </div>
                    ` : ''}}
                    
                    <div style="margin-top: 30px;">
                        ${{!isPassed ? 
                            `<button class="btn btn-primary" onclick="retryQuiz()">
                                Try Again
                            </button>` :
                            PERK_ID ? 
                                `<a href="${{PERK_RETURN_URL}}" class="back-to-perk">
                                    🎯 Return to Perk
                                </a>` :
                                `<button class="btn btn-secondary" onclick="initQuiz()">
                                    Back to Start
                                </button>`
                        }}
                    </div>
                </div>
            `;
            
            document.getElementById('quizContent').innerHTML = content;
        }}

        // Retry quiz
        function retryQuiz() {{
            currentQuestion = 0;
            score = 0;
            userAnswers = {{}};
            sessionId = null;
            initQuiz();
        }}

        // Show error message
        function showError(message) {{
            const errorEl = document.getElementById('errorMessage');
            if (errorEl) {{
                errorEl.textContent = message;
                errorEl.style.display = 'block';
                setTimeout(() => {{
                    errorEl.style.display = 'none';
                }}, 5000);
            }} else {{
                alert(message);
            }}
        }}

        // Initialize on load
        initQuiz();
    </script>
</body>
</html>"""
        
        # Send HTML response
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(quiz_html.encode())