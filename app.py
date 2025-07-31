import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# ------------------ Data Management ------------------
DATA_FILE = "todo_data.json"

def load_tasks():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    return []

def save_tasks(tasks):
    with open(DATA_FILE, "w") as f:
        json.dump(tasks, f, indent=4)

def reset_data():
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    st.session_state.tasks = []

# ------------------ UI Functions ------------------
def display_tasks(tasks, theme):
    st.subheader("📋 Your Tasks")
    
    # Initialize filtered tasks with all tasks
    filtered_tasks = tasks.copy()

    # Search functionality
    search_term = st.text_input("🔍 Search tasks")
    if search_term:
        filtered_tasks = [task for task in filtered_tasks if search_term.lower() in task['task'].lower()]

    # Category filter
    categories = ["All"] + sorted(list(set(t['category'] for t in tasks if 'category' in t)))
    category_filter = st.selectbox("📂 Filter by category", categories)
    if category_filter != "All":
        filtered_tasks = [t for t in filtered_tasks if t['category'] == category_filter]

    # Priority filter
    priority_filter = st.selectbox("🔝 Filter by priority", ["All", "Low", "Medium", "High"])
    if priority_filter != "All":
        filtered_tasks = [t for t in filtered_tasks if t['priority'] == priority_filter]

    # Status filter
    status_filter = st.selectbox("✅ Filter by status", ["All", "Completed", "Pending"])
    if status_filter == "Completed":
        filtered_tasks = [t for t in filtered_tasks if t['completed']]
    elif status_filter == "Pending":
        filtered_tasks = [t for t in filtered_tasks if not t['completed']]

    if not filtered_tasks:
        st.info("No tasks match your filters.")
        return

    for idx, task in enumerate(filtered_tasks):
        cols = st.columns([0.05, 0.6, 0.1, 0.15, 0.1])
        
        # Checkbox for completion status
        done = cols[0].checkbox("", value=task.get('completed', False), 
                               key=f"done_{task.get('id', idx)}")
        if done != task.get('completed', False):
            task['completed'] = done
            save_tasks(tasks)
            st.rerun()

        # Task display with enhanced formatting
        task_display = f"**{task['task']}**"
        if 'category' in task:
            task_display += f" | {task['category']}"
        if 'priority' in task:
            priority_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(task['priority'], "")
            task_display += f" | {priority_emoji} {task['priority']}"
        
        if 'due_date' in task and task['due_date']:
            try:
                due_date = datetime.strptime(task['due_date'], "%Y-%m-%d").date()
                today = datetime.now().date()
                days_left = (due_date - today).days
                
                if days_left < 0:
                    task_display += f" | ⚠️ Overdue by {-days_left} days"
                elif days_left == 0:
                    task_display += " | ⏳ Due today"
                else:
                    task_display += f" | ⏳ {days_left} days left"
            except:
                pass

        # Apply strikethrough for completed tasks
        if task.get('completed', False):
            cols[1].markdown(f"<span style='color:gray;text-decoration:line-through'>{task_display}</span>", 
                           unsafe_allow_html=True)
        else:
            cols[1].markdown(task_display)

        # Edit button
        if cols[2].button("✏️", key=f"edit_{task.get('id', idx)}"):
            st.session_state.editing_task = task
            st.rerun()

        # Delete button
        if cols[3].button("🗑️", key=f"del_{task.get('id', idx)}"):
            tasks.remove(task)
            save_tasks(tasks)
            st.rerun()

def edit_task_form():
    if 'editing_task' not in st.session_state:
        return
    
    task = st.session_state.editing_task
    with st.expander(f"✏️ Editing: {task['task']}", expanded=True):
        new_task = st.text_input("Task", task['task'])
        new_category = st.text_input("Category", task.get('category', 'General'))
        new_priority = st.selectbox("Priority", ["Low", "Medium", "High"], 
                                  index=["Low", "Medium", "High"].index(task.get('priority', 'Medium')))
        
        # Handle due date safely
        current_due = task.get('due_date', '')
        try:
            default_date = datetime.strptime(current_due, "%Y-%m-%d") if current_due else datetime.now()
        except:
            default_date = datetime.now()
            
        new_due = st.date_input("Due Date", value=default_date)
        
        col1, col2 = st.columns(2)
        if col1.button("💾 Save Changes"):
            task['task'] = new_task
            task['category'] = new_category
            task['priority'] = new_priority
            task['due_date'] = new_due.strftime("%Y-%m-%d")
            save_tasks(st.session_state.tasks)
            del st.session_state.editing_task
            st.rerun()
            
        if col2.button("❌ Cancel"):
            del st.session_state.editing_task
            st.rerun()

