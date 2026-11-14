
import json
import re

from pypdf import PdfReader
from docx import Document
from pptx import Presentation
from ollama import chat


# CONFIGURATION

MODEL = "llama3.2:1b"
CHUNK_SIZE = 2500
CHUNK_OVERLAP = 200


# FILE EXTRACTION

def extract_text(uploaded_file):

    filename = uploaded_file.name.lower()

    try:

        if filename.endswith(".pdf"):

            reader = PdfReader(uploaded_file)
            pages = []

            for number, page in enumerate(reader.pages, 1):
                content = page.extract_text() or ""

                if content.strip():
                    pages.append(f"\n--- Page {number} ---\n{content}")

            return "\n".join(pages)

        elif filename.endswith(".pptx"):

            presentation = Presentation(uploaded_file)
            slides = []

            for number, slide in enumerate(presentation.slides, 1):

                content = []

                for shape in slide.shapes:

                    if hasattr(shape, "text") and shape.text.strip():
                        content.append(shape.text)

                    if shape.has_table:
                        for row in shape.table.rows:
                            content.append(
                                " | ".join(cell.text for cell in row.cells)
                            )

                slides.append(
                    f"\n--- Slide {number} ---\n" + "\n".join(content)
                )

            return "\n".join(slides)

        elif filename.endswith(".docx"):

            document = Document(uploaded_file)

            return "\n".join(
                p.text for p in document.paragraphs if p.text.strip()
            )

        elif filename.endswith(".txt"):

            return uploaded_file.getvalue().decode(
                "utf-8", errors="replace"
            )

        raise ValueError("Unsupported file format.")

    except Exception as error:
        raise RuntimeError(f"Text extraction failed: {error}")


# CHUNKING

def split_into_chunks(text):

    if not text or not text.strip():
        return []

    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    chunks = []
    start = 0

    while start < len(text):

        end = min(start + CHUNK_SIZE, len(text))

        if end < len(text):

            boundary = max(
                text.rfind("\n", start, end),
                text.rfind(". ", start, end),
                text.rfind("! ", start, end),
                text.rfind("? ", start, end)
            )

            if boundary > start + CHUNK_SIZE // 2:
                end = boundary + 1

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(end - CHUNK_OVERLAP, start + 1)

    return chunks


# JSON PARSING

def parse_json_response(response):

    if isinstance(response, dict):
        return response

    if not isinstance(response, str):
        raise ValueError("Invalid AI response.")

    response = response.strip()

    response = re.sub(
        r"^```(?:json)?\s*", "", response,
        flags=re.IGNORECASE
    )

    response = re.sub(r"\s*```$", "", response)

    try:
        return json.loads(response)

    except json.JSONDecodeError:

        match = re.search(r"\{.*\}", response, re.DOTALL)

        if match:
            return json.loads(match.group(0))

        raise ValueError("AI did not return valid JSON.")


# GENERAL AI REQUEST

def ask_ai(prompt):

    try:

        response = chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            format="json",
            options={
                "temperature": 0.2,
                "num_ctx": 4096
            }
        )

        return parse_json_response(
            response["message"]["content"]
        )

    except Exception as error:
        raise RuntimeError(f"Ollama request failed: {error}")


# DOCUMENT CHUNK ANALYSIS

def analyze_chunk(chunk, number, total):

    prompt = f"""
Analyze section {number} of {total} of a student's document.

CONTENT:
{chunk}

Return JSON:
{{
  "topics": [
    {{
      "name": "Main topic",
      "concepts": ["Subtopic 1", "Subtopic 2"]
    }}
  ],
  "summary": "Section summary"
}}

Extract only topics actually present. Return JSON only.
"""

    result = ask_ai(prompt)

    topics = result.get("topics", [])

    if not isinstance(topics, list):
        topics = []

    return {
        "topics": topics,
        "summary": str(result.get("summary", ""))
    }


# MERGE TOPICS

def merge_topics(all_topics):

    merged = {}

    for topic in all_topics:

        if not isinstance(topic, dict):
            continue

        name = str(topic.get("name", "")).strip()

        if not name:
            continue

        key = name.lower()

        if key not in merged:
            merged[key] = {
                "name": name,
                "concepts": []
            }

        concepts = topic.get("concepts", [])

        if isinstance(concepts, str):
            concepts = [concepts]

        if not isinstance(concepts, list):
            continue

        for concept in concepts:

            concept = str(concept).strip()

            existing = [
                x.lower() for x in merged[key]["concepts"]
            ]

            if concept and concept.lower() not in existing:
                merged[key]["concepts"].append(concept)

    return list(merged.values())


# COMPLETE DOCUMENT ANALYSIS

def analyze_study_material(study_text):

    chunks = split_into_chunks(study_text)

    if not chunks:
        raise ValueError("No readable study material found.")

    all_topics = []
    summaries = []

    for index, chunk in enumerate(chunks, 1):

        result = analyze_chunk(chunk, index, len(chunks))

        all_topics.extend(result["topics"])

        if result["summary"]:
            summaries.append(result["summary"])

    return {
        "document_summary": " ".join(summaries),
        "topics": merge_topics(all_topics),
        "total_chunks": len(chunks)
    }


