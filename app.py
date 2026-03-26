from flask import Flask, render_template, request, jsonify
import sqlite3
import os
import subprocess
import tempfile
import re
import json
from datetime import datetime

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
DATABASE = 'lean_annotator.db'

def get_llm_info():
    """Get LLM provider and model info."""
    provider = os.environ.get('LLM_PROVIDER', '').lower()
    
    # Auto-detect provider based on available API keys
    if not provider:
        if os.environ.get('XAI_API_KEY') or os.environ.get('GROK_API_KEY'):
            provider = 'grok'
        elif os.environ.get('OPENAI_API_KEY') or os.environ.get('LLM_API_KEY'):
            provider = 'openai'
        elif os.environ.get('ANTHROPIC_API_KEY'):
            provider = 'anthropic'
        else:
            provider = 'mock'
    
    # Get model
    model = os.environ.get('LLM_MODEL', '')
    if not model:
        if provider == 'grok':
            model = 'grok-3'
        elif provider == 'openai':
            model = 'gpt-4'
        elif provider == 'anthropic':
            model = 'claude-3-opus'
        else:
            model = 'template-based'
    
    return provider.upper(), model

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            natural_language TEXT,
            difficulty TEXT DEFAULT 'medium',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS formalizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            problem_id INTEGER NOT NULL,
            lean_code TEXT,
            status TEXT DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (problem_id) REFERENCES problems (id)
        )
    ''')
    
    cursor.execute('SELECT COUNT(*) FROM problems')
    if cursor.fetchone()[0] == 0:
        sample_problems = [
            ('Sum of Two Even Numbers', 'Prove that the sum of two even numbers is even.', 'Let m and n be even numbers. Show that m + n is even.', 'easy'),
            ('Irrationality of Square Root of 2', 'Prove that √2 is irrational.', 'Show that there are no integers p and q such that (p/q)² = 2.', 'medium'),
            ('Infinitude of Primes', 'Prove that there are infinitely many prime numbers.', 'Show that for any finite list of primes, there exists a prime not in the list.', 'medium'),
            ('Triangle Inequality', 'Prove that for any real numbers a and b, |a + b| ≤ |a| + |b|.', 'Establish the triangle inequality for real numbers.', 'easy'),
            ('Fermat\'s Little Theorem', 'Prove that if p is prime and a is not divisible by p, then a^(p-1) ≡ 1 (mod p).', 'For a prime p and integer a not divisible by p, show that a^(p-1) is congruent to 1 modulo p.', 'hard'),
            ('Division Algorithm', 'For integers a and b with b > 0, there exist unique integers q and r such that a = bq + r and 0 ≤ r < b.', 'Prove the existence and uniqueness of quotient and remainder.', 'easy'),
            ('Fundamental Theorem of Arithmetic', 'Every integer greater than 1 can be uniquely expressed as a product of prime powers.', 'Prove existence and uniqueness of prime factorization.', 'medium'),
            ('Bézout\'s Identity', 'For integers a and b, there exist integers x and y such that ax + by = gcd(a,b).', 'Prove that the gcd can be expressed as a linear combination.', 'medium'),
            ('Euclidean Algorithm Correctness', 'Prove that the Euclidean algorithm correctly computes gcd(a, b).', 'Show that gcd(a, b) = gcd(b, a mod b) and the algorithm terminates.', 'medium'),
            ('Wilson\'s Theorem', 'A positive integer n > 1 is prime if and only if (n-1)! ≡ -1 (mod n).', 'Prove both directions of this characterization of primes.', 'hard'),
            ('Chinese Remainder Theorem', 'If m and n are coprime, then for any a, b, there exists x such that x ≡ a (mod m) and x ≡ b (mod n).', 'Prove existence and uniqueness modulo mn.', 'medium'),
            ('Binomial Theorem', '(x + y)^n = Σ_{k=0}^{n} C(n,k) x^k y^{n-k}', 'Prove the binomial expansion formula.', 'easy'),
            ('Cauchy-Schwarz Inequality', 'For real sequences a_i and b_i: (Σa_i b_i)² ≤ (Σa_i²)(Σb_i²)', 'Prove this fundamental inequality.', 'medium'),
            ('AM-GM Inequality', 'For non-negative real numbers, the arithmetic mean is at least the geometric mean.', 'Prove that (x₁ + ... + xₙ)/n ≥ (x₁...xₙ)^(1/n).', 'medium'),
            ('Bernoulli\'s Inequality', 'For real x ≥ -1 and integer n ≥ 0: (1 + x)^n ≥ 1 + nx.', 'Prove by induction.', 'easy'),
            ('Sum of First n Natural Numbers', 'Prove that 1 + 2 + ... + n = n(n+1)/2.', 'Establish the formula for the sum of arithmetic sequence.', 'easy'),
            ('Sum of Squares', 'Prove that 1² + 2² + ... + n² = n(n+1)(2n+1)/6.', 'Find and prove the closed form.', 'easy'),
            ('Sum of Cubes', 'Prove that 1³ + 2³ + ... + n³ = (n(n+1)/2)².', 'Establish the relationship with sum of first n numbers.', 'easy'),
            ('Geometric Series', 'Prove that Σ_{k=0}^{n-1} r^k = (r^n - 1)/(r - 1) for r ≠ 1.', 'Derive the formula for finite geometric series.', 'easy'),
            ('Infinite Geometric Series', 'Prove that Σ_{k=0}^{∞} r^k = 1/(1-r) for |r| < 1.', 'Establish convergence and sum of infinite geometric series.', 'medium'),
        ]
        cursor.executemany('INSERT INTO problems (title, description, natural_language, difficulty) VALUES (?, ?, ?, ?)', sample_problems)
    
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    conn = get_db()
    problems = conn.execute('SELECT * FROM problems ORDER BY created_at DESC').fetchall()
    conn.close()
    
    llm_provider, llm_model = get_llm_info()
    
    return render_template('index.html', 
                          problems=[dict(p) for p in problems],
                          llm_provider=llm_provider,
                          llm_model=llm_model)

@app.route('/problem/<int:problem_id>')
def problem_page(problem_id):
    conn = get_db()
    problem = conn.execute('SELECT * FROM problems WHERE id = ?', (problem_id,)).fetchone()
    if not problem:
        conn.close()
        return "Problem not found", 404
    formalizations = conn.execute('SELECT * FROM formalizations WHERE problem_id = ? ORDER BY updated_at DESC', (problem_id,)).fetchall()
    conn.close()
    
    llm_provider, llm_model = get_llm_info()
    
    return render_template('problem.html', 
                          problem=dict(problem), 
                          formalizations=[dict(f) for f in formalizations],
                          llm_provider=llm_provider,
                          llm_model=llm_model)

@app.route('/api/problems', methods=['GET'])
def get_problems():
    conn = get_db()
    problems = conn.execute('SELECT * FROM problems ORDER BY created_at DESC').fetchall()
    conn.close()
    return jsonify([dict(p) for p in problems])

@app.route('/api/problems', methods=['POST'])
def add_problem():
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    natural_language = data.get('natural_language', '').strip()
    difficulty = data.get('difficulty', 'medium')
    
    if not title or not description:
        return jsonify({'error': 'Title and description are required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO problems (title, description, natural_language, difficulty) VALUES (?, ?, ?, ?)',
                   (title, description, natural_language, difficulty))
    problem_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'id': problem_id, 'title': title, 'description': description, 'natural_language': natural_language, 'difficulty': difficulty})

@app.route('/api/problem/<int:problem_id>', methods=['GET'])
def get_problem(problem_id):
    conn = get_db()
    problem = conn.execute('SELECT * FROM problems WHERE id = ?', (problem_id,)).fetchone()
    if not problem:
        conn.close()
        return jsonify({'error': 'Problem not found'}), 404
    formalizations = conn.execute('SELECT * FROM formalizations WHERE problem_id = ? ORDER BY updated_at DESC', (problem_id,)).fetchall()
    conn.close()
    result = dict(problem)
    result['formalizations'] = [dict(f) for f in formalizations]
    return jsonify(result)

@app.route('/api/problem/<int:problem_id>', methods=['PUT'])
def update_problem(problem_id):
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    natural_language = data.get('natural_language', '').strip()
    difficulty = data.get('difficulty', 'medium')
    
    if not title or not description:
        return jsonify({'error': 'Title and description are required'}), 400
    
    conn = get_db()
    conn.execute('UPDATE problems SET title = ?, description = ?, natural_language = ?, difficulty = ? WHERE id = ?',
                 (title, description, natural_language, difficulty, problem_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/problems/import-csv', methods=['POST'])
def import_csv():
    """Import problems from a CSV file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'File must be a CSV'}), 400
    
    try:
        import csv
        from io import StringIO
        
        # Read file content
        content = file.read().decode('utf-8')
        reader = csv.DictReader(StringIO(content))
        
        # Expected columns: title, description, natural_language (optional), difficulty (optional)
        imported = []
        errors = []
        
        conn = get_db()
        cursor = conn.cursor()
        
        for i, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
            title = row.get('title', '').strip()
            description = row.get('description', '').strip()
            natural_language = row.get('natural_language', row.get('natural', '')).strip()
            difficulty = row.get('difficulty', 'medium').strip().lower()
            
            if not title or not description:
                errors.append(f"Row {i}: Missing title or description")
                continue
            
            if difficulty not in ['easy', 'medium', 'hard']:
                difficulty = 'medium'
            
            cursor.execute(
                'INSERT INTO problems (title, description, natural_language, difficulty) VALUES (?, ?, ?, ?)',
                (title, description, natural_language, difficulty)
            )
            imported.append({
                'id': cursor.lastrowid,
                'title': title,
                'description': description,
                'difficulty': difficulty
            })
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'imported': len(imported),
            'problems': imported,
            'errors': errors
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/problems/export-csv', methods=['GET'])
def export_csv():
    """Export all problems to a CSV file."""
    import csv
    from io import StringIO
    from flask import Response
    
    conn = get_db()
    problems = conn.execute('SELECT title, description, natural_language, difficulty FROM problems ORDER BY created_at DESC').fetchall()
    conn.close()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['title', 'description', 'natural_language', 'difficulty'])
    
    for p in problems:
        writer.writerow([p['title'], p['description'], p['natural_language'], p['difficulty']])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=problems.csv'}
    )

@app.route('/api/problem/<int:problem_id>', methods=['DELETE'])
def delete_problem(problem_id):
    conn = get_db()
    conn.execute('DELETE FROM formalizations WHERE problem_id = ?', (problem_id,))
    conn.execute('DELETE FROM problems WHERE id = ?', (problem_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/formalize/<int:problem_id>', methods=['POST'])
def formalize_problem(problem_id):
    conn = get_db()
    problem = conn.execute('SELECT * FROM problems WHERE id = ?', (problem_id,)).fetchone()
    if not problem:
        conn.close()
        return jsonify({'error': 'Problem not found'}), 404
    problem_dict = dict(problem)
    conn.close()
    
    data = request.get_json() or {}
    current_code = data.get('code', '')
    action = data.get('action', 'formalize')
    
    lean_code = generate_lean_formalization(problem_dict, current_code, action)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO formalizations (problem_id, lean_code, status) VALUES (?, ?, ?)',
                   (problem_id, lean_code, 'generated'))
    formalization_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'id': formalization_id, 'lean_code': lean_code, 'problem_id': problem_id})

@app.route('/api/formalize-stream/<int:problem_id>', methods=['POST'])
def formalize_problem_stream(problem_id):
    """Stream AI formalization response."""
    from flask import Response, stream_with_context
    
    conn = get_db()
    problem = conn.execute('SELECT * FROM problems WHERE id = ?', (problem_id,)).fetchone()
    if not problem:
        conn.close()
        return jsonify({'error': 'Problem not found'}), 404
    problem_dict = dict(problem)
    conn.close()
    
    data = request.get_json() or {}
    current_code = data.get('code', '')
    action = data.get('action', 'formalize')
    
    # Auto-detect provider
    provider = os.environ.get('LLM_PROVIDER', '').lower()
    if not provider:
        if os.environ.get('XAI_API_KEY') or os.environ.get('GROK_API_KEY'):
            provider = 'grok'
        elif os.environ.get('OPENAI_API_KEY') or os.environ.get('LLM_API_KEY'):
            provider = 'openai'
        elif os.environ.get('ANTHROPIC_API_KEY'):
            provider = 'anthropic'
        else:
            provider = 'mock'
    
    if provider in ['grok', 'xai']:
        return stream_grok_formalization(problem_dict, current_code, action, problem_id)
    else:
        # For mock and other providers, just return the result
        lean_code = generate_lean_formalization(problem_dict, current_code, action)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO formalizations (problem_id, lean_code, status) VALUES (?, ?, ?)',
                       (problem_id, lean_code, 'generated'))
        formalization_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        def generate():
            yield f"data: {json.dumps({'id': formalization_id, 'lean_code': lean_code, 'problem_id': problem_id})}\n\n"
        
        return Response(stream_with_context(generate()), mimetype='text/event-stream')

def stream_grok_formalization(problem, current_code, action, problem_id):
    """Stream formalization using xAI Grok API."""
    from flask import Response, stream_with_context
    import requests
    import re
    
    api_key = os.environ.get('XAI_API_KEY') or os.environ.get('GROK_API_KEY')
    model = os.environ.get('LLM_MODEL', 'grok-3')
    
    if not api_key:
        lean_code = "-- Error: Set XAI_API_KEY environment variable\n-- Get your API key from https://console.x.ai/"
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO formalizations (problem_id, lean_code, status) VALUES (?, ?, ?)',
                       (problem_id, lean_code, 'error'))
        formalization_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        def error_gen():
            yield f"data: {json.dumps({'id': formalization_id, 'lean_code': lean_code, 'problem_id': problem_id})}\n\n"
        return Response(error_gen(), mimetype='text/event-stream')
    
    title = problem['title']
    desc = problem['description']
    natural = problem.get('natural_language', '')
    difficulty = problem.get('difficulty', 'medium')
    
    system_prompt = """You are an expert Lean 4 theorem prover and formal verification specialist. Your task is to generate clean, idiomatic Lean 4 code to formalize mathematical problems.

Guidelines for Lean 4 formalization:
1. Use modern Lean 4 syntax (not Lean 3)
2. Prefer `theorem` for propositions and `def` for computations
3. Use `by` for tactic proofs
4. Common tactics: `intro`, `intros`, `cases`, `rcases`, `induction`, `simp`, `omega`, `linarith`, `ring`, `exact`, `apply`, `use`, `obtain`, `have`, `constructor`
5. Use `sorry` only when a proof is genuinely difficult
6. Include helpful comments explaining the approach
7. Use Mathlib imports when helpful (noted in comments)
8. Structure: definitions first, then helper lemmas, then main theorem"""

    if action == 'improve' and current_code:
        prompt = f"""Improve this Lean 4 formalization for the following problem.

**Problem:** {title}
**Description:** {desc}
{f"**Natural language statement:** {natural}" if natural else ""}
**Difficulty:** {difficulty}

**Current Lean code:**
```lean
{current_code}
```

Return ONLY the improved Lean code."""
    elif action == 'fix' and current_code:
        prompt = f"""Fix the errors in this Lean 4 formalization.

**Problem:** {title}
**Description:** {desc}

**Current Lean code with errors:**
```lean
{current_code}
```

Return ONLY the fixed Lean code."""
    else:
        prompt = f"""Create a Lean 4 formalization for this mathematical problem.

**Problem:** {title}
**Description:** {desc}
{f"**Natural language statement:** {natural}" if natural else ""}
**Difficulty:** {difficulty}

Return ONLY the Lean code with comments."""
    
    def generate():
        try:
            response = requests.post(
                'https://api.x.ai/v1/chat/completions',
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}'
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4000,
                    "stream": True
                },
                timeout=120,
                stream=True
            )
            
            full_content = ""
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')
                            if delta:
                                full_content += delta
                                yield f"data: {json.dumps({'delta': delta})}\n\n"
                        except json.JSONDecodeError:
                            continue
            
            # Extract code from markdown if present
            if '```lean' in full_content:
                matches = re.findall(r'```lean\n(.*?)```', full_content, re.DOTALL)
                if matches:
                    full_content = '\n'.join(matches)
            elif '```' in full_content:
                matches = re.findall(r'```\n?(.*?)```', full_content, re.DOTALL)
                if matches:
                    full_content = '\n'.join(matches)
            
            # Save to database
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO formalizations (problem_id, lean_code, status) VALUES (?, ?, ?)',
                           (problem_id, full_content, 'generated'))
            formalization_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            yield f"data: {json.dumps({'done': True, 'id': formalization_id, 'lean_code': full_content})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/api/formalization/<int:formalization_id>', methods=['PUT'])
def update_formalization(formalization_id):
    data = request.get_json() or {}
    lean_code = data.get('code', '')
    conn = get_db()
    conn.execute('UPDATE formalizations SET lean_code = ?, status = ?, updated_at = ? WHERE id = ?',
                 (lean_code, 'edited', datetime.now().isoformat(), formalization_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/formalization/<int:formalization_id>', methods=['DELETE'])
def delete_formalization(formalization_id):
    conn = get_db()
    conn.execute('DELETE FROM formalizations WHERE id = ?', (formalization_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

def generate_lean_formalization(problem, current_code, action):
    provider = os.environ.get('LLM_PROVIDER', '').lower()
    
    # Auto-detect provider based on available API keys
    if not provider:
        if os.environ.get('XAI_API_KEY') or os.environ.get('GROK_API_KEY'):
            provider = 'grok'
        elif os.environ.get('OPENAI_API_KEY') or os.environ.get('LLM_API_KEY'):
            provider = 'openai'
        elif os.environ.get('ANTHROPIC_API_KEY'):
            provider = 'anthropic'
        else:
            provider = 'mock'
    
    if provider == 'grok' or provider == 'xai':
        return generate_grok_formalization(problem, current_code, action)
    elif provider == 'openai':
        return generate_openai_formalization(problem, current_code, action)
    elif provider == 'anthropic':
        return generate_anthropic_formalization(problem, current_code, action)
    else:
        return generate_mock_formalization(problem, current_code, action)

def generate_grok_formalization(problem, current_code, action):
    """Generate formalization using xAI Grok API."""
    import requests
    import re
    
    api_key = os.environ.get('XAI_API_KEY') or os.environ.get('GROK_API_KEY')
    model = os.environ.get('LLM_MODEL', 'grok-3')
    
    if not api_key:
        return "-- Error: Set XAI_API_KEY environment variable\n-- Get your API key from https://console.x.ai/"
    
    title = problem['title']
    desc = problem['description']
    natural = problem.get('natural_language', '')
    difficulty = problem.get('difficulty', 'medium')
    
    system_prompt = """You are an expert Lean 4 theorem prover and formal verification specialist. Your task is to generate clean, idiomatic Lean 4 code to formalize mathematical problems.

Guidelines for Lean 4 formalization:
1. Use modern Lean 4 syntax (not Lean 3)
2. Prefer `theorem` for propositions and `def` for computations
3. Use `by` for tactic proofs
4. Common tactics: `intro`, `intros`, `cases`, `rcases`, `induction`, `simp`, `omega`, `linarith`, `ring`, `exact`, `apply`, `use`, `obtain`, `have`, `constructor`
5. Use `sorry` only when a proof is genuinely difficult
6. Include helpful comments explaining the approach
7. Use Mathlib imports when helpful (noted in comments)
8. Structure: definitions first, then helper lemmas, then main theorem

For proofs:
- Start with simple tactics like `simp`, `omega`, `linarith`
- Use `rcases` for destructuring
- Use `have` for intermediate results
- Consider `calc` blocks for chains of equalities/inequalities"""

    if action == 'improve' and current_code:
        prompt = f"""Improve this Lean 4 formalization for the following problem.

**Problem:** {title}
**Description:** {desc}
{f"**Natural language statement:** {natural}" if natural else ""}
**Difficulty:** {difficulty}

**Current Lean code:**
```lean
{current_code}
```

Please improve this formalization by:
1. Fixing any syntax errors or type errors
2. Making the proof more complete (reduce `sorry` usage if possible)
3. Improving code structure and readability
4. Adding helpful comments
5. Using more appropriate tactics or lemmas

Return ONLY the improved Lean code, no explanations outside the code comments."""
    
    elif action == 'fix' and current_code:
        prompt = f"""Fix the errors in this Lean 4 formalization.

**Problem:** {title}
**Description:** {desc}

**Current Lean code with errors:**
```lean
{current_code}
```

Please:
1. Identify and fix all syntax and type errors
2. Ensure the theorem statement is correct
3. Complete the proof if possible (use `sorry` only if truly stuck)
4. Add comments explaining the fixes

Return ONLY the fixed Lean code."""
    
    else:
        prompt = f"""Create a Lean 4 formalization for this mathematical problem.

**Problem:** {title}
**Description:** {desc}
{f"**Natural language statement:** {natural}" if natural else ""}
**Difficulty:** {difficulty}

Please provide a complete Lean 4 formalization including:
1. Any necessary imports (as comments, e.g., `-- import Mathlib.Data.Nat.Prime`)
2. Definitions of key concepts
3. Helper lemmas if needed
4. The main theorem with a proper type signature
5. A proof using tactics (complete if possible, use `sorry` for hard parts)
6. Comments explaining the approach

Return ONLY the Lean code, with comments for explanations."""
    
    try:
        response = requests.post(
            'https://api.x.ai/v1/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 4000
            },
            timeout=120
        )
        
        response.raise_for_status()
        result = response.json()
        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        # Extract code from markdown if present
        if '```lean' in content:
            matches = re.findall(r'```lean\n(.*?)```', content, re.DOTALL)
            if matches:
                content = '\n'.join(matches)
        elif '```' in content:
            matches = re.findall(r'```\n?(.*?)```', content, re.DOTALL)
            if matches:
                content = '\n'.join(matches)
        
        return content if content else "-- Error: Empty response from Grok"
        
    except requests.exceptions.HTTPError as e:
        return f"-- Error calling Grok API (HTTP {e.response.status_code}):\n-- {e.response.text}"
    except Exception as e:
        return f"-- Error calling Grok API: {str(e)}"

def generate_mock_formalization(problem, current_code, action):
    title = problem['title'].lower()
    desc = problem['description'].lower()
    difficulty = problem.get('difficulty', 'medium')
    
    # Check for specific problem types
    if 'even' in title and 'sum' in desc:
        return '''-- Formalization: Sum of Two Even Numbers