# ------------------ Charts ------------------
def show_charts(tasks):
    st.subheader("📊 Task Summary")
    if not tasks:
        st.info("No tasks to show charts.")
        return
    
    try:
        df = pd.DataFrame(tasks)
        
        # Completion rate
        completion_rate = df['completed'].mean() * 100
        st.metric("📈 Completion Rate", f"{completion_rate:.1f}%")
        
        # Tasks by Category
        if 'category' in df.columns:
            category_count = df['category'].value_counts().reset_index()
            category_count.columns = ['Category', 'Count']
            st.plotly_chart(px.pie(category_count, names='Category', values='Count', 
                                  title='Tasks by Category', hole=0.3), use_container_width=True)

        # Tasks by Priority
        if 'priority' in df.columns:
            priority_count = df['priority'].value_counts().reset_index()
            priority_count.columns = ['Priority', 'Count']
            st.plotly_chart(px.bar(priority_count, x='Priority', y='Count', 
                                 title='Tasks by Priority', color='Priority',
                                 color_discrete_map={
                                     "High": "#FF2B2B",
                                     "Medium": "#F0C808",
                                     "Low": "#2BA84A"
                                 }), use_container_width=True)

        # Due Date Analysis
        if 'due_date' in df.columns:
            try:
                df['due_date'] = pd.to_datetime(df['due_date'])
                df['days_until_due'] = (df['due_date'] - pd.Timestamp.now()).dt.days
                df['status'] = df.apply(lambda x: 
                    "Overdue" if x['days_until_due'] < 0 else 
                    ("Due Soon" if x['days_until_due'] <= 3 else "Future"), axis=1)
                
                status_count = df[~df['completed']]['status'].value_counts().reset_index()
                status_count.columns = ['Status', 'Count']
                if not status_count.empty:
                    st.plotly_chart(px.bar(status_count, x='Status', y='Count', 
                                         title='Pending Tasks by Due Status',
                                         color='Status'), use_container_width=True)
            except:
                pass
                
    except Exception as e:
        st.error(f"Error generating charts: {str(e)}")

# ------------------ Add Task ------------------
def add_task_form():
    st.sidebar.markdown("## ➕ Add a New Task")
    with st.sidebar.form("add_task", clear_on_submit=True):
        task = st.text_input("Task*", placeholder="What needs to be done?")
        category = st.text_input("Category", value="General", placeholder="e.g. Work, Personal")
        priority = st.selectbox("Priority*", ["Low", "Medium", "High"])
        due_date = st.date_input("Due Date", value=datetime.now())
        notes = st.text_area("Notes", placeholder="Additional details...")
        submitted = st.form_submit_button("Add Task")
        
        if submitted:
            if not task:
                st.sidebar.error("Task description is required!")
                return None
            return {
                "id": int(datetime.now().timestamp()),  # Unique ID for each task
                "task": task,
                "category": category,
                "priority": priority,
                "due_date": due_date.strftime("%Y-%m-%d"),
                "notes": notes,
                "completed": False,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    return None

# ------------------ Main App ------------------
def main():
    # Page configuration
    st.set_page_config(
        page_title="📌 To-Do App", 
        layout="wide",
        page_icon="✅"
    )
    
    # Initialize session state
    if 'tasks' not in st.session_state:
        st.session_state.tasks = load_tasks()
    if 'theme' not in st.session_state:
        st.session_state.theme = "light"
    
    # Apply theme
    if st.session_state.theme == "dark":
        dark_mode = """
        <style>
            body {color: #fff; background-color: #0E1117;}
            .stTextInput input, .stSelectbox select, .stDateInput input {
                background-color: #262730 !important;
                color: white !important;
            }
            .css-1aumxhk {background-color: #262730;}
        </style>
        """
        st.markdown(dark_mode, unsafe_allow_html=True)
    
    # Main layout
    st.title("🗂️ Personal To-Do Tracker")
    
    # Add new task
    new_task = add_task_form()
    if new_task:
        st.session_state.tasks.append(new_task)
        save_tasks(st.session_state.tasks)
        st.sidebar.success("Task added successfully!")
        st.rerun()
    
    # Edit task form if needed
    if 'editing_task' in st.session_state:
        edit_task_form()
    
    # Main columns
    col1, col2 = st.columns([3, 1])
    
    with col1:
        display_tasks(st.session_state.tasks, st.session_state.theme)
        show_charts(st.session_state.tasks)
    
    with col2:
        st.markdown("## ⚙️ App Settings")
        
        # Theme switcher
        theme_choice = st.radio("Choose Theme", ["light", "dark"], 
                               index=0 if st.session_state.theme == "light" else 1,
                               key="theme_selector")
        if theme_choice != st.session_state.theme:
            st.session_state.theme = theme_choice
            st.rerun()
        
        # Data management
        st.markdown("### 🔄 Data Management")
        if st.button("🗑️ Reset All Data", help="Permanently delete all tasks"):
            reset_data()
            st.session_state.tasks = []
            st.success("All data has been reset!")
            st.rerun()
            
        st.download_button(
            label="📥 Export to CSV",
            data=pd.DataFrame(st.session_state.tasks).to_csv(index=False),
            file_name="tasks_export.csv",
            mime="text/csv"
        )
        
        # Statistics
        st.markdown("### 📈 Quick Stats")
        if st.session_state.tasks:
            total_tasks = len(st.session_state.tasks)
            completed_tasks = sum(1 for t in st.session_state.tasks if t.get('completed', False))
            st.metric("Total Tasks", total_tasks)
            st.metric("Completed", f"{completed_tasks} ({completed_tasks/total_tasks:.0%})")
            
            # Count overdue tasks
            overdue = 0
            for task in st.session_state.tasks:
                if not task.get('completed', False) and 'due_date' in task:
                    try:
                        due_date = datetime.strptime(task['due_date'], "%Y-%m-%d").date()
                        if due_date < datetime.now().date():
                            overdue += 1
                    except:
                        pass
            if overdue > 0:
                st.warning(f"⚠️ {overdue} overdue tasks")
        else:
            st.info("No tasks yet. Add some tasks to see statistics.")

if __name__ == '__main__':
    main()