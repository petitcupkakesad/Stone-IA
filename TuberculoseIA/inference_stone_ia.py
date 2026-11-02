# inference_stone_ia.py
import torch
import torch.nn as nn
import numpy as np

class StoneG4Net(nn.Module):
    def __init__(self, input_dim=6):
        super(StoneG4Net, self).__init__()
        self.fc1 = nn.Linear(input_dim, 64)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(0.3)
        self.fc2 = nn.Linear(64, 32)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(0.3)
        self.fc3 = nn.Linear(32, 4)  # 4 classes : Négatif, Sensible, Résistant, Erreur/Invalide

    def forward(self, x):
        out = self.fc1(x)
        out = self.relu1(out)
        out = self.dropout1(out)
        out = self.fc2(out)
        out = self.relu2(out)
        out = self.dropout2(out)
        out = self.fc3(out)
        return out

def charger_modele_et_scaler(chemin_modele="modeles/stone_g4_model.pt"):
    # weights_only=False est obligatoire ici car le checkpoint contient le scaler et les métadonnées, pas seulement les poids bruts.
    checkpoint = torch.load(chemin_modele, map_location=torch.device('cpu'), weights_only=False)
    
    model = StoneG4Net(input_dim=6)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    mean = np.array(checkpoint['scaler_mean'], dtype=np.float32)
    scale = np.array(checkpoint['scaler_scale'], dtype=np.float32)
    features = checkpoint.get('features_list', ['PROBE A', 'PROBE B', 'PROBE C', 'PROBE D', 'PROBE E', 'SPC'])
    
    return model, mean, scale, features

def predire_echantillon(model, mean, scale, valeurs_ct):
    vals_array = np.array(valeurs_ct, dtype=np.float32).reshape(1, -1)
    vals_scaled = (vals_array - mean) / scale
    
    tensor_x = torch.tensor(vals_scaled, dtype=torch.float32)
    
    with torch.no_grad():
        outputs = model(tensor_x)
        probs = torch.softmax(outputs, dim=1)
        conf, pred = torch.max(probs, dim=1)
        
    return int(pred.item()), float(conf.item()) * 100.0

# ==========================================
# 2. ARCHITECTURE & INFÉRENCE : ULTRA (8 classes)
# ==========================================
class StoneUltraNet(nn.Module):
    def __init__(self, input_dim=6, num_classes=8):
        super(StoneUltraNet, self).__init__()
        self.fc1 = nn.Linear(input_dim, 128)
        self.bn1 = nn.BatchNorm1d(128)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.2)
        
        self.fc2 = nn.Linear(128, 64)
        self.bn2 = nn.BatchNorm1d(64)
        
        self.out = nn.Linear(64, num_classes)

    def forward(self, x):
        # En mode inférence, batch_size=1, on désactive ou gère le BatchNorm de manière sécurisée
        if x.size(0) == 1:
            self.eval() # bascule temporaire en eval pour éviter les erreurs de batch size 1 sur BatchNorm
        x = self.relu(self.bn1(self.fc1(x)))
        x = self.dropout(x)
        x = self.relu(self.bn2(self.fc2(x)))
        return self.out(x)

def charger_modele_et_scaler_ultra(chemin_modele="modeles/stone_ultra_model.pt"):
    checkpoint = torch.load(chemin_modele, map_location=torch.device('cpu'), weights_only=False)
    
    model = StoneUltraNet(input_dim=6, num_classes=8)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    mean = np.array(checkpoint['scaler_mean'], dtype=np.float32)
    scale = np.array(checkpoint['scaler_scale'], dtype=np.float32)
    features = checkpoint.get('features_list', ['rpoB1', 'rpoB2', 'rpoB3', 'rpoB4', 'IS1081-IS6110', 'SPC'])
    
    return model, mean, scale, features

def predire_echantillon_ultra(model, mean, scale, valeurs_ct):
    vals_array = np.array(valeurs_ct, dtype=np.float32).reshape(1, -1)
    vals_scaled = (vals_array - mean) / scale
    
    tensor_x = torch.tensor(vals_scaled, dtype=torch.float32)
    
    with torch.no_grad():
        model.eval()
        outputs = model(tensor_x)
        probs = torch.softmax(outputs, dim=1)
        conf, pred = torch.max(probs, dim=1)
        
    return int(pred.item()), float(conf.item()) * 100.0

# Dictionnaire officiel des libellés Ultra (8 classes)
CLASSES_ULTRA_LABELS = {
    0: "MTB Non Détecté",
    1: "MTB Détecté Très Bas | RIF Résistance Non Détecté",
    2: "MTB Détecté Très Bas | RIF Résistance Détecté / Indéterminé",
    3: "MTB Détecté Bas | RIF Résistance Non Détecté / Indéterminé",
    4: "MTB Détecté Moyen | RIF Résistance Non Détecté",
    5: "MTB Détecté Élevé | RIF Résistance Détecté / Non Détecté",
    6: "MTB Trace Détecté | RIF Résistance Indéterminé",
    7: "Erreur / Non Valide / Pas de Résultat"
}


# ==========================================
# 3. CONSTRUCTION DU TABLEAU DE RÉSULTATS RICHE
# ==========================================
def formater_tableau_resultats_ultra(df_brut, liste_predictions, liste_confiances):
    """
    Enrichit le DataFrame d'origine avec les colonnes d'analyse IA et métadonnées demandées.
    """
    df_resultats = df_brut.copy()
    
    # Ajout des colonnes de prédiction IA
    df_resultats["Résultat IA Ultra"] = [CLASSES_ULTRA_LABELS.get(p, "Inconnu") for p in liste_predictions]
    df_resultats["Prédiction Confiance"] = [f"{c:.2f}%" for c in liste_confiances]
    
    # Liste des colonnes cibles à afficher en priorité dans l'interface
    colonnes_prioritaires = [
        "Sample ID", 
        "Patient ID", 
        "IS1081-IS6110", 
        "SPC", 
        "Résultat IA Ultra", 
        "Prédiction Confiance", 
        "Test Result",  # Résultat Instrument d'origine
        "System Name", 
        "Cartridge S/N", 
        "Instrument S/N", 
        "Reagent Lot ID", 
        "Expiration Date", 
        "Start Time"
    ]
    
    # Filtrer uniquement les colonnes présentes dans le DataFrame pour éviter les erreurs
    colonnes_finales = [col for col in colonnes_prioritaires if col in df_resultats.columns]
    
    # S'il reste d'autres colonnes utiles, on peut les conserver ou se focaliser sur celles-ci
    return df_resultats[colonnes_finales]