import streamlit as st
import pandas as pd

def colorer_lignes_urgence(row):
    """
    Applique un code couleur dynamique en fonction de la criticité clinique et du statut de résistance :
    - 🔴 ROUGE VIF : Résistance à la Rifampicine détectée (Urgence MDR-TB / Risque sanitaire majeur)
    - 🟡 JAUNE / ORANGE CLAIR : Trace détectée ou Résistance Indéterminée (Contrôle requis)
    - 🟠 ORANGE FONCÉ : Erreur technique ou Test non valide (Re-manipulation de la cartouche)
    - 🟢 VERT : MTB Non Détecté (Négatif / Sécurisé)
    - 🔵 BLEU CLAIR : MTB Détecté & Sensible / Wild-Type (Traitement standard)
    """
    res_raw = str(row.get('Test Result (Gold Standard)', '') or row.get('Test Result', '')).upper()
    classification = str(row.get('Classification Finale Stone IA', '')).upper()
    
    # 1. URGENCE CRITIQUE : Résistance détectée
    if "RESISTANCE DETECTED" in res_raw or "RÉSISTANCE DÉTECTÉE" in classification:
        return ['background-color: #ff4d4d; color: white; font-weight: bold'] * len(row)
    
    # 2. ATTENTION : Trace ou Indéterminé
    elif "TRACE" in res_raw or "INDETERMINATE" in res_raw or "INDÉTERMINÉ" in classification:
        return ['background-color: #ffeb3b; color: black; font-weight: bold'] * len(row)
    
    # 3. ERREUR TECHNIQUE : Erreur / Invalide / No Result
    elif any(err in res_raw or err in classification for err in ["ERROR", "INVALID", "NO RESULT", "ERREUR", "INVALIDE"]):
        return ['background-color: #ff9800; color: black; font-weight: bold'] * len(row)
    
    # 4. NÉGATIF : Sécurisé
    elif "NOT DETECTED" in res_raw or "NON DÉTECTÉ" in classification:
        return ['background-color: #d4edda; color: black'] * len(row)
    
    # 5. STANDARD SENSIBLE : Positif sensible (Wild-Type)
    else:
        return ['background-color: #cce5ff; color: black'] * len(row)

def afficher_tableau_affichage_urgences():
    st.subheader("🚨 Tableau d'Affichage & Triage des Urgences Cliniques (Stone IA)")
    st.markdown("""
    Ce tableau priorise les flux d'échantillons du laboratoire selon un code couleur standardisé pour l'aide à la décision médicale :
    * 🔴 **Rouge (#ff4d4d)** : **Résistance à la Rifampicine détectée** — *Urgence absolue (Suspicion de Tuberculose Multirésistante - MDR).*
    * 🟡 **Jaune (#ffeb3b)** : **Trace / Indéterminé** — *Nécessite une corrélation clinique ou un contrôle de second tour.*
    * 🟠 **Orange (#ff9800)** : **Erreur / Invalide** — *Échec technique de la cartouche ou de la PCR, à ré-analyser.*
    * 🟢 **Vert (#d4edda)** : **Négatif** — *Absence de détection de l'ADN de la bactérie.*
    * 🔵 **Bleu (#cce5ff)** : **Sensible (Wild-Type)** — *MTB détecté, sensible à la rifampicine.*
    """)
    
    # Vérification de la présence des données d'inférence Ultra ou G4 dans la session
    df_u = st.session_state.get("df_inference_ultra", pd.DataFrame())
    df_g4 = st.session_state.get("df_inference_g4", pd.DataFrame())
    
    # Fusion ou sélection du DataFrame actif
    if not df_u.empty:
        df_actif = df_u.copy()
        titre_source = "Module Ultra (Xpert MTB/RIF Ultra)"
    elif not df_g4.empty:
        df_actif = df_g4.copy()
        titre_source = "Module G4 (Xpert MTB/RIF Assay)"
    else:
        st.info("ℹ️ Aucun fichier d'analyse n'a encore été chargé ou exécuté dans la session active.")
        return

    st.markdown(f"**Source active affichée :** `{titre_source}` ({len(df_actif)} échantillons traités)")

    # Filtre rapide par niveau d'urgence pour le technicien ou le médecin
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtre_urgence = st.checkbox("🚨 Afficher uniquement les cas urgents / suspects (Résistances & Erreurs)", value=False)
    
    if filtre_urgence and not df_actif.empty:
        mask = df_actif.apply(lambda r: any(k in str(r.values).upper() for k in ["RESISTANCE DETECTED", "RÉSISTANCE DÉTECTÉE", "ERROR", "INVALID", "ERREUR", "TRACE"]), axis=1)
        df_affiche = df_actif[mask]
    else:
        df_affiche = df_actif

    if not df_affiche.empty:
        # Application du style de mise en forme conditionnelle pandas Styler
        styled_table = df_affiche.style.apply(colorer_lignes_urgence, axis=1)
        st.dataframe(styled_table, use_container_width=True)
        
        # Bouton d'export du rapport d'urgences
        csv_data = df_affiche.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Télécharger le registre de tri des urgences (.csv)",
            data=csv_data,
            file_name="registre_urgences_tuberculose_lnsp.csv",
            mime="text/csv"
        )
    else:
        st.warning("Aucun échantillon ne correspond aux critères sélectionnés.")