-- Problem: Prove that the sum of two even numbers is even.

-- Definition: A natural number is even if it is twice some natural number
def isEven (n : Nat) : Prop := ∃ k, n = 2 * k

-- Theorem: The sum of two even numbers is even
theorem even_add_even {m n : Nat} (hm : isEven m) (hn : isEven n) : isEven (m + n) := by
  obtain ⟨k, hk⟩ := hm
  obtain ⟨l, hl⟩ := hn
  use k + l
  omega
'''
    elif 'irrational' in title or '√2' in problem['description']:
        return '''-- Formalization: Irrationality of √2
-- Problem: Prove that √2 is irrational.

-- A number is rational if it can be expressed as p/q with q ≠ 0
def isRational (x : Real) : Prop := ∃ p q : Int, q ≠ 0 ∧ x = p / q

-- Main theorem (requires Mathlib for full proof)
theorem sqrt_two_irrational : ¬isRational (Real.sqrt 2) := by
  intro h
  sorry -- Full proof requires infinite descent argument

-- Alternative approach using Nat:
-- The key insight: if √2 = p/q in lowest terms, then both p and q are even
-- This contradicts the assumption that p/q is in lowest terms
'''
    elif 'prime' in title and 'infinit' in desc:
        return '''-- Formalization: Infinitude of Primes
