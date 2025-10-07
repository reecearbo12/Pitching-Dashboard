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

# --- Page Setup ---
st.set_page_config(page_title="Pitching Dashboard", layout="wide")

# --- Player Name Input ---
player_name = st.text_input("Enter Player Name:", "")
if player_name:
    st.title(f"⚾ {player_name}'s Pitching Dashboard")
else:
    st.title("⚾ Pitching Dashboard")

st.markdown("Interactive visualization of pitching data with multiple plots. Please upload .csv files downloaded directly from Rapsodo without editing.")

# --- File Upload ---
uploaded_file = st.file_uploader("Upload your pitching CSV file", type=["csv"])

if uploaded_file is not None:
    # --- Load & Clean Data ---
    pitching = pd.read_csv(uploaded_file)
    
    pitching = pitching.iloc[2:].reset_index(drop=True)
    pitching.columns = pitching.iloc[0]
    pitching = pitching.drop(pitching.index[0])
    pitching = pitching.dropna(axis=1, how="all")

    pitching = pitching[
        [
            "No","Date","Pitch Type","Is Strike","Strike Zone Side","Strike Zone Height",
            "Velocity","Total Spin","Spin Efficiency (release)","Spin Direction",
            "HB (trajectory)","VB (spin)","Horizontal Angle","Release Angle",
            "Release Height","Release Side","Gyro Degree (deg)","Release Extension (ft)"
        ]
    ]

    pitching["Date"] = pd.to_datetime(pitching["Date"], errors="coerce")
    pitching["Date"] = pitching["Date"].dt.strftime("%#m/%#d/%#y")
    pitching = pitching[pitching["Pitch Type"] != "-"].reset_index(drop=True)

    numeric_columns = [
        "Strike Zone Side","Strike Zone Height","Velocity","Total Spin",
        "Spin Efficiency (release)","HB (trajectory)","VB (spin)",
        "Horizontal Angle","Release Angle","Release Height","Release Side",
        "Gyro Degree (deg)","Release Extension (ft)"
    ]
    pitching[numeric_columns] = pitching[numeric_columns].apply(pd.to_numeric, errors="coerce")
    pitching["Pitch Number"] = pitching.groupby("Date").cumcount() + 1

    # --- Sidebar Filters ---
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
        pitching = pitching[(pitching["Velocity"] >= velocity_range[0]) & 
                            (pitching["Velocity"] <= velocity_range[1])]

    # --- Tabs ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "Movement Plot", "Velocity Plot", "Spin Plot", "Strike Zone Plot"
    ])

    # Prepare PdfPages buffer for multi-page PDF
    pdf_buffer = io.BytesIO()
    pdf = PdfPages(pdf_buffer)

    # --- Tab 1: Movement Plot ---
    with tab1:
        st.subheader("Pitch Movement (HB vs VB)")
        fig, ax = plt.subplots(figsize=(7,7))
        sns.scatterplot(
            data=pitching,
            x="HB (trajectory)",
            y="VB (spin)",
            hue="Pitch Type",
            s=60,
            alpha=0.8,
            ax=ax
        )
        ax.axhline(0, color='gray', linestyle='--')
        ax.axvline(0, color='gray', linestyle='--')
        ax.set_xlim(-30, 30)
        ax.set_ylim(-30, 30)
        ax.set_xlabel("Horizontal Break (inches)")
        ax.set_ylabel("Vertical Break (inches)")
        ax.set_aspect("equal", adjustable="box")
        ax.set_title(f"{player_name} - Pitch Movement", fontsize=14, weight='bold')
        st.pyplot(fig)

        # Add to PDF
        pdf.savefig(fig)
        plt.close(fig)

        # Download PNG and PDF individually
        buf = io.BytesIO()
        fig.savefig(buf, format="pdf")
        buf.seek(0)
        st.download_button(
            label="Download Movement Plot (PDF)",
            data=buf,
            file_name=f"{player_name}_movement_plot.pdf",
            mime="application/pdf"
        )

    # --- Tab 2: Velocity Plot ---
    with tab2:
        st.subheader("Velocity Trends by Day with Hardest Pitches Labeled")
        pitching_sorted = pitching.sort_values(by=["Date", "Pitch Number"])

        for day in pitching_sorted["Date"].unique():
            st.markdown(f"**Date: {day}**")
            day_data = pitching_sorted[pitching_sorted["Date"] == day]

            fig, ax = plt.subplots(figsize=(8,4))
            sns.lineplot(
                data=day_data,
                x="Pitch Number",
                y="Velocity",
                hue="Pitch Type",
                marker="o",
                ax=ax
            )

            for pitch_type in day_data["Pitch Type"].unique():
                pitch_type_data = day_data[day_data["Pitch Type"] == pitch_type]
                if not pitch_type_data.empty:
                    max_row = pitch_type_data.loc[pitch_type_data["Velocity"].idxmax()]
                    ax.annotate(
                        f"{int(max_row['Velocity'])} MPH",
                        xy=(max_row["Pitch Number"], max_row["Velocity"]),
                        xytext=(5,5),
                        textcoords="offset points",
                        fontsize=9,
                        color='red',
                        weight='bold'
                    )

            ax.set_xlabel("Pitch Number on Date")
            ax.set_ylabel("Velocity (MPH)")
            ax.set_title(f"{player_name} - Velocity Trend ({day})", fontsize=14, weight='bold')
            st.pyplot(fig)

            pdf.savefig(fig)
            plt.close(fig)

            buf = io.BytesIO()
            fig.savefig(buf, format="pdf")
            buf.seek(0)
            st.download_button(
                label=f"Download Velocity Plot - {day} (PDF)",
                data=buf,
                file_name=f"{player_name}_velocity_{day}.pdf",
                mime="application/pdf"
            )

    # --- Tab 3: Spin Plot ---
    with tab3:
        st.subheader("Spin Analysis")
        fig, ax = plt.subplots(figsize=(7,4))
        sns.boxplot(data=pitching, x="Pitch Type", y="Total Spin", ax=ax)
        ax.set_ylabel("Total Spin (RPM)")
        ax.set_title(f"{player_name} - Spin Analysis", fontsize=14, weight='bold')
        st.pyplot(fig)

        pdf.savefig(fig)
        plt.close(fig)

        buf = io.BytesIO()
        fig.savefig(buf, format="pdf")
        buf.seek(0)
        st.download_button(
            label="Download Spin Plot (PDF)",
            data=buf,
            file_name=f"{player_name}_spin_plot.pdf",
            mime="application/pdf"
        )

    # --- Tab 4: Strike Zone ---
    with tab4:
        st.subheader("Strike Zone Plot")
        fig, ax = plt.subplots(figsize=(6,7))

        sns.scatterplot(
            data=pitching,
            x="Strike Zone Side",
            y="Strike Zone Height",
            hue="Pitch Type",
            s=60,
            alpha=0.8,
            ax=ax
        )

        strike_zone = Rectangle(
            xy=(-8.5, 18),  # bottom-left in inches
            width=17,
            height=24,      # 18 to 42 inches
            edgecolor="black",
            linewidth=2,
            facecolor="none"
        )
        ax.add_patch(strike_zone)

        ax.set_xlabel("Horizontal Location (inches)")
        ax.set_ylabel("Vertical Location (inches)")
        ax.set_aspect("equal", adjustable="box")
        ax.set_title(f"{player_name} - Strike Zone", fontsize=14, weight='bold')
        st.pyplot(fig)

        pdf.savefig(fig)
        plt.close(fig)

        buf = io.BytesIO()
        fig.savefig(buf, format="pdf")
        buf.seek(0)
        st.download_button(
            label="Download Strike Zone Plot (PDF)",
            data=buf,
            file_name=f"{player_name}_strikezone_plot.pdf",
            mime="application/pdf"
        )

    # --- Multi-page PDF Download ---
    pdf.close()
    pdf_buffer.seek(0)
    st.download_button(
        label="Download All Plots as Multi-page PDF",
        data=pdf_buffer,
        file_name=f"{player_name}_pitching_dashboard.pdf",
        mime="application/pdf"
    )

else:
    st.info("👆 Upload your pitching CSV file to start.")
