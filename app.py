from flask import Flask, render_template, request, jsonify
import os
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

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
                results.append({
                    'title': title_elem.get_text(strip=True),
                    'url': title_elem.get('href', ''),
                    'snippet': snippet_elem.get_text(strip=True) if snippet_elem else ''
                })
        return results
    except Exception as e:
        print(f"Search error: {e}")
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        messages = data.get('messages', [])
        car_info = data.get('car_info', {})
        
        last_message = messages[-1]['content'].lower()
        search_terms = ['wiring diagram', 'wiring', 'diagram', 'schematic', 'manual', 'fuse', 'serpentine']
        
        web_results = None
        if any(term in last_message for term in search_terms):
            year = car_info.get('year', '')
            make = car_info.get('make', '')
            model = car_info.get('model', '')
            search_query = f"{year} {make} {model} {last_message}"
            web_results = search_web(search_query)
        
        system_content = "You are an automotive troubleshooting assistant. Help diagnose car problems."
        
        if web_results:
            system_content += "\n\nI found these resources:\n"
            for idx, result in enumerate(web_results, 1):
                system_content += f"\n{idx}. {result['title']}\n   URL: {result['url']}\n"
            system_content += "\nReference these in your response."
        
        if len(messages) == 1:
            messages.insert(0, {'role': 'system', 'content': system_content})
        else:
            messages[0] = {'role': 'system', 'content': system_content}
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {OPENAI_API_KEY}', 'Content-Type': 'application/json'},
            json={'model': 'gpt-3.5-turbo', 'messages': messages, 'max_tokens': 1500},
            timeout=30
        )
        
        response.raise_for_status()
        ai_message = response.json()['choices'][0]['message']['content']
        
        return jsonify({
            'success': True,
            'message': ai_message,
            'web_results': web_results
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
