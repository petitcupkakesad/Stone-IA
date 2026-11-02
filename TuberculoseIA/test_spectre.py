# test_spectre.py
import os
import pandas as pd
import numpy as np
import torch
from csv_parser import parser_rapport_genexpert
from inference_stone_ia import charger_modele_et_scaler, predire_echantillon

def tester_spectre():
    print("=" * 60)
    print("    TEST DU SPECTRE COMPLET (CLASSES 2 & 3)    ")
    print("=" * 60)

    chemin_cible = "csv/tableau_MTB_RIF_G4_LNSP_23_juillet_2021.csv"
    if not os.path.exists(chemin_cible):
        print(f"❌ Fichier introuvable : {chemin_cible}")
        return

    print("📂 Chargement du modèle et du scaler...")
    model, mean, scale, features = charger_modele_et_scaler("modeles/stone_g4_model.pt")

    print("📂 Parsing du fichier pour trouver des cas de Classe 2 et Classe 3...")
    df = pd.read_csv(chemin_cible, encoding="latin1")
    resultats = parser_rapport_genexpert(df)

    classes_noms = {
        0: "Négatif",
        1: "Positif Sensible",
        2: "Positif Résistant",
        3: "Erreur / Invalide"
    }

    cas_trouves = {2: None, 3: None}

    for res in resultats:
        label = res['label_reel']
        if label in [2, 3] and cas_trouves[label] is None:
            cas_trouves[label] = res
        if cas_trouves[2] is not None and cas_trouves[3] is not None:
            break

    for classe_cible, res in cas_trouves.items():
        print("\n" + "-" * 50)
        if res is not None:
            pred, conf = predire_echantillon(model, mean, scale, res['valeurs_ct'])
            print(f"Échantillon cible : {classes_noms[classe_cible]}")
            print(f"  - Sample ID      : {res['sample_id']}")
            print(f"  - Patient ID     : {res['patient_id']}")
            print(f"  - Ct (A-E, SPC)  : {res['valeurs_ct']}")
            print(f"  - Texte brut     : {res['texte_brut']}")
            print(f"  - Label Parser   : {classes_noms[res['label_reel']]}")
            print(f"  - Prédiction IA  : {classes_noms[pred]} (Confiance: {conf:.2f}%)")
        else:
            print(f"⚠️ Aucun échantillon de {classes_noms[classe_cible]} trouvé dans ce fichier.")
        print("-" * 50)

if __name__ == "__main__":
    tester_spectre()