from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
import requests
from typing import Dict, List, Optional
import traceback
from dotenv import load_dotenv
from pathlib import Path
import re

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
class Config:
    # API Keys
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    
    # CV File
    CV_FILE_PATH = os.getenv("CV_FILE_PATH", "LaIba_CV.txt")
    
    # Server
    PORT = int(os.getenv("PORT", "5001"))
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    MAX_MESSAGE_LENGTH = 2000
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set in .env file")
        
        # CV file is optional - chatbot works without it too
        if not Path(cls.CV_FILE_PATH).exists():
            logger.warning(f"⚠️  CV file not found: {cls.CV_FILE_PATH}")
            logger.warning("    Chatbot will only answer technical questions")
        else:
            logger.info(f"✅ CV file loaded: {cls.CV_FILE_PATH}")

# Global variables
conversation_history: Dict[str, List[Dict]] = {}
cv_content: str = ""

def load_cv_content():
    """Load CV content from file"""
    global cv_content
    
    try:
        cv_path = Path(Config.CV_FILE_PATH)
        if cv_path.exists():
            with open(cv_path, 'r', encoding='utf-8') as f:
                cv_content = f.read()
            logger.info(f"✅ Loaded CV ({len(cv_content)} characters)")
            return True
        else:
            logger.warning("⚠️  CV file not found - will only answer technical questions")
            return False
    except Exception as e:
        logger.error(f"Error loading CV: {str(e)}")
        return False

def is_cv_question(message: str) -> bool:
    """Detect if question is about Laiba/CV or technical CS"""
    message_lower = message.lower()
    
    # CV-related keywords
    cv_keywords = [
        # Personal
        'laiba', 'you', 'your', 'yourself',
        # Experience
        'experience', 'worked', 'job', 'intern', 'company', 'binate', 'stackware',
        # Skills
        'skills', 'know', 'proficient', 'expert',
        # Education
        'study', 'studied', 'education', 'degree', 'university', 'college', 'cgpa', 'gpa',
        # Projects
        'projects', 'built', 'created', 'developed', 'portfolio',
        # Contact
        'contact', 'email', 'github', 'portfolio', 'reach',
        # About
        'about', 'who are', 'tell me about', 'background'
    ]
    
    # Check if message contains CV keywords
    has_cv_keyword = any(keyword in message_lower for keyword in cv_keywords)
    
    # Check if it's a general tech question
    tech_keywords = [
        'what is', 'how does', 'explain', 'difference between',
        'algorithm', 'data structure', 'code', 'program',
        'example', 'tutorial', 'learn'
    ]
    
    is_general_tech = any(keyword in message_lower for keyword in tech_keywords) and not has_cv_keyword
    
    return has_cv_keyword and not is_general_tech

def create_system_prompt(is_cv_query: bool) -> str:
    """Create appropriate system prompt based on query type"""
    
    if is_cv_query and cv_content:
        return f"""You are Laiba Qayoom's AI assistant. Answer questions about Laiba using ONLY the CV information provided below. Be professional, concise, and accurate.

CV INFORMATION:
{cv_content}

RULES:
- Answer questions about Laiba's experience, skills, education, and projects
- Use information ONLY from the CV above
- Be conversational but professional
- If asked about something not in the CV, say you don't have that information
- Keep responses focused and concise
- Include specific details like percentages, technologies, and achievements when relevant"""
    
    else:
        return """You are a helpful technical assistant specializing in Computer Science, programming, and software development.

Your expertise includes:
- Programming languages (Python, JavaScript, Java, C++, etc.)
- Data structures and algorithms
- Web development (Frontend & Backend)
- Databases (SQL, NoSQL)
- Machine Learning and AI
- Software engineering principles
- System design and architecture

Provide clear, accurate, and practical answers. Include code examples when relevant. Be concise but thorough."""

def chat_with_groq(message: str, session_id: str = "default") -> str:
    """Send message to Groq API with appropriate context"""
    try:
        # Get conversation history
        if session_id not in conversation_history:
            conversation_history[session_id] = []
        
        # Detect question type
        is_cv_query = is_cv_question(message)
        
        # Create system prompt
        system_prompt = create_system_prompt(is_cv_query)
        
        # Build messages array
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation history (last 5 messages)
        for msg in conversation_history[session_id][-5:]:
            messages.append(msg)
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Call Groq API
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {Config.GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1024,
                "top_p": 1,
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            assistant_message = data['choices'][0]['message']['content']
            
            # Store in history
            conversation_history[session_id].append({"role": "user", "content": message})
            conversation_history[session_id].append({"role": "assistant", "content": assistant_message})
            
            # Keep only last 10 messages
            if len(conversation_history[session_id]) > 10:
                conversation_history[session_id] = conversation_history[session_id][-10:]
            
            return assistant_message, is_cv_query
        else:
            logger.error(f"Groq API error: {response.status_code} - {response.text}")
            raise Exception(f"API error: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Error calling Groq API: {str(e)}")
        raise

@app.before_request
def before_first_request():
    """Initialize before first request"""
    global cv_content
    if not cv_content:
        load_cv_content()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'api_key_set': bool(Config.GROQ_API_KEY),
        'cv_loaded': bool(cv_content),
        'cv_size': len(cv_content)
    }), 200

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat requests"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        data = request.json
        message = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')
        
        if not message:
            return jsonify({'error': 'No message provided'}), 400
        
        if len(message) > Config.MAX_MESSAGE_LENGTH:
            return jsonify({'error': f'Message too long (max {Config.MAX_MESSAGE_LENGTH} characters)'}), 400
        
        logger.info(f"Processing message: {message[:100]}...")
        
        # Get response from AI
        response_text, is_cv_query = chat_with_groq(message, session_id)
        
        return jsonify({
            'response': response_text,
            'status': 'success',
            'session_id': session_id,
            'query_type': 'cv' if is_cv_query else 'technical'
        }), 200
    
    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        return jsonify({
            'error': str(e),
            'details': 'Please check your API key configuration'
        }), 500
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'error': 'An error occurred processing your request',
            'details': str(e) if Config.DEBUG else None
        }), 500

@app.route('/api/chat/reset', methods=['POST'])
def reset_chat():
    """Reset conversation history"""
    try:
        data = request.json if request.is_json else {}
        session_id = data.get('session_id', 'default')
        
        if session_id in conversation_history:
            del conversation_history[session_id]
        
        return jsonify({
            'status': 'Conversation history reset',
            'session_id': session_id
        }), 200
    
    except Exception as e:
        logger.error(f"Error resetting chat: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cv/info', methods=['GET'])
def get_cv_info():
    """Get CV metadata"""
    try:
        return jsonify({
            'cv_loaded': bool(cv_content),
            'cv_size': len(cv_content),
            'cv_file': Config.CV_FILE_PATH
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    try:
        # Validate configuration
        Config.validate()
        
        # Load CV
        load_cv_content()
        
        logger.info("=" * 60)
        logger.info("🚀 Starting Hybrid AI Chatbot")
        logger.info("=" * 60)
        logger.info(f"✅ Groq API configured")
        logger.info(f"{'✅' if cv_content else '⚠️ '} CV {'loaded' if cv_content else 'not loaded'}")
        logger.info(f"📡 Port: {Config.PORT}")
        logger.info("=" * 60)
        logger.info("Chatbot can answer:")
        logger.info("  • Technical CS questions (algorithms, coding, etc.)")
        if cv_content:
            logger.info("  • Questions about Laiba (experience, skills, projects)")
        logger.info("=" * 60)
        
        app.run(
            host='0.0.0.0',
            port=Config.PORT,
            debug=Config.DEBUG
        )
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise