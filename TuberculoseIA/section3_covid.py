# section3_covid.py
from typing import Dict, Any, List, Tuple

def traiter_section3_covid(lignes_raw: List[str], ligne_patient: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """
    Section 3 : Traitement des résultats SARS-CoV-2 (COVID-19).
    
    Règles appliquées :
    1. Extraction de 'Result_Covid19' depuis 'Test Result,' ou 'Résultat du test,'.
    2. Positif / Négatif / Présumé Positif -> Redirection vers le Bloc 4.
    3. Erreur / Invalide / Aucun résultat -> Redirection vers la Sous-section 1.
    """
    resultat_brut = ""
    for line_str in lignes_raw:
        line_clean = line_str.strip('\ufeff').strip()
        if line_clean.startswith("Test Result,") or line_clean.startswith("Résultat du test,"):
            parts = [p.strip() for p in line_clean.split(',')]
            if len(parts) >= 2:
                resultat_brut = parts[1]
                break

    res_clean = resultat_brut.rstrip('|').strip()
    ligne_patient["Result_Covid19"] = res_clean
    res_upper = res_clean.upper()

    mots_cles_erreur = ["INVALID", "INVALIDE", "ERROR", "ERREUR", "NO RESULT", "AUCUN RÉSULTAT", "PAS DE RÉSULTAT"]
    if any(err in res_upper for err in mots_cles_erreur):
        return ligne_patient, "SOUS_SECTION_1_ERREURS"

    # Positif, Négatif ou Présumé Positif -> Bloc 4
    return ligne_patient, "BLOC_4"


if __name__ == "__main__":
    from exporter_schema import initialiser_ligne_patient_vierge

    p = initialiser_ligne_patient_vierge()
    p, route = traiter_section3_covid(["Test Result, SARS-CoV-2 DETECTED"], p)
    print("✅ Section 3 (COVID-19) exécutée avec succès :")
    print(f"   • Result_Covid19 : {p['Result_Covid19']} --> Route : {route}")