-- Problem: Prove that there are infinitely many prime numbers.

open Nat

-- Main theorem: For any n, there exists a prime greater than n
theorem infinite_primes : ∀ n : Nat, ∃ p : Nat, p > n ∧ Prime p := by
  intro n
  have h : ∃ p, Prime p ∧ p ∣ (n ! + 1) := by
    apply exists_prime_and_dvd
    simp [Nat.add_one_ne_zero]
  obtain ⟨p, hp, hd⟩ := h
  use p
  constructor
  · by_contra hle
    push_neg at hle
    have : p ∣ n ! := by
      apply dvd_factorial
      · exact le_of_not_gt hle
      · exact hp.pos
    have : p ∣ 1 := by
      have h1 : p ∣ n ! + 1 := hd
      exact Nat.dvd_add_right ‹_› h1
    have hp1 : p = 1 := Nat.eq_one_of_dvd_one hp.pos this
    exact hp.not_one hp1
  · exact hp
'''
    elif 'triangle' in title or ('inequality' in title and 'real' in desc):
        return '''-- Formalization: Triangle Inequality
-- Problem: Prove that |a + b| ≤ |a| + |b| for real numbers.

theorem triangle_inequality (a b : Real) : |a + b| ≤ |a| + |b| := by
  exact abs_add a b

