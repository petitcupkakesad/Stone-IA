# reparer_modele.py
import torch
import os
import numpy as np

chemin = "modeles/stone_g4_model.pt"

if not os.path.exists(chemin):
    print("❌ Fichier modèle introuvable.")
else:
    print("📂 Lecture brute du checkpoint...")
    # Chargement forcé pour récupérer le contenu actuel
    checkpoint = torch.load(chemin, map_location='cpu', weights_only=False)
    
    # Extraction des données du scaler sous forme de tableaux numpy purs (ou listes)
    mean_val = np.array(checkpoint['scaler_mean'], dtype=np.float32)
    scale_val = np.array(checkpoint['scaler_scale'], dtype=np.float32)
    
    # Reconstruction propre d'un dictionnaire sans objets complexes non sécurisés
    nouveau_checkpoint = {
        'model_state_dict': checkpoint['model_state_dict'],
        'scaler_mean': mean_val,
        'scaler_scale': scale_val,
        'features_list': checkpoint.get('features_list', ['PROBE A', 'PROBE B', 'PROBE C', 'PROBE D', 'PROBE E', 'SPC'])
    }
    
    # Sauvegarde propre
    torch.save(nouveau_checkpoint, chemin)
    print("[✔] Modèle réparé et ré-enregistré avec succès pour PyTorch 2.6+ !")