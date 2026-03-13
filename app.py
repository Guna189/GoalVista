import streamlit as st
import pandas as pd
import datetime
import calendar
import plotly.express as px
import os
from supabase import create_client

st.markdown(
    """
    <link rel="manifest" href="assets/manifest.json">
    <link rel="apple-touch-icon" href="AppIcons/android/mipmap-xxxhdpi/ic_launcher.png">
    """,
    unsafe_allow_html=True
)

# ==============================
# CONFIG
# ==============================
SUPABASE_URL = "https://jkhiifxrcykqkfwyqbcn.supabase.co"
SUPABASE_KEY = "sb_publishable_JNCq_i2OBZl-j_H1p96R4Q_sHdhzXUo"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

DAILY_TABLE = "goalvista_daily_tasks"
WEEKLY_TABLE = "goalvista_weekly_tasks"
CAL_TABLE = "goalvista_calendar_notes"

# ==============================
# UTILITIES
# ==============================
def today():
    return datetime.date.today()

def week_start(date=today()):
    return date - datetime.timedelta(days=date.weekday())

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
# WEEKLY TASKS
# ==============================
def get_weekly_tasks_for_date(date):
    wk_start = week_start(date)
    res = supabase.table(WEEKLY_TABLE).select("*").eq("week_start", str(wk_start)).execute()
    return res.data

def save_weekly_tasks(rows, date):
    wk_start = week_start(date)
    # Delete old week data first
    supabase.table(WEEKLY_TABLE).delete().eq("week_start", str(wk_start)).execute()
    for r in rows:
        data = {
            "week_start": str(wk_start),
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

# ==============================
# DAILY TASKS PAGE
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
        status = col1.checkbox(task["task"], value=task["completed"], key=f"task{task['id']}")
        if status != task["completed"]:
            update_task_status(task["id"], status)
            st.rerun()
        if col2.button("🗑", key=f"del{task['id']}"):
            delete_task(task["id"])
            st.rerun()

# ==============================
# WEEKLY HABIT TRACKER PAGE
# ==============================
def weekly_tasks_page():
    st.title("✅ Weekly Habit Tracker")

    # ----------------------
    # Week Picker
    # ----------------------
    year = st.number_input("Year", value=today().year, step=1)
    week_no = st.number_input("Week Number", min_value=1, max_value=53, value=today().isocalendar()[1], step=1)
    week_start_date = datetime.date.fromisocalendar(year, week_no, 1)  # Monday of selected week

    # Fetch weekly tasks for this week
    rows = supabase.table(WEEKLY_TABLE).select("*") \
        .eq("week_start", str(week_start_date)).execute().data

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.rename(columns={
            "task_name":"Task","mon":"Mon","tue":"Tue","wed":"Wed",
            "thu":"Thu","fri":"Fri","sat":"Sat","sun":"Sun"
        })
        # Drop DB metadata
        df = df.drop(columns=[c for c in ["id","week_start","created_on","created_at"] if c in df.columns])
    else:
        df = pd.DataFrame(columns=["Task","Mon","Tue","Wed","Thu","Fri","Sat","Sun"])

    # Ensure boolean
    for col in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]:
        if col not in df: df[col] = False
        df[col] = df[col].fillna(False).astype(bool)

    edited = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={col: st.column_config.CheckboxColumn(col) for col in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]},
    disabled=False, 
    hide_index=True,  
    key="weekly_editor",
    column_order=None, 
    hide_columns=[],
    row_order=False  
    )

    if st.button("💾 Save Weekly Tasks"):
        # Save updated tasks
        # First delete old data for this week
        supabase.table(WEEKLY_TABLE).delete().eq("week_start", str(week_start_date)).execute()
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
# CALENDAR PAGE
# ==============================
def calendar_page():
    st.title("📅 Calendar Notes")

    if "cal_year" not in st.session_state: st.session_state.cal_year = today().year
    if "cal_month" not in st.session_state: st.session_state.cal_month = today().month

    col1, col2, col3 = st.columns([1,6,1])
    with col1:
        if st.button("⬅ Prev"):
            if st.session_state.cal_month == 1:
                st.session_state.cal_month = 12
                st.session_state.cal_year -= 1
            else:
                st.session_state.cal_month -= 1
    with col3:
        if st.button("Next ➡"):
            if st.session_state.cal_month == 12:
                st.session_state.cal_month = 1
                st.session_state.cal_year += 1
            else:
                st.session_state.cal_month += 1

    st.session_state.cal_month = st.selectbox("Month", list(range(1,13)), index=st.session_state.cal_month-1)
    st.session_state.cal_year = st.number_input("Year", value=st.session_state.cal_year, step=1)

    year = st.session_state.cal_year
    month = st.session_state.cal_month
    st.markdown(f"### {calendar.month_name[month]} {year}")

    cal = calendar.monthcalendar(year, month)
    notes = get_calendar_notes()
    notes_dict = {n["note_date"]: n["note_text"] for n in notes}

    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("")
                continue
            with cols[i]:
                st.markdown(f"**{day}**")
                date = datetime.date(year, month, day)
                key = f"note{date}"
                note_text = notes_dict.get(str(date), "")
                note = st.text_area("Note", value=note_text, key=key)
                if st.button("Save", key=f"save{date}"):
                    save_calendar_note(date, note)
                    st.success("Saved")

