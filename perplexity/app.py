from flask import Flask, request, jsonify, send_from_directory
import os
import json
import time
from PyPDF2 import PdfReader
import google.generativeai as genai

# Setup Flask App
app = Flask(__name__)

# Configure Google Gemini
API_KEY = "AIzaSyBx5q6-2i8U6DOZ1nzeESZAqlbfDSLf6lI"
genai.configure(api_key=API_KEY)

# Define the model with system instructions for Perplexity-style behavior
SYSTEM_PROMPT = """
You are an advanced AI search assistant similar to Perplexity AI.

Your goals:
1. Provide accurate, real-time, and well-structured answers.
2. Combine web-style retrieval thinking with deep reasoning.
3. Always explain your reasoning step-by-step in a clear, human-friendly way.
4. When relevant, cite sources or simulate credible references.
5. Break down complex questions into smaller logical parts before answering.

Core Features:
- Multi-step reasoning (chain-of-thought style, but summarized clearly)
- Context awareness across the conversation
- Ability to challenge assumptions and explore unconventional perspectives ("anti-gravity thinking")
- Compare multiple viewpoints before concluding
- Provide concise summaries + detailed explanations

Response Structure:
1. Quick Answer (short, direct response)
2. Explanation (step-by-step reasoning)
3. Alternative Perspectives (if applicable)
4. Final Insight or Recommendation

Behavior Rules:
- If the query is ambiguous, ask a clarifying question before answering.
- If unsure, state uncertainty instead of guessing.
- Avoid hallucinations; prioritize factual correctness.
- Use examples, analogies, or simple explanations when helpful.
- Keep tone professional but conversational.

Advanced Mode ("Anti-Gravity Thinking"):
- Reframe the problem from unexpected angles
- Consider edge cases and contrarian ideas
- Go beyond obvious answers to generate deeper insights
- Connect ideas across domains (science, philosophy, technology, etc.)

You are not just answering — you are helping the user think better.
"""

model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    system_instruction=SYSTEM_PROMPT
)

# Store chat history and PDF context in memory
chat_session = model.start_chat(history=[])
current_pdf_context = ""

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

HISTORY_FILE = 'history.json'

def get_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_to_history(user_msg, bot_msg):
    history = get_history()
    item = {
        'id': int(time.time() * 1000),
        'timestamp': time.time(),
        'user': user_msg,
        'bot': bot_msg
    }
    history.append(item)
    # limit generic logging to 50 for storage, but we only show 5
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history[-50:], f, indent=2)

@app.route('/api/history', methods=['GET'])
def history_endpoint():
    hist = get_history()
    return jsonify({'history': hist[-5:]})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    global current_pdf_context
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not file.filename.endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are supported'}), 400

    try:
        reader = PdfReader(file)
        text = ""
        # Simply extract all text from the PDF
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        current_pdf_context = text.strip()
        print(f"Extracted {len(current_pdf_context)} characters from {file.filename}")
        
        return jsonify({
            'message': 'File uploaded and parsed successfully!',
            'filename': file.filename,
            'charCount': len(current_pdf_context)
        })
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400
    
    user_message = data['message']
    
    # Simple RAG: Prepend context to the user's message
    full_prompt = user_message
    if current_pdf_context:
        full_prompt = f"Using the following context from an uploaded PDF, please answer the question: \n\nCONTEXT:\n{current_pdf_context}\n\nUSER QUESTION: {user_message}"
    
    try:
        # Send message to gemini using the active chat session (maintains history)
        response = chat_session.send_message(full_prompt)
        
        save_to_history(user_message, response.text)
        
        return jsonify({
            'response': response.text
        })
    except Exception as e:
        print(f"Error during API call: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Run the server
    print("Starting Flask server for Chat Bot clone...")
    app.run(host='0.0.0.0', port=5000, debug=True)
