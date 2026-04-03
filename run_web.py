import os
from flask import Flask, render_template, jsonify
from google.cloud import run_v2
from supabase import create_client, Client

app = Flask(__name__)
app.secret_key = "super-secret-poc-key"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://placeholder-project.supabase.co")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "placeholder-anon-key")
# supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


@app.route("/", methods=["GET"])
def index():
    """
    Route / (GET): Liefert die einfache HTML-Seite mit Bootstrap.
    """
    return render_template("index.html")


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
