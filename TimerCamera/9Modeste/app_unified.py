#!/usr/bin/env python3
"""
NICHOIR CONNECTÉ - Système complet
Combinaison du listener MQTT et de l'application Flask
"""
import paho.mqtt.client as mqtt
import mariadb
import json
from datetime import datetime
import os
import sys
import threading
from flask import Flask, render_template, jsonify

# ===== CONFIGURATION =====
# Configuration MQTT
MQTT_BROKER = "192.168.2.45"
MQTT_PORT = 1883
MQTT_TOPIC_IMAGE = "nichoir/camera/image"
MQTT_TOPIC_METADATA = "nichoir/camera/metadata"

# Configuration Base de Données
DB_CONFIG = {
    'host': 'localhost',
    'user': 'nichoir_user',
    'password': 'modeste123',
    'database': 'nichoir_db'
}

# Configuration Chemins
WEB_STATIC_DIR = "/home/modeste/nichoir_projet/web/static"
IMAGE_DIR = os.path.join(WEB_STATIC_DIR, "images")
DEVICE_ID = "M5_TimerCAM_01"

# ===== VARIABLES GLOBALES =====
image_buffer = bytearray()
current_metadata = {}
db_conn = None
mqtt_client = None

# ===== APPLICATION FLASK =====
app = Flask(__name__)

def init_database():
    """Initialise la connexion à MariaDB"""
    global db_conn
    try:
        db_conn = mariadb.connect(**DB_CONFIG)
        print("✅ Connecté à MariaDB")
        return True
    except mariadb.Error as e:
        print(f"❌ Erreur MariaDB: {e}")
        return False

# ===== FONCTIONS MQTT =====
def save_image_to_disk(image_data, filename):
    """Sauvegarde l'image dans le dossier web/static/images/"""
    try:
        os.makedirs(IMAGE_DIR, exist_ok=True)
        filepath = os.path.join(IMAGE_DIR, filename)

        with open(filepath, 'wb') as f:
            f.write(image_data)

        print(f"💾 Image sauvegardée: {filepath}")
        return f"images/{filename}"

    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")
        return None

def save_image_to_db(image_data, metadata):
    """Sauvegarde dans la base avec chemin relatif"""
    try:
        cursor = db_conn.cursor()

        # Nom de fichier
        timestamp = datetime.now()
        filename = f"nichoir_{metadata.get('photo_id', 0)}_{int(timestamp.timestamp())}.jpg"

        # Sauvegarde disque (retourne chemin relatif)
        relative_path = save_image_to_disk(image_data, filename)

        if not relative_path:
            return False

        # Insertion BD avec chemin relatif
        query = """
            INSERT INTO captures
            (timestamp, image_path, battery_level, motion_detected, device_id)
            VALUES (?, ?, ?, ?, ?)
        """

        cursor.execute(query, (
            timestamp,
            relative_path,  # Chemin relatif: "images/filename.jpg"
            metadata.get('battery', 0),
            0,  # motion_detected = 0 (capture auto)
            DEVICE_ID
        ))

        db_conn.commit()
        image_id = cursor.lastrowid
        cursor.close()

        print(f"✅ BD: ID {image_id} - Chemin: {relative_path}")
        return True

    except mariadb.Error as e:
        print(f"❌ Erreur BD: {e}")
        db_conn.rollback()
        return False

def mqtt_on_connect(client, userdata, flags, rc):
    """Callback connexion MQTT"""
    if rc == 0:
        print("✅ Connecté au broker MQTT")
        client.subscribe(MQTT_TOPIC_IMAGE)
        client.subscribe(MQTT_TOPIC_METADATA)
        print(f"📡 Topics: {MQTT_TOPIC_IMAGE}, {MQTT_TOPIC_METADATA}")
    else:
        print(f"❌ Échec MQTT: {rc}")

def mqtt_on_message(client, userdata, msg):
    """Callback réception messages MQTT"""
    global image_buffer, current_metadata

    if msg.topic == MQTT_TOPIC_METADATA:
        try:
            metadata = json.loads(msg.payload.decode())

            if 'status' in metadata and metadata['status'] == 'complete':
                # Image complète
                print(f"\n📸 Image complète ({len(image_buffer)} octets)")

                if len(image_buffer) > 0:
                    save_image_to_db(bytes(image_buffer), current_metadata)

                image_buffer = bytearray()
                current_metadata = {}
                print("─" * 60)

            else:
                # Métadonnées
                current_metadata = metadata
                print(f"\n{'='*60}")
                print(f"📋 Capture #{metadata.get('photo_id')}")
                print(f"   Batterie: {metadata.get('battery')}%")

        except Exception as e:
            print(f"❌ Erreur métadonnées: {e}")

    elif msg.topic == MQTT_TOPIC_IMAGE:
        image_buffer.extend(msg.payload)
        print(f"📦 Morceau: {len(msg.payload)} octets (total: {len(image_buffer)})")