# QUIZ GENERATION

def generate_chunk_quiz(chunk, number, total):

    prompt = f"""
Create 3 multiple-choice questions from section {number} of {total}.

CONTENT:
{chunk}

Return JSON:
{{
  "quiz": [
    {{
      "question": "Question",
      "options": ["A", "B", "C", "D"],
      "answer": 0,
      "topic": "Topic name"
    }}
  ]
}}

Use exactly four options. Answer must be a zero-based integer.
Return JSON only.
"""

    result = ask_ai(prompt)
    questions = result.get("quiz", [])

    if not isinstance(questions, list):
        return []

    valid = []

    for q in questions:

        if not isinstance(q, dict):
            continue

        options = q.get("options", [])

        if not isinstance(options, list) or len(options) != 4:
            continue

        try:
            answer = int(q.get("answer", -1))
        except (ValueError, TypeError):
            continue

        if not 0 <= answer < 4:
            continue

        valid.append({
            "question": str(q.get("question", "")),
            "options": [str(x) for x in options],
            "answer": answer,
            "topic": str(q.get("topic", "General"))
        })

    return valid


def generate_diagnostic_quiz(study_text):

    chunks = split_into_chunks(study_text)

    if not chunks:
        raise ValueError("No study material available.")

    all_questions = []

    for index, chunk in enumerate(chunks, 1):

        questions = generate_chunk_quiz(
            chunk, index, len(chunks)
        )

        all_questions.extend(questions)

    if not all_questions:
        raise ValueError("No valid quiz questions were generated.")

    return {"quiz": all_questions}


# PERSONALIZED LESSON

def generate_personalized_learning(
    study_text, topic, performance_level
):

    chunks = split_into_chunks(study_text)

    relevant = [
        chunk for chunk in chunks
        if topic.lower() in chunk.lower()
    ]

    if not relevant:
        relevant = chunks[:3]

    material = "\n\n".join(relevant)[:6000]

    prompt = f"""
You are StudyGenie, an expert academic tutor.

Create a detailed lesson for: {topic}
Student performance: {performance_level}

Study material:
{material}

Return JSON:
{{
  "topic": "{topic}",
  "explanation": "Detailed explanation with introduction, definitions, subheadings and steps.",
  "important_points": [
    "Point 1", "Point 2", "Point 3", "Point 4", "Point 5"
  ],
  "example": "A clear example",
  "practice_questions": [
    "Question 1", "Question 2", "Question 3",
    "Question 4", "Question 5"
  ]
}}

Use beginner-friendly language. Do not invent facts.
Return JSON only.
"""

    result = ask_ai(prompt)

    result.setdefault("topic", topic)
    result.setdefault("explanation", "")
    result.setdefault("important_points", [])
    result.setdefault("example", "")
    result.setdefault("practice_questions", [])

    for field in ["important_points", "practice_questions"]:

        if isinstance(result[field], str):
            result[field] = [result[field]]

        if not isinstance(result[field], list):
            result[field] = []

        result[field] = [str(x) for x in result[field]]

    result["topic"] = str(result["topic"])
    result["explanation"] = str(result["explanation"])
    result["example"] = str(result["example"])

    if not result["explanation"].strip():
        raise ValueError("AI did not generate a lesson explanation.")

    return result


# AI DOUBT SOLVER

def ask_study_doubt(question, study_material="", chat_history=None):

    if not question.strip():
        return "Please enter a question."

    messages = [
        {
            "role": "system",
            "content": """
You are StudyGenie, a friendly and knowledgeable AI tutor.

Help students understand academic concepts.

Instructions:
1. Explain in simple beginner-friendly language.
2. Give step-by-step explanations.
3. Provide examples wherever useful.
4. Explain programming code line by line when requested.
5. Answer follow-up questions using conversation history.
6. Use headings and bullet points where helpful.
7. Prioritize uploaded study material when provided.
8. Clearly distinguish general knowledge from information
   supported by the uploaded material.
9. If you are unsure, say so instead of inventing facts.
10. Be helpful, clear and encouraging.
"""
        }
    ]

    if study_material:

        messages.append({
            "role": "system",
            "content": (
                "Use this uploaded material as the primary reference "
                "for questions about the student's document:\n\n"
                + study_material[:12000]
            )
        })

    if chat_history:

        for item in chat_history[-10:]:

            if item.get("role") in ["user", "assistant"]:

                messages.append({
                    "role": item["role"],
                    "content": item["content"]
                })

    messages.append({
        "role": "user",
        "content": question
    })

    try:

        response = chat(
            model=MODEL,
            messages=messages,
            options={
                "temperature": 0.4,
                "num_ctx": 8192
            }
        )

        return response["message"]["content"]

    except Exception as error:
        raise RuntimeError(f"AI Tutor error: {error}")
