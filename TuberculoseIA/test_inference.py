# test_inference.py
import os
import pandas as pd
from csv_parser import parser_rapport_genexpert
from inference_stone_ia import charger_modele_et_scaler, predire_echantillon

def tester_inference():
    print("=" * 60)
    print("        TEST DU MODULE D'INFÉRENCE STONE IA         ")
    print("=" * 60)

    dossier_abs = os.path.dirname(os.path.abspath(__file__)) if __file__ else os.getcwd()
    fichiers = [f for f in os.listdir(dossier_abs) if f.endswith('.csv') or f.endswith('.xlsx')]
    
    dossier_csv = os.path.join(dossier_abs, "csv")
    if os.path.exists(dossier_csv):
        fichiers += [os.path.join("csv", f) for f in os.listdir(dossier_csv) if f.endswith('.csv') or f.endswith('.xlsx')]

    if not fichiers:
        print("❌ Aucun fichier trouvé.")
        return

    # Sélection automatique du fichier (le dernier de la liste, ex: juillet 2021)
    chemin_cible = fichiers[-1]
    print(f"\n📂 Fichier sélectionné : {chemin_cible}")

    print("\n📂 Chargement du modèle PyTorch...")
    try:
        model, mean, scale, features = charger_modele_et_scaler("modeles/stone_g4_model.pt")
        print("[✔] Modèle et scaler chargés avec succès (weights_only=True).")
    except Exception as e:
        print(f"❌ Erreur lors du chargement du modèle : {e}")
        return

    print(f"📂 Chargement et parsing du fichier...")
    try:
        if chemin_cible.endswith('.xlsx'):
            df = pd.read_excel(chemin_cible)
        else:
            df = pd.read_csv(chemin_cible, encoding="latin1")
    except Exception as e:
        print(f"❌ Erreur de lecture : {e}")
        return

    resultats_parser = parser_rapport_genexpert(df)
    print(f"[✔] {len(resultats_parser)} échantillons parsés. Lancement de l'inférence sur les 5 premiers...")

    classes_noms = {
        0: "Négatif",
        1: "Positif Sensible",
        2: "Positif Résistant",
        3: "Erreur / Invalide"
    }

    print("\n" + "-" * 50)
    for i, res in enumerate(resultats_parser[:5]):
        valeurs_ct = res['valeurs_ct']
        pred_class, conf = predire_echantillon(model, mean, scale, valeurs_ct)
        
        print(f"Échantillon {i+1}:")
        print(f"  - Sample ID      : {res['sample_id']}")
        print(f"  - Patient ID     : {res['patient_id']}")
        print(f"  - Ct (A-E, SPC)  : {valeurs_ct}")
        print(f"  - Label Parser   : {classes_noms.get(res['label_reel'], 'Inconnu')}")
        print(f"  - Prédiction IA  : {classes_noms.get(pred_class, 'Inconnu')} (Confiance: {conf:.2f}%)")
        print("-" * 50)

if __name__ == "__main__":
    tester_inference()