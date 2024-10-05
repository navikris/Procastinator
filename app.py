from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, timedelta
import time
import random
import logging
from huggingface_hub import InferenceClient

client = InferenceClient(
    model = "NousResearch/Hermes-3-Llama-3.1-8B",
    token = 'secret_token',
    timeout = 60.0,
)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'secret_key'

# Temporary storage (equivalent to localStorage)
tasks = {}
user_preferences = {"name": "John Doe", "email": "john@gmail.com"}

# Logging setup
logging.basicConfig(filename='app.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Generate a unique numeric ID
def generate_numeric_id():
    return int(datetime.now().timestamp() * 1000)

# Filter tasks by section (e.g., My Day, This Week, etc.)
def filter_tasks(section):
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    start_of_month = today.replace(day=1)
    end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    filtered_tasks = []
    for task in tasks.values():
        task_date = datetime.strptime(task['date'], '%Y-%m-%d').date()

        if section == "myDay" and task_date == today:
            filtered_tasks.append(task)
        elif section == "thisWeek" and start_of_week <= task_date <= end_of_week:
            filtered_tasks.append(task)
        elif section == "thisMonth" and start_of_month <= task_date <= end_of_month:
            filtered_tasks.append(task)
        elif section == "other":
            filtered_tasks.append(task)

    return filtered_tasks

# Check for tasks approaching deadlines
def check_deadlines():
    today = datetime.now().date()
    upcoming_tasks = []

    for task in tasks.values():
        task_date = datetime.strptime(task['date'], '%Y-%m-%d').date()
        if today <= task_date <= today + timedelta(days=2):  # Within 2 days
            upcoming_tasks.append(task)

    return upcoming_tasks

# Function to alert user using LLM procrastination assistant
# Function to alert user using LLM procrastination assistant
def alert_user(upcoming_tasks):
    procrastination_messages = []

    # Only alert if there are upcoming tasks
    if upcoming_tasks:
        for task in upcoming_tasks:
            task_description = f"""
            You are my task manager who will prevent me from completing the tasks.
            I will provide the task name and deadline date,
            your job is to make me procrast the task.
            don't say that you cannot procrast.

            example reply:
                you still have a few minutes for completing {task['text']}, now relax and watch a video.

            You have a task '{task['text']}' due on {task['date']}"""
            
            agent_reply = client.chat_completion(
                messages=[{"role": "user", "content": task_description}],
                max_tokens=200,
                stream=False,
            )
            
            procrastination_message = agent_reply.choices[0].message.content
            procrastination_messages.append(procrastination_message)
            logging.info(f"Generated procrastination message for task '{task['text']}': {procrastination_message}")
    
    return procrastination_messages


# Home route, default to "My Day"
@app.route('/')
def home():
    section = request.args.get('section', 'myDay')
    filtered_tasks = filter_tasks(section)
    # Check for upcoming deadlines and get procrastination messages
    upcoming_tasks = check_deadlines()
    if upcoming_tasks:
        procrastination_messages = alert_user(upcoming_tasks)
    else:
        procrastination_messages = None

    logging.info(f"Rendering home page for section: {section}, tasks count: {len(filtered_tasks)}")
    return render_template('index.html', tasks=filtered_tasks, section=section,
                           user_preferences=user_preferences, procrastination_messages=procrastination_messages)

# Route to add a new task
@app.route('/add_task', methods=['POST'])
def add_task():
    task_text = request.form.get('todo')
    due_date = request.form.get('duedate')

    if task_text and due_date:
        task_id = generate_numeric_id()
        tasks[task_id] = {
            "id": task_id,
            "text": task_text,
            "date": due_date,
            "completed": False
        }
        logging.info(f"Task added: {task_text}, due date: {due_date}")

    return redirect(url_for('home'))

# Route to mark a task as complete/incomplete
@app.route('/toggle_task/<int:task_id>', methods=['POST'])
def toggle_task(task_id):
    task = tasks.get(task_id)
    if task:
        task['completed'] = not task['completed']
        logging.info(f"Toggled task '{task['text']}' to {'completed' if task['completed'] else 'incomplete'}")

    return redirect(url_for('home'))

# Route to delete a task
@app.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    if task_id in tasks:
        logging.info(f"Task deleted: {tasks[task_id]['text']}")
        tasks.pop(task_id, None)

    return redirect(url_for('home'))

# Route to delete all tasks
@app.route('/delete_all_tasks', methods=['POST'])
def delete_all_tasks():
    tasks.clear()
    logging.info("All tasks deleted.")
    return redirect(url_for('home'))

# Route to update user preferences
@app.route('/update_preferences', methods=['POST'])
def update_preferences():
    user_preferences['name'] = request.form.get('name', 'John Doe')
    user_preferences['email'] = request.form.get('email', 'john@gmail.com')
    logging.info(f"Updated user preferences: {user_preferences}")

    return redirect(url_for('home'))

if __name__ == '__main__':
    logging.info("Starting Flask app...")
    app.run(debug=True)
