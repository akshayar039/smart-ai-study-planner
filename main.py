from flask import Flask, request, redirect, url_for, render_template_string, abort
from datetime import date, datetime, time, timedelta
import json
import os
import uuid

app = Flask(__name__)

# Study plans are stored in this JSON file beside main.py.
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "study_plans.json")

HOME_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Smart Study Planner</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;background:#eef2ff;color:#172554}
.card{max-width:850px;margin:35px auto;background:#fff;padding:30px;border-radius:18px;box-shadow:0 8px 28px #1e3a8a18}
h1{text-align:center;color:#315bd6;margin-top:0}.subtitle{text-align:center;color:#64748b}
label{display:block;font-weight:bold;margin:18px 0 8px}
input{width:100%;padding:13px;border:1px solid #cbd5e1;border-radius:8px;font-size:16px}
button,.button{display:inline-block;border:0;border-radius:9px;background:#2563eb;color:white;padding:13px 18px;font-size:16px;text-decoration:none;cursor:pointer}
button{width:100%;margin-top:22px}button:hover,.button:hover{background:#1d4ed8}
.note{color:#64748b;font-size:14px}.links{text-align:center;margin-top:20px}.error{background:#fee2e2;color:#991b1b;padding:12px;border-radius:8px}
</style>
</head>
<body>
<div class="card">
<h1>🎓 Smart Study Planner</h1>
<p class="subtitle">Create a personalized study timetable and track your progress.</p>
{% if error %}<p class="error">{{ error }}</p>{% endif %}
<form action="{{ url_for('create_plan') }}" method="post">
<label for="subjects">Subjects (separate with commas)</label>
<input id="subjects" name="subjects" placeholder="Python, Java, Maths" required>
<p class="note">Enter a subject name for each class.</p>

<label for="difficulties">Difficulty for each subject (1–5, same order)</label>
<input id="difficulties" name="difficulties" placeholder="2, 5, 3" pattern="[1-5](\s*,\s*[1-5])*" required>
<p class="note">1 = Easy, 5 = Hard. Example: Python, Java, Maths → 2, 5, 3.</p>

<label for="exam_date">Exam date</label>
<input id="exam_date" type="date" name="exam_date" min="{{ today }}" required>

<label for="study_hours">Study hours per day (1–12)</label>
<input id="study_hours" type="number" name="study_hours" min="1" max="12" value="4" required>

<button type="submit">Generate My Smart Study Plan</button>
</form>
<div class="links"><a href="{{ url_for('saved_plans') }}">View Saved Plans</a></div>
</div>
</body>
</html>
"""

PLAN_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Your Personalized Study Plan</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;background:#eef2ff;color:#172554}
.card{max-width:1100px;margin:28px auto;background:#fff;padding:26px;border-radius:18px;box-shadow:0 8px 28px #1e3a8a18;overflow-x:auto}
h1{text-align:center;color:#315bd6}.stats{text-align:center;font-size:18px;line-height:1.8}
.progress-container{max-width:700px;margin:25px auto;text-align:center}
.progress-background{height:25px;background:#e0e7ff;border-radius:20px;overflow:hidden}
.progress-fill{height:100%;width:0;background:linear-gradient(90deg,#2563eb,#22c55e);transition:width .3s ease}
table{width:100%;border-collapse:collapse;margin-top:24px;min-width:720px}
th{background:#2f63e9;color:#fff;padding:14px}td{padding:14px;text-align:center;border-bottom:1px solid #dbeafe}
tr.completed{background:#d9fbe8;color:#047857}tr.completed .subject{text-decoration:line-through}
input[type=checkbox]{width:22px;height:22px;cursor:pointer;accent-color:#16a34a}
.tip{text-align:center;margin-top:22px}.links{text-align:center;margin:25px 0}
a{color:#2563eb}.button{display:inline-block;background:#2563eb;color:#fff;padding:10px 15px;border-radius:8px;text-decoration:none}
.small{font-size:14px;color:#64748b}.save-status{color:#047857;text-align:center;min-height:20px}
@media(max-width:600px){.card{margin:10px;padding:15px}h1{font-size:24px}.stats{font-size:16px}}
</style>
</head>
<body>
<div class="card">
<h1>🎓 Your Personalized Study Plan</h1>
<div class="stats">
<div>Days until exam: <strong>{{ days_left }}</strong></div>
<div>Daily study time: <strong>{{ hours }} hours</strong></div>
<div>Exam date: <strong>{{ exam_date }}</strong></div>
</div>

<div class="progress-container">
<h3>📊 Your Study Progress</h3>
<div class="progress-background" role="progressbar" aria-label="Study progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{{ progress }}">
<div class="progress-fill" id="progressBar" style="width:{{ progress }}%"></div>
</div>
<p id="progressText">{{ progress }}% completed ({{ completed_count }} of {{ total_count }} subjects)</p>
<p class="save-status" id="saveStatus" aria-live="polite"></p>
</div>

<table>
<thead><tr><th>Completed</th><th>Subject</th><th>Difficulty</th><th>Priority</th><th>Study time</th><th>Duration</th></tr></thead>
<tbody>
{% for subject in plan["subjects"] %}
<tr class="{% if subject.completed %}completed{% endif %}" data-subject-id="{{ subject.id }}">
<td><input type="checkbox" class="completed-checkbox" aria-label="Mark {{ subject.name }} completed" {% if subject.completed %}checked{% endif %}></td>
<td class="subject">{{ subject.name }}</td>
<td>{{ subject.difficulty }}/5</td>
<td>{{ subject.priority }}</td>
<td>{{ subject.start }} - {{ subject.end }}</td>
<td>{{ subject.duration }} minutes</td>
</tr>
{% endfor %}
</tbody>
</table>
<p class="tip">💪 Keep going! Every study session counts.</p>
<p class="tip">💡 Harder subjects receive more study time.</p>
<div class="links">
<a class="button" href="{{ url_for('home') }}">Create Another Plan</a>
&nbsp;&nbsp;|&nbsp;&nbsp;
<a href="{{ url_for('saved_plans') }}">View Saved Plans</a>
</div>
<p class="small">Your checkbox progress is saved automatically.</p>
</div>

<script>
const planId = {{ plan["id"]|tojson }};
const progressBar = document.getElementById("progressBar");
const progressText = document.getElementById("progressText");
const saveStatus = document.getElementById("saveStatus");

function updateProgress() {
    const rows = Array.from(document.querySelectorAll("tbody tr[data-subject-id]"));
    const total = rows.length;
    const completed = rows.filter(row => row.querySelector(".completed-checkbox").checked).length;
    const percentage = total === 0 ? 0 : Math.round(completed * 100 / total);
    progressBar.style.width = percentage + "%";
    progressBar.parentElement.setAttribute("aria-valuenow", percentage);
    progressText.textContent = `${percentage}% completed (${completed} of ${total} subjects)`;
    rows.forEach(row => {
        const checkbox = row.querySelector(".completed-checkbox");
        row.classList.toggle("completed", checkbox.checked);
    });
}

async function saveCompletion(row, checkbox) {
    checkbox.disabled = true;
    saveStatus.textContent = "Saving progress…";
    try {
        const response = await fetch(`/plan/${planId}/completion`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                subject_id: row.dataset.subjectId,
                completed: checkbox.checked
            })
        });
        const result = await response.json();
        if (!response.ok || !result.success) {
            throw new Error(result.error || "Could not save progress");
        }
        saveStatus.textContent = "Progress saved successfully.";
    } catch (error) {
        checkbox.checked = !checkbox.checked;
        updateProgress();
        saveStatus.textContent = "Could not save progress. Please try again.";
    } finally {
        checkbox.disabled = false;
    }
}

document.querySelectorAll(".completed-checkbox").forEach(checkbox => {
    checkbox.addEventListener("change", () => {
        const row = checkbox.closest("tr");
        updateProgress();
        saveCompletion(row, checkbox);
    });
});
updateProgress();
</script>
</body>
</html>
"""

SAVED_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Saved Study Plans</title>
<style>
body{font-family:Arial,sans-serif;background:#eef2ff;color:#172554;margin:0}
.card{max-width:900px;margin:30px auto;background:#fff;padding:25px;border-radius:16px;box-shadow:0 8px 28px #1e3a8a18}
h1{text-align:center;color:#315bd6}.plan{border:1px solid #dbeafe;padding:16px;margin:14px 0;border-radius:10px}
a{color:#2563eb}.button{display:inline-block;background:#2563eb;color:#fff;padding:9px 13px;border-radius:7px;text-decoration:none}
.muted{color:#64748b}
</style>
</head>
<body><div class="card">
<h1>📚 Your Saved Study Plans</h1>
{% if plans %}
{% for plan in plans %}
<div class="plan">
<h3>{{ plan["subjects"]|length }} subjects · Exam: {{ plan["exam_date"] }}</h3>
<p class="muted">Daily study time: {{ plan["hours"] }} hours · Created: {{ plan["created_at"] }}</p>
<p>Progress: {{ plan["subjects"]|selectattr("completed")|list|length }} of {{ plan["subjects"]|length }} subjects completed</p>
<p>
<a class="button" href="{{ url_for('view_plan', plan_id=plan['id']) }}">Open Plan</a>
&nbsp; <a href="{{ url_for('delete_plan', plan_id=plan['id']) }}" onclick="return confirm('Delete this saved plan?')">Delete</a>
</p>
</div>
{% endfor %}
{% else %}
<p>No saved plans yet. Create a study plan first.</p>
{% endif %}
<p style="text-align:center;margin-top:24px"><a class="button" href="{{ url_for('home') }}">Back to Study Planner</a></p>
</div></body></html>
"""

def load_plans():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []

def save_plans(plans):
    temp_file = DATA_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(plans, file, indent=2, ensure_ascii=False)
    os.replace(temp_file, DATA_FILE)

def get_plan(plan_id):
    return next((plan for plan in load_plans() if plan.get("id") == plan_id), None)

@app.get("/")
def home():
    return render_template_string(HOME_HTML, today=date.today().isoformat(), error=None)

@app.post("/plan")
def create_plan():
    subjects_raw = request.form.get("subjects", "").strip()
    difficulties_raw = request.form.get("difficulties", "").strip()
    exam_raw = request.form.get("exam_date", "").strip()
    hours_raw = request.form.get("study_hours", "4").strip()

    subjects = [name.strip() for name in subjects_raw.split(",") if name.strip()]
    try:
        difficulties = [int(value.strip()) for value in difficulties_raw.split(",") if value.strip()]
        exam_date = date.fromisoformat(exam_raw)
        hours = int(hours_raw)
    except (ValueError, TypeError):
        return render_template_string(
            HOME_HTML, today=date.today().isoformat(),
            error="Please enter valid difficulties, exam date, and study hours."
        ), 400

    if not subjects:
        return render_template_string(HOME_HTML, today=date.today().isoformat(), error="Enter at least one subject."), 400
    if len(subjects) != len(difficulties):
        return render_template_string(HOME_HTML, today=date.today().isoformat(), error="Enter exactly one difficulty for each subject."), 400
    if any(level < 1 or level > 5 for level in difficulties):
        return render_template_string(HOME_HTML, today=date.today().isoformat(), error="Each difficulty must be between 1 and 5."), 400
    if len(set(name.casefold() for name in subjects)) != len(subjects):
        return render_template_string(HOME_HTML, today=date.today().isoformat(), error="Subject names must be unique."), 400
    if exam_date < date.today():
        return render_template_string(HOME_HTML, today=date.today().isoformat(), error="Exam date cannot be in the past."), 400
    if not 1 <= hours <= 12:
        return render_template_string(HOME_HTML, today=date.today().isoformat(), error="Study hours must be between 1 and 12."), 400

    total_minutes = hours * 60
    # Give harder subjects a larger share, while reserving short breaks between sessions.
    weights = difficulties
    total_weight = sum(weights)
    durations = [int(total_minutes * weight / total_weight) for weight in weights]
    # Distribute rounding remainder so session durations add up exactly.
    remainder = total_minutes - sum(durations)
    for index in range(remainder):
        durations[index % len(durations)] += 1

    start_minutes = 9 * 60
    plan_subjects = []
    for index, (name, difficulty, duration) in enumerate(zip(subjects, difficulties, durations)):
        start = start_minutes
        end = start + duration
        priority = "High" if difficulty >= 4 else ("Medium" if difficulty == 3 else "Low")
        plan_subjects.append({
            "id": str(uuid.uuid4()),
            "name": name,
            "difficulty": difficulty,
            "priority": priority,
            "start": f"{start // 60:02d}:{start % 60:02d}",
            "end": f"{end // 60:02d}:{end % 60:02d}",
            "duration": duration,
            "completed": False
        })
        start_minutes = end + (15 if index < len(subjects) - 1 else 0)

    plan = {
        "id": uuid.uuid4().hex,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "exam_date": exam_date.isoformat(),
        "hours": hours,
        "subjects": plan_subjects
    }
    plans = load_plans()
    plans.insert(0, plan)
    save_plans(plans)
    return redirect(url_for("view_plan", plan_id=plan["id"]))

@app.get("/plan/<plan_id>")
def view_plan(plan_id):
    plan = get_plan(plan_id)
    if plan is None:
        abort(404, description="Study plan not found.")
    total = len(plan["subjects"])
    completed = sum(1 for subject in plan["subjects"] if subject.get("completed", False))
    percentage = round(completed * 100 / total) if total else 0
    exam_date = date.fromisoformat(plan["exam_date"])
    days_left = max(0, (exam_date - date.today()).days)
    return render_template_string(
        PLAN_HTML, plan=plan, hours=plan["hours"], exam_date=plan["exam_date"],
        days_left=days_left, progress=percentage, completed_count=completed,
        total_count=total
    )

@app.post("/plan/<plan_id>/completion")
def update_completion(plan_id):
    plan = get_plan(plan_id)
    if plan is None:
        return {"success": False, "error": "Study plan not found."}, 404
    payload = request.get_json(silent=True) or {}
    subject_id = payload.get("subject_id")
    completed = payload.get("completed")
    if not isinstance(subject_id, str) or not isinstance(completed, bool):
        return {"success": False, "error": "Invalid completion update."}, 400

    subject = next((item for item in plan["subjects"] if item.get("id") == subject_id), None)
    if subject is None:
        return {"success": False, "error": "Subject not found."}, 404
    subject["completed"] = completed
    plans = load_plans()
    for index, saved_plan in enumerate(plans):
        if saved_plan.get("id") == plan_id:
            plans[index] = plan
            break
    else:
        return {"success": False, "error": "Study plan not found."}, 404
    try:
        save_plans(plans)
    except OSError:
        app.logger.exception("Could not save study plan")
        return {"success": False, "error": "Could not save progress to disk."}, 500
    return {"success": True}

@app.get("/saved")
def saved_plans():
    return render_template_string(SAVED_HTML, plans=load_plans())

@app.get("/plan/<plan_id>/delete")
def delete_plan(plan_id):
    plans = load_plans()
    remaining = [plan for plan in plans if plan.get("id") != plan_id]
    if len(remaining) == len(plans):
        abort(404, description="Study plan not found.")
    save_plans(remaining)
    return redirect(url_for("saved_plans"))

@app.errorhandler(404)
def not_found(error):
    return f"""<!DOCTYPE html><html><head><title>Not Found</title></head>
    <body style="font-family:Arial,sans-serif;padding:30px">
    <h2>Study plan not found</h2><p>{error.description}</p>
    <a href="{url_for('home')}">Return to Study Planner</a></body></html>""", 404

if __name__ == "__main__":
    app.run(debug=True)
