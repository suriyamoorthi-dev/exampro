from flask import Flask, request, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import random
import re
import requests
import json

app = Flask(__name__)
app.secret_key = "suriya"  # 🔐 Required for sessions and forms

from flask import Flask, send_from_directory
import os

app = Flask(__name__)

# ✅ Serve ads.txt from root
@app.route('/ads.txt')
def ads():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'ads.txt')


# Database setup
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'questions.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

API_KEY = "tgp_v1_EPe-j4YVJAAItehj-3vYdCz-nV0AO3A0ow4cJK7joHs"
TOGETHER_API_URL = "https://api.together.xyz/v1/completions"


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam = db.Column(db.String(50))
    section = db.Column(db.String(100))
    topic = db.Column(db.String(100), nullable=True)
    question_text = db.Column(db.Text)
    option_a = db.Column(db.Text)
    option_b = db.Column(db.Text)
    option_c = db.Column(db.Text)
    option_d = db.Column(db.Text)
    answer = db.Column(db.String(1))

    def to_dict(self):
        return {
            "id": self.id,
            "question": self.question_text,
            "options": {
                "A": self.option_a,
                "B": self.option_b,
                "C": self.option_c,
                "D": self.option_d
            },
            "answer": self.answer
        }


@app.route('/doubt')
def doubt_page():
    return render_template('doubt.html')


@app.route('/ask', methods=['POST'])
def ask_ai():
    data = request.get_json()
    mode = data.get('mode')
    topic = data.get('topic')
    question = data.get('question', '')
    exam = data.get('exam', '').lower()

    if not mode or not topic or not exam or (mode == 'doubt' and not question):
        return jsonify({
            "error": "Missing fields: mode, topic, exam, and question (for doubt mode)"
        }), 400

    # Exam-specific prompt base
    exam_names = {
        "jee": "JEE (Joint Entrance Exam - for Engineering aspirants)",
        "neet": "NEET (Medical Entrance - for Biology, Physics, Chemistry)",
        "gate": "GATE (Graduate Aptitude Test in Engineering - Postgraduate technical exam)"
    }

    if exam not in exam_names:
        return jsonify({"error": f"Unsupported exam: {exam}"}), 400

    exam_full = exam_names[exam]

    # Build AI Prompt
    if mode == "doubt":
        prompt = (
            f"You are an expert faculty for {exam_full}. A student is confused about a question and needs help.\n"
            f"Explain it in simple, clear steps. Break down formulas, concepts, and solve it logically.\n"
            f"Use short paragraphs, relevant formulas, and examples if needed.\n\n"
            f"Topic: {topic}\n"
            f"Question: {question}\n\n"
            f"Your Explanation:"
        )
    elif mode == "trick":
        prompt = (
            f"You are a top-level {exam_full} coach. Share 5 smart shortcut methods, memory hacks, formula tricks or conceptual tips "
            f"to solve questions fast in the topic: {topic}.\n\n"
            f"Use bullet points. Make it exam-focused and beginner-friendly.\n"
        )
    else:
        return jsonify({"error": "Invalid mode. Use 'doubt' or 'trick'."}), 400

    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }

    payload = {
        "model": "lgai/exaone-3-5-32b-instruct",  # You can switch to a fast one like 8B if needed
        "prompt": prompt,
        "max_tokens": 600,
        "temperature": 0.3,
        "top_p": 0.9
    }

    try:
        res = requests.post(TOGETHER_API_URL, headers=headers, json=payload)
        if res.status_code != 200:
            return jsonify({"answer": "⚠️ AI model error. Please try again later."}), 500

        result = res.json()
        ai_text = result.get("output")

        # Fallback
        if not ai_text:
            choices = result.get("choices", [])
            ai_text = choices[0].get("text", "") if choices else ""

        if not ai_text.strip():
            ai_text = "⚠️ AI returned no useful answer. Try again."

        return jsonify({"answer": ai_text.strip()})

    except Exception as e:
        return jsonify({"answer": "❌ Error while connecting to AI server."}), 500



