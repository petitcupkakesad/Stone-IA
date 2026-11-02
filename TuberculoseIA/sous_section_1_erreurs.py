# sous_section_1_erreurs.py
import re
from typing import Dict, Any, List

def traiter_sous_section_1_erreurs(lignes_raw: List[str], ligne_patient: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sous-section 1 : Extraction et structuration des messages d'erreur et d'avertissement.
    
    Règles appliquées :
    1. Détection du tableau d'erreurs via "#,Description,Detail,Time" ou "N°,Description,Détail,Heure".
    2. Extraction des lignes commençant par un numéro suivi d'une virgule ("1,", "2,", etc.).
    3. Remplissage de 'Message_Erreur' et de 'Nombre_message_erreur' (concaténation avec ' | ' si multiples).
    4. Extraction du bloc "Messages" jusqu'à la prochaine ligne vide et remplissage de 'Message_s'.
    """
    messages_erreur = []
    messages_systeme = []
    
    lecture_tableau_erreurs = False
    lecture_section_messages = False

    # Motifs d'en-tête pour le tableau d'erreurs
    headers_erreurs = ("#,description,detail,time", "n°,description,détail,heure")

    for line_str in lignes_raw:
        line_clean = line_str.strip('\ufeff').strip()
        line_lower = line_clean.lower()

        # --- A. Gestion de la section "Messages" (Règle 4) ---
        if line_clean == "Messages":
            lecture_section_messages = True
            lecture_tableau_erreurs = False
            continue

        if lecture_section_messages:
            if not line_clean:
                lecture_section_messages = False
            else:
                messages_systeme.append(line_clean)
            continue

        # --- B. Détection de l'en-tête du tableau d'erreurs (Règle 1) ---
        if any(line_lower.startswith(h) for h in headers_erreurs):
            lecture_tableau_erreurs = True
            continue

        # --- C. Extraction des lignes d'erreurs numérotées (Règle 2) ---
        if lecture_tableau_erreurs:
            # Si on croise une ligne vide ou un autre titre, on arrête la lecture du tableau
            if not line_clean or line_clean.startswith("RESULT TABLE") or line_clean == "Messages":
                lecture_tableau_erreurs = False
                if line_clean == "Messages":
                    lecture_section_messages = True
                continue

            # Vérifie si la ligne commence par un nombre suivi d'une virgule ("1,", "2,", etc.)
            if re.match(r"^\d+,", line_clean):
                messages_erreur.append(line_clean)

    # --- D. Traitement et affectation dans le dictionnaire (Règle 3 & 4.b) ---
    nb_erreurs = len(messages_erreur)
    if nb_erreurs > 0:
        ligne_patient["Nombre_message_erreur"] = nb_erreurs
        ligne_patient["Message_Erreur"] = " | ".join(messages_erreur)
    else:
        ligne_patient["Nombre_message_erreur"] = 0
        ligne_patient["Message_Erreur"] = ""

    if messages_systeme:
        ligne_patient["Message_s"] = " | ".join(messages_systeme)

    return ligne_patient


if __name__ == "__main__":
    from exporter_schema import initialiser_ligne_patient_vierge

    # Test unitaire de la Sous-section 1
    lignes_test_erreur = [
        "RESULT TABLE",
        "Sample ID, PATIENT_ERR_01",
        "Test Result, ERROR",
        "#,Description,Detail,Time",
        "1,5011,Seringue bloquée,18/09/2026 10:15:00",
        "2,2012,Pression hors norme,18/09/2026 10:15:05",
        "",
        "Messages",
        "Module 1: auto-test échoué",
        "Avertissement de température",
        ""
    ]

    patient = initialiser_ligne_patient_vierge()
    patient = traiter_sous_section_1_erreurs(lignes_test_erreur, patient)

    print("✅ Sous-section 1 exécutée avec succès :")
    print(f"   • Nombre_message_erreur : {patient['Nombre_message_erreur']}")
    print(f"   • Message_Erreur        : {patient['Message_Erreur']}")
    print(f"   • Message_s             : {patient['Message_s']}")