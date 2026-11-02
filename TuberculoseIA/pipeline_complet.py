import os
from gxx_to_csv import convertir_dossier_gxx_en_csv
from inference_stone_ia import predire_depuis_csv

def executer_pipeline(dossier_gxx="./", fichier_poids="modele_stone_ia.pth"):
    print("=" * 60)
    print("      LANCEMENT DU PIPELINE AUTOMATIQUE STONE IA - TB     ")
    print("=" * 60)

    # 1. Décodage automatique des fichiers .gxx / .bin en CSV
    fichier_csv_intermediaire = "donnees_tuberculose_converties.csv"
    print("\n[Étape 1/2] Extraction des données binaires .gxx...")
    convertir_dossier_gxx_en_csv(dossier_gxx, fichier_csv_intermediaire)

    # 2. Inférence PyTorch sur les valeurs de Ct extraites
    print("\n[Étape 2/2] Analyse et prédiction par le modèle PyTorch...")
    
    # Vérification si un fichier de poids .pth existe
    chemin_poids = fichier_poids if os.path.exists(fichier_poids) else None
    
    df_resultats = predire_depuis_csv(fichier_csv_intermediaire, chemin_poids_model=chemin_poids)

    print("\n" + "=" * 60)
    print("               RÉSULTATS DE L'ANALYSE IA                ")
    print("=" * 60)
    print(df_resultats.to_string(index=False))
    print("\n[✔] Pipeline exécuté avec succès !")

if __name__ == "__main__":
    executer_pipeline()