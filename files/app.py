
import streamlit as st
import sqlite3
import json
from datetime import datetime
import pandas as pd
import plotly.express as px

from ai_engine import (
    extract_text,
    analyze_study_material,
    generate_diagnostic_quiz,
    ask_study_doubt
)

# =====================================================
# PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="StudyGenie",
    page_icon="📚",
    layout="wide"
)

DB_FILE = "studygenie.db"


# =====================================================
# CUSTOM CSS
# =====================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background: #f5f7fc !important;
    color: #24324b !important;
}

.block-container {
    padding-top: 2.5rem !important;
    padding-bottom: 3rem !important;
}

/* MAIN HEADINGS */

[data-testid="stMain"] h1,
[data-testid="stMain"] h2,
[data-testid="stMain"] h3,
[data-testid="stMain"] h4 {
    color: #14213d !important;
    font-weight: 700 !important;
}

/* MAIN TEXT */

[data-testid="stMain"] p,
[data-testid="stMain"] span,
[data-testid="stMain"] label,
[data-testid="stMain"] li {
    color: #344563;
}

/* SIDEBAR */

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #101b35, #172747) !important;
}

[data-testid="stSidebar"] * {
    color: #ffffff !important;
}

/* WELCOME BANNER */

.sg-banner {
    background: linear-gradient(110deg, #e8f0ff, #f1eaff);
    border: 1px solid #dce5ff;
    border-radius: 18px;
    padding: 30px;
    margin-bottom: 24px;
}

.sg-banner h1,
.sg-banner h2,
.sg-banner h3 {
    color: #14213d !important;
}

.sg-banner p {
    color: #506487 !important;
}

/* DASHBOARD CARDS */

.sg-card {
    background: #ffffff !important;
    border: 1px solid #e1e8f5;
    padding: 18px;
    border-radius: 14px;
    margin-bottom: 12px;
    color: #263b63 !important;
}

.sg-card * {
    color: #263b63 !important;
}

/* METRICS */

[data-testid="stMetric"] {
    background: #ffffff !important;
    border: 1px solid #e1e8f5;
    padding: 20px;
    border-radius: 15px;
}

[data-testid="stMetric"] label,
[data-testid="stMetric"] label *,
[data-testid="stMetricValue"],
[data-testid="stMetricValue"] *,
[data-testid="stMetricDelta"] {
    color: #263b63 !important;
}

/* CHART TEXT */

.js-plotly-plot .plotly text {
    fill: #344563 !important;
}

/* ALL BUTTONS */

div.stButton > button {
    background-color: #243b70 !important;
    color: #ffffff !important;
    border: 1px solid #243b70 !important;
    border-radius: 12px !important;
    min-height: 46px;
    font-weight: 600 !important;
}

div.stButton > button p,
div.stButton > button span,
div.stButton > button div {
    color: #ffffff !important;
}

div.stButton > button:hover {
    background-color: #405da0 !important;
    color: #ffffff !important;
    border-color: #405da0 !important;
}

div.stButton > button:focus {
    color: #ffffff !important;
    border-color: #6478f7 !important;
}

/* INPUTS */

[data-testid="stTextInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stFileUploader"] label,
[data-testid="stRadio"] label,
[data-testid="stCheckbox"] label {
    color: #263b63 !important;
}

/* AI TUTOR CHAT */

[data-testid="stChatMessage"] {
    background-color: #ffffff !important;
    border: 1px solid #dce4f2 !important;
    border-radius: 14px !important;
    padding: 18px !important;
    margin-bottom: 12px !important;
}

[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] strong,
[data-testid="stChatMessage"] em,
[data-testid="stChatMessage"] h1,
[data-testid="stChatMessage"] h2,
[data-testid="stChatMessage"] h3,
[data-testid="stChatMessage"] h4,
[data-testid="stChatMessage"] code,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
    color: #24324b !important;
}

/* CHAT INPUT */