-- Alternative proof from first principles:
theorem triangle_inequality' (a b : Real) : |a + b| ≤ |a| + |b| := by
  have h1 : -|a| ≤ a := neg_abs_le a
  have h2 : a ≤ |a| := le_abs_self a
  have h3 : -|b| ≤ b := neg_abs_le b
  have h4 : b ≤ |b| := le_abs_self b
  linarith
'''
    elif 'fermat' in title.lower():
        return '''-- Formalization: Fermat's Little Theorem
-- Problem: If p is prime and a is not divisible by p, then a^(p-1) ≡ 1 (mod p).

-- This requires Mathlib's ZMod for a clean formulation
-- theorem fermat_little_theorem (p : Nat) [Fact (Prime p)] (a : ZMod p) (ha : a ≠ 0) :
--     a ^ (p - 1) = 1 := by
--   exact ZMod.pow_card_sub_one_eq_one ha

-- Basic formulation:
theorem fermat_little_theorem (p a : Nat) (hp : Prime p) (ha : ¬p ∣ a) : 
    a ^ (p - 1) % p = 1 := by
  sorry -- Requires group theory: the multiplicative group mod p has order p-1
'''
    elif 'division' in title.lower() or 'quotient' in desc or 'remainder' in desc:
        return '''-- Formalization: Division Algorithm
