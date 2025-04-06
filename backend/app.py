from flask import Flask, request, jsonify,send_file
from flask_cors import CORS
from chatbot_agent import ask_llama
from reportlab.pdfgen import canvas
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit

app = Flask(__name__)
CORS(app)

# Convert short language codes to full language names
def get_language_name(code):
    return {
        "en": "English",
        "hi": "Hindi",
        "ta": "Tamil",
        "te": "Telugu",
        "kn": "Kannada"
    }.get(code, "English")

def create_chat_history(language="English"):
    return [
        {
            "role": "system",
            "content": f"You are a healthcare chatbot that helps rural users identify and apply for Indian government health schemes. Be simple and clear. Respond only in {language}."
        }
    ]

def generate_pdf(data, summary):
    if not os.path.exists("generated_reports"):
        os.makedirs("generated_reports")

    filename = f"{data['name'].replace(' ', '_')}_report.pdf"
    filepath = os.path.join("generated_reports", filename)

    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Health Report")

    y -= 30
    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Name: {data['name']}"); y -= 20
    c.drawString(50, y, f"Gender: {data['gender']}"); y -= 20
    c.drawString(50, y, f"Category: {data['category']}"); y -= 20
    c.drawString(50, y, f"Symptom: {data['symptom']}"); y -= 20
    c.drawString(50, y, f"Duration: {data['duration']}"); y -= 20
    c.drawString(50, y, f"Notes: {data.get('notes', '')}"); y -= 30

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "AI Summary:"); y -= 20

    c.setFont("Helvetica", 11)
    wrapped_lines = simpleSplit(summary, "Helvetica", 11, width - 100)

    for line in wrapped_lines:
        if y <= 50:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = height - 50
        c.drawString(50, y, line)
        y -= 15

    c.save()
    return filepath




@app.route("/start", methods=["GET"])
def start():
    first_question = "What is your age group?"
    options = ["Below 18", "18-40", "41-60", "Above 60"]
    return jsonify({"question": first_question, "options": options})

@app.route("/submit", methods=["POST"])
def submit():
    user_answer = request.json.get("answer")
    lang_code = request.json.get("lang", "en")  # Language code from Flutter

    language = get_language_name(lang_code)
    history = create_chat_history(language)
    history.append({"role": "user", "content": user_answer})

    reply = ask_llama(history)
    return jsonify({"question": reply, "options": []})


@app.route("/summary", methods=["POST"])
def generate_summary():
    data = request.json
    notes = data.get('notes', 'N/A')
    if notes:
        notes = notes.strip().replace('\n', ' ').replace('"', "'")
    else:
        notes = 'N/A'
    prompt = f"""
    You are a medical assistant. Based on the following patient information, generate a health report in three sections:

    1. **Problem Description**: Clearly define the possible health issue based on symptoms, duration, and gender.
    2. **Precautionary Measures**: List some immediate steps the patient can take to manage their symptoms.
    3. **Recommendations**: Suggest what the patient should do next, such as consulting a doctor, tests to consider, etc.

    ### Patient Information:
    - Category: {data['category']}
    - Symptom: {data['symptom']}
    - Duration: {data['duration']}
    - Gender: {data['gender']}
    - Notes: {notes}
    """

    messages = [
        {
            "role": "system",
            "content": "You are a medical assistant that creates a short and helpful health report summary based on patient input."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    print("📩 Prompt sent to LLaMA:", repr(prompt))
    summary = ask_llama(messages)
    print("🧠 AI Summary returned:", repr(summary))

    return jsonify({"summary": summary})


@app.route("/report", methods=["POST"])
def report():
    data = request.json
    summary = data.get("summary", "No AI summary available.")

    # Debug print to confirm summary is received
    print("📥 Received summary for PDF:")
    print(repr(summary))

    # Generate the PDF report
    pdf_path = generate_pdf(data, summary)

    # Check if PDF was created successfully
    if not os.path.exists(pdf_path):
        return {"error": "PDF generation failed."}, 500

    # Send the PDF as a downloadable file
    return send_file(pdf_path, as_attachment=True)



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