[data-testid="stChatInput"] {
    background-color: #ffffff !important;
}

[data-testid="stChatInput"] textarea {
    background-color: #ffffff !important;
    color: #24324b !important;
    caret-color: #24324b !important;
    border: 1px solid #cbd5e8 !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #718096 !important;
    opacity: 1 !important;
}

/* EXPANDERS */

[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1px solid #e1e8f5;
    border-radius: 12px;
}

/* FOOTER */

#MainMenu,
footer {
    visibility: hidden;
}
</style>
""", unsafe_allow_html=True)


# =====================================================
# DATABASE
# =====================================================

def connect():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def initialize_database():

    with connect() as conn:

        conn.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            filename TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            extracted_text TEXT
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            filename TEXT,
            score INTEGER,
            total INTEGER,
            percentage REAL,
            topics_json TEXT,
            attempted_at TEXT
        )
        """)

        columns = [
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(materials)"
            ).fetchall()
        ]

        if "extracted_text" not in columns:
            conn.execute(
                "ALTER TABLE materials ADD COLUMN extracted_text TEXT"
            )

        conn.commit()


initialize_database()


# =====================================================
# DATABASE OPERATIONS
# =====================================================

def save_material(email, filename, text):

    with connect() as conn:
        conn.execute("""
        INSERT INTO materials
        (user_email, filename, uploaded_at, extracted_text)
        VALUES (?, ?, ?, ?)
        """, (
            email,
            filename,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            text
        ))
        conn.commit()


def load_materials(email):

    with connect() as conn:
        return conn.execute("""
        SELECT id, filename, uploaded_at
        FROM materials
        WHERE user_email=?
        ORDER BY id DESC
        """, (email,)).fetchall()


def get_material(email, material_id):

    with connect() as conn:
        return conn.execute("""
        SELECT filename, extracted_text
        FROM materials
        WHERE user_email=? AND id=?
        """, (email, material_id)).fetchone()


def delete_material(email, material_id):

    with connect() as conn:
        conn.execute("""
        DELETE FROM materials
        WHERE user_email=? AND id=?
        """, (email, material_id))
        conn.commit()


