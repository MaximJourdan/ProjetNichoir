# 🐦 Nichoir Connecté – SmartCities 2025-2026

Projet étudiant développé à la **Haute École de la Province de Liège (HEPL)** dans le cadre du programme **Sciences de l’ingénieur industriel – orientation informatique**.

## 📌 Objectif
Créer un nichoir intelligent et connecté permettant de suivre la vie des oiseaux :
- Coût accessible (moins de 50 €)
- Autonomie énergétique prolongée (6 mois à 1 an sur batterie)
- Évolutif : ajout possible d’un panneau solaire

---

## 🔎 Analyse du marché
- Prix des solutions existantes : 130 – 300 €
- Alimentation : câble, panneaux solaires
- Stockage : carte SD, Wi-Fi cloud privé, RTSP
- Exemples : Green Backyard, Greenfeathers Bird Box Camera Kit

---

## ⚙️ Caractéristiques techniques
- **Microcontrôleur** : ESP32-DOWDQ6-V3  
- **Mémoire** : 8 MB PSRAM  
- **Caméra** : OV3660, 3MP, DFOV 66.5°, résolution max 2048x1536  
- **Indicateurs** : LED de statut + bouton RESET  
- **Gestion énergie** : RTC BM8563, consommation en veille ~2 µA, connecteur batterie externe  
- **Connectivité** : Wi-Fi, port USB debug, port HY2.0-4P pour périphériques externes  

Librairies utilisées : [TimerCam Arduino](https://github.com/m5stack/TimerCam-arduino/tree/master)

---

## 🔋 Gestion de l’énergie
- Mode **standby** : réveil quotidien pour envoi du niveau de batterie via MQTT  
- Mode **présence** : détection PIR → capture photo + envoi batterie associé  

---

## 📡 Fonctionnement du système
### Détection de mouvement
- Capteur PIR → déclenche capture photo avec éclairage IR

### Transmission des données
- Envoi des images au Raspberry Pi via Wi-Fi
- Script Python MQTT listener → stockage dans MariaDB
- Serveur Flask → galerie web + affichage des données

---

## 🛠️ Conception
- Breakout pour PIR, LED, TimerCam
- Package complet avec batterie/support piles
- Versioning et suivi sur GitHub

---

## ✅ Évaluation & Compétences
### C1 – Concevoir des systèmes complexes
- Architecture claire et modulaire
- Passage de la conception théorique à la réalisation pratique
- Optimisation en fonction des tests

### C2 – Mettre en œuvre des systèmes complexes
- Fiabilité et traçabilité des tests
- Documentation et reproductibilité
- Respect du cahier des charges

### C3 – Développer sa professionnalité
- Auto-formation et apprentissage continu
- Initiative et autonomie dans la recherche de solutions

---

## 🚀 Installation & Utilisation
### Prérequis
- ESP32 TimerCam
- Raspberry Pi avec Python 3
- MariaDB/MySQL
- Flask

