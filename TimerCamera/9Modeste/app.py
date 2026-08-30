#!/usr/bin/env python3
"""
Application Flask SIMPLE - Affichage images ESP32 uniquement
"""
from flask import Flask, render_template, jsonify
import mariadb
import os
from datetime import datetime

app = Flask(__name__)

# Configuration BD
DB_CONFIG = {
    'host': 'localhost',
    'user': 'nichoir_user',
    'password': 'modeste123',
    'database': 'nichoir_db'
}

def get_db_connection():
    """Connexion à MariaDB"""
    try:
        return mariadb.connect(**DB_CONFIG)
    except mariadb.Error as e:
        print(f"❌ Erreur BD: {e}")
        return None

@app.route('/')
def index():
    """Page principale avec toutes les images"""
    conn = get_db_connection()
    if not conn:
        return "Erreur base de données", 500

    try:
        cursor = conn.cursor(dictionary=True)

        # Récupérer TOUTES les captures
        cursor.execute("""
            SELECT id, timestamp, image_path, battery_level,
                   motion_detected, device_id
            FROM captures
            ORDER BY timestamp DESC
        """)

        captures = cursor.fetchall()

        # Transformer les chemins pour le web
        for capture in captures:
            if capture['image_path']:
                capture['web_url'] = f"/static/{capture['image_path']}"
                capture['filename'] = capture['image_path'].split('/')[-1]
            else:
                capture['web_url'] = None

            # Dates formatées
            capture['date_full'] = capture['timestamp'].strftime('%d/%m/%Y à %H:%M')
            capture['time_ago'] = get_time_ago(capture['timestamp'])

        # Statistiques simples
        cursor.execute("SELECT COUNT(*) as total, AVG(battery_level) as avg_battery FROM captures")
        stats = cursor.fetchone()

        return render_template('index.html',
                             captures=captures,
                             total=stats['total'] if stats else 0,
                             avg_battery=round(stats['avg_battery'], 1) if stats and stats['avg_battery'] else 0)

    except mariadb.Error as e:
        return f"Erreur BD: {e}", 500
    finally:
        conn.close()

@app.route('/api/health')
def health():
    """API santé du système"""
    return jsonify({
        'status': 'online',
        'service': 'Nichoir Connecté',
        'timestamp': datetime.now().isoformat()
    })

def get_time_ago(timestamp):
    """Texte "il y a X temps" """
    now = datetime.now()
    diff = now - timestamp

    if diff.days > 30:
        months = diff.days // 30
        return f"il y a {months} mois"
    elif diff.days > 0:
        return f"il y a {diff.days} jour{'s' if diff.days > 1 else ''}"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"il y a {hours} heure{'s' if hours > 1 else ''}"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"il y a {minutes} minute{'s' if minutes > 1 else ''}"
    else:
        return "à l'instant"

if __name__ == '__main__':
    # Créer le dossier images
    os.makedirs("static/images", exist_ok=True)

    print("="*60)
    print("   NICHOR CONNECTÉ - Interface Simplifiée")
    print("="*60)
    print(f"📁 Dossier images: {os.path.abspath('static/images')}")
    print(f"🌐 Adresse: http://192.168.2.45:5000")
    print(f"📊 Base: {DB_CONFIG['database']}")
    print("="*60)

    app.run(host='0.0.0.0', port=5000, debug=True)