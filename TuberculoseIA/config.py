# config.py
import streamlit as st
import os
from supabase import create_client, Client

LOGO_PATH = "Logo.png"
MODELE_PATH = "modeles/stone_g4_model.pt"

CLASSES_DICT = {
    0: ("🟢 Négatif", "MTB Non Détecté"),
    1: ("🟡 Positif Sensible", "MTB Détecté - Sensible à la Rifampicine"),
    2: ("🔴 Positif Résistant", "MTB Détecté - Résistant à la Rifampicine"),
    3: ("⚪ Erreur / Invalide", "Résultat Invalide ou Erreur Technique")
}

ROLES_LIST = [
    "Personnel de santé",
    "Technicien de laboratoire",
    "Ingénieur de laboratoire",
    "Docteur",
    "Professeur titulaire"
]

@st.cache_resource
def init_supabase() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        return None

supabase = init_supabase()