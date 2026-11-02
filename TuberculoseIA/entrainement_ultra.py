import os
import glob
import re
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

# 1. Architecture StoneUltraNet enrichie avec BatchNorm pour une haute précision
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
        x = self.relu(self.bn1(self.fc1(x)))
        x = self.dropout(x)
        x = self.relu(self.bn2(self.fc2(x)))
        return self.out(x)

def selectionner_fichiers_ultra():
    dossier_abs = os.path.dirname(os.path.abspath(__file__)) if __file__ else os.getcwd()
    fichiers = glob.glob(os.path.join(dossier_abs, "*.csv")) + glob.glob(os.path.join(dossier_abs, "*.xlsx"))
    dossier_csv = os.path.join(dossier_abs, "csv")
    if os.path.exists(dossier_csv):
        fichiers += glob.glob(os.path.join(dossier_csv, "*.csv")) + glob.glob(os.path.join(dossier_csv, "*.xlsx"))
        
    fichiers = sorted(list(set(fichiers)))

    if not fichiers:
        print("❌ Aucun fichier CSV ou Excel trouvé.")
        return None

    print("\n📁 Fichiers disponibles pour l'entraînement Ultra :")
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

def attribuer_label_ultra_exact(row):
    texte_ligne = " | ".join([str(row[c]) for c in row.index if pd.notna(row[c])]).upper()
    resultat_instr = str(row.get('Test Result', '')).strip().upper()

    # Cibles spécifiques GeneXpert MTB/RIF Ultra
    sondes_cibles = ['RPOB1', 'RPOB2', 'RPOB3', 'RPOB4', 'IS1081-IS6110', 'SPC']
    valeurs_ct = []

    for sonde in sondes_cibles:
        pattern = re.compile(rf"{sonde}\s*,\s*([0-9]+)\s*[\.,\,]\s*([0-9]+)", re.IGNORECASE)
        matches = pattern.findall(texte_ligne)
        val = 0.0
        if matches:
            ent, dec = matches[0]
            try:
                v = float(f"{ent}.{dec}")
                if 0 < v < 50:
                    val = v
            except ValueError:
                pass
        valeurs_ct.append(val)

    # --- Analyse robuste par mots-clés ---
    if any(err in resultat_instr for err in ['ERREUR', 'NON VALIDE', 'PAS DE RÉSULTAT']):
        return valeurs_ct, 7
    elif "NON DÉTECTÉ" in resultat_instr and "MTB" in resultat_instr and "RIF" not in resultat_instr:
        return valeurs_ct, 0
    elif "TRÈS BAS" in resultat_instr and ("DÉTECTÉ" in resultat_instr or "INDÉTERMINÉ" in resultat_instr) and "NON" not in resultat_instr:
        return valeurs_ct, 2
    elif "TRÈS BAS" in resultat_instr:
        return valeurs_ct, 1
    elif "BAS" in resultat_instr:
        return valeurs_ct, 3
    elif "MOYEN" in resultat_instr:
        return valeurs_ct, 4
    elif "ÉLEVÉ" in resultat_instr or "ELEVE" in resultat_instr:
        return valeurs_ct, 5
    elif "TRACE" in resultat_instr or "INDÉTERMINÉ" in resultat_instr:
        return valeurs_ct, 6
    else:
        return valeurs_ct, 7

def charger_donnees_ultra(liste_chemins: list):
    liste_X, liste_y = [], []

    for chemin in liste_chemins:
        if not os.path.exists(chemin):
            print(f"⚠️ Fichier introuvable : {chemin}")
            continue

        try:
            if chemin.endswith('.xlsx') or chemin.endswith('.xls'):
                df = pd.read_excel(chemin)
            else:
                df = pd.read_csv(chemin, encoding="utf-8-sig")
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement de {os.path.basename(chemin)} : {e}")
            continue

        if 'Test Result' in df.columns:
            df = df[df['Test Result'].notna()].copy()
            print(f"\n--- Fichier : {os.path.basename(chemin)} ---")
            print("Valeurs uniques de Test Result propres :")
            print(df['Test Result'].unique())

        for _, row in df.iterrows():
            valeurs_patient, label = attribuer_label_ultra_exact(row)
            liste_X.append(valeurs_patient)
            liste_y.append(label)

    X = np.array(liste_X, dtype=np.float32)
    y = np.array(liste_y, dtype=np.int64)
    return X, y

