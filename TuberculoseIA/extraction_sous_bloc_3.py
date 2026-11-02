# extraction_sous_bloc_3.py
import re
from typing import Dict, Any, List

def extraire_donnees_patient_sous_bloc_3(lignes_raw: List[str], ligne_patient: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sous-bloc 3 : Extraction de l'identifiant échantillon, des dates et du type de test.
    
    Règles appliquées :
    1. #Echantillon : Chaine exactement après "Sample ID," ou "N° Id de l'échantillon,".
    2. Run_Date : Chaine exactement après "Start Time," ou "Heure de lancement,", convertie en JJ/MM/20AA (sans l'heure).
    3. Test_Xpert : Ligne commençant exactement par "Assay," ou "Test," (en excluant les préfixes parasites).
    4. Annee : Extrait AAAA à partir de Run_Date.
    """
    
    # Exclusions strictes pour le champ Test_Xpert (Règle 1.c)
    exclusions_assay_test = (
        "Assay Type,",
        "Assay Version,",
        "Test Type,",
        "Test Result,",
        "Test Disclamer,",
        "Test Disclaimer,"
    )

    for line_str in lignes_raw:
        line_clean = line_str.strip('\ufeff').strip()
        
        # --- 1.a. Extraction de #Echantillon ---
        if line_clean.startswith("Sample ID,") or line_clean.startswith("N° Id de l'échantillon,"):
            parts = [p.strip() for p in line_clean.split(',')]
            if len(parts) >= 2:
                ligne_patient["#Echantillon"] = parts[1]

        # --- 1.b. Extraction de Run_Date ---
        elif line_clean.startswith("Start Time,") or line_clean.startswith("Heure de lancement,"):
            # Cherche le motif de date JJ/MM/AA ou JJ-MM-AA
            match = re.search(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{2})", line_clean)
            if match:
                jour, mois, annee_2d = match.groups()
                # Formate JJ/MM/20AA (Règle 1.b.i & 1.b.ii)
                run_date_formatee = f"{int(jour):02d}/{int(mois):02d}/20{annee_2d}"
                ligne_patient["Run_Date"] = run_date_formatee
                
                # --- 2. Dérivation de l'Année (AAAA) ---
                ligne_patient["Annee"] = f"20{annee_2d}"

        # --- 1.c. Extraction de Test_Xpert ---
        elif (line_clean.startswith("Assay,") or line_clean.startswith("Test,")) and not any(line_clean.startswith(excl) for excl in exclusions_assay_test):
            parts = [p.strip() for p in line_clean.split(',')]
            if len(parts) >= 2:
                ligne_patient["Test_Xpert"] = parts[1]

    return ligne_patient


if __name__ == "__main__":
    from exporter_schema import initialiser_ligne_patient_vierge

    # Test unitaire du Sous-bloc 3
    lignes_test = [
        "Sample ID, TB_PATIENT_2026_09",
        "Start Time, 19/09/26 08:45:10",
        "Assay Version, 3.0",
        "Assay, Xpert MTB-RIF Ultra",
        "Test Result, MTB DETECTED"
    ]

    patient = initialiser_ligne_patient_vierge()
    patient = extraire_donnees_patient_sous_bloc_3(lignes_test, patient)

    print("✅ Sous-bloc 3 exécuté avec succès :")
    print(f"   • #Echantillon : {patient['#Echantillon']}")
    print(f"   • Run_Date     : {patient['Run_Date']}")
    print(f"   • Annee        : {patient['Annee']}")
    print(f"   • Test_Xpert   : {patient['Test_Xpert']}")