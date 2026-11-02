# entrainement.py
import os
import glob
import re
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_class_weight
from inference_stone_ia import StoneG4Net

def selectionner_fichiers():
    dossier_abs = os.path.dirname(os.path.abspath(__file__)) if __file__ else os.getcwd()
    fichiers = glob.glob(os.path.join(dossier_abs, "*.csv")) + glob.glob(os.path.join(dossier_abs, "*.xlsx"))
    dossier_csv = os.path.join(dossier_abs, "csv")
    if os.path.exists(dossier_csv):
        fichiers += glob.glob(os.path.join(dossier_csv, "*.csv")) + glob.glob(os.path.join(dossier_csv, "*.xlsx"))
        
    fichiers = sorted(list(set(fichiers)))

    if not fichiers:
        print("❌ Aucun fichier CSV ou Excel trouvé.")
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

def attribuer_label_g4_exact(row):
    texte_ligne = " | ".join([str(row[c]) for c in row.index if pd.notna(row[c])]).upper()
    resultat_instr = str(row.get('Test Result', '')).upper()

    sondes_cibles = ['PROBE A', 'PROBE B', 'PROBE C', 'PROBE D', 'PROBE E', 'SPC']
    valeurs_ct = []

    # 1. Extraction tolérante aux virgules décimales (ex: Probe D,21,9)
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

    sondes_ae = valeurs_ct[:5]
    spc_valeur = valeurs_ct[5]
    sondes_actives = [v for v in sondes_ae if v > 0.0]
    nb_actives = len(sondes_actives)

    # 2. Analyse des chaînes de caractères
    is_error = any(err in resultat_instr for err in ['ERREUR', 'ERROR', 'INVALID', 'NON VALIDE', 'NO RESULT', 'PAS DE RÃ'])
    is_non_detecte = any(nd in resultat_instr for nd in ['NON DÉTECTÉ', 'NOT DETECTED', 'NON DÃ', 'NON DETECTE'])
    
    is_detecte = ('DÉTECTÉ' in resultat_instr or 'DETECTED' in resultat_instr or 'DÃ' in resultat_instr) and not is_non_detecte
    
    is_rif_detecte = ('RESISTANCE DETECTED' in resultat_instr or 'RÉSISTANCE DÉTECTÉE' in resultat_instr or 'RÃ‰SISTANCE' in resultat_instr) and not ('RIF RESISTANCE NON' in resultat_instr or 'RIF RESISTANCE NOT' in resultat_instr or 'RESISTANCE NON DÃ' in resultat_instr)

    # 3. Attribution stricte et corrigée des 4 classes
    if is_error or (nb_actives == 0 and spc_valeur == 0.0 and not is_non_detecte):
        return valeurs_ct, 3  # Classe 3 : Invalide / Erreur
    elif nb_actives >= 2 or is_detecte:
        if is_rif_detecte:
            return valeurs_ct, 2  # Classe 2 : Positif Résistant
        else:
            return valeurs_ct, 1  # Classe 1 : Positif Sensible
    else:
        return valeurs_ct, 0  # Classe 0 : Négatif

def charger_donnees_g4(liste_chemins: list):
    liste_X, liste_y = [], []

    for chemin in liste_chemins:
        if not os.path.exists(chemin):
            print(f"⚠️ Fichier introuvable : {chemin}")
            continue

        try:
            if chemin.endswith('.xlsx') or chemin.endswith('.xls'):
                df = pd.read_excel(chemin)
            else:
                df = pd.read_csv(chemin, encoding="latin1")
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement de {os.path.basename(chemin)} : {e}")
            continue

        if 'Test Result' in df.columns:
            df = df[df['Test Result'].notna()].copy()

        for _, row in df.iterrows():
            valeurs_patient, label = attribuer_label_g4_exact(row)
            liste_X.append(valeurs_patient)
            liste_y.append(label)

    X = np.array(liste_X, dtype=np.float32)
    y = np.array(liste_y, dtype=np.int64)
    return X, y

def entrainer_modele_stone_ia():
    print("=" * 60)
    print("    ENTRAÎNEMENT STONE IA - G4 (ROBUSTE & 4 CLASSES)   ")
    print("=" * 60)

    fichiers_selectionnes = selectionner_fichiers()
    if not fichiers_selectionnes:
        return

    print("\n📥 Chargement, extraction et labélisation des données...")
    X_raw, y_raw = charger_donnees_g4(fichiers_selectionnes)

    if X_raw is None or len(X_raw) == 0:
        print("❌ Erreur : Aucune donnée extraite des fichiers sélectionnés.")
        return

    print(f"\n[+] {len(X_raw)} échantillons extraits au total.")
    unique, counts = np.unique(y_raw, return_counts=True)
    for u, c in zip(unique, counts):
        print(f"    - Classe {u} : {c} échantillons")
    print("Total validé :", sum(counts))

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    # Calcul des poids de classes pour équilibrer l'apprentissage
    class_weights = compute_class_weight('balanced', classes=np.unique(y_raw), y=y_raw)
    class_weights_tensor = torch.tensor(class_weights, dtype=torch.float32)
    print(f"\n⚖️ Poids de classes calculés : {class_weights}")

    X_tensor = torch.tensor(X_scaled, dtype=torch.float32)
    y_tensor = torch.tensor(y_raw, dtype=torch.long)

    X_train, X_test, y_train, y_test = train_test_split(X_tensor, y_tensor, test_size=0.15, random_state=42, stratify=y_tensor)

    train_dataset = TensorDataset(X_train, y_train)
    val_dataset = TensorDataset(X_test, y_test)

    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=64, shuffle=False)

    model = StoneG4Net(input_dim=6)
    criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)
    optimizer = optim.AdamW(model.parameters(), lr=0.01, weight_decay=1e-4)

    epochs = 50
    best_acc = 0.0

    print(f"\n[+] Lancement de l'apprentissage sur {len(train_dataset)} exemples...")

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

        epoch_loss = running_loss / len(train_dataset)

        model.eval()
        correct, total = 0, 0
        with torch.no_grad():  # CORRIGÉ ICI
            for batch_x, batch_y in val_loader:
                outputs = model(batch_x)
                preds = torch.argmax(outputs, dim=1)
                correct += (preds == batch_y).sum().item()
                total += batch_y.size(0)

        val_acc = correct / total if total > 0 else 0.0

        if val_acc >= best_acc:
            best_acc = val_acc
            os.makedirs("modeles", exist_ok=True)
            torch.save({
                'model_state_dict': model.state_dict(),
                'scaler_mean': scaler.mean_,
                'scaler_scale': scaler.scale_,
                'features_list': ['PROBE A', 'PROBE B', 'PROBE C', 'PROBE D', 'PROBE E', 'SPC']
            }, "modeles/stone_g4_model.pt")

        if (epoch + 1) % 10 == 0:
            print(f"Époque [{epoch+1}/{epochs}] - Perte Train: {epoch_loss:.4f} | Précision Val: {val_acc * 100:.2f}%")

    print("\n" + "=" * 60)
    print(f"[✔] Entraînement terminé ! Meilleure précision : {best_acc * 100:.2f}%")
    print(f"[✔] Modèle et scaler sauvegardés dans 'modeles/stone_g4_model.pt'")
    print("=" * 60)

if __name__ == "__main__":
    entrainer_modele_stone_ia()