# sous_sections_2_3.py
from typing import Dict, Any, Tuple
from bloc6_mutations import evaluer_patient_mutations


def traiter_sous_section2_standard(ligne_patient: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sous-section 2 : Préparation du kit Xpert MTB/RIF Standard.
    Isole les sondes A, B, C, D, E et achemine le résultat vers le Bloc 6.
    """
    # Liste des sondes requises pour la version Standard
    sondes_std = ["Sonde_A", "Sonde_B", "Sonde_C", "Sonde_D", "Sonde_E"]
    
    # Vérification et initialisation si manquantes dans le dictionnaire
    for s in sondes_std:
        if s not in ligne_patient or ligne_patient[s] is None:
            ligne_patient[s] = "null"

    # Envoi direct vers le traitement des sondes et mutations du Bloc 6
    ligne_patient = evaluer_patient_mutations(ligne_patient)
    return ligne_patient


def traiter_sous_section3_ultra(ligne_patient: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sous-section 3 : Préparation du kit Xpert MTB/RIF Ultra.
    Isole les sondes rpoB (1 à 4) et leurs canaux de fusion (Melt),
    puis achemine le tout vers le Sous-bloc 5 du Bloc 6.
    """
    # Clés requises pour les analyses de fusion de la version Ultra
    cles_ultra = [
        "rpoB1_", "rpoB2_", "rpoB3_", "rpoB4_",
        "rpoB1_melt", "rpoB1_Mut_melt",
        "rpoB2_melt", "rpoB2_Mut_melt",
        "rpoB3_melt", "rpoB3_Mut_melt",
        "rpoB4_melt", "rpoB4_Mut_meltA", "rpoB4_Mut_meltB"
    ]

    for k in cles_ultra:
        if k not in ligne_patient or ligne_patient[k] is None:
            ligne_patient[k] = "null"

    # Envoi vers le Bloc 6 pour découpage T°/Height et calcul de la table Ultra (43 règles)
    ligne_patient = evaluer_patient_mutations(ligne_patient)
    return ligne_patient


def aiguiller_sous_section_5_1(ligne_patient: Dict[str, Any], prochaine_etape: str) -> Dict[str, Any]:
    """
    Routage intermédiaire basé sur la décision rendue par la Sous-section 5.1.
    """
    if prochaine_etape == "SOUS_SECTION_3":
        return traiter_sous_section3_ultra(ligne_patient)
    elif prochaine_etape == "SOUS_SECTION_2":
        return traiter_sous_section2_standard(ligne_patient)
    else:
        # Cas par défaut si non spécifié
        return evaluer_patient_mutations(ligne_patient)