# tester_scaling.py
import numpy as np
from inference_stone_ia import charger_modele_et_scaler

model, mean, scale, features = charger_modele_et_scaler("modeles/stone_g4_model.pt")

print("--- DIAGNOSTIC DU SCALER ---")
print(f"Features attendues : {features}")
print(f"Mean (Moyenne)     : {mean}")
print(f"Scale (Écart-type) : {scale}")

# Test avec l'échantillon 2
valeurs_ct_ech2 = [28.7, 27.9, 27.8, 28.5, 31.0, 23.2]
vals_array = np.array(valeurs_ct_ech2, dtype=np.float32).reshape(1, -1)

print(f"\nValeurs brutes échantillon 2 : {vals_array}")
vals_scaled = (vals_array - mean) / scale
print(f"Valeurs après scaling        : {vals_scaled}")