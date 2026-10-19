
import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Recherche Acheteur - Accords 2027", page_icon="🔎", layout="wide")

# ============================================================
# Chargement des données
# ============================================================
@st.cache_data
def load_data():
    df = pd.read_csv("app_data.csv", dtype={"Code GNX": str}, encoding="utf-8-sig")
    df["Ambigu"] = df["Ambigu"].astype(str).str.lower().isin(["true", "1"])
    return df

df = load_data()

# ============================================================
# En-tête
# ============================================================
st.title("🔎 Recherche Acheteur — Accords & Conditions 2027")
st.markdown(
    "Saisissez le **nom d'un fournisseur** *ou* un **code ERP / code GNX** pour afficher "
    "l'ensemble des lignes de l'accord correspondant, avec le détail des conditions négociées."
)

with st.expander("ℹ️ Comment ça marche ?", expanded=False):
    st.markdown("""
    - Un **Négoscope** est un périmètre de négociation global avec un fournisseur.
    - Un **Sous-négoscope** est un sous-périmètre plus précis, rattaché à un Négoscope.
    - La colonne **Code GNX** indique, pour chaque ligne d'accord, l'ensemble des codes ERP rattachés :
        - Au niveau du **Négoscope global**, elle regroupe **tous les codes** de ses sous-négoscopes.
        - Au niveau d'un **Sous-négoscope**, elle n'affiche que **son propre code**.
    - **Exemple** : taper `001581` fait apparaître le fournisseur **SBV**. Les lignes liées au Négoscope
      `NS - 050107 - SBV` afficheront `Code GNX = 001581, 001582, 001583, 001584`, tandis que les lignes
      liées au Sous-négoscope `SNS - 001581 - SBV BRUT SURG` n'afficheront que `001581`.
    - ⚠️ Certains codes sont **ambigus** (portés par plusieurs négoscopes différents). Une alerte s'affiche
      dans ce cas — vérifiez bien le nom du fournisseur.
    """)

st.divider()

# ============================================================
# Zone de recherche
# ============================================================
col1, col2 = st.columns(2)

fournisseurs_list = sorted(df["Fournisseur"].dropna().unique().tolist())

with col1:
    fournisseur_input = st.selectbox(
        "👤 Rechercher par NOM de fournisseur",
        options=[""] + fournisseurs_list,
        index=0,
        help="Sélectionnez un fournisseur dans la liste déroulante."
    )
    fournisseur_text = st.text_input(
        "...ou tapez directement un nom (recherche partielle)",
        value="",
        placeholder="ex: SBV, OVIMPEX, BIGARD..."
    )

with col2:
    code_input = st.text_input(
        "🔢 Rechercher par CODE ERP / GNX",
        value="",
        placeholder="ex: 001581 ou 1581"
    )

st.divider()

# ============================================================
# Logique de filtrage
# ============================================================
def normalize_code(c):
    c = c.strip()
    if c.isdigit():
        return c.zfill(6)
    return c

result = pd.DataFrame()
search_mode = None

if fournisseur_input:
    result = df[df["Fournisseur"] == fournisseur_input].copy()
    search_mode = f"Fournisseur sélectionné : **{fournisseur_input}**"

elif fournisseur_text.strip():
    mask = df["Fournisseur"].str.contains(fournisseur_text.strip(), case=False, na=False)
    result = df[mask].copy()
    search_mode = f"Recherche texte fournisseur : **{fournisseur_text.strip()}**"

elif code_input.strip():
    code_norm = normalize_code(code_input)
    mask = df["Code GNX_list"].astype(str).apply(
        lambda s: code_norm.lstrip("0") in [x.strip().lstrip("0") for x in s.split(",")]
    )
    result = df[mask].copy()
    fournisseurs_trouves = result["Fournisseur"].unique().tolist()
    if len(fournisseurs_trouves) == 1:
        search_mode = f"Code **{code_norm}** → Fournisseur détecté : **{fournisseurs_trouves[0]}**"
    elif len(fournisseurs_trouves) > 1:
        search_mode = (f"⚠️ Code **{code_norm}** trouvé chez **{len(fournisseurs_trouves)} fournisseurs différents** "
                        f"(code ambigu) : {', '.join(fournisseurs_trouves)}")
    else:
        search_mode = f"Code **{code_norm}** → aucun résultat"

# ============================================================
# Affichage des résultats
# ============================================================
if search_mode:
    st.markdown(f"### {search_mode}")

if not result.empty:
    if result["Ambigu"].any():
        st.warning(
            "⚠️ Certaines lignes ci-dessous concernent un **code ambigu** "
            "(porté par plusieurs négoscopes différents). Vérifiez bien le fournisseur avant utilisation.",
            icon="⚠️"
        )

    nb_accords = result["Accord"].nunique()
    nb_fournisseurs = result["Fournisseur"].nunique()
    c1, c2, c3 = st.columns(3)
    c1.metric("Lignes trouvées", len(result))
    c2.metric("Accord(s) concerné(s)", nb_accords)
    c3.metric("Fournisseur(s)", nb_fournisseurs)

    display_cols = ["Fournisseur", "Accord", "Negoscope_SousNegoscope", "Code GNX",
                     "Code_Condition", "Libelle_Condition", "Valeur"]
    rename_cols = {
        "Negoscope_SousNegoscope": "Négoscope / Sous-négoscope",
        "Code_Condition": "Code Condition",
        "Libelle_Condition": "Libellé Condition",
    }

    display_df = result[display_cols].rename(columns=rename_cols).reset_index(drop=True)

    def highlight_ambigu(row):
        orig_idx = result.index[row.name]
        if result.loc[orig_idx, "Ambigu"]:
            return ["background-color: #FFF3CD"] * len(row)
        return [""] * len(row)

    st.dataframe(
        display_df.style.apply(highlight_ambigu, axis=1),
        use_container_width=True,
        height=min(600, 60 + 35 * len(display_df))
    )

    csv_export = display_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        "📥 Télécharger ce résultat (CSV)",
        data=csv_export,
        file_name="resultat_recherche_acheteur.csv",
        mime="text/csv"
    )

elif search_mode:
    st.info("Aucune ligne d'accord ne correspond à cette recherche.")
else:
    st.info("👆 Saisissez un fournisseur ou un code ci-dessus pour lancer la recherche.")

st.divider()
st.caption("Outil d'aide pour les accords 2027 — Base consolidée : "
           f"{df['Fournisseur'].nunique()} fournisseurs, {len(df)} lignes de conditions, "
           f"{df['root_name'].nunique()} négoscopes.")