def entrainer_modele_stone_ultra():
    print("=" * 60)
    print("    ENTRAÎNEMENT STONE IA - MTB/RIF ULTRA (5-FOLD CV)     ")
    print("=" * 60)

    fichiers_selectionnes = selectionner_fichiers_ultra()
    if not fichiers_selectionnes:
        return

    print("\n📥 Chargement, extraction et labélisation des données Ultra...")
    X_raw, y_raw = charger_donnees_ultra(fichiers_selectionnes)

    if X_raw is None or len(X_raw) == 0:
        print("❌ Erreur : Aucune donnée extraite des fichiers sélectionnés.")
        return

    print(f"\n[+] {len(X_raw)} échantillons Ultra extraits au total.")
    unique, counts = np.unique(y_raw, return_counts=True)
    for u, c in zip(unique, counts):
        print(f"    - Classe {u} : {c} échantillons")
    print("Total validé :", sum(counts))

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    # Calcul dynamique et sécurisé des poids pour les 8 classes
    classes_possibles = list(range(8))
    class_weights = []
    total_echantillons = len(y_raw)

    for c in classes_possibles:
        nb_c = np.sum(y_raw == c)
        if nb_c > 0:
            w = total_echantillons / (len(classes_possibles) * nb_c)
        else:
            w = 1.0
        class_weights.append(w)

    class_weights_tensor = torch.tensor(class_weights, dtype=torch.float32)
    print(f"\n⚖️ Poids de classes calculés (8 classes) : {class_weights}")

    X_tensor = torch.tensor(X_scaled, dtype=torch.float32)
    y_tensor = torch.tensor(y_raw, dtype=torch.long)

    # Configuration de la validation croisée 5-Fold stratifiée
    k_folds = 5
    skf = StratifiedKFold(n_splits=k_folds, shuffle=True, random_state=42)

    best_global_acc = 0.0
    fold_accuracies = []

    print(f"\n[+] Lancement de la validation croisée sur {k_folds} plis (Folds)...")

    for fold, (train_idx, val_idx) in enumerate(skf.split(X_tensor, y_tensor)):
        print(f"\n--- 🔄 Pli (Fold) [{fold+1}/{k_folds}] ---")
        
        X_train, y_train = X_tensor[train_idx], y_tensor[train_idx]
        X_val, y_val = X_tensor[val_idx], y_tensor[val_idx]

        train_dataset = TensorDataset(X_train, y_train)
        val_dataset = TensorDataset(X_val, y_val)

        train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=64, shuffle=False)

        model = StoneUltraNet(input_dim=6, num_classes=8)
        criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)
        optimizer = optim.AdamW(model.parameters(), lr=0.01, weight_decay=1e-4)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=5)

        epochs = 100
        best_fold_acc = 0.0

        for epoch in range(epochs):
            model.train()
            running_loss = 0.0

            for batch_x, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                running_loss += loss.item() * batch_x.size(0)

            model.eval()
            correct, total = 0, 0
            with torch.no_grad():
                for batch_x, batch_y in val_loader:
                    outputs = model(batch_x)
                    preds = torch.argmax(outputs, dim=1)
                    correct += (preds == batch_y).sum().item()
                    total += batch_y.size(0)

            val_acc = correct / total if total > 0 else 0.0
            scheduler.step(val_acc)

            if val_acc > best_fold_acc:
                best_fold_acc = val_acc

            # Sauvegarde du meilleur modèle global tous plis confondus
            if val_acc > best_global_acc:
                best_global_acc = val_acc
                os.makedirs("modeles", exist_ok=True)
                torch.save({
                    'model_state_dict': model.state_dict(),
                    'scaler_mean': scaler.mean_,
                    'scaler_scale': scaler.scale_,
                    'features_list': ['rpoB1', 'rpoB2', 'rpoB3', 'rpoB4', 'IS1081-IS6110', 'SPC']
                }, "modeles/stone_ultra_model.pt")

        print(f"    ✔ Fin du Pli {fold+1} | Meilleure Précision Pli : {best_fold_acc * 100:.2f}%")
        fold_accuracies.append(best_fold_acc)

    mean_acc = np.mean(fold_accuracies) * 100
    print("\n" + "=" * 60)
    print(f"[✔] Entraînement 5-Fold CV terminé !")
    print(f"[📊] Précision moyenne sur les 5 plis : {mean_acc:.2f}%")
    print(f"[🏆] Meilleure précision globale atteinte : {best_global_acc * 100:.2f}%")
    print(f"[✔] Modèle optimal et scaler sauvegardés dans 'modeles/stone_ultra_model.pt'")
    print("=" * 60)

if __name__ == "__main__":
    entrainer_modele_stone_ultra()