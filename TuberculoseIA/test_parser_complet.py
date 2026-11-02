# test_parser_complet.py
import os
import pandas as pd
from csv_parser import parser_rapport_genexpert

def tester_parser():
    print("=" * 60)
    print("        TEST DU PARSER ET DE LA LABÉLISATION         ")
    print("=" * 60)

    chemin_cible = "csv/tableau_MTB_RIF_G4_LNSP_23_juillet_2021.csv"
    if not os.path.exists(chemin_cible):
        print(f"❌ Fichier introuvable : {chemin_cible}")
        return

    df = pd.read_csv(chemin_cible, encoding="latin1")
    resultats = parser_rapport_genexpert(df)
    
    print(f"[✔] Total échantillons parsés : {len(resultats)}")
    
    classes_noms = {
        0: "Négatif",
        1: "Positif Sensible",
        2: "Positif Résistant",
        3: "Erreur / Invalide"
    }

    # Affichage de l'échantillon 2 (index 1)
    if len(resultats) >= 2:
        res = resultats[1]
        print("\n" + "-" * 50)
        print("Échantillon 2 (Vérification de la correction) :")
        print(f"  - Sample ID      : {res['sample_id']}")
        print(f"  - Patient ID     : {res['patient_id']}")
        print(f"  - Ct (A-E, SPC)  : {res['valeurs_ct']}")
        print(f"  - Texte brut     : {res['texte_brut']}")
        print(f"  - Label Attribué : {classes_noms.get(res['label_reel'], 'Inconnu')}")
        print("-" * 50)

if __name__ == "__main__":
    tester_parser()