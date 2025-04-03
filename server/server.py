# === FLASK BACKEND (server.py) ===
from flask import Flask, request, jsonify, make_response, send_from_directory
import sqlite3
from rapidfuzz import fuzz
from flask_cors import CORS
import logging
import os

app = Flask(__name__, static_folder='../client/build', static_url_path='/')
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Symptom Normalization Dictionary ===
SYMPTOM_NORMALIZATION_DICT = {
    "tingling": "paresthesia",
    "numbness": "hypoesthesia",
    "burning": "burning sensation",
    "itching": "pruritus",
    "itchiness": "pruritus",
    "swelling": "edema",
    "redness": "erythema",
    "blue skin": "cyanosis",
    "pale skin": "pallor",
    "blisters": "vesicles",
    "welts": "urticaria",
    "hives": "urticaria",
    "rash": "dermatitis",
    "pain": "localized pain",
    "muscle pain": "myalgia",
    "joint pain": "arthralgia",
    "abdominal pain": "abdominal cramps",
    "headache": "cephalalgia",
    "dizziness": "vertigo",
    "nausea": "nausea",
    "vomiting": "emesis",
    "diarrhea": "diarrhea",
    "fainting": "syncope",
    "shortness of breath": "dyspnea",
    "trouble breathing": "dyspnea",
    "difficulty breathing": "dyspnea",
    "rapid heartbeat": "tachycardia",
    "slow heartbeat": "bradycardia",
    "high blood pressure": "hypertension",
    "low blood pressure": "hypotension",
    "convulsions": "seizures",
    "shaking": "tremors",
    "muscle spasms": "spasms",
    "paralysis": "paralysis",
    "sweating": "diaphoresis",
    "confusion": "disorientation",
    "hallucinations": "visual disturbances",
    "chills": "shivering",
    "fever": "pyrexia",
    "blurred vision": "vision disturbances",
    "drooping eyelids": "ptosis",
    "excessive salivation": "hypersalivation",
    "difficulty swallowing": "dysphagia",
    "difficulty speaking": "dysarthria",
    "loss of coordination": "ataxia",
    "muscle weakness": "muscular weakness",
    "chest tightness": "chest discomfort",
    "cyanotic lips": "cyanosis"
}

def normalize_user_input(text):
    words = text.lower().split()
    return ' '.join(SYMPTOM_NORMALIZATION_DICT.get(word, word) for word in words)


def fuzzy_match(symptoms_list, text):
    score = 0
    for symptom in symptoms_list:
        score += fuzz.partial_ratio(symptom.lower(), text.lower())
    return score


def infer_species_and_treatment(user_symptoms):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(os.path.join(BASE_DIR, "knowledge-base.db"))
    cursor = conn.cursor()
    normalized_input = normalize_user_input(user_symptoms)
    symptoms_list = normalized_input.split()

    cursor.execute("""
        SELECT es.species_id, es.reference_id, es.symptom, es.onset_time, es.duration
        FROM Envenomation_Symptoms es
    """)
    rows = cursor.fetchall()

    if not rows:
        conn.close()
        return []

    probable_species = []
    for row in rows:
        species_id, reference_id, symptom, onset_time, duration = row
        combined_text = f"{symptom} {onset_time or ''} {duration or ''}"
        match_score = fuzzy_match(symptoms_list, combined_text)
        if match_score > 30:
            probable_species.append({
                "species_id": species_id,
                "reference_id": reference_id,
                "symptom": symptom,
                "onset_time": onset_time,
                "duration": duration,
                "match_score": match_score
            })

    probable_species.sort(key=lambda x: x["match_score"], reverse=True)

    results = []
    for species in probable_species:
        species_id = species["species_id"]
        reference_id = species["reference_id"]

        cursor.execute("""
            SELECT common_name FROM Common_Names
            WHERE species_id = ? AND reference_id = ? LIMIT 1
        """, (species_id, reference_id))
        common_name = cursor.fetchone()

        cursor.execute("SELECT picture FROM Species WHERE species_id = ?", (species_id,))
        picture_row = cursor.fetchone()
        img_path = '/' + picture_row[0] if picture_row and picture_row[0] else None

        cursor.execute("SELECT doi FROM References_Table WHERE reference_id = ?", (reference_id,))
        ref_row = cursor.fetchone()
        reference = ref_row[0] if ref_row else None

        cursor.execute("""
            SELECT first_aid, hospital_treatment, prognosis
            FROM Treatment_Protocols
            WHERE species_id = ? AND reference_id = ?
        """, (species_id, reference_id))
        treatment_data = cursor.fetchone()

        results.append({
            "common_name": common_name[0] if common_name else "Unknown",
            "image": img_path,
            "match_score": round(species["match_score"], 2),
            "symptom": species["symptom"],
            "onset_time": species["onset_time"],
            "duration": species["duration"],
            "reference": reference,
            "doi_url": f"https://dx.doi.org/{reference}" if reference else None,
            "first_aid": treatment_data[0] if treatment_data else None,
            "hospital_treatment": treatment_data[1] if treatment_data else None,
            "prognosis": treatment_data[2] if treatment_data else None
        })

    conn.close()
    return results


@app.route('/api/infer', methods=['POST', 'OPTIONS'])
def infer():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        return response, 200

    data = request.get_json()
    if not data or 'symptoms' not in data:
        return jsonify({'error': 'Missing symptoms in request'}), 400
    symptoms = data['symptoms']
    result = infer_species_and_treatment(symptoms)
    return jsonify(result), 200


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')
