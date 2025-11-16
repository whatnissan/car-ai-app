from flask import Flask, render_template, request, jsonify
import os, requests
app = Flask(__name__)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
@app.route('/')
def index():
    return render_template('index.html')
@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        messages = data.get('messages', [])
        if len(messages) == 1:
            messages.insert(0, {"role": "system", "content": "You are an automotive troubleshooting assistant."})
        r = requests.post('https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {OPENAI_API_KEY}', 'Content-Type': 'application/json'},
            json={'model': 'gpt-3.5-turbo', 'messages': messages, 'max_tokens': 1000}, timeout=30)
        r.raise_for_status()
        return jsonify({'success': True, 'message': r.json()['choices'][0]['message']['content']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
