from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import psycopg2.pool
import os
import uuid
import base64
import re
from datetime import datetime, date
import traceback

app = Flask(__name__)
CORS(app, origins=[
    "https://vetovo.in",
    "https://www.vetovo.in",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5500"
])

DB_CONFIG = {
    "dbname": "vetovo",
    "user": "animitr",
    "password": "Animitr2026",
    "host": "127.0.0.1",
    "port": 5432
}

# Connection pool — initialized at module load so Gunicorn workers can use)
def get_db():
    return psycopg2.connect(**DB_CONFIG)

def release_db(conn):
    conn.close()


def validate_whatsapp(number):
    cleaned = re.sub(r'\D', '', str(number))
    if cleaned.startswith('91') and len(cleaned) == 12:
        cleaned = cleaned[2:]
    return len(cleaned) == 10 and cleaned[0] in '6789'


def save_file_locally(base64_data, filename, subfolder):
    try:
        upload_dir = f"/home/ubuntu/vetovo/uploads/{subfolder}"
        os.makedirs(upload_dir, exist_ok=True)

        if ',' in base64_data:
            base64_data = base64_data.split(',')[1]

        file_bytes = base64.b64decode(base64_data)
        safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        filepath = os.path.join(upload_dir, safe_name)

        with open(filepath, 'wb') as f:
            f.write(file_bytes)

        return f"/uploads/{subfolder}/{safe_name}"
    except Exception as e:
        print(f"File save error: {e}")
        return None


def schedule_reminders(conn, vetovo_id, whatsapp, pet_name, vaccinations):
    try:
        cur = conn.cursor()
        today = date.today()

        for vax in vaccinations:
            next_due = vax.get('next_due') or vax.get('vnd') or vax.get('next')
            vax_name = vax.get('name') or vax.get('vaccine_name', 'Vaccination')

            if not next_due:
                continue

            try:
                due = datetime.strptime(next_due, '%Y-%m-%d').date()
                if due > today:
                    cur.execute("""
                        INSERT INTO reminders
                            (vetovo_id, whatsapp, pet_name, vaccine_name, due_date)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (vetovo_id, whatsapp, pet_name, vax_name, due))
            except ValueError:
                continue

        conn.commit()
        cur.close()
    except Exception as e:
        print(f"Reminder scheduling error: {e}")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "vetovo", "timestamp": datetime.now().isoformat()})


@app.route("/pets/create", methods=["POST"])
def create_pet():
    conn = None
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "No data received"}), 400

        owner_name = str(data.get("owner_name", "")).strip()
        owner_whatsapp = str(data.get("owner_whatsapp", "")).strip()
        pet_name = str(data.get("pet_name", "")).strip()

        errors = []
        if not pet_name:
            errors.append("Pet name is required")
        if not owner_name:
            errors.append("Owner name is required")
        if not owner_whatsapp or not validate_whatsapp(owner_whatsapp):
            errors.append("Valid 10-digit Indian mobile number is required")

        if errors:
            return jsonify({"error": "; ".join(errors)}), 400

        vetovo_id = "VTV-" + uuid.uuid4().hex[:8].upper()

        pet_photo_path = None
        cert_paths = []

        pet_photo_b64 = data.get("pet_photo")
        if pet_photo_b64:
            ext = "jpg"
            if "png" in str(data.get("pet_photo_type", "")).lower():
                ext = "png"
            filename = f"{vetovo_id}_photo.{ext}"
            pet_photo_path = save_file_locally(pet_photo_b64, filename, vetovo_id)

        cert_files = data.get("cert_files", [])
        for i, cf in enumerate(cert_files):
            cf_data = cf.get("dataUrl") or cf.get("data", "")
            cf_name = cf.get("name", f"cert_{i+1}.jpg")
            path = save_file_locally(cf_data, f"{vetovo_id}_cert_{i+1}_{cf_name}", vetovo_id)
            if path:
                cert_paths.append({"path": path, "name": cf_name})

        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO pets (
                vetovo_id, pet_name, species, breed, dob, gender,
                weight, color, microchip,
                owner_name, owner_whatsapp, owner_email,
                owner_city, owner_address, owner_pincode, emergency_contact,
                vaccinations, deworming, flea_treatment, medical_history,
                sterilised, sterilise_date, sterilise_clinic, sterilise_vet,
                insurance, pet_photo_path, cert_paths
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,
                %s,%s,%s,%s,
                %s,%s,%s
            ) RETURNING vetovo_id
        """, (
            vetovo_id,
            pet_name,
            data.get("species", ""),
            data.get("breed", ""),
            data.get("dob", ""),
            data.get("gender", ""),
            data.get("weight", ""),
            data.get("color", ""),
            data.get("microchip", ""),
            owner_name,
            owner_whatsapp,
            data.get("owner_email", ""),
            data.get("owner_city", ""),
            data.get("owner_address", ""),
            data.get("owner_pincode", ""),
            data.get("emergency_contact", ""),
            psycopg2.extras.Json(data.get("vaccinations", [])),
            psycopg2.extras.Json(data.get("deworming", {})),
            psycopg2.extras.Json(data.get("flea_treatment", {})),
            psycopg2.extras.Json(data.get("medical_history", {})),
            data.get("sterilised", ""),
            data.get("sterilise_date", ""),
            data.get("sterilise_clinic", ""),
            data.get("sterilise_vet", ""),
            psycopg2.extras.Json(data.get("insurance", {})),
            pet_photo_path,
            psycopg2.extras.Json(cert_paths)
        ))

        result = cur.fetchone()
        conn.commit()

        vaccinations = data.get("vaccinations", [])
        if vaccinations and owner_whatsapp:
            schedule_reminders(conn, vetovo_id, owner_whatsapp, pet_name, vaccinations)

        cur.close()

        return jsonify({
            "success": True,
            "vetovo_id": vetovo_id,
            "url": f"https://vetovo.in/pets/{vetovo_id}"
        })

    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        print(f"DB integrity error: {e}")
        return jsonify({"error": "A record with this ID already exists. Please try again."}), 409
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"create_pet error: {traceback.format_exc()}")
        return jsonify({"error": "Something went wrong. Please try again."}), 500
    finally:
        if conn:
            release_db(conn)