@app.route('/')
def index():
    exams = ['JEE', 'GATE', 'NEET']
    sections = {
        'JEE': ['Main', 'Advanced'],
        'GATE': ['CSE', 'ECE', 'EEE', 'Mechanical', 'Civil'],
        'NEET': ['Biology', 'Chemistry', 'Physics']
    }
    sub_topics = {
        'JEE': {
            'Main': ['Maths', 'Physics', 'Chemistry'],
            'Advanced': ['Maths', 'Physics', 'Chemistry']
        },
        'GATE': {
            'CSE': ['Data Structures', 'Algorithms', 'Operating Systems', 'DBMS'],
            'ECE': ['Signals', 'Networks'],
            'EEE': ['Machines', 'Power Systems'],
            'Mechanical': ['Thermodynamics', 'Fluid Mechanics'],
            'Civil': ['Structures', 'Environmental Engineering']
        },
        'NEET': {
            'Biology': ['Genetics', 'Ecology', 'Botany', 'Zoology'],
            'Chemistry': ['Organic', 'Inorganic', 'Physical'],
            'Physics': ['Mechanics', 'Electrostatics', 'Modern Physics']
        }
    }
    return render_template("index.html", exams=exams, sections=sections, sub_topics=json.dumps(sub_topics))

def generate_ai_questions(exam, section, topic=None, count=20, retries=0):
    MAX_RETRIES = 3

    # ✅ English Prompt for All Exams
    prompt = f"""
Generate {count} multiple-choice questions for the {exam} exam in the {section} section{" on the topic " + topic if topic else ""}.
Use this format strictly:
Q1: question text
A: option A
B: option B
C: option C
D: option D
Answer: A

Continue this format from Q1 to Q{count}.
"""

    # ✅ API Call to Together AI
    headers = {
        'Authorization': f'Bearer {API_KEY}',  # Replace with your actual API key
        'Content-Type': 'application/json'
    }
    payload = {
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
        "prompt": prompt,
        "max_tokens": 1800,
        "temperature": 0.3
    }

    response = requests.post(TOGETHER_API_URL, headers=headers, json=payload)

    if response.status_code != 200:
        print("❌ API Error:", response.status_code, response.text)
        return []

    output = response.json().get("choices", [{}])[0].get("text", "")
    print("🧠 AI Raw Output:\n", output)

    # ✅ Parse AI Output into Structured Questions
    blocks = re.split(r"Q\d+:", output)[1:]
    if not blocks:
        print("❌ No questions matched the expected format.")
        return []

    questions = []
    for block in blocks:
        lines = block.strip().split('\n')
        q_text = ""
        opts = {}
        ans = ""

        for line in lines:
            line = line.strip()
            if line.startswith("A:"):
                opts["A"] = line[2:].strip()
            elif line.startswith("B:"):
                opts["B"] = line[2:].strip()
            elif line.startswith("C:"):
                opts["C"] = line[2:].strip()
            elif line.startswith("D:"):
                opts["D"] = line[2:].strip()
            elif line.lower().startswith("answer:"):
                ans = line.split(":")[1].strip().upper()
            elif line:
                q_text += line + " "

        if opts and ans in opts:
            q = Question(
                exam=exam,
                section=section,
                topic=topic or "",
                question_text=q_text.strip(),
                option_a=opts.get("A", ""),
                option_b=opts.get("B", ""),
                option_c=opts.get("C", ""),
                option_d=opts.get("D", ""),
                answer=ans
            )
            questions.append(q)

    # ✅ Retry if Fewer Than Expected
    if len(questions) < count and retries < MAX_RETRIES:
        print(f"⚠️ Only got {len(questions)} questions. Retrying {MAX_RETRIES - retries} more time(s)...")
        more_questions = generate_ai_questions(exam, section, topic, count - len(questions), retries + 1)
        questions.extend(more_questions)

    return questions[:count]



