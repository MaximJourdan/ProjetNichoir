"""
Executer le listener avant d'executer app
"""


#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import mariadb
import json
from datetime import datetime
import os
import sys

# ===== CONFIGURATION =====
MQTT_BROKER = "192.168.2.45"  # IP CORRECTE de ton Raspberry
MQTT_PORT = 1883
MQTT_TOPIC_IMAGE = "nichoir/camera/image"
MQTT_TOPIC_METADATA = "nichoir/camera/metadata"

DB_CONFIG = {
    'host': 'localhost',
    'user': 'nichoir_user',
    'password': 'modeste123',
    'database': 'nichoir_db'
}

# IMPORTANT : Chemin pour les images WEB
WEB_STATIC_DIR = "/home/modeste/nichoir_projet/web/static"
IMAGE_DIR = os.path.join(WEB_STATIC_DIR, "images")  # Dossier nichoir
DEVICE_ID = "M5_TimerCAM_01"

# ===== VARIABLES =====
image_buffer = bytearray()
current_metadata = {}
db_conn = None

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

def save_image_to_disk(image_data, filename):
    """Sauvegarde l'image dans le dossier web/static/images/"""
    try:
        os.makedirs(IMAGE_DIR, exist_ok=True)
        filepath = os.path.join(IMAGE_DIR, filename)

        with open(filepath, 'wb') as f:
            f.write(image_data)

        print(f"💾 Image sauvegardée: {filepath}")
        # Retourne le chemin RELATIF pour le web
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

def on_connect(client, userdata, flags, rc):
    """Connexion MQTT"""
    if rc == 0:
        print("✅ Connecté au broker MQTT")
        client.subscribe(MQTT_TOPIC_IMAGE)
        client.subscribe(MQTT_TOPIC_METADATA)
        print(f"📡 Topics: {MQTT_TOPIC_IMAGE}, {MQTT_TOPIC_METADATA}")
    else:
        print(f"❌ Échec MQTT: {rc}")

def on_message(client, userdata, msg):
    """Réception messages"""
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

def main():
    print("="*60)
    print("   LISTENER MQTT - Images ESP32 TimerCAM")
    print("="*60)

    if not init_database():
        sys.exit(1)

    os.makedirs(IMAGE_DIR, exist_ok=True)
    print(f"📁 Dossier images: {IMAGE_DIR}")

    client = mqtt.Client(client_id="RPi_Listener")
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        print(f"\n🔌 Connexion à {MQTT_BROKER}:{MQTT_PORT}...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)

        print("\n⏳ En attente des images ESP32...")
        client.loop_forever()

    except KeyboardInterrupt:
        print("\n⏹️  Arrêt")
    finally:
        if db_conn:
            db_conn.close()

if __name__ == "__main__":
    main()