# ==============================
# REPORTS PAGE (Daily / Weekly / Monthly Filter)
# ==============================
# ----------------------------
# REPORTS PAGE
# ----------------------------
def reports_page():
    st.title("📊 Reports")

    # ----------------------------
    # Choose report type
    # ----------------------------
    report_type = st.radio("Select Report Type", ["Daily", "Weekly", "Monthly"])

    if report_type == "Daily":
        # ----------------------------
        # Daily Reports
        # ----------------------------
        selected_date = st.date_input("Select Date", value=today())

        # Fetch daily tasks
        tasks = supabase.table(DAILY_TABLE).select("*") \
            .eq("task_date", str(selected_date)).execute().data

        if not tasks:
            st.info("No tasks for selected day.")
            return

        df = pd.DataFrame(tasks)
        df["completed"] = df["completed"].astype(bool)
        df["not_completed"] = ~df["completed"]

        st.subheader(f"Daily Tasks Analysis: {selected_date}")

        # ----------------------------
        # Visual 1: Completed vs Not Completed Pie
        # ----------------------------
        fig1 = px.pie(df, names=df["completed"].map({True: "Completed", False: "Not Completed"}), 
                      title="Task Completion Status")
        st.plotly_chart(fig1, use_container_width=True)

        # ----------------------------
        # Visual 2: Completion Bar
        # ----------------------------
        fig2 = px.bar(df, x="task", y="completed", title="Task Completion (1=Done, 0=Not Done)")
        st.plotly_chart(fig2, use_container_width=True)

        # ----------------------------
        # Visual 3: Count Metrics
        # ----------------------------
        total_tasks = len(df)
        completed_tasks = df["completed"].sum()
        not_completed_tasks = total_tasks - completed_tasks
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Tasks", total_tasks)
        c2.metric("Completed Tasks", completed_tasks)
        c3.metric("Not Completed", not_completed_tasks)

        # ----------------------------
        # Visual 4: Cumulative Completion Bar
        # ----------------------------
        df_cum = df.copy()
        df_cum["cumulative"] = df_cum["completed"].cumsum()
        fig4 = px.line(df_cum, x=df_cum.index, y="cumulative", title="Cumulative Completed Tasks")
        st.plotly_chart(fig4, use_container_width=True)

        # ----------------------------
        # Visual 5: Completed vs Not Completed Summary
        # ----------------------------
        fig5 = px.histogram(df, x="completed", color="completed", 
                            title="Completed vs Not Completed Distribution", text_auto=True)
        st.plotly_chart(fig5, use_container_width=True)

    elif report_type == "Weekly":
        # ----------------------------
        # Weekly Reports
        # ----------------------------
        year = st.number_input("Year", value=today().year, step=1)
        week_no = st.number_input("Week Number", min_value=1, max_value=53, value=today().isocalendar()[1], step=1)
        week_start_date = datetime.date.fromisocalendar(year, week_no, 1)

        rows = supabase.table(WEEKLY_TABLE).select("*") \
            .eq("week_start", str(week_start_date)).execute().data

        if not rows:
            st.info("No weekly tasks for selected week.")
            return

        df = pd.DataFrame(rows)
        df = df.rename(columns={"task_name":"Task","mon":"Mon","tue":"Tue","wed":"Wed",
                                "thu":"Thu","fri":"Fri","sat":"Sat","sun":"Sun"})
        df = df.drop(columns=[c for c in ["id","week_start","created_on","created_at"] if c in df.columns])
        
        # Compute total completion per task
        df["total_completed"] = df[["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]].sum(axis=1)

        st.subheader(f"Weekly Habit Analysis: Week {week_no}, {year}")

        # ----------------------------
        # Visual 1: Total Completion per Task
        # ----------------------------
        fig1 = px.bar(df, x="Task", y="total_completed", title="Total Completion per Task")
        st.plotly_chart(fig1, use_container_width=True)

        # ----------------------------
        # Visual 2: Day-wise Completion
        # ----------------------------
        day_sum = df[["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]].sum().reset_index()
        day_sum.columns = ["Day","Completed"]
        fig2 = px.bar(day_sum, x="Day", y="Completed", title="Completion per Day")
        st.plotly_chart(fig2, use_container_width=True)

        # ----------------------------
        # Visual 3: Task Completion Heatmap
        # ----------------------------
        fig3 = px.imshow(df[["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]], 
                         labels=dict(x="Day", y="Task", color="Done"),
                         x=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
                         y=df["Task"])
        st.plotly_chart(fig3, use_container_width=True)

        # ----------------------------
        # Visual 4: Completion Distribution Pie
        # ----------------------------
        total_done = df[["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]].sum().sum()
        total_possible = df[["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]].size
        fig4 = px.pie(values=[total_done, total_possible-total_done],
                      names=["Completed","Not Completed"], title="Overall Completion Distribution")
        st.plotly_chart(fig4, use_container_width=True)

        # ----------------------------
        # Visual 5: Average Completion per Task
        # ----------------------------
        avg_completion = df["total_completed"].mean()
        st.metric("Average Completion per Task", round(avg_completion,2))

        # ----------------------------
        # Visual 6: Cumulative Completion Trend
        # ----------------------------
        df_cum = df.copy()
        df_cum["cumulative"] = df_cum["total_completed"].cumsum()
        fig6 = px.line(df_cum, x=df_cum.index, y="cumulative", title="Cumulative Task Completion Trend")
        st.plotly_chart(fig6, use_container_width=True)

        # ----------------------------
        # Visual 7: Task Completion Histogram
        # ----------------------------
        fig7 = px.histogram(df, x="total_completed", nbins=7, title="Tasks by Completion Count")
        st.plotly_chart(fig7, use_container_width=True)

    elif report_type == "Monthly":
        # ----------------------------
        # Monthly Reports
        # ----------------------------
        year = st.number_input("Year", value=today().year, step=1)
        month = st.selectbox("Month", list(range(1,13)), index=today().month-1)
        
        start_date = datetime.date(year, month, 1)
        end_day = calendar.monthrange(year, month)[1]
        end_date = datetime.date(year, month, end_day)

        rows = supabase.table(DAILY_TABLE).select("*") \
            .gte("task_date", str(start_date)) \
            .lte("task_date", str(end_date)) \
            .execute().data

        if not rows:
            st.info("No daily tasks for selected month.")
            return

        df = pd.DataFrame(rows)
        df["completed"] = df["completed"].astype(bool)
        df_group = df.groupby("task_date").agg(total_tasks=('task','count'), completed=('completed','sum')).reset_index()
        df_group["not_completed"] = df_group["total_tasks"] - df_group["completed"]

        st.subheader(f"Monthly Task Analysis: {calendar.month_name[month]} {year}")

        # ----------------------------
        # Visual 1: Completed vs Not Completed (line)
        # ----------------------------
        fig1 = px.line(df_group, x="task_date", y=["completed","not_completed"], 
                       title="Daily Completed vs Not Completed Tasks", markers=True)
        st.plotly_chart(fig1, use_container_width=True)

        # ----------------------------
        # Visual 2: Total Tasks per Day (Bar)
        # ----------------------------
        fig2 = px.bar(df_group, x="task_date", y="total_tasks", title="Total Tasks per Day")
        st.plotly_chart(fig2, use_container_width=True)

        # ----------------------------
        # Visual 3: Completion Percentage per Day
        # ----------------------------
        df_group["completion_percent"] = (df_group["completed"]/df_group["total_tasks"])*100
        fig3 = px.line(df_group, x="task_date", y="completion_percent", title="Daily Completion %", markers=True)
        st.plotly_chart(fig3, use_container_width=True)

        # ----------------------------
        # Visual 4: Completed vs Not Completed Pie
        # ----------------------------
        total_done = df_group["completed"].sum()
        total_not_done = df_group["not_completed"].sum()
        fig4 = px.pie(values=[total_done, total_not_done], names=["Completed","Not Completed"], title="Overall Completion Distribution")
        st.plotly_chart(fig4, use_container_width=True)

        # ----------------------------
        # Visual 5: Cumulative Completed Tasks
        # ----------------------------
        df_group["cumulative_done"] = df_group["completed"].cumsum()
        fig5 = px.line(df_group, x="task_date", y="cumulative_done", title="Cumulative Completed Tasks", markers=True)
        st.plotly_chart(fig5, use_container_width=True)

        # ----------------------------
        # Visual 6: Histogram of Completed Tasks
        # ----------------------------
        fig6 = px.histogram(df_group, x="completed", nbins=10, title="Daily Completed Tasks Distribution")
        st.plotly_chart(fig6, use_container_width=True)

        # ----------------------------
        # Visual 7: Average Completion Metric
        # ----------------------------
        avg_daily = df_group["completion_percent"].mean()
        st.metric("Average Daily Completion %", round(avg_daily,2))

# ==============================
# MAIN APP
# ==============================
st.set_page_config(page_title="GoalVista", page_icon="assets/logo.png", layout="centered")
st.sidebar.title("🎯 GoalVista")

page = st.sidebar.radio("Navigation", ["Daily Tasks", "Weekly Tasks", "Calendar", "Reports"])

if page == "Daily Tasks":
    daily_tasks_page()
elif page == "Weekly Tasks":
    weekly_tasks_page()
elif page == "Calendar":
    calendar_page()
elif page == "Reports":

    reports_page()





