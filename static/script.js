const examTypeSelect = document.getElementById('examType');
const subExamSelect = document.getElementById('subExam');
const modeSelect = document.getElementById('mode');
const sectionDiv = document.getElementById('sectionDiv');
const sectionSelect = document.getElementById('section');
const startBtn = document.getElementById('startBtn');
const examArea = document.getElementById('examArea');
const questionText = document.getElementById('questionText');
const optionsDiv = document.getElementById('optionsDiv');
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');
const submitBtn = document.getElementById('submitBtn');
const resultDiv = document.getElementById('result');

let questions = [];
let questionsBySection = [];
let currentMode = 'practice';
let currentSectionIndex = 0;
let currentQuestionIndex = 0;
let userAnswers = {};

modeSelect.addEventListener('change', () => {
  sectionDiv.style.display = modeSelect.value === 'practice' ? 'block' : 'none';
});

function renderOptions(options, key) {
  optionsDiv.innerHTML = '';
  for (const [optKey, val] of Object.entries(options)) {
    const label = document.createElement('label');
    const input = document.createElement('input');
    input.type = 'radio';
    input.name = 'option';
    input.value = optKey;
    input.checked = userAnswers[key] === optKey;
    input.addEventListener('change', () => {
      userAnswers[key] = optKey;
    });
    label.appendChild(input);
    label.append(` ${optKey}: ${val}`);
    optionsDiv.appendChild(label);
  }
}

function renderQuestion() {
  let q, key;
  if (currentMode === 'mock') {
    q = questionsBySection[currentSectionIndex].questions[currentQuestionIndex];
    key = `${currentSectionIndex}_${currentQuestionIndex}`;
  } else {
    q = questions[currentQuestionIndex];
    key = `${currentQuestionIndex}`;
  }
  questionText.innerText = q.question;
  renderOptions(q.options, key);
  prevBtn.disabled = currentQuestionIndex === 0;
  nextBtn.disabled = currentMode === 'mock'
    ? currentQuestionIndex === questionsBySection[currentSectionIndex].questions.length - 1
    : currentQuestionIndex === questions.length - 1;
  submitBtn.disabled = false;
}

startBtn.addEventListener('click', async () => {
  currentMode = modeSelect.value;
  const payload = {
    exam_type: examTypeSelect.value,
    sub_exam: subExamSelect.value,
    mode: currentMode,
    section: sectionSelect.value
  };
  const res = await fetch('/get_questions', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  if (currentMode === 'mock') {
    questionsBySection = data.questions_by_section;
  } else {
    questions = data.questions;
  }
  examArea.style.display = 'block';
  currentSectionIndex = 0;
  currentQuestionIndex = 0;
  userAnswers = {};
  renderQuestion();
});

nextBtn.addEventListener('click', () => {
  currentQuestionIndex++;
  renderQuestion();
});

prevBtn.addEventListener('click', () => {
  currentQuestionIndex--;
  renderQuestion();
});

submitBtn.addEventListener('click', () => {
  let score = 0, total = 0;
  if (currentMode === 'mock') {
    questionsBySection.forEach((section, si) => {
      section.questions.forEach((q, qi) => {
        total++;
        if (userAnswers[`${si}_${qi}`] === q.answer) score++;
      });
    });
  } else {
    questions.forEach((q, i) => {
      total++;
      if (userAnswers[`${i}`] === q.answer) score++;
    });
  }
  resultDiv.style.display = 'block';
  resultDiv.innerText = `You scored ${score} out of ${total}`;
});
