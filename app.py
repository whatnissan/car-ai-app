from flask import Flask, render_template, request, jsonify
import os
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

def search_web(query):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        response = requests.get(search_url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        for result in soup.find_all('div', class_='result__body')[:5]:
            title_elem = result.find('a', class_='result__a')
            snippet_elem = result.find('a', class_='result__snippet')
            if title_elem:
                results.append({'title': title_elem.get_text(strip=True), 'url': title_elem.get('href', ''), 'snippet': snippet_elem.get_text(strip=True) if snippet_elem else ''})
        return results
    except:
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_messages = data.get('messages', [])
        car_info = data.get('car_info', {})
        
        last_message = user_messages[-1]['content'] if user_messages else ''
        search_terms = ['wiring diagram', 'wiring', 'diagram', 'schematic', 'manual', 'fuse']
        
        web_results = None
        if any(term in last_message.lower() for term in search_terms):
            search_query = f"{car_info.get('year', '')} {car_info.get('make', '')} {car_info.get('model', '')} {last_message}"
            web_results = search_web(search_query)
        
        groq_messages = []
        
        for msg in user_messages:
            if msg.get('role') in ['user', 'assistant']:
                groq_messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
        
        if web_results and groq_messages:
            resources_text = "Resources found:\n"
            for idx, r in enumerate(web_results, 1):
                resources_text += f"{idx}. {r['title']} - {r['url']}\n"
            groq_messages[0]['content'] = resources_text + "\n" + groq_messages[0]['content']
        
        payload = {
            'messages': groq_messages,
            'model': 'llama3-8b-8192',
            'temperature': 0.7,
            'max_tokens': 1024
        }
        
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {GROQ_API_KEY}',
                'Content-Type': 'application/json'
            },
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            return jsonify({'success': False, 'error': f'API Error: {response.text}'}), 500
        
        result = response.json()
        ai_message = result['choices'][0]['message']['content']
        
        return jsonify({'success': True, 'message': ai_message, 'web_results': web_results})
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