@app.route("/pets/<vetovo_id>", methods=["GET"])
def get_pet(vetovo_id):
    if not re.match(r'^VTV-[A-Z0-9]{8}$', vetovo_id):
        return jsonify({"error": "Invalid health card ID"}), 400

    conn = None
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT vetovo_id, pet_name, species, breed, dob, gender,
                   weight, color, microchip,
                   owner_name, owner_whatsapp, owner_city,
                   vaccinations, deworming, flea_treatment,
                   medical_history, sterilised, sterilise_date,
                   sterilise_clinic, insurance, pet_photo_path,
                   cert_paths, created_at
            FROM pets WHERE vetovo_id = %s
        """, (vetovo_id,))
        pet = cur.fetchone()
        cur.close()

        if not pet:
            return jsonify({"error": "Health card not found"}), 404

        pet_dict = dict(pet)
        if pet_dict.get("created_at"):
            pet_dict["created_at"] = pet_dict["created_at"].isoformat()

        return jsonify(pet_dict)

    except Exception as e:
        print(f"get_pet error: {traceback.format_exc()}")
        return jsonify({"error": "Something went wrong. Please try again."}), 500
    finally:
        if conn:
            release_db(conn)


@app.route("/reminders/due", methods=["GET"])
def get_due_reminders():
    if request.remote_addr not in ['127.0.0.1', 'localhost']:
        return jsonify({"error": "Unauthorized"}), 403

    conn = None
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT * FROM reminders
            WHERE due_date = CURRENT_DATE + INTERVAL '3 days'
            AND sent = FALSE
        """)
        reminders = [dict(r) for r in cur.fetchall()]
        cur.close()
        return jsonify({"reminders": reminders, "count": len(reminders)})
    except Exception as e:
        print(f"reminders error: {traceback.format_exc()}")
        return jsonify({"error": "Something went wrong"}), 500
    finally:
        if conn:
            release_db(conn)


@app.route("/reminders/<int:reminder_id>/sent", methods=["POST"])
def mark_reminder_sent(reminder_id):
    if request.remote_addr not in ['127.0.0.1', 'localhost']:
        return jsonify({"error": "Unauthorized"}), 403

    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE reminders SET sent = TRUE WHERE id = %s", (reminder_id,))
        conn.commit()
        cur.close()
        return jsonify({"success": True})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            release_db(conn)

@app.route("/admin/pets", methods=["GET"])
def admin_get_pets():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT vetovo_id, pet_name, species, breed, gender,
                   owner_name, owner_whatsapp, owner_city, created_at
            FROM pets ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        pets = []
        for r in rows:
            pets.append({
                "vetovo_id": r[0],
                "pet_name": r[1],
                "species": r[2],
                "breed": r[3],
                "gender": r[4],
                "owner_name": r[5],
                "owner_whatsapp": r[6],
                "owner_city": r[7],
                "created_at": r[8].isoformat() if r[8] else None
            })
        return jsonify(pets)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=6000, debug=False)
