# parser.py
import os
import re
from typing import List, Dict, Any
from preprocessing import nettoyer_et_pretraiter_bytes

def est_ligne_vide_ou_bom(ligne: str) -> bool:
    """Vérifie si une ligne est vide, contient uniquement des espaces ou un caractère BOM."""
    cleaned = ligne.strip('\ufeff').strip()
    return len(cleaned) == 0

def diviser_et_nettoyer_ligne(ligne: str) -> List[str]:
    """Découpe une ligne CSV/texte par virgule en conservant les valeurs propres."""
    return [el.strip() for el in ligne.split(',')]

def extraire_blocs_patients(contenu_texte: str) -> List[Dict[str, Any]]:
    """
    Bloc 2 : Analyse syntaxique (Parsing) et découpage en blocs patients.
    
    Applique les règles :
    1. Détection des blocs patients via "RESULT TABLE" / "TABLEAU DE RÉSULTATS".
    2. Filtrage des sections parasites (History, OPTICAL DATA, ASSAY INFORMATION, Analysis Settings).
    3. Exclusion des en-têtes et métadonnées secondaires.
    4. Indépendance des occurrences de Sample ID / Patient ID.
    5. Ignorer les messages de privilèges insuffisants.
    """
    lignes = contenu_texte.splitlines()
    blocs_patients = []
    
    dans_result_table = False
    section_a_ignorer = False
    
    bloc_courant = {
        "lignes_raw": [],
        "champs_cles": {}
    }

    prefixes_a_ignorer = (
        "Nom de l'analyte,Contrôle de sonde",
        "Analyte Name,Prb Chk",
        "Assay Type,In Vitro Diagnostic",
        "Test Type,Specimen",
        "Sample Type",
        "Assay Version,",
        "Version du test,",
        "Type de test,Diagnostic in vitro",
        "Type de test,",
        "Type d'échantillon"
    )

    for line_str in lignes:
        line_clean = line_str.strip('\ufeff').strip()

        if "privilège insuffisant" in line_clean.lower() or "insufficient privilege" in line_clean.lower():
            continue

        if line_clean.startswith("RESULT TABLE") or line_clean.startswith("TABLEAU DE RÉSULTATS"):
            if bloc_courant["lignes_raw"]:
                blocs_patients.append(bloc_courant)
                bloc_courant = {"lignes_raw": [], "champs_cles": {}}
            
            dans_result_table = True
            section_a_ignorer = False
            continue

        if not dans_result_table:
            continue

        if section_a_ignorer:
            if est_ligne_vide_ou_bom(line_clean):
                section_a_ignorer = False
            continue

        if line_clean == "History" or line_clean == "Historique":
            section_a_ignorer = True
            continue

        if any(line_clean.startswith(header) for header in [
            "OPTICAL DATA", "DONNÉES OPTIQUES",
            "ASSAY INFORMATION", "INFORMATIONS DU TEST", "INFORMATIONS SUR LE TEST",
            "Analysis Settings", "Paramètres d'analyse"
        ]):
            section_a_ignorer = True
            continue

        if any(line_clean.startswith(prefix) for prefix in prefixes_a_ignorer):
            continue

        if line_clean:
            bloc_courant["lignes_raw"].append(line_str)
            parts = diviser_et_nettoyer_ligne(line_str)
            if len(parts) >= 2 and parts[0]:
                cle = parts[0]
                valeur = ",".join(parts[1:])
                bloc_courant["champs_cles"][cle] = valeur

    if bloc_courant["lignes_raw"]:
        blocs_patients.append(bloc_courant)

    return blocs_patients


if __name__ == "__main__":
    # Résolution dynamique des chemins
    base_dir = os.path.dirname(os.path.abspath(__file__))
    fichier_test = os.path.join(base_dir, "Pré-traitement_clined-file.txt")
    
    if not os.path.exists(fichier_test):
        fichier_test_racine = "Pré-traitement_clined-file.txt"
        if os.path.exists(fichier_test_racine):
            fichier_test = fichier_test_racine

    if os.path.exists(fichier_test):
        with open(fichier_test, "r", encoding="utf-8") as f:
            contenu = f.read()
        résultats = extraire_blocs_patients(contenu)
        print(f"✅ Bloc 2 exécuté avec succès : {len(résultats)} blocs patients identifiés à partir de '{os.path.basename(fichier_test)}'.")
    else:
        print("⚠️ Fichier intermédiaire absent. Génération d'un fichier de test vierge via Bloc 1...")
        nettoyer_et_pretraiter_bytes(b"RESULT TABLE\nSample ID,PATIENT_TEST_001\nTest Result,MTB DETECTED\nProbe A,18.5\n")
        print("✅ Fichier généré. Relancez le script !")