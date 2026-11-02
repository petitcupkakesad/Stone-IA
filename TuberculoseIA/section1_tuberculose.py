# section1_tuberculose.py
import re
from typing import Dict, Any, Tuple

def traiter_section1_tuberculose(lignes_raw: list[str], ligne_patient: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """
    Section 1 : Traitement principal des résultats Tuberculose (MTB).
    
    Règles d'aiguillage :
    1. Extraction de 'Resultat_TB' via "Test Result," ou "Résultat du test,".
    a) Si MTB NOT DETECTED / NON DÉTECTÉ (après suppression des '|' de fin) -> Redirection Bloc 4.
    b) Si Invalid/Invalide, Error/Erreur, No Result/Aucun résultat -> Redirection Sous-section 1.
    c) Si MTB DETECTED / MTB Trace DETECTED -> Maintien pour la suite de la Section 1 (Sous-section 2 / Sondes / RIF).
    """
    resultat_brut = ""

    # Extraction du résultat brut
    for line_str in lignes_raw:
        line_clean = line_str.strip('\ufeff').strip()
        if line_clean.startswith("Test Result,") or line_clean.startswith("Résultat du test,"):
            parts = [p.strip() for p in line_clean.split(',')]
            if len(parts) >= 2:
                resultat_brut = parts[1]
                break

    # Nettoyage des '|' résiduels et en fin de chaîne (Règle 1.a.i & 1.a.ii)
    resultat_nettoye = resultat_brut.rstrip('|').strip()
    ligne_patient["Resultat_TB"] = resultat_nettoye

    # Normalisation pour vérification robuste sans cas de casse
    res_upper = resultat_nettoye.upper()

    # --- Branchement b) Erreur / Invalide / Pas de résultat ---
    mots_cles_erreur = ["INVALID", "INVALIDE", "ERROR", "ERREUR", "NO RESULT", "AUCUN RÉSULTAT", "PAS DE RÉSULTAT"]
    if any(err in res_upper for err in mots_cles_erreur):
        return ligne_patient, "SOUS_SECTION_1_ERREURS"

    # --- Branchement a) MTB NOT DETECTED / NON DÉTECTÉ ---
    # Motif exact : MTB immédiatement suivi de NOT DETECTED ou NON DÉTECTÉ
    if re.search(r"MTB\s+(NOT\s+DETECTED|NON\s+DÉTECTÉ)", res_upper):
        return ligne_patient, "BLOC_4"

    # --- Branchement c) MTB (Trace)? DETECTED / DÉTECTÉ ---
    # Motif : MTB suivi (avec ou sans 'TRACE') de DETECTED ou DÉTECTÉ, peu importe ce qu'il y a plus loin pour RIF
    if re.search(r"MTB\s+(TRACE\s+)?(DETECTED|DÉTECTÉ)", res_upper):
        return ligne_patient, "SECTION_1_SOUS_SECTION_2_POSITIF"

    return ligne_patient, "BLOC_4"


if __name__ == "__main__":
    from exporter_schema import initialiser_ligne_patient_vierge

    # Tests unitaires du routage Section 1
    cas_tests = [
        ("Test Result, MTB NOT DETECTED||", "Attendu: BLOC_4"),
        ("Test Result, MTB NON DÉTECTÉ", "Attendu: BLOC_4"),
        ("Test Result, ERROR: 5011", "Attendu: SOUS_SECTION_1_ERREURS"),
        ("Test Result, Invalid", "Attendu: SOUS_SECTION_1_ERREURS"),
        ("Test Result, MTB DETECTED ULTRA LOW; RIF Resistance NOT DETECTED", "Attendu: SECTION_1_SOUS_SECTION_2_POSITIF"),
        ("Test Result, MTB Trace DETECTED", "Attendu: SECTION_1_SOUS_SECTION_2_POSITIF"),
    ]

    print("✅ Section 1 (Routage Tuberculose) exécutée avec succès :")
    for ligne_test, note in cas_tests:
        p = initialiser_ligne_patient_vierge()
        p, redirection = traiter_section1_tuberculose([ligne_test], p)
        print(f"   • Résultat: '{p['Resultat_TB']}' --> {redirection} ({note})")