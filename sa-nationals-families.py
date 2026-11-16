"""
SA Nationals 2026 — Family Analysis

Answers: Are there more masters competitors who have kids in nippers or in lifeguards?
Families identified by shared surname + club.

Run: streamlit run sa-nationals-families.py
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

RAW_DIR = Path(__file__).parent / "raw-lifesavingsa"

EVENTS = {
    "Nippers": "478250.json",        # 2026 DHL SA Lifesaving Nippers Surf Championships
    "Lifeguards": "478184.json",     # 2026 DHL SA Lifesaving Junior & Senior Surf Championships
    "Masters": "478458.json",        # 2026 DHL SA Lifesaving Masters Surf Championships
}


def load_athletes(filename: str) -> pd.DataFrame:
    path = RAW_DIR / filename
    with open(path) as f:
        data = json.load(f)
    evt = data["data"]["event"]
    rows = []
    seen = set()
    for div in evt["eventDivisions"]:
        div_name = div["division"]["name"]
        for heat in div["heats"]:
            for result in heat["result"]:
                comp = result["competitor"]
                athlete = comp["athlete"]
                aid = athlete["id"]
                if aid not in seen:
                    seen.add(aid)
                    rows.append({
                        "athlete_id": aid,
                        "first_name": athlete.get("firstName", ""),
                        "last_name": athlete.get("lastName", ""),
                        "club": comp.get("teamName", ""),
                    })
    return pd.DataFrame(rows)


def load_all():
    frames = {}
    for category, filename in EVENTS.items():
        df = load_athletes(filename)
        df["category"] = category
        frames[category] = df
    return frames


def find_families(frames):
    masters = frames["Masters"]
    nippers = frames["Nippers"]
    lifeguards = frames["Lifeguards"]

    # Build surname+club sets for nippers and lifeguards
    nipper_keys = set(zip(nippers["last_name"].str.upper(), nippers["club"].str.upper()))
    lifeguard_keys = set(zip(lifeguards["last_name"].str.upper(), lifeguards["club"].str.upper()))

    results = []
    for _, row in masters.iterrows():
        key = (row["last_name"].upper(), row["club"].upper())
        in_nippers = key in nipper_keys
        in_lifeguards = key in lifeguard_keys

        if in_nippers and in_lifeguards:
            family_type = "Both"
        elif in_nippers:
            family_type = "Nippers"
        elif in_lifeguards:
            family_type = "Lifeguards"
        else:
            family_type = "None"

        results.append({
            "master_athlete_id": row["athlete_id"],
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "club": row["club"],
            "kids_in_nippers": in_nippers,
            "kids_in_lifeguards": in_lifeguards,
            "family_type": family_type,
        })

    return pd.DataFrame(results)


# --- Streamlit app ---

st.set_page_config(page_title="SA Nationals 2026 — Family Analysis", layout="wide")
st.title("SA Nationals 2026 — Family Analysis")
st.caption("Masters competitors matched to Nippers / Lifeguards by surname + club")

frames = load_all()
family_df = find_families(frames)

# Summary counts
st.subheader("Summary")
total_masters = len(family_df)
counts = family_df["family_type"].value_counts()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Masters", total_masters)
col2.metric("Kids in Nippers only", counts.get("Nippers", 0))
col3.metric("Kids in Lifeguards only", counts.get("Lifeguards", 0))
col4.metric("Kids in Both", counts.get("Both", 0))

matched = total_masters - counts.get("None", 0)
st.metric("Masters with surname+club match in youth events", matched,
          delta=f"{matched/total_masters*100:.1f}%" if total_masters else None)

# Bar chart
st.subheader("Masters by family connection type")
chart_data = family_df["family_type"].value_counts().reset_index()
chart_data.columns = ["Family Type", "Count"]
st.bar_chart(chart_data, x="Family Type", y="Count")

# Matched families detail
st.subheader("Matched families")
matched_df = family_df[family_df["family_type"] != "None"].sort_values(["last_name", "club"])
st.dataframe(matched_df, use_container_width=True, hide_index=True)

# Cross-reference: show the actual nipper/lifeguard kids
st.subheader("Family detail (Masters + their matched youth athletes)")
matched_surnames = matched_df[["last_name", "club"]].drop_duplicates()
all_athletes = pd.concat(frames.values(), ignore_index=True)

family_detail = all_athletes.merge(
    matched_surnames,
    on=["last_name", "club"],
    how="inner"
).sort_values(["last_name", "club", "category", "first_name"])

st.dataframe(family_detail, use_container_width=True, hide_index=True)

# Export
st.subheader("Export")
col_a, col_b = st.columns(2)
with col_a:
    st.download_button(
        "Download matched families CSV",
        matched_df.to_csv(index=False),
        "sa_nationals_2026_matched_families.csv",
        "text/csv",
    )
with col_b:
    st.download_button(
        "Download full family detail CSV",
        family_detail.to_csv(index=False),
        "sa_nationals_2026_family_detail.csv",
        "text/csv",
    )

# Unmatched masters for review
with st.expander("Unmatched masters (no surname+club match)"):
    unmatched = family_df[family_df["family_type"] == "None"].sort_values("last_name")
    st.dataframe(unmatched, use_container_width=True, hide_index=True)

# Raw athlete counts per category
with st.expander("Athlete counts per category"):
    for cat, df in frames.items():
        st.write(f"**{cat}**: {len(df)} unique athletes")
