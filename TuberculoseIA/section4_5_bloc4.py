# section4_5_bloc4.py
from typing import Dict, Any, List, Tuple

def traiter_section4_vih_qual(lignes_raw: List[str], ligne_patient: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """Section 4 : VIH Qualitatif."""
    resultat_brut = ""
    for line in lignes_raw:
        line_clean = line.strip('\ufeff').strip()
        if line_clean.startswith("Test Result,") or line_clean.startswith("Résultat du test,"):
            parts = [p.strip() for p in line_clean.split(',')]
            if len(parts) >= 2:
                resultat_brut = parts[1]
                break

    res_clean = resultat_brut.rstrip('|').strip()
    ligne_patient["VIH_Qual_result"] = res_clean
    res_upper = res_clean.upper()

    mots_cles_erreur = ["INVALID", "INVALIDE", "ERROR", "ERREUR", "NO RESULT", "AUCUN RÉSULTAT", "PAS DE RÉSULTAT"]
    if any(err in res_upper for err in mots_cles_erreur):
        return ligne_patient, "SOUS_SECTION_1_ERREURS"

    return ligne_patient, "BLOC_4"


def traiter_section5_hpv(lignes_raw: List[str], ligne_patient: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """Section 5 : HPV 16 / 18-45."""
    resultat_brut = ""
    for line in lignes_raw:
        line_clean = line.strip('\ufeff').strip()
        if line_clean.startswith("Test Result,") or line_clean.startswith("Résultat du test,"):
            parts = [p.strip() for p in line_clean.split(',')]
            if len(parts) >= 2:
                resultat_brut = parts[1]
                break

    res_clean = resultat_brut.rstrip('|').strip()
    ligne_patient["HPV_result"] = res_clean

    has_16 = "HPV 16" in res_clean
    has_18_45 = "HPV 18" in res_clean or "HPV 45" in res_clean

    if has_16 and has_18_45:
        ligne_patient["HPV_16"] = "Détecté"
        ligne_patient["HPV_18-45"] = "Détecté"
    elif has_16:
        ligne_patient["HPV_16"] = "Détecté"
        ligne_patient["HPV_18-45"] = "HPV non détecté"
    elif has_18_45:
        ligne_patient["HPV_16"] = "HPV non détecté"
        ligne_patient["HPV_18-45"] = "Détecté"
    else:
        ligne_patient["HPV_16"] = "HPV non détecté"
        ligne_patient["HPV_18-45"] = "HPV non détecté"

    return ligne_patient, "BLOC_4"


def traiter_bloc4_metadonnees(lignes_raw: List[str], ligne_patient: Dict[str, Any]) -> Dict[str, Any]:
    """Bloc 4 : Extraction des métadonnées système."""
    mapping_prefix = {
        "Module Name,": "Module",
        "Nom du module,": "Module",
        "Reagent Lot ID,": "Lot_reactif",
        "N° du lot,": "Lot_reactif",
        "Expiration Date,": "Expiration_reactif",
        "Date d'expiration,": "Expiration_reactif",
        "Error Status,": "Statut_erreur",
        "État de l'erreur,": "Statut_erreur",
        "User,": "Utilisateur",
        "Utilisateur,": "Utilisateur"
    }

    for line in lignes_raw:
        line_clean = line.strip('\ufeff').strip()
        
        # Règle 5 : Distinction stricte entre "Status," et "Error Status,"
        if line_clean.startswith("Status,") or line_clean.startswith("État,"):
            parts = [p.strip() for p in line_clean.split(',')]
            if len(parts) >= 2:
                ligne_patient["Statut_f"] = parts[1]
            continue

        for pfx, col in mapping_prefix.items():
            if line_clean.startswith(pfx):
                parts = [p.strip() for p in line_clean.split(',')]
                if len(parts) >= 2:
                    ligne_patient[col] = parts[1]
                break

    return ligne_patient