from flask import Flask, render_template, request, jsonify
import os
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

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
        messages = data.get('messages', [])
        car_info = data.get('car_info', {})
        last_message = messages[-1]['content'].lower()
        search_terms = ['wiring diagram', 'wiring', 'diagram', 'schematic', 'manual', 'fuse']
        web_results = None
        if any(term in last_message for term in search_terms):
            search_query = f"{car_info.get('year', '')} {car_info.get('make', '')} {car_info.get('model', '')} {last_message}"
            web_results = search_web(search_query)
        system_content = "You are an automotive troubleshooting assistant."
        if web_results:
            system_content += "\n\nResources found:\n"
            for idx, r in enumerate(web_results, 1):
                system_content += f"\n{idx}. {r['title']}\n   URL: {r['url']}\n"
        gemini_contents = []
        for msg in messages:
            if msg['role'] != 'system':
                role = "user" if msg['role'] == 'user' else "model"
                gemini_contents.append({"role": role, "parts": [{"text": msg['content']}]})
        if gemini_contents and web_results:
            gemini_contents[0]['parts'][0]['text'] = system_content + "\n\nUser: " + gemini_contents[0]['parts'][0]['text']
        response = requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}', headers={'Content-Type': 'application/json'}, json={'contents': gemini_contents}, timeout=30)
        response.raise_for_status()
        ai_message = response.json()['candidates'][0]['content']['parts'][0]['text']
        return jsonify({'success': True, 'message': ai_message, 'web_results': web_results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