EXAM_PATTERNS = {
    'JEE': {
        'Main': {
            'Physics': 10,
            'Chemistry': 10,
            'Maths': 10
        },
        'Advanced': {
            'Physics': 10,
            'Chemistry': 10,
            'Maths': 10
        }
    },
    'GATE': {
        'CSE': {
            'Programming': 10,
            'Data Structures': 10,
            'OS': 10
        },
        'ECE': {
            'Networks': 10,
            'Control Systems': 10,
            'Analog': 10
        },
        'EEE': {
            'Machines': 10,
            'Power Systems': 10,
            'EMFT': 10
        },
        'Mechanical': {
            'Thermodynamics': 10,
            'Fluid Mechanics': 10,
            'Manufacturing': 10
        },
        'Civil': {
            'Structures': 10,
            'Environment': 10,
            'Geotech': 10
        }
    },
    'NEET': {
        'Biology': {
            'Botany': 15,
            'Zoology': 15
        },
        'Chemistry': {
            'Organic': 10,
            'Inorganic': 10,
            'Physical': 10
        },
        'Physics': {
            'Mechanics': 10,
            'Optics': 10,
            'Modern Physics': 10
        }
    }
}


def get_hybrid_questions(exam, section, topic, count=20):
    # Step 1: Get cached questions from DB
    cached_questions = Question.query.filter_by(exam=exam, section=section, topic=topic).all()
    cached_count = len(cached_questions)

    half_count = count // 2
    use_cached = min(half_count, cached_count)   # Use as many cached as possible up to half_count
    use_ai = count - use_cached

    selected_cached = random.sample(cached_questions, use_cached) if use_cached > 0 else []

    # Step 2: Generate remaining with AI if needed
    ai_questions = []
    if use_ai > 0:
        ai_questions = generate_ai_questions(exam, section, topic, use_ai)
        for q in ai_questions:
            # Save new AI questions to DB for future reuse
            db.session.add(q)
        db.session.commit()

    combined_questions = selected_cached + ai_questions
    random.shuffle(combined_questions)
    return combined_questions


@app.route('/generate_questions', methods=['POST'])
def generate_questions():
    data = request.form
    exam = data.get('exam')
    section = data.get('section')
    topic = data.get('topic')  # might be None
    mode = data.get('mode')

    if mode == 'practice':
        count = 10  # or 10, as you want
        questions = get_hybrid_questions(exam, section, topic, count=count)

        if not questions:
            return "Unable to generate questions for this topic.", 400

        return render_template('exam_onebyone.html', questions=[q.to_dict() for q in questions],
                               exam=exam, section=section, topic=topic, mode=mode)

    elif mode == 'mock':
        pattern = EXAM_PATTERNS.get(exam, {}).get(section)
        if not pattern:
            return f"No mock exam pattern defined for {exam} - {section}", 400

        all_questions = []

        for sec_name, count in pattern.items():
            qs = Question.query.filter_by(exam=exam, section=sec_name).limit(count).all()
            if len(qs) < count:
                ai_questions = generate_ai_questions(exam, sec_name, topic=None, count=count - len(qs))
                for q in ai_questions:
                    db.session.add(q)
                qs.extend(ai_questions)

            all_questions.extend(qs)

        # Commit once after all additions
        db.session.commit()

        if not all_questions:
            return "No questions available for mock exam.", 400

        random.shuffle(all_questions)
        return render_template('exam_onebyone.html',
                               questions=[q.to_dict() for q in all_questions],
                               exam=exam, section=section, topic=None, mode=mode)
    else:
        return "Invalid mode selected", 400

@app.route('/submit_exam', methods=['POST'])
def submit_exam():
    question_ids = request.form.getlist('question_id')
    correct_answers = request.form.getlist('correct_answer')
    sections = request.form.getlist('section')

    score = 0
    total = len(question_ids)
    weak_tracker = {}

    for i, qid in enumerate(question_ids):
        user_answer = request.form.get(f"user_answer_{qid}")
        correct = correct_answers[i]
        section = sections[i]

        if section not in weak_tracker:
            weak_tracker[section] = {'total': 0, 'correct': 0}

        weak_tracker[section]['total'] += 1
        if user_answer == correct:
            score += 1
            weak_tracker[section]['correct'] += 1

    weak_areas = [sec for sec, data in weak_tracker.items()
                  if data['correct'] / data['total'] < 0.6]

    return render_template("result.html", score=score, total=total, weak_areas=weak_areas)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