def start_mqtt_listener():
    """Démarre le listener MQTT dans un thread séparé"""
    global mqtt_client
    
    print("="*60)
    print("   LISTENER MQTT - Images ESP32 TimerCAM")
    print("="*60)

    if not init_database():
        sys.exit(1)

    os.makedirs(IMAGE_DIR, exist_ok=True)
    print(f"📁 Dossier images: {IMAGE_DIR}")

    mqtt_client = mqtt.Client(client_id="RPi_Listener")
    mqtt_client.on_connect = mqtt_on_connect
    mqtt_client.on_message = mqtt_on_message

    try:
        print(f"\n🔌 Connexion à {MQTT_BROKER}:{MQTT_PORT}...")
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

        print("\n⏳ En attente des images ESP32...")
        mqtt_client.loop_forever()

    except KeyboardInterrupt:
        print("\n⏹️  Arrêt MQTT")
    except Exception as e:
        print(f"❌ Erreur MQTT: {e}")
    finally:
        if db_conn:
            db_conn.close()

# ===== ROUTES FLASK =====
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
                             avg_battery=round(stats['avg_battery'], 1) if stats and stats['avg_battery'] else 0,
                             now=datetime.now())

    except mariadb.Error as e:
        return f"Erreur BD: {e}", 500
    finally:
        conn.close()

@app.route('/api/health')
def health():
    """API santé du système"""
    mqtt_status = "connected" if mqtt_client and mqtt_client.is_connected() else "disconnected"
    db_status = "connected" if db_conn else "disconnected"
    
    return jsonify({
        'status': 'online',
        'service': 'Nichoir Connecté',
        'timestamp': datetime.now().isoformat(),
        'mqtt': mqtt_status,
        'database': db_status,
        'images_dir': IMAGE_DIR
    })

@app.route('/api/captures')
def api_captures():
    """API JSON des captures"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database error'}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, timestamp, image_path, battery_level,
                   motion_detected, device_id
            FROM captures
            ORDER BY timestamp DESC
            LIMIT 50
        """)
        
        captures = cursor.fetchall()
        
        for capture in captures:
            if capture['image_path']:
                capture['web_url'] = f"/static/{capture['image_path']}"
            capture['date_str'] = capture['timestamp'].strftime('%d/%m/%Y %H:%M')
            capture['time_ago'] = get_time_ago(capture['timestamp'])
        
        return jsonify(captures)
        
    except mariadb.Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/stats')
def api_stats():
    """API statistiques"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database error'}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                AVG(battery_level) as avg_battery,
                MAX(timestamp) as last_capture,
                COUNT(CASE WHEN timestamp > DATE_SUB(NOW(), INTERVAL 24 HOUR) THEN 1 END) as last_24h
            FROM captures
        """)
        
        stats = cursor.fetchone()
        
        return jsonify({
            'total': stats['total'] or 0,
            'avg_battery': round(stats['avg_battery'], 1) if stats['avg_battery'] else 0,
            'last_capture': stats['last_capture'].strftime('%d/%m/%Y %H:%M') if stats['last_capture'] else 'Jamais',
            'last_24h': stats['last_24h'] or 0,
            'status': 'online'
        })
        
    except mariadb.Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

def get_db_connection():
    """Obtient une connexion à la BD (pour Flask)"""
    try:
        return mariadb.connect(**DB_CONFIG)
    except mariadb.Error as e:
        print(f"❌ Erreur BD Flask: {e}")
        return None

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

# ===== MAIN =====
def main():
    """Fonction principale"""
    print("="*60)
    print("   NICHOIR CONNECTÉ - Système Complet")
    print("="*60)
    print("🔧 Fonctionnalités:")
    print("   ✓ Listener MQTT pour ESP32 TimerCAM")
    print("   ✓ Interface Web Flask élégante")
    print("   ✓ Base de données MariaDB")
    print("   ✓ Sauvegarde automatique des images")
    print("="*60)
    print(f"📁 Dossier images: {IMAGE_DIR}")
    print(f"🌐 Interface web: http://192.168.2.45:5000")
    print(f"📡 MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"📊 Base: {DB_CONFIG['database']}")
    print("="*60)
    
    # Créer les dossiers nécessaires
    os.makedirs("static/images", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    
    # Démarrer le listener MQTT dans un thread séparé
    mqtt_thread = threading.Thread(target=start_mqtt_listener, daemon=True)
    mqtt_thread.start()
    
    # Démarrer Flask
    print("\n🚀 Démarrage de l'interface web...")
    print("   Appuyez sur Ctrl+C pour arrêter")
    print("-" * 60)
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n⏹️  Arrêt du système")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # Arrêter MQTT
    if mqtt_client:
        mqtt_client.disconnect()

if __name__ == '__main__':
    main()