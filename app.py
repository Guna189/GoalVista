import streamlit as st
import pandas as pd
import datetime
import calendar
import plotly.express as px
from supabase import create_client

# ==============================
# CONFIG
# ==============================

SUPABASE_URL = "https://jkhiifxrcykqkfwyqbcn.supabase.co"
SUPABASE_KEY = "sb_publishable_JNCq_i2OBZl-j_H1p96R4Q_sHdhzXUo"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

DAILY_TABLE = "goalvista_daily_tasks"
WEEKLY_TABLE = "goalvista_weekly_tasks"
CAL_TABLE = "goalvista_calendar_notes"
USERS_TABLE = "goalvista_users"

# ==============================
# SESSION STATE
# ==============================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ==============================
# UTILITIES
# ==============================

def today():
    return datetime.date.today()

def week_start(date=today()):
    return date - datetime.timedelta(days=date.weekday())

# ==============================
# AUTHENTICATION
# ==============================

def authenticate_user(username, password):

    res = supabase.table(USERS_TABLE)\
        .select("*")\
        .eq("username", username)\
        .eq("password", password)\
        .execute()

    if res.data:
        return True
    return False


def login_page():

    st.title("🔐 GoalVista Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        if authenticate_user(username, password):

            st.session_state.logged_in = True
            st.success("Login Successful")
            st.rerun()

        else:
            st.error("Invalid Username or Password")

# ==============================
# DAILY TASKS
# ==============================

def create_task(task, task_date):
    supabase.table(DAILY_TABLE).insert({
        "task": task,
        "task_date": str(task_date),
        "completed": False
    }).execute()

def get_tasks_by_date(date):
    res = supabase.table(DAILY_TABLE).select("*").eq("task_date", str(date)).execute()
    return res.data

def update_task_status(task_id, status):
    supabase.table(DAILY_TABLE).update({"completed": status}).eq("id", task_id).execute()

def delete_task(task_id):
    supabase.table(DAILY_TABLE).delete().eq("id", task_id).execute()

# ==============================
# DAILY TASK PAGE
# ==============================

def daily_tasks_page():

    st.title("📝 Daily Tasks")

    selected_date = st.date_input("Select Date", value=today())
    tasks = get_tasks_by_date(selected_date)

    df = pd.DataFrame(tasks)

    if df.empty:
        st.info("No tasks for this day")
    else:

        total = len(df)
        completed = int(df["completed"].sum())

        c1, c2, c3 = st.columns(3)

        c1.metric("Total Tasks", total)
        c2.metric("Completed", completed)
        c3.metric("Completion %", round((completed/total)*100, 1))

    st.divider()

    new_task = st.text_input("Add Task")

    if st.button("➕ Add Task"):

        if new_task:
            create_task(new_task, selected_date)
            st.success("Task Added")
            st.rerun()

    st.divider()

    for task in tasks:

        col1, col2 = st.columns([10,1])

        status = col1.checkbox(
            task["task"],
            value=task["completed"],
            key=f"task{task['id']}"
        )

        if status != task["completed"]:
            update_task_status(task["id"], status)
            st.rerun()

        if col2.button("🗑", key=f"del{task['id']}"):
            delete_task(task["id"])
            st.rerun()

# ==============================
# WEEKLY HABIT TRACKER
# ==============================

def weekly_tasks_page():

    st.title("✅ Weekly Habit Tracker")

    year = st.number_input("Year", value=today().year, step=1)

    week_no = st.number_input(
        "Week Number",
        min_value=1,
        max_value=53,
        value=today().isocalendar()[1]
    )

    week_start_date = datetime.date.fromisocalendar(year, week_no, 1)

    rows = supabase.table(WEEKLY_TABLE)\
        .select("*")\
        .eq("week_start", str(week_start_date))\
        .execute().data

    df = pd.DataFrame(rows)

    if not df.empty:

        df = df.rename(columns={
            "task_name":"Task",
            "mon":"Mon","tue":"Tue","wed":"Wed",
            "thu":"Thu","fri":"Fri","sat":"Sat","sun":"Sun"
        })

        df = df.drop(columns=[
            c for c in ["id","week_start","created_on","created_at"]
            if c in df.columns
        ])

    else:

        df = pd.DataFrame(columns=[
            "Task","Mon","Tue","Wed","Thu","Fri","Sat","Sun"
        ])

    for col in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]:

        if col not in df:
            df[col] = False

        df[col] = df[col].fillna(False).astype(bool)

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True
    )

    if st.button("💾 Save Weekly Tasks"):

        supabase.table(WEEKLY_TABLE)\
            .delete()\
            .eq("week_start", str(week_start_date))\
            .execute()

        for r in edited.to_dict("records"):

            data = {
                "week_start": str(week_start_date),
                "task_name": r["Task"],
                "mon": bool(r.get("Mon", False)),
                "tue": bool(r.get("Tue", False)),
                "wed": bool(r.get("Wed", False)),
                "thu": bool(r.get("Thu", False)),
                "fri": bool(r.get("Fri", False)),
                "sat": bool(r.get("Sat", False)),
                "sun": bool(r.get("Sun", False)),
            }

            supabase.table(WEEKLY_TABLE).insert(data).execute()

        st.success("Saved Successfully")

# ==============================
# CALENDAR NOTES
# ==============================

def save_calendar_note(date, note):

    supabase.table(CAL_TABLE).insert({
        "note_date": str(date),
        "note_text": note
    }).execute()

def get_calendar_notes():

    res = supabase.table(CAL_TABLE).select("*").execute()
    return res.data


def calendar_page():

    st.title("📅 Calendar Notes")

    year = st.number_input("Year", value=today().year)
    month = st.selectbox("Month", list(range(1,13)), index=today().month-1)

    cal = calendar.monthcalendar(year, month)

    notes = get_calendar_notes()
    notes_dict = {n["note_date"]: n["note_text"] for n in notes}

    for week in cal:

        cols = st.columns(7)

        for i, day in enumerate(week):

            if day == 0:
                continue

            with cols[i]:

                st.markdown(f"**{day}**")

                date = datetime.date(year, month, day)

                note = st.text_area(
                    "Note",
                    value=notes_dict.get(str(date),""),
                    key=str(date)
                )

                if st.button("Save", key=f"save{date}"):

                    save_calendar_note(date, note)
                    st.success("Saved")

# ==============================
# REPORTS
# ==============================

def reports_page():

    st.title("📊 Reports")

    rows = supabase.table(DAILY_TABLE).select("*").execute().data

    if not rows:
        st.info("No data available")
        return

    df = pd.DataFrame(rows)

    df["completed"] = df["completed"].astype(bool)

    fig = px.pie(
        df,
        names=df["completed"].map({True:"Completed",False:"Not Completed"}),
        title="Task Completion"
    )

    st.plotly_chart(fig)

# ==============================
# MAIN APP
# ==============================

st.set_page_config(
    page_title="GoalVista",
    page_icon="🎯",
    layout="centered"
)

if not st.session_state.logged_in:

    login_page()
    st.stop()

st.sidebar.title("🎯 GoalVista")

if st.sidebar.button("Logout"):

    st.session_state.logged_in = False
    st.rerun()

page = st.sidebar.radio(
    "Navigation",
    ["Daily Tasks","Weekly Tasks","Calendar","Reports"]
)

if page == "Daily Tasks":
    daily_tasks_page()

elif page == "Weekly Tasks":
    weekly_tasks_page()

elif page == "Calendar":
    calendar_page()

elif page == "Reports":
    reports_page()
