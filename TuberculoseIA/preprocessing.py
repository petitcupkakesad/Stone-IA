# preprocessing.py
import chardet
import io
import re

def nettoyer_et_pretraiter_bytes(file_bytes: bytes) -> str:
    """
    Bloc 1 : Pré-traitement du contenu binaire GeneXpert
    - Détection et normalisation de l'encodage vers UTF-8 sans BOM
    - Nettoyage des lignes vides/fantômes en préservant les champs clés
    - Génération et écriture du fichier intermédiaire 'Pré-traitement_clined-file.txt'
    - Retourne le contenu texte nettoyé
    """
    raw_data = file_bytes

    # 1) Détection de l'encodage et suppression du BOM
    if raw_data.startswith(b'\xff\xfe') or raw_data.startswith(b'\xfe\xff'):
        content = raw_data.decode('utf-16')
    elif raw_data.startswith(b'\xef\xbb\xbf'):
        content = raw_data[3:].decode('utf-8', errors='replace')
    else:
        detection = chardet.detect(raw_data)
        detected_encoding = detection.get('encoding') or 'utf-8'
        try:
            content = raw_data.decode(detected_encoding)
        except (UnicodeDecodeError, TypeError):
            content = raw_data.decode('utf-8', errors='ignore')

    # 2) Nettoyage ligne par ligne
    lignes = content.splitlines()
    lignes_nettoyees = []

    champs_a_conserver = [
        "sample type", "notes", "run notes", "patient id", 
        "sample id", "test date", "user", "status"
    ]

    for ligne in lignes:
        ligne_epuree = ligne.replace('\uFEFF', '').strip()

        contient_champ_reconnu = any(
            ligne_epuree.lower().startswith(champ) for champ in champs_a_conserver
        )

        # Règle 2.a & 2.b : Si la ligne est vide et ne contient pas de champ clé, on l'ignore
        if not ligne_epuree and not contient_champ_reconnu:
            continue

        lignes_nettoyees.append(ligne.replace('\uFEFF', ''))

    contenu_final = "\n".join(lignes_nettoyees)

    # 4) Génération du fichier intermédiaire sur le disque
    fichier_sortie = "Pré-traitement_clined-file.txt"
    with open(fichier_sortie, 'w', encoding='utf-8', newline='') as f:
        f.write(contenu_final)

    return contenu_final