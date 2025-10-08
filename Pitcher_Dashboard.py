# -*- coding: utf-8 -*-
"""
Created on Tue Oct  7 14:44:51 2025

@author: rarbo
"""

import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import io
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_pdf import PdfPages

#Page Setup
st.set_page_config(page_title="Pitching Dashboard", layout="wide")

#Creating Logos
col1, col2, col3 = st.columns([1, 0.5, 1])

with col1:
    st.image("sebalogo.png", use_column_width = True)

with col2:
    st.write("")

with col3:
    st.image("p2p.jpg", width = 225)
    
#Player Name Input
player_name = st.text_input("Enter Player Name:", "")
if player_name:
    st.title(f"⚾ {player_name}'s Pitching Dashboard")
else:
    st.title("⚾ Pitching Dashboard")

st.markdown(
    "Interactive visualization of pitching data with multiple plots. "
    "Please upload .csv files downloaded directly from Rapsodo without editing."
)

#File Upload
uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

pitching = None

if uploaded_file is not None:
    try:
        #Skip first 3 lines (Player ID, Player Name, blank line)
        pitching = pd.read_csv(uploaded_file, skiprows=3)
        st.success("✅ CSV loaded successfully!")
    except pd.errors.ParserError as e:
        st.error(f"❌ Parsing error: {e}")
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")

#Continue only if data is valid
if pitching is not None:
    st.dataframe(pitching.head())

    #Clean up columns
    pitching = pitching.dropna(axis=1, how="all")
    pitching = pitching[
        [
            "No", "Date", "Pitch Type", "Is Strike", "Strike Zone Side", "Strike Zone Height",
            "Velocity", "Total Spin", "Spin Efficiency (release)", "Spin Direction",
            "HB (trajectory)", "VB (spin)", "Horizontal Angle", "Release Angle",
            "Release Height", "Release Side", "Gyro Degree (deg)", "Release Extension (ft)"
        ]
    ]

    pitching["Date"] = pd.to_datetime(pitching["Date"], errors="coerce")
    pitching["Date"] = pitching["Date"].dt.strftime("%#m/%#d/%#y")
    pitching = pitching[pitching["Pitch Type"] != "-"].reset_index(drop=True)

    numeric_columns = [
        "Strike Zone Side", "Strike Zone Height", "Velocity", "Total Spin",
        "Spin Efficiency (release)", "HB (trajectory)", "VB (spin)",
        "Horizontal Angle", "Release Angle", "Release Height", "Release Side",
        "Gyro Degree (deg)", "Release Extension (ft)"
    ]
    pitching[numeric_columns] = pitching[numeric_columns].apply(pd.to_numeric, errors="coerce")
    pitching["Pitch Number"] = pitching.groupby("Date").cumcount() + 1

    #Sidebar Filters
    st.sidebar.header("Filter Options")
    if pitching["Date"].notna().any():
        unique_dates = sorted(pitching["Date"].dropna().unique())
        selected_dates = st.sidebar.multiselect("Select Dates", unique_dates, default=unique_dates)
        pitching = pitching[pitching["Date"].isin(selected_dates)]

    pitch_types = sorted(pitching["Pitch Type"].dropna().unique())
    selected_pitch_types = st.sidebar.multiselect("Select Pitch Types", pitch_types, default=pitch_types)
    pitching = pitching[pitching["Pitch Type"].isin(selected_pitch_types)]

    if "Velocity" in pitching.columns:
        vmin, vmax = int(pitching["Velocity"].min()), int(pitching["Velocity"].max())
        velocity_range = st.sidebar.slider("Velocity Range (MPH)", vmin, vmax, (vmin, vmax))
        pitching = pitching[
            (pitching["Velocity"] >= velocity_range[0]) &
            (pitching["Velocity"] <= velocity_range[1])
        ]

    #Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Movement Plot", "Velocity Plot", "Spin Plot", "Strike Zone Plot"])

    pdf_buffer = io.BytesIO()
    pdf = PdfPages(pdf_buffer)

    #Tab 1: Movement Plot
    with tab1:
        st.subheader("Pitch Movement (HB vs VB)")

    # --- Plot ---
        fig, ax = plt.subplots(figsize=(7, 7))
        sns.scatterplot(
            data=pitching, x="HB (trajectory)", y="VB (spin)",
           hue="Pitch Type", s=60, alpha=0.8, ax=ax
           )
        ax.axhline(0, color='gray', linestyle='--')
        ax.axvline(0, color='gray', linestyle='--')
        ax.set_xlim(-30, 30)
        ax.set_ylim(-30, 30)
        ax.set_xlabel("Horizontal Break (inches)")
        ax.set_ylabel("Vertical Break (inches)")
        ax.set_aspect("equal", adjustable="box")
        ax.set_title(f"{player_name} - Pitch Movement", fontsize=14, weight='bold')

    # --- Show in Streamlit ---
        st.pyplot(fig)

    # --- Save Plot to PDF (plot only) ---
        buf = io.BytesIO()
        fig.savefig(buf, format="pdf", bbox_inches='tight')
        buf.seek(0)
        st.download_button(
            label="Download Movement Plot (PDF)",
            data=buf,
            file_name=f"{player_name}_movement_plot.pdf",
            mime="application/pdf"
            )

        plt.close(fig)

    # --- Summary Statistics / Insights in Streamlit only ---
        st.markdown("### 📊 Movement Summary by Pitch Type")
        movement_summary = (
            pitching.groupby("Pitch Type")[["HB (trajectory)", "VB (spin)"]]
            .agg(["mean", "std", "max"])
            .round(1)
       )
    # Flatten MultiIndex columns
        movement_summary.columns = ["HB Mean", "HB Std", "HB Max", "VB Mean", "VB Std", "VB Max"]
        st.dataframe(movement_summary)

        st.markdown("### 💬 Pitch-Specific Insights")
        for pitch_type, row in movement_summary.iterrows():
            st.markdown(
                f"💡 **{pitch_type}:** The avg HB is **{row['HB Mean']:+.1f}″**, "
                f"and the max HB is **{row['HB Max']:+.1f}″**. "
                f"Avg VB is **{row['VB Mean']:+.1f}″**, and max VB is **{row['VB Max']:+.1f}″.**"
                )

    #Tab 2: Velocity Plot
    with tab2:
        st.subheader("Velocity Trends by Day with Hardest Pitches Labeled")
        pitching_sorted = pitching.sort_values(by=["Date", "Pitch Number"])

        for day in pitching_sorted["Date"].unique():
            st.markdown(f"**Date: {day}**")
            day_data = pitching_sorted[pitching_sorted["Date"] == day]

            fig, ax = plt.subplots(figsize=(8, 4))
            sns.lineplot(
                data=day_data, x="Pitch Number", y="Velocity",
                hue="Pitch Type", marker="o", ax=ax
            )

            for pitch_type in day_data["Pitch Type"].unique():
                pitch_type_data = day_data[day_data["Pitch Type"] == pitch_type]
                if not pitch_type_data.empty:
                    max_row = pitch_type_data.loc[pitch_type_data["Velocity"].idxmax()]
                    ax.annotate(
                        f"{int(max_row['Velocity'])} MPH",
                        xy=(max_row["Pitch Number"], max_row["Velocity"]),
                        xytext=(5, 5),
                        textcoords="offset points",
                        fontsize=9, color='red', weight='bold'
                    )

            ax.set_xlabel("Pitch Number on Date")
            ax.set_ylabel("Velocity (MPH)")
            ax.set_title(f"{player_name} - Velocity Trend ({day})", fontsize=14, weight='bold')
            st.pyplot(fig)

            pdf.savefig(fig)
            plt.close(fig)
            
        #Summary Stats
        st.markdown("### 📊 Velocity Summary by Pitch Type")
        velocity = (
            pitching.groupby("Pitch Type")[["Velocity"]]
            .agg(["mean", "std", "max"])
            .round(1))
            
        velocity.columns = ["Avg Velocity", "Std", "Max Velocity"]
        st.dataframe(velocity)
            
        st.markdown("### 💬 Pitch-Specific Insights")
        for pitch_type, row, in velocity.iterrows():
            st.markdown(
                f"💡 **{pitch_type}:** The average velocity of your {pitch_type} is **{row['Avg Velocity']:.1f} MPH**, "
                f"and the max velocity is **{row['Max Velocity']:.1f} MPH**.")

            

    #Tab 3: Spin Plot
    with tab3:
        st.subheader("Spin Analysis")
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.boxplot(data=pitching, x="Pitch Type", y="Total Spin", ax=ax)
        ax.set_ylabel("Total Spin (RPM)")
        ax.set_title(f"{player_name} - Spin Analysis", fontsize=14, weight='bold')
        st.pyplot(fig)
        pdf.savefig(fig)
        plt.close(fig)

    #Tab 4: Strike Zone
    with tab4:
        st.subheader("Strike Zone Plot")
        fig, ax = plt.subplots(figsize=(6, 7))
        sns.scatterplot(
            data=pitching, x="Strike Zone Side", y="Strike Zone Height",
            hue="Pitch Type", s=60, alpha=0.8, ax=ax
        )

        strike_zone = Rectangle(
            xy=(-8.5, 18), width=17, height=24,
            edgecolor="black", linewidth=2, facecolor="none"
        )
        ax.add_patch(strike_zone)
        ax.set_xlabel("Horizontal Location (inches)")
        ax.set_ylabel("Vertical Location (inches)")
        ax.set_aspect("equal", adjustable="box")
        ax.set_title(f"{player_name} - Strike Zone", fontsize=14, weight='bold')
        st.pyplot(fig)
        pdf.savefig(fig)
        plt.close(fig)

    #Multi-page PDF Download
    pdf.close()
    pdf_buffer.seek(0)
    st.download_button(
        label="Download All Plots as Multi-page PDF",
        data=pdf_buffer,
        file_name=f"{player_name}_pitching_dashboard.pdf",
        mime="application/pdf"
    )

else:
    st.info("👆 Enter a player name and upload a CSV file to start.")
