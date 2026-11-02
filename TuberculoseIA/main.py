# main.py
import os
import glob
from typing import List, Dict, Any, Tuple
import pandas as pd

# Imports des modules
from section4_5_bloc4 import (
    traiter_section4_vih_qual,
    traiter_section5_hpv,
    traiter_bloc4_metadonnees
)
from sous_section5 import traiter_sous_section5
from sous_sections_2_3 import aiguiller_sous_section_5_1
from bloc5_export import generer_excel_final


def lire_fichier_gxx(chemin_fichier: str) -> List[str]:
    lignes = []
    encodages = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
    for enc in encodages:
        try:
            with open(chemin_fichier, 'r', encoding=enc) as f:
                lignes = f.readlines()
            break
        except UnicodeDecodeError:
            continue
    return lignes


def extraire_blocs_patients(lignes: List[str]) -> List[List[str]]:
    blocs = []
    bloc_courant = []
    for line in lignes:
        if ("Patient ID," in line or "Sample ID," in line or "ID Patient," in line) and bloc_courant:
            blocs.append(bloc_courant)
            bloc_courant = []
        bloc_courant.append(line)
    if bloc_courant:
        blocs.append(bloc_courant)
    return blocs


def parser_bloc_patient(lignes_bloc: List[str]) -> Dict[str, Any]:
    patient_data: Dict[str, Any] = {
        "Patient ID": "null",
        "Sample ID": "null",
        "Test_Xpert": "null",
        "Test Result": "null",
        "Resultat_TB": "null",
        "Result_VIH": "null",
        "VIH_Qual_result": "null",
        "Result_Covid19": "null",
        "HPV_result": "null",
        "HPV_16": "null",
        "HPV_18-45": "null",
        "Charge_bacille": "null",
        "RIF resistance": "null",
        "Module": "null",
        "Lot_reactif": "null",
        "Expiration_reactif": "null",
        "Statut_erreur": "null",
        "Utilisateur": "null",
        "Statut_f": "null"
    }

    # Premier passage pour identifier le type de test
    for line in lignes_bloc:
        line_clean = line.strip('\ufeff').strip()
        if not line_clean or ',' not in line_clean:
            continue
        parts = [p.strip() for p in line_clean.split(',')]
        if len(parts) >= 2 and parts[0] in ["Test", "Test Name", "Nom du test"]:
            patient_data["Test_Xpert"] = parts[1]
            break

    test_name = str(patient_data["Test_Xpert"]).upper()

    # Second passage pour assigner correctement les valeurs selon la cible
    for line in lignes_bloc:
        line_clean = line.strip('\ufeff').strip()
        if not line_clean or ',' not in line_clean:
            continue
            
        parts = [p.strip() for p in line_clean.split(',')]
        if len(parts) < 2:
            continue
            
        key, val = parts[0], parts[1]

        if key in ["Patient ID", "ID Patient"]:
            patient_data["Patient ID"] = val
        elif key in ["Sample ID", "ID Échantillon"]:
            patient_data["Sample ID"] = val
        elif key in ["Test Result", "Résultat du test"]:
            patient_data["Test Result"] = val
            if "MTB" in test_name or "TB" in test_name:
                patient_data["Resultat_TB"] = val
            elif "VIH" in test_name or "HIV" in test_name:
                patient_data["Result_VIH"] = val
            elif "COVID" in test_name or "SARS" in test_name:
                patient_data["Result_Covid19"] = val

        if len(parts) >= 2 and any(k in key for k in ["Sonde", "rpoB", "melt"]):
            patient_data[key] = val

    patient_data = traiter_bloc4_metadonnees(lignes_bloc, patient_data)
    return patient_data


def executer_pipeline(dossier_entree: str, fichier_sortie_excel: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    # Élargissement pour accepter les .gxx, .csv et .xlsx
    fichiers = (
        glob.glob(os.path.join(dossier_entree, "*.gxx")) + 
        glob.glob(os.path.join(dossier_entree, "*.GXX")) + 
        glob.glob(os.path.join(dossier_entree, "*.csv")) + 
        glob.glob(os.path.join(dossier_entree, "*.xlsx"))
    )
    
    if not fichiers:
        print(f"⚠️ Aucun fichier .gxx, .csv ou .xlsx trouvé dans le dossier : '{dossier_entree}'")
        return pd.DataFrame(), pd.DataFrame()

    print(f"📂 {len(fichiers)} fichier(s) détecté(s). Début du traitement...\n")

    donnees_principales = []
    donnees_mutations = []

    for chemin in fichiers:
        print(f"📄 Lecture du fichier : {os.path.basename(chemin)}")
        
        # Si c'est un CSV ou Excel (comme vos tableaux d'archives G4)
        if chemin.lower().endswith(('.csv', '.xlsx')):
            if chemin.lower().endswith('.csv'):
                df_temp = pd.read_csv(chemin)
            else:
                df_temp = pd.read_excel(chemin)
                
            # Conversion du DataFrame tabulaire en dictionnaire compatible avec le pipeline
            for _, row in df_temp.iterrows():
                patient = row.to_dict()
                # S'assurer que les clés minimales existent
                if "Test Result" not in patient and "Result" in patient:
                    patient["Test Result"] = patient["Result"]
                
                donnees_principales.append(patient)
        
        # Sinon, traitement classique par blocs .gxx
        else:
            lignes = lire_fichier_gxx(chemin)
            blocs_patients = extraire_blocs_patients(lignes)

            for bloc in blocs_patients:
                patient = parser_bloc_patient(bloc)
                test_xpert = str(patient.get("Test_Xpert", "")).upper()

                if "MTB" in test_xpert or "TB" in test_xpert:
                    patient, etape_suivante = traiter_sous_section5(patient)
                    patient = aiguiller_sous_section_5_1(patient, etape_suivante)

                    if "ULTRA" in test_xpert:
                        donnees_mutations.append(patient.copy())

                elif "VIH" in test_xpert or "HIV" in test_xpert:
                    patient, _ = traiter_section4_vih_qual(bloc, patient)

                elif "HPV" in test_xpert:
                    patient, _ = traiter_section5_hpv(bloc, patient)

                donnees_principales.append(patient)

    # Exportation Excel via openpyxl
    generer_excel_final(
        donnees_principales=donnees_principales,
        donnees_mutations=donnees_mutations,
        fichier_sortie=fichier_sortie_excel
    )

    df_principale = pd.DataFrame(donnees_principales)
    df_mutations = pd.DataFrame(donnees_mutations)

    return df_principale, df_mutations

    # Conversion en DataFrames Pandas pour l'intégration Streamlit / Inférence
    df_principale = pd.DataFrame(donnees_principales)
    df_mutations = pd.DataFrame(donnees_mutations)

    return df_principale, df_mutations


if __name__ == "__main__":
    DOSSIER_BASE = os.path.dirname(os.path.abspath(__file__))
    DOSSIER_DONNEES = os.path.join(DOSSIER_BASE, "donnees_gxx")
    FICHIER_EXCEL_SORTIE = os.path.join(DOSSIER_BASE, "GeneXpert_Rapport_Final.xlsx")

    os.makedirs(DOSSIER_DONNEES, exist_ok=True)
    df_main, df_mut = executer_pipeline(DOSSIER_DONNEES, FICHIER_EXCEL_SORTIE)
    print(f"\n✅ Pipeline exécuté avec succès. {len(df_main)} enregistrements traités.")