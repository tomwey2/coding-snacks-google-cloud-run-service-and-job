import os
from flask import Flask, render_template, jsonify, request, redirect, session, flash
from google.cloud import run_v2
from supabase import create_client, Client, ClientOptions
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "super-secret-poc-key"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://placeholder-project.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "placeholder-key")


def get_supabase_client() -> Client:
    """
    Creates for each request a fresh, secure client.
    If the user is logged in, their personal token is injected.
    """
    access_token = session.get("access_token")

    if access_token:
        # Personalized client for logged-in users (RLS applies!)
        options = ClientOptions(headers={"Authorization": f"Bearer {access_token}"})
        return create_client(SUPABASE_URL, SUPABASE_KEY, options=options)
    else:
        # Anonymous client for guests (e.g. for login/signup)
        return create_client(SUPABASE_URL, SUPABASE_KEY)


@app.route("/", methods=["GET"])
def index():
    """
    Route / (GET): Liefert die einfache HTML-Seite mit Bootstrap.
    """
    return render_template("index.html")


@app.route("/get-data", methods=["GET"])
def get_data():
    if not session.get("user"):
        return redirect("/login")

    try:
        db = get_supabase_client()
        response = db.table("issues").select("name, created_at").execute()
        return render_template("index.html", issues=response.data)
    except Exception as e:
        flash(f"Error fetching data: {e}", "danger")
        return render_template("index.html", issues=[])


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        db = get_supabase_client()
        email = request.form.get("email")
        password = request.form.get("password")
        try:
            db.auth.sign_up({"email": email, "password": password})
            flash("Registration successful! You can now log in.", "success")
            return redirect("/login")
        except Exception as e:
            flash(f"Error during registration: {e}", "danger")

    return render_template("auth.html", action="signup")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        db = get_supabase_client()
        email = request.form.get("email")
        password = request.form.get("password")
        try:
            res = db.auth.sign_in_with_password({"email": email, "password": password})
            session["user"] = res.user.id
            session["access_token"] = res.session.access_token
            flash("Successfully logged in!", "success")
            return redirect("/")
        except Exception as e:
            flash(f"Error during login: {e}", "danger")

    return render_template("auth.html", action="login")


@app.route("/logout", methods=["GET"])
def logout():
    db = get_supabase_client()
    db.auth.sign_out()
    session.clear()
    flash("Successfully logged out.", "success")
    return redirect("/")


@app.route("/start-worker", methods=["POST"])
def start_worker():
    """
    Route /start-worker (POST): Startet asynchron den Cloud Run Job
    `poc-worker-job` und übergibt die Umgebungsvariable `TEST_INPUT`.
    """
    try:
        # Initialisiere den Cloud Run Jobs Client
        # Die Authentifizierung mit Google Cloud (Application Default Credentials)
        # muss zuvor in der lokalen Umgebung (z.B. per `gcloud auth application-default login`)
        # eingerichtet worden sein.
        client = run_v2.JobsClient()

        # Konfigurationen aus Umgebungsvariablen laden (mit sinnvollen Fallbacks für lokales Testing)
        # Für einen echten Einsatz müssen GOOGLE_CLOUD_PROJECT und GOOGLE_CLOUD_REGION gesetzt werden.
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "cleankoda-poc")
        region = os.environ.get("GOOGLE_CLOUD_REGION", "europe-west3")
        job_id = "poc-worker-job"

        # Den Full-Resource Name des Cloud Run Jobs zusammenbauen
        name = f"projects/{project_id}/locations/{region}/jobs/{job_id}"

        # Override für die Umgebungsvariable erstellen, die dem Container übergeben wird
        env_var = run_v2.EnvVar(name="TEST_INPUT", value="Hello from Flask UI!")

        # Container-Override kapselt unser EnvVar
        container_override = run_v2.RunJobRequest.Overrides.ContainerOverride(
            env=[env_var]
        )

        # Laufzeit-Overrides kapseln den Container-Override
        overrides = run_v2.RunJobRequest.Overrides(
            container_overrides=[container_override]
        )

        # Den eigentlichen Request zum Starten des Jobs konfigurieren
        request = run_v2.RunJobRequest(name=name, overrides=overrides)

        # Job in der Google Cloud asynchron auslösen.
        # run_job() ist ein asynchroner API-Call auf Google-Seite (gibt Object des Typs Operation zurück).
        # Wir warten nicht auf den Abschluss (client.run_job(...).result()), da der Job autonom arbeiten soll.
        operation = client.run_job(request=request)

        # Direkt dem Frontend Erfolg melden
        return jsonify({"status": "success", "message": "Job gestartet!"}), 200

    except Exception as e:
        # Im Fehlerfall (z.B. falsche Projekt-ID, fehlende Berechtigungen, Job existiert nicht)
        # werfen wir einen 500er Fehler für das UI.
        app.logger.error(f"Fehler beim Starten des Jobs: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


if __name__ == "__main__":
    # Starten der App beim lokalen Aufruf von `python run_web.py`
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
