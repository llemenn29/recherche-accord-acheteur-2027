
import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Recherche Acheteur - Accords 2027", page_icon="🔎", layout="wide")

# ============================================================
# Chargement des données
# ============================================================
@st.cache_data
def load_data():
    df = pd.read_csv("app_data.csv", dtype={"Code GNX": str, "CodeNegoscope": str}, encoding="utf-8-sig")
    df["Ambigu"] = df["Ambigu"].astype(str).str.lower().isin(["true", "1"])
    return df

df = load_data()

def extract_condition_num(code):
    m = re.search(r'(\d+)$', str(code))
    return int(m.group(1)) if m else 999999

def normalize_code_token(c):
    c = str(c).strip()
    return c.lstrip("0") or "0"

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
    - La clé d'un **Accord** est la combinaison **Nom de l'accord + Négoscope** : un accord n'a qu'un seul
      Négoscope rattaché, mais peut concerner plusieurs Sous-négoscopes.
    - La colonne **Code GNX** indique, pour chaque ligne d'accord, l'ensemble des codes ERP rattachés :
        - Au niveau du **Négoscope global**, elle regroupe **tous les codes** de ses sous-négoscopes.
        - Au niveau d'un **Sous-négoscope**, elle n'affiche que **son propre code**.
    - 🏢 Un bandeau met en évidence le **nom** de chaque fournisseur trouvé ainsi que l'**ensemble de ses
      codes GNX** rattachés.
    - 📋 Un **tableau résumé des accords** s'affiche ensuite. **Cliquez sur une ligne** pour filtrer le détail
      ci-dessous sur cet accord précis (utile quand un fournisseur a plusieurs accords, ex : BONDUELLE).
    - 📊 Les résultats du détail sont **classés automatiquement par Code Condition**, en se basant sur les
      chiffres situés à droite du code (ex : CCP001 → 001 → en premier, puis PPP002 → 002, etc.).
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
# Logique de filtrage principal
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
    code_stripped = normalize_code_token(code_norm)
    mask = df["Code GNX_list"].astype(str).apply(
        lambda s: code_stripped in [normalize_code_token(x) for x in s.split(",")]
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

    nb_accords = result.groupby(["Accord", "root_name"]).ngroups
    nb_fournisseurs_r = result["Fournisseur"].nunique()
    c1, c2, c3 = st.columns(3)
    c1.metric("Lignes trouvées (total)", len(result))
    c2.metric("Accord(s) concerné(s)", nb_accords)
    c3.metric("Fournisseur(s)", nb_fournisseurs_r)

    # --------------------------------------------------------
    # Bandeau Nom fournisseur + Codes GNX rattachés
    # --------------------------------------------------------
    st.markdown("#### 🏢 Fournisseur(s) identifié(s) — Codes GNX rattachés")
    supplier_groups = {}
    for _, row in result.iterrows():
        nom = row["Fournisseur"]
        codes = [c.strip() for c in str(row["Code GNX_list"]).split(",") if c.strip()]
        supplier_groups.setdefault(nom, set()).update(int(c) for c in codes)

    for nom in sorted(supplier_groups.keys()):
        codes_sorted = sorted(supplier_groups[nom])
        codes_str = "  ".join(f"`{c:06d}`" for c in codes_sorted)
        st.markdown(f"**{nom}** : {codes_str}")

    st.markdown("---")

    # --------------------------------------------------------
    # Tableau résumé des accords (clé = Accord + Négoscope)
    # --------------------------------------------------------
    st.markdown(f"#### 📋 Résumé des accords concernés ({nb_accords} accord(s))")

    summary_rows = []
    for (acc, root), grp in result.groupby(["Accord", "root_name"]):
        fournisseur = grp["Fournisseur"].iloc[0]
        all_slabs = sorted(grp["Negoscope_SousNegoscope"].unique())
        sous_negoscopes = [s for s in all_slabs if s.strip().startswith("SNS")]
        all_codes = set()
        for l in grp["Code GNX_list"]:
            for c in str(l).split(","):
                c = c.strip()
                if c:
                    all_codes.add(int(c))
        codes_gnx_str = ", ".join(f"{c:06d}" for c in sorted(all_codes))
        summary_rows.append({
            "Fournisseur": fournisseur,
            "Accord": acc,
            "Négoscope": root,
            "Sous-négoscopes concernés": ", ".join(sous_negoscopes) if sous_negoscopes else "—",
            "Codes GNX concernés": codes_gnx_str,
            "_key": f"{acc}||{root}"
        })

    summary_df = pd.DataFrame(summary_rows).sort_values("Accord").reset_index(drop=True)

    if len(summary_df) > 1:
        st.caption("👆 Sélectionnez un accord ci-dessous pour focaliser le détail sur celui-ci (ou laissez sur « Tous »).")

    options = ["— Tous les accords —"] + summary_df["_key"].tolist()
    labels = {row["_key"]: f"{row['Accord']} | {row['Négoscope']}" for _, row in summary_df.iterrows()}

    def format_option(key):
        if key == "— Tous les accords —":
            return "🔁 Tous les accords"
        return labels.get(key, key)

    selected_key = st.selectbox(
        "Filtrer le détail sur un accord précis :",
        options=options,
        format_func=format_option,
        index=0,
        key="accord_focus"
    )

    st.dataframe(
        summary_df.drop(columns=["_key"]),
        use_container_width=True,
        height=min(350, 60 + 35 * len(summary_df))
    )

    # --------------------------------------------------------
    # Application du filtre de focus sur le détail
    # --------------------------------------------------------
    if selected_key != "— Tous les accords —":
        acc_sel, root_sel = selected_key.split("||")
        detail_df = result[(result["Accord"] == acc_sel) & (result["root_name"] == root_sel)].copy()
        st.info(f"🔎 Détail filtré sur l'accord **{acc_sel}** — Négoscope **{root_sel}** "
                f"({len(detail_df)} ligne(s) de condition)")
    else:
        detail_df = result.copy()

    st.markdown("---")

    # --------------------------------------------------------
    # Tableau détail des conditions, trié par Code Condition (suffixe numérique)
    # --------------------------------------------------------
    st.markdown("#### 📑 Détail des conditions négociées")

    detail_df["_CondNum"] = detail_df["Code_Condition"].apply(extract_condition_num)
    detail_df = detail_df.sort_values("_CondNum").reset_index(drop=True)

    display_cols = ["Fournisseur", "Accord", "Negoscope_SousNegoscope", "Code GNX",
                     "Code_Condition", "Libelle_Condition", "Valeur"]
    rename_cols = {
        "Negoscope_SousNegoscope": "Négoscope / Sous-négoscope",
        "Code_Condition": "Code Condition",
        "Libelle_Condition": "Libellé Condition",
    }
    display_df = detail_df[display_cols].rename(columns=rename_cols).reset_index(drop=True)

    def highlight_ambigu(row):
        orig_idx = detail_df.index[row.name]
        if detail_df.loc[orig_idx, "Ambigu"]:
            return ["background-color: #FFF3CD"] * len(row)
        return [""] * len(row)

    st.caption("📊 Classement : Code Condition croissant (basé sur le suffixe numérique, ex: CCP001 → 1).")

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
