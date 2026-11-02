# train_stone_for_mtb_rif_assey_g4.py
import os
import glob
import re
import io
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score

# ---------------------------------------------------------
# 1. Sélection Interactive des Fichiers
# ---------------------------------------------------------
def selectionner_fichiers(dossier_csv="csv"):
    dossier_abs = os.path.dirname(os.path.abspath(__file__))
    fichiers = [os.path.join(dossier_abs, "tableau_MTB_RIF_G4_LNSP_23_juillet_2021.csv")]
    
    # Recherche additionnelle si besoin
    fichiers += glob.glob(os.path.join(dossier_abs, "*.csv")) + glob.glob(os.path.join(dossier_abs, "*.xlsx"))
    fichiers = list(set(fichiers)) # déduplication
    
    if not fichiers:
        print(f"❌ Aucun fichier trouvé.")
        return None

    print("\n📁 Fichiers disponibles pour l'entraînement :")
    print(" [0] 🚀 ENTRAÎNER SUR TOUS LES FICHIERS COMBINÉS (Consolidation globale)")
    for idx, f in enumerate(fichiers):
        print(f" [{idx + 1}] {os.path.basename(f)}")
        
    try:
        choix = int(input("\nEntrez le numéro du fichier à utiliser (ou 0 pour tous) : "))
        if choix == 0:
            return fichiers
        elif 1 <= choix <= len(fichiers):
            return [fichiers[choix - 1]]
        else:
            return fichiers
    except ValueError:
        return fichiers

# ---------------------------------------------------------
# 2. Parsing Robuste et Labélisation Intelligente (4 Classes)
# ---------------------------------------------------------
def charger_et_preparer_donnees(liste_chemins: list):
    sondes_cibles = ['PROBE A', 'PROBE B', 'PROBE C', 'PROBE D', 'PROBE E', 'SPC']
    liste_X, liste_y = [], []

    for chemin in liste_chemins:
        if not os.path.exists(chemin):
            continue
        try:
            df = pd.read_csv(chemin, encoding="latin1")
        except Exception:
            try:
                df = pd.read_excel(chemin)
            except Exception:
                continue

        # Filtrer uniquement les lignes contenant des résultats valides
        if 'Test Result' in df.columns:
            df = df[df['Test Result'].notna()].copy()

        for _, row in df.iterrows():
            texte_ligne = " | ".join([str(row[c]) for c in df.columns if pd.notna(row[c])]).upper()
            resultat_instr = str(row.get('Test Result', '')).upper()
            
            # Extraction multi-blocs des Ct des sondes
            valeurs_patient = []
            for sonde in sondes_cibles:
                pattern = re.compile(rf"{sonde}[,\s:]+([0-9\.\-]+)", re.IGNORECASE)
                matches = pattern.findall(texte_ligne)
                
                val = 0.0
                if matches:
                    valeurs_trouvees = []
                    for m in matches:
                        try:
                            v = float(m)
                            if v > 0: # on privilégie les Ct d'amplification valides (>0)
                                valeurs_trouvees.append(v)
                        except ValueError:
                            pass
                    if valeurs_trouvees:
                        val = valeurs_trouvees[0]
                valeurs_patient.append(val)

            # Détermination rigoureuse de la vérité terrain (Classes 0, 1, 2, 3)
            # Classe 0 : Négatif / Non Détecté (MTB Non Détecté avec SPC valide)
            # Classe 1 : Positif Sensible (MTB Détecté, Rif Non Résistant)
            # Classe 2 : Positif Résistant (MTB Détecté, Rif Résistant)
            # Classe 3 : Indéterminé / Erreur technique
            
            is_error = 'ERREUR' in resultat_instr or 'ERROR' in resultat_instr or 'PAS DE RÉSULTAT' in resultat_instr
            is_resistant = 'RESISTANT' in resultat_instr or 'RÉSI' in resultat_instr
            is_detected = 'DETECTED' in resultat_instr or 'DÉTECTÉ' in resultat_instr
            
            if is_error:
                label = 3
            elif is_detected and is_resistant:
                label = 2
            elif is_detected and not is_resistant:
                label = 1
            else:
                label = 0 # Négatif valide

            liste_X.append(valeurs_patient)
            liste_y.append(label)

    X = np.array(liste_X, dtype=np.float32)
    y = np.array(liste_y, dtype=np.int64)
    return X, y, sondes_cibles

# ---------------------------------------------------------
# 3. Architecture Réseau de Neurones Multiclasse (4 Classes)
# ---------------------------------------------------------
class StoneG4Net(nn.Module):
    def __init__(self, input_dim):
        super(StoneG4Net, self).__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 4)  # 4 classes de sortie distinctes
        )

    def forward(self, x):
        return self.network(x)

# ---------------------------------------------------------
# 4. Entraînement Global
# ---------------------------------------------------------
def entrainer_modele_g4(liste_fichiers: list):
    print(f"\n📥 Chargement et analyse des données...")
    X, y, features = charger_et_preparer_donnees(liste_fichiers)
    
    print(f"📊 Dataset total : {X.shape[0]} échantillons analysés.")
    for c in range(4):
        print(f"   - Classe {c} : {np.sum(y == c)} échantillons")

    if X.shape[0] == 0:
        print("❌ Erreur : Aucune donnée valide extraite.")
        return

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    X_train_t = torch.tensor(X_train_scaled, dtype=torch.float32)
    y_train_t = torch.tensor(y_train, dtype=torch.long)
    X_test_t = torch.tensor(X_test_scaled, dtype=torch.float32)
    y_test_t = torch.tensor(y_test, dtype=torch.long)

    model = StoneG4Net(input_dim=X_train.shape[1])
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.003)

    epochs = 150
    print("\n🚀 Début de l'apprentissage profond...")
    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        outputs = model(X_train_t)
        loss = criterion(outputs, y_train_t)
        loss.backward()
        optimizer.step()

        if (epoch + 1) % 30 == 0:
            print(f"Epoch [{epoch+1}/{epochs}] - Loss: {loss.item():.4f}")

    model.eval()
    with torch.no_grad():
        logits = model(X_test_t)
        preds = torch.argmax(logits, dim=1)
        acc = accuracy_score(y_test, preds.numpy())
        print(f"\n✅ Entraînement terminé ! Précision globale : {acc * 100:.2f}%\n")
        print("Rapport de classification :")
        print(classification_report(y_test, preds.numpy(), zero_division=0))

    dossier_modeles = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modeles")
    os.makedirs(dossier_modeles, exist_ok=True)
    
    chemin_sauvegarde = os.path.join(dossier_modeles, "stone_g4_model.pt")
    torch.save({
        'model_state_dict': model.state_dict(),
        'scaler_mean': scaler.mean_,
        'scaler_scale': scaler.scale_,
        'features_list': features
    }, chemin_sauvegarde)
    
    print(f"💾 Modèle intelligent sauvegardé sous : '{chemin_sauvegarde}'")

if __name__ == "__main__":
    fichiers_choisis = selectionner_fichiers("csv")
    if fichiers_choisis:
        entrainer_modele_g4(fichiers_choisis)