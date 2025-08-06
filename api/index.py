#!/usr/bin/env python3
"""
Vercel Serverless API for Interactive Perk Quizzes
"""

from flask import Flask, request, jsonify
import requests
import json
import hashlib
import time
from datetime import datetime
import os

# Create Flask app
app = Flask(__name__)

# Configuration
PERK_API_KEY = os.getenv("PERK_API_KEY", "bdaps0_BtUknvFg5uAlEnQj1LkXBA")
PERK_BASE_URL = "https://perk.studio/api/v2"

# Store completed quizzes (in production, use a database)
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

# CORS headers for all responses
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

@app.after_request
def after_request(response):
    return add_cors_headers(response)

@app.route('/api/quiz/start', methods=['POST', 'OPTIONS'])
def start_quiz():
    """Initialize a quiz session"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    data = request.json
    quiz_id = data.get('quiz_id')
    email = data.get('email')
    
    if not quiz_id or quiz_id not in QUIZ_CONFIG:
        return jsonify({"error": "Invalid quiz ID"}), 400
    
    if not email:
        return jsonify({"error": "Email required"}), 400
    
    # Create session ID
    timestamp = int(time.time())
    session_data = f"{email}_{timestamp}_{quiz_id}"
    session_id = hashlib.sha256(session_data.encode()).hexdigest()[:16]
    
    # Check if already completed
    if has_completed_quiz(email, quiz_id):
        return jsonify({
            "error": "Quiz already completed",
            "message": "You have already completed this quiz and received your points."
        }), 400
    
    return jsonify({
        "session_id": f"{email}_{timestamp}_{session_id}",
        "quiz_config": QUIZ_CONFIG[quiz_id],
        "message": "Quiz started successfully"
    })

@app.route('/api/quiz/submit', methods=['POST', 'OPTIONS'])
def submit_quiz():
    """Submit quiz answers and award points if passed"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    data = request.json
    session_id = data.get('session_id')
    quiz_id = data.get('quiz_id')
    score = data.get('score')
    answers = data.get('answers', {})
    
    if not all([session_id, quiz_id, score is not None]):
        return jsonify({"error": "Missing required fields"}), 400
    
    # Validate quiz exists
    if quiz_id not in QUIZ_CONFIG:
        return jsonify({"error": "Invalid quiz ID"}), 400
    
    # Get user email from session
    email = get_user_email_from_session(session_id)
    if not email:
        return jsonify({"error": "Invalid session"}), 401
    
    # Check if already completed
    if has_completed_quiz(email, quiz_id):
        return jsonify({
            "error": "Quiz already completed",
            "message": "You have already completed this quiz."
        }), 400
    
    quiz_config = QUIZ_CONFIG[quiz_id]
    passing_score = quiz_config['passing_score']
    
    # Validate score
    if score > quiz_config['total_questions']:
        return jsonify({"error": "Invalid score"}), 400
    
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
            
            return jsonify({
                "success": True,
                "passed": True,
                "message": f"Congratulations! You earned {quiz_config['points']} points!",
                "score": score,
                "passing_score": passing_score,
                "points_awarded": quiz_config['points']
            })
        else:
            return jsonify({
                "success": False,
                "error": message
            }), 500
    else:
        return jsonify({
            "success": True,
            "passed": False,
            "message": f"You scored {score}/{quiz_config['total_questions']}. You need {passing_score} to pass. Try again!",
            "score": score,
            "passing_score": passing_score
        })

@app.route('/api/quiz/status', methods=['GET', 'OPTIONS'])
def quiz_status():
    """Check quiz completion status for a user"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    email = request.args.get('email')
    quiz_id = request.args.get('quiz_id')
    
    if not email:
        return jsonify({"error": "Email required"}), 400
    
    if quiz_id:
        # Check specific quiz
        completed = has_completed_quiz(email, quiz_id)
        return jsonify({
            "quiz_id": quiz_id,
            "completed": completed
        })
    else:
        # Check all quizzes
        status = {}
        for qid in QUIZ_CONFIG:
            status[qid] = has_completed_quiz(email, qid)
        return jsonify(status)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "quizzes_available": list(QUIZ_CONFIG.keys()),
        "platform": "Vercel Serverless"
    })

@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return jsonify({
        "message": "Game Face Quiz Backend API",
        "version": "1.0.0",
        "platform": "Vercel Serverless",
        "endpoints": {
            "health": "/health",
            "start_quiz": "/api/quiz/start",
            "submit_quiz": "/api/quiz/submit", 
            "quiz_status": "/api/quiz/status"
        }
    })

# Export the Flask app for Vercel
def handler(request):
    return app(request)

# For local development
if __name__ == '__main__':
    app.run(debug=True)