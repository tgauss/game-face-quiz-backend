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
        
        # Set CORS headers
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