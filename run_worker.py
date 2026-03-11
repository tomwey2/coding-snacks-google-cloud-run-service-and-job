import os
import sys
import time

def main():
    """
    Simples, autonomes Python-Skript (Worker).
    Es wird per Cloud Run Job einmalig ausgeführt und beendet sich selbst.
    """
    
    # 1. Umgebungsvariable TEST_INPUT einlesen
    # Fallback nutzen, falls sie nicht (z.B. lokal ohne Override) gesetzt ist
    test_input = os.environ.get("TEST_INPUT", "Kein Input empfangen (Fallback)")
    
    # 2. Startmeldung printen (wird im Cloud Build/Logging sichtbar)
    print(f"Worker gestartet. Empfangener Input: {test_input}")
    
    # 3. 10 Sekunden lang "Arbeiten" (Warten)
    print("Starte Arbeit (warte 10 Sekunden)...")
    time.sleep(10)
    
    # 4. Endmeldung printen
    print("10 Sekunden vergangen. Arbeit erfolgreich beendet.")
    
    # 5. Skript sauber mit Status-Code 0 (Erfolg) beenden
    sys.exit(0)

if __name__ == "__main__":
    main()