-- Problem: For integers a and b with b > 0, there exist unique q, r with a = bq + r and 0 ≤ r < b.

-- Existence
theorem div_algo_exists (a b : Int) (hb : b > 0) :
    ∃ q r : Int, a = b * q + r ∧ 0 ≤ r ∧ r < b := by
  use a / b, a % b
  constructor
  · exact Int.ediv_add_emod a b
  constructor
  · exact Int.emod_nonneg a (Int.pos_iff_ne_zero.mpr (Int.ne_of_gt hb))
  · exact Int.emod_lt_of_pos a hb

-- Uniqueness
theorem div_algo_unique (a b q r q' r' : Int) (hb : b > 0)
    (h1 : a = b * q + r) (h2 : 0 ≤ r) (h3 : r < b)
    (h4 : a = b * q' + r') (h5 : 0 ≤ r') (h6 : r' < b) :
    q = q' ∧ r = r' := by
  have : r - r' = b * (q' - q) := by omega
  have : |r - r'| < b := by
    have : -b < r - r' ∧ r - r' < b := by omega
    exact abs_lt.mpr this
  have : r - r' = 0 := by
    have hdiv : b ∣ (r - r') := ⟨q' - q, by omega⟩
    have : |r - r'| < |b| := by simp [abs_lt]; omega
    exact Int.eq_zero_of_abs_lt_one_iff.mpr (by
      have : |r - r'| < b := this
      have hb' : b ≥ 1 := Int.le_of_lt hb
      omega)
  omega
'''
    elif 'bezout' in title.lower() or 'gcd' in desc:
        return '''-- Formalization: Bézout's Identity
-- Problem: For integers a and b, there exist x, y such that ax + by = gcd(a,b).

theorem bezout (a b : Int) : ∃ x y : Int, a * x + b * y = Int.gcd a b := by
  sorry -- Requires extended Euclidean algorithm

-- For natural numbers:
theorem bezout_nat (a b : Nat) : ∃ x y : Int, a * x + b * y = Int.gcd a b := by
  sorry
'''
    elif 'binomial' in title.lower():
        return '''-- Formalization: Binomial Theorem
-- Problem: (x + y)^n = Σ_{k=0}^{n} C(n,k) x^k y^{n-k}

theorem binomial_theorem (x y : ℝ) (n : ℕ) :
    (x + y)^n = ∑ k in Finset.range (n + 1), (n.choose k) * x^k * y^(n - k) := by
  exact add_pow x y n

-- Proof by induction:
theorem binomial_theorem_induct (x y : ℝ) (n : ℕ) :
    (x + y)^n = ∑ k in Finset.range (n + 1), (n.choose k) * x^k * y^(n - k) := by
  induction n with
  | zero => simp
  | succ n ih =>
    simp [pow_succ, ih]
    sorry -- Requires summation manipulation
'''
    elif 'sum' in title.lower() and 'natural' in desc.lower():
        return '''-- Formalization: Sum of First n Natural Numbers
-- Problem: Prove that 1 + 2 + ... + n = n(n+1)/2.

theorem sum_first_n (n : Nat) : ∑ k in Finset.range (n + 1), k = n * (n + 1) / 2 := by
  induction n with
  | zero => simp
  | succ n ih =>
    simp [Finset.sum_range_succ, ih]
    omega

-- Alternative using Gauss's formula:
theorem gauss_sum (n : Nat) : 2 * ∑ k in Finset.range (n + 1), k = n * (n + 1) := by
  induction n with
  | zero => simp
  | succ n ih =>
    simp [Finset.sum_range_succ]
    omega
'''
    elif 'sum' in title.lower() and 'square' in desc.lower():
        return '''-- Formalization: Sum of Squares
-- Problem: Prove that 1² + 2² + ... + n² = n(n+1)(2n+1)/6.

theorem sum_squares (n : Nat) : 
    ∑ k in Finset.range (n + 1), k^2 = n * (n + 1) * (2 * n + 1) / 6 := by
  induction n with
  | zero => simp
  | succ n ih =>
    simp [Finset.sum_range_succ, ih]
    sorry -- Requires algebraic manipulation
'''
    elif 'geometric' in title.lower() and 'infinite' not in desc.lower():
        return '''-- Formalization: Geometric Series
-- Problem: Σ_{k=0}^{n-1} r^k = (r^n - 1)/(r - 1) for r ≠ 1.

theorem geometric_series (r : ℝ) (n : ℕ) (hr : r ≠ 1) :
    ∑ k in Finset.range n, r^k = (r^n - 1) / (r - 1) := by
  induction n with
  | zero => simp
  | succ n ih =>
    simp [Finset.sum_range_succ, ih]
    field_simp
    ring

-- Alternative formulation:
theorem geometric_series' (r : ℝ) (n : ℕ) :
    (r - 1) * ∑ k in Finset.range n, r^k = r^n - 1 := by
  induction n with
  | zero => simp
  | succ n ih =>
    simp [Finset.sum_range_succ]
    ring
'''
    elif 'cauchy' in title.lower() or 'schwarz' in title.lower():
        return '''-- Formalization: Cauchy-Schwarz Inequality
-- Problem: (Σa_i b_i)² ≤ (Σa_i²)(Σb_i²)

theorem cauchy_schwarz {n : ℕ} (a b : Fin n → ℝ) :
    (∑ i, a i * b i)^2 ≤ (∑ i, (a i)^2) * (∑ i, (b i)^2) := by
  exact Real.inner_mul_inner_self_le (a i) (b i) -- Requires Mathlib

-- From first principles:
theorem cauchy_schwarz' {n : ℕ} (a b : Fin n → ℝ) :
    (∑ i, a i * b i)^2 ≤ (∑ i, (a i)^2) * (∑ i, (b i)^2) := by
  sorry -- Proof uses discriminant of quadratic
'''
    else:
        # Generate a template for any problem
        title = problem['title']
        desc = problem['description']
        natural = problem.get('natural_language', '')
        
        return f'''-- Formalization: {title}
-- Problem: {desc}
{f"-- Natural language: {natural}" if natural else ""}
-- Difficulty: {difficulty}

-- Step 1: Define the key concepts and types
-- Example: def myType : Type := Nat

-- Step 2: Define any helper functions or predicates
-- Example: def myPredicate (x : Nat) : Prop := x > 0

-- Step 3: State the main theorem
theorem main_theorem : True := by
  -- Replace 'True' with your actual proposition
  -- Add your proof steps here
  trivial

-- Common Lean 4 tactics:
--   intro h        - introduce a hypothesis
--   intros         - introduce multiple hypotheses
--   have h : P     - introduce a new hypothesis
--   obtain ⟨x, hx⟩ - destruct an existential/and
--   use x          - provide a witness for existential
--   simp           - simplify using lemmas
--   omega          - solve linear arithmetic
--   ring           - solve ring equations
--   linarith       - linear arithmetic solver
--   apply          - apply a theorem
--   exact          - provide exact term
--   cases h        - case analysis
--   rcases h       - recursive case analysis
--   induction n    - induction on n
--   sorry          - placeholder for incomplete proof
'''

def generate_openai_formalization(problem, current_code, action):
    try:
        import openai
    except ImportError:
        return "-- Error: Run 'pip install openai'"
    
    api_key = os.environ.get('LLM_API_KEY')
    if not api_key:
        return "-- Error: Set LLM_API_KEY environment variable"
    
    client = openai.OpenAI(api_key=api_key)
    prompt = f"Create a Lean 4 formalization for this problem:\n\nProblem: {problem['title']}\nDescription: {problem['description']}\n\nProvide definitions, theorem statement, and proof."
    
    try:
        response = client.chat.completions.create(
            model=os.environ.get('LLM_MODEL', 'gpt-4'),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"-- Error: {str(e)}"

def generate_anthropic_formalization(problem, current_code, action):
    try:
        import anthropic
    except ImportError:
        return "-- Error: Run 'pip install anthropic'"
    
    api_key = os.environ.get('LLM_API_KEY')
    if not api_key:
        return "-- Error: Set LLM_API_KEY environment variable"
    
    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"Create a Lean 4 formalization for this problem:\n\nProblem: {problem['title']}\nDescription: {problem['description']}\n\nProvide definitions, theorem statement, and proof."
    
    try:
        message = client.messages.create(
            model=os.environ.get('LLM_MODEL', 'claude-3-opus-20240229'),
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return f"-- Error: {str(e)}"

@app.route('/api/check_lean', methods=['POST'])
def check_lean():
    data = request.get_json() or {}
    lean_code = data.get('code', '')
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.lean', delete=False) as f:
        f.write(lean_code)
        temp_file = f.name
    
    try:
        result = subprocess.run(['lake', 'env', 'lean', temp_file], capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        return jsonify({'success': result.returncode == 0, 'output': output})
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'output': 'Lean check timed out'})
    except FileNotFoundError:
        return jsonify({'success': False, 'output': 'Lean is not installed. Install from https://leanprover.github.io/', 'error': 'lean_not_found'})
    finally:
        os.unlink(temp_file)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
