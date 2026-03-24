import os
from flask import Flask, render_template_string, jsonify
from google.cloud import run_v2

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cloud Run PoC</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { 
            background-color: #f8f9fa; 
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }
        .card { 
            padding: 40px; 
            border-radius: 12px; 
            box-shadow: 0 10px 15px rgba(0,0,0,0.1); 
            text-align: center; 
            background: white;
            max-width: 500px;
            width: 100%;
        }
        .btn-start { 
            padding: 15px 30px; 
            font-size: 1.2rem; 
            margin-top: 20px; 
            transition: all 0.3s ease;
        }
        .btn-start:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,123,255,0.4);
        }
        #response-msg { 
            margin-top: 20px; 
            font-weight: 500; 
            min-height: 24px;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1 class="mb-3 text-primary">Cloud Run PoC</h1>
        <p class="text-muted">Startet den super dynamischen Cloud Run Worker-Job direkt aus dem Frontend.</p>
        <button id="start-btn" class="btn btn-primary btn-lg btn-start" onclick="startWorker()">Start Worker</button>
        <div id="response-msg"></div>
    </div>

    <script>
        async function startWorker() {
            const btn = document.getElementById('start-btn');
            const msg = document.getElementById('response-msg');
            
            // Ladezustand UI
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Starten...';
            msg.innerText = "";
            msg.className = "";

            try {
                const response = await fetch('/start-worker', { method: 'POST' });
                const data = await response.json();
                
                if (response.ok) {
                    msg.innerText = data.message || "Job erfolgreich gestartet!";
                    msg.className = "text-success";
                } else {
                    msg.innerText = "Fehler: " + (data.error || "Unbekannter Fehler");
                    msg.className = "text-danger";
                }
            } catch (error) {
                msg.innerText = "Netzwerkfehler: " + error.message;
                msg.className = "text-danger";
            } finally {
                // UI zurücksetzen
                btn.disabled = false;
                btn.innerText = "Start Worker";
            }
        }
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    """
    Route / (GET): Liefert die einfache HTML-Seite mit Bootstrap.
    """
    return render_template_string(HTML_TEMPLATE)

@app.route('/start-worker', methods=['POST'])
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
        request = run_v2.RunJobRequest(
            name=name,
            overrides=overrides
        )

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