def save_attempt(email, filename, result):

    with connect() as conn:
        conn.execute("""
        INSERT INTO quiz_attempts
        (user_email, filename, score, total,
         percentage, topics_json, attempted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            email,
            filename,
            result["score"],
            result["total"],
            result["percentage"],
            json.dumps(result["topics"]),
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        conn.commit()


def load_attempts(email):

    with connect() as conn:
        return conn.execute("""
        SELECT filename, score, total, percentage,
               topics_json, attempted_at
        FROM quiz_attempts
        WHERE user_email=?
        ORDER BY id DESC
        """, (email,)).fetchall()


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def mastery(value):

    if value >= 80:
        return "Strong"
    if value >= 60:
        return "Good"
    if value >= 40:
        return "Developing"
    return "Needs Improvement"


def get_topic_totals(attempts):

    totals = {}

    for row in attempts:

        try:
            topics = json.loads(row[4] or "{}")

            for topic, data in topics.items():

                totals.setdefault(
                    topic,
                    {"correct": 0, "total": 0}
                )

                totals[topic]["correct"] += data.get("correct", 0)
                totals[topic]["total"] += data.get("total", 0)

        except (ValueError, TypeError):
            continue

    return totals


def show_score_chart(attempts):

    data = []

    for index, row in enumerate(reversed(attempts), 1):

        if row[3] is not None:
            data.append({
                "Quiz": f"Quiz {index}",
                "Score": float(row[3])
            })

    if not data:
        st.info("Complete a quiz to view your score history.")
        return

    df = pd.DataFrame(data)

    fig = px.bar(
        df,
        x="Quiz",
        y="Score",
        text="Score",
        range_y=[0, 100]
    )

    fig.update_traces(
        marker_color="#6478f7",
        texttemplate="%{text:.0f}%",
        textposition="outside"
    )

    fig.update_layout(
        height=350,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(
            family="Inter",
            color="#263b63",
            size=12
        ),
        yaxis=dict(
            title="Score (%)",
            range=[0, 110],
            dtick=20,
            gridcolor="#e8edf5",
            tickfont=dict(color="#263b63"),
            title_font=dict(color="#263b63")
        ),
        xaxis=dict(
            title="Quiz Attempts",
            tickfont=dict(color="#263b63"),
            title_font=dict(color="#263b63")
        ),
        margin=dict(l=45, r=20, t=35, b=50)
    )

    st.plotly_chart(fig, use_container_width=True)


# =====================================================
# GOOGLE LOGIN
# =====================================================

if not st.user.is_logged_in:

    st.markdown("""
    <div class="sg-banner">
        <h1>📚 StudyGenie</h1>
        <p>AI-Powered Personalized Learning Assistant</p>
    </div>
    """, unsafe_allow_html=True)

    st.title("Welcome to StudyGenie")

    st.write(
        "Sign in using your Google account to access "
        "your personalized learning dashboard."
    )

    st.button(
        "🌐 Continue with Google",
        on_click=st.login,
        args=("google",)
    )

    st.stop()


# =====================================================
# USER DETAILS
# =====================================================

user_email = st.user.email

user_name = (
    getattr(st.user, "name", None)
    or user_email.split("@")[0]
)

user_picture = getattr(st.user, "picture", None)

materials = load_materials(user_email)
attempts = load_attempts(user_email)


# =====================================================
# NAVIGATION STATE
# =====================================================

pages = [
    "Overview",
    "My Materials",
    "Take Quiz",
    "Performance",
    "AI Tutor",
    "My Progress"
]

# Apply pending navigation before creating radio widget.

if "next_navigation" in st.session_state:

    destination = st.session_state.pop("next_navigation")

    if destination in pages:
        st.session_state["main_navigation"] = destination

if "main_navigation" not in st.session_state:
    st.session_state["main_navigation"] = "Overview"


# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:

    st.title("📚 StudyGenie")
    st.caption("AI-Powered Personalized Learning")

    st.divider()

    if user_picture:
        st.image(user_picture, width=75)

    st.write(f"**{user_name}**")
    st.caption(user_email)

    st.success("Signed in with Google")

    st.divider()

    page = st.radio(
        "Navigation",
        pages,
        key="main_navigation",
        label_visibility="collapsed"
    )

    st.divider()

    if st.button("↪ Logout", use_container_width=True):
        st.logout()


# =====================================================
# OVERVIEW DASHBOARD
# =====================================================

if page == "Overview":

    total_materials = len(materials)
    total_quizzes = len(attempts)

    average = (
        sum(row[3] for row in attempts) / total_quizzes
        if total_quizzes else 0
    )

    st.markdown(f"""
    <div class="sg-banner">
        <h1>Welcome back, {user_name}! 👋</h1>
        <p>Your personal AI-powered learning dashboard.</p>
        <p>Upload materials, take quizzes, track your progress and learn with AI.</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("📚 Study Materials", total_materials)
    c2.metric("📝 Quizzes Completed", total_quizzes)
    c3.metric("🎯 Average Score", f"{average:.1f}%")
    c4.metric("🔥 Learning Streak", "Not tracked")

    st.write("")

    left, middle, right = st.columns([1, 1.2, 0.9])

    with left:

        st.markdown("### 🕒 Recent Activity")

        activities = []

        for item in materials[:3]:
            activities.append(
                (item[2], "📄 Material Uploaded", item[1])
            )

        for item in attempts[:3]:
            activities.append(
                (item[5], "✅ Quiz Completed", item[0])
            )

        activities.sort(
            key=lambda x: x[0] or "",
            reverse=True
        )

        if activities:

            for date, title, name in activities[:5]:

                st.markdown(f"""
                <div class="sg-card">
                    <b>{title}</b>
                    <p>{name}</p>
                    <small>{date}</small>
                </div>
                """, unsafe_allow_html=True)

        else:
            st.info("Your recent activity will appear here.")

    with middle:

        st.markdown("### 📊 Performance Overview")

        if attempts:
            show_score_chart(attempts)
        else:
            st.info("Complete quizzes to see your score trend.")

        st.markdown("#### Topic-wise Performance")

        totals = get_topic_totals(attempts)

        if totals:

            for topic, data in totals.items():

                percentage = (
                    data["correct"] / data["total"] * 100
                    if data["total"] else 0
                )

                st.write(f"**{topic} — {percentage:.0f}%**")
                st.progress(percentage / 100)

        else:
            st.caption("Topic progress appears after completing a quiz.")

    with right:

        st.markdown("### ⚡ Quick Actions")

        actions = [
            ("📄 My Materials", "My Materials"),
            ("📝 Take Quiz", "Take Quiz"),
            ("📊 Performance", "Performance"),
            ("🤖 AI Doubt Solver", "AI Tutor")
        ]

        for label, destination in actions:

            if st.button(
                label,
                key=f"quick_{destination}",
                use_container_width=True
            ):
                st.session_state["next_navigation"] = destination
                st.rerun()

        st.markdown("""
        <div class="sg-banner">
            <h3>🌱 Keep Going!</h3>
            <p>Every quiz, every lesson and every effort brings you closer to your goals.</p>
        </div>
        """, unsafe_allow_html=True)


# =====================================================
# MY MATERIALS
# =====================================================

elif page == "My Materials":

    st.title("📚 My Materials")
    st.write("Upload and manage your study documents.")

    uploaded_file = st.file_uploader(
        "Upload PDF, PPT, DOCX or TXT",
        type=["pdf", "pptx", "docx", "txt"]
    )

    if uploaded_file:

        if st.button("📥 Upload and Save Material"):

            with st.spinner("Extracting document text..."):

                try:

                    text = extract_text(uploaded_file)

                    if not text.strip():
                        st.error("No readable text found.")

                    else:

                        save_material(
                            user_email,
                            uploaded_file.name,
                            text
                        )

                        st.session_state["current_material_text"] = text
                        st.session_state["current_material_name"] = uploaded_file.name

                        st.session_state.pop("analysis", None)
                        st.session_state.pop("study_text", None)

                        st.success("Material uploaded successfully!")
                        st.rerun()

                except Exception as error:
                    st.error(f"Upload failed: {error}")

    st.divider()
    st.subheader("Your Documents")

    for material in materials:

        material_id, filename, uploaded_at = material

        with st.container(border=True):

            col1, col2, col3 = st.columns([4, 1, 1])

            with col1:
                st.write(f"📄 **{filename}**")
                st.caption(uploaded_at)

            with col2:

                if st.button("Open", key=f"open_{material_id}"):

                    selected = get_material(
                        user_email, material_id
                    )

                    if selected:

                        st.session_state["current_material_name"] = selected[0]
                        st.session_state["current_material_text"] = selected[1]

                        st.session_state.pop("analysis", None)
                        st.session_state.pop("study_text", None)

                        st.rerun()

            with col3:

                if st.button("Delete", key=f"delete_{material_id}"):

                    delete_material(user_email, material_id)
                    st.rerun()

    if not materials:
        st.info("No documents uploaded yet.")

    if "current_material_text" in st.session_state:

        st.divider()
        st.subheader("Selected Material")

        st.write(st.session_state["current_material_name"])

        with st.expander("Preview extracted content"):
            st.write(
                st.session_state["current_material_text"][:5000]
            )

        if st.button("🔍 Analyze Selected Material"):

            try:

                with st.spinner("AI is analyzing your material..."):

                    analysis = analyze_study_material(
                        st.session_state["current_material_text"]
                    )

                    st.session_state["analysis"] = analysis
                    st.session_state["study_text"] = st.session_state["current_material_text"]
                    st.session_state["source_name"] = st.session_state["current_material_name"]

                st.success("Analysis completed!")

            except Exception as error:
                st.error(f"Analysis failed: {error}")

        if "analysis" in st.session_state:

            st.subheader("📚 Identified Topics")

            analysis = st.session_state["analysis"]

            st.write(
                analysis.get("document_summary", "")
            )

            for topic in analysis.get("topics", []):

                st.markdown(
                    f"**{topic.get('name', 'Topic')}**"
                )

                for concept in topic.get("concepts", []):
                    st.write("• " + str(concept))


# =====================================================
# TAKE QUIZ
# =====================================================

elif page == "Take Quiz":

    st.title("📝 Take Quiz")

    if "study_text" not in st.session_state:

        st.info(
            "Open My Materials and analyze a document first."
        )

    else:

        st.success(
            f"Selected: {st.session_state.get('source_name', 'Study Material')}"
        )

        if st.button("🧠 Generate Diagnostic Quiz"):

            try:

                with st.spinner("Generating questions..."):

                    result = generate_diagnostic_quiz(
                        st.session_state["study_text"]
                    )

                    st.session_state["quiz"] = result["quiz"]
                    st.session_state.pop("results", None)

                st.success(
                    f"{len(result['quiz'])} questions generated!"
                )

            except Exception as error:
                st.error(f"Quiz generation failed: {error}")

    if "quiz" in st.session_state:

        with st.form("study_quiz"):

            answers = []

            for index, question in enumerate(
                st.session_state["quiz"]
            ):

                st.markdown(f"### Question {index + 1}")
                st.write(question["question"])

                answer = st.radio(
                    "Select answer",
                    question["options"],
                    index=None,
                    key=f"answer_{index}"
                )

                answers.append(answer)

            submitted = st.form_submit_button("Submit Quiz")

        if submitted:

            if any(answer is None for answer in answers):

                st.warning("Answer all questions before submitting.")

            else:

                score = 0
                topics = {}
                review = []

                for answer, question in zip(
                    answers, st.session_state["quiz"]
                ):

                    topic = question.get("topic", "General")

                    topics.setdefault(
                        topic,
                        {"correct": 0, "total": 0}
                    )

                    topics[topic]["total"] += 1

                    correct_answer = question["options"][
                        question["answer"]
                    ]

                    correct = answer == correct_answer

                    if correct:
                        score += 1
                        topics[topic]["correct"] += 1

                    review.append({
                        "question": question["question"],
                        "correct_answer": correct_answer,
                        "your_answer": answer,
                        "correct": correct
                    })

                total = len(answers)
                percentage = round(score / total * 100)

                result = {
                    "score": score,
                    "total": total,
                    "percentage": percentage,
                    "topics": topics
                }

                st.session_state["results"] = result

                save_attempt(
                    user_email,
                    st.session_state.get("source_name", ""),
                    result
                )

                st.success(
                    f"Your score: {score}/{total} ({percentage}%)"
                )

                st.balloons()

                for index, item in enumerate(review, 1):

                    st.write(
                        f"{'✅' if item['correct'] else '❌'} "
                        f"Q{index}: {item['question']}"
                    )

                    if not item["correct"]:
                        st.write(
                            f"Correct answer: {item['correct_answer']}"
                        )


# =====================================================
# PERFORMANCE
# =====================================================

elif page == "Performance":

    st.title("📊 Performance Dashboard")

    if not attempts:

        st.info("Complete a quiz to see your performance.")

    else:

        average = sum(row[3] for row in attempts) / len(attempts)

        c1, c2, c3 = st.columns(3)

        c1.metric("Total Quizzes", len(attempts))
        c2.metric("Average Score", f"{average:.1f}%")
        c3.metric("Latest Score", f"{attempts[0][3]:.0f}%")

        st.subheader("Quiz Score History")
        show_score_chart(attempts)

        st.subheader("Topic-wise Performance")

        totals = get_topic_totals(attempts)

        if totals:

            for topic, data in totals.items():

                percentage = (
                    data["correct"] / data["total"] * 100
                    if data["total"] else 0
                )

                st.write(
                    f"**{topic}: {mastery(percentage)} ({percentage:.0f}%)**"
                )

                st.progress(percentage / 100)

        st.subheader("Recent Results")

        for row in attempts:

            st.write(
                f"**{row[0]}** — {row[1]}/{row[2]} "
                f"({row[3]:.0f}%)"
            )

            st.caption(row[5])
            st.divider()


# =====================================================
# AI TUTOR / DOUBT SOLVER
# =====================================================

elif page == "AI Tutor":

    st.title("🤖 StudyGenie AI Doubt Solver")

    st.write(
        "Ask any academic question and get step-by-step explanations."
    )

    if "doubt_messages" not in st.session_state:
        st.session_state["doubt_messages"] = []

    if "study_text" in st.session_state:

        use_material = st.toggle(
            "Use my uploaded study material as reference",
            value=True
        )

        if use_material:
            st.success(
                "Your uploaded study material will be used as reference."
            )

    else:

        use_material = False

        st.info(
            "You can ask general academic questions. "
            "Analyze a document to ask questions based on your material."
        )

    col1, col2 = st.columns([4, 1])

    with col1:
        st.subheader("💬 Chat with StudyGenie")

    with col2:

        if st.button("🗑️ Clear Chat"):

            st.session_state["doubt_messages"] = []
            st.rerun()

    for message in st.session_state["doubt_messages"]:

        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input(
        "Ask your academic doubt here..."
    )

    if question:

        history = st.session_state["doubt_messages"].copy()

        st.session_state["doubt_messages"].append({
            "role": "user",
            "content": question
        })

        with st.chat_message("user"):
            st.markdown(question)

        material = (
            st.session_state.get("study_text", "")
            if use_material else ""
        )

        with st.chat_message("assistant"):

            with st.spinner("StudyGenie is thinking..."):

                try:

                    answer = ask_study_doubt(
                        question,
                        material,
                        history
                    )

                    st.markdown(answer)

                    st.session_state["doubt_messages"].append({
                        "role": "assistant",
                        "content": answer
                    })

                except Exception as error:

                    st.error(f"AI Tutor error: {error}")
                    st.session_state["doubt_messages"].pop()

    st.divider()

    st.caption(
        "StudyGenie AI Tutor • Ask follow-up questions and learn at your own pace."
    )


# =====================================================
# MY PROGRESS
# =====================================================

elif page == "My Progress":

    st.title("📈 My Learning Progress")

    if not attempts:

        st.info("Complete your first quiz to track your progress.")

    else:

        percentages = [
            row[3] for row in reversed(attempts)
        ]

        average = sum(percentages) / len(percentages)

        c1, c2 = st.columns(2)

        c1.metric("Total Quizzes", len(attempts))
        c2.metric("Overall Average", f"{average:.1f}%")

        if len(percentages) >= 2:

            improvement = percentages[-1] - percentages[0]

            if improvement > 0:
                st.success(
                    f"Your score improved by {improvement:.1f} percentage points!"
                )

            elif improvement < 0:
                st.info(
                    f"Your latest score is {abs(improvement):.1f} points lower than your first attempt."
                )

            else:
                st.info("Your score has remained unchanged.")

        st.subheader("Your Learning Journey")

        for index, row in enumerate(attempts, 1):

            with st.container(border=True):

                st.markdown(f"### Quiz Attempt {index}")

                st.write(f"Material: {row[0]}")
                st.write(f"Date: {row[5]}")
                st.write(f"Score: {row[1]}/{row[2]}")

                st.progress(
                    max(0.0, min(1.0, float(row[3]) / 100))
                )

                st.write(
                    f"{row[3]:.0f}% — {mastery(row[3])}"
                )
