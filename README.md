# ADAPT – Automated Drive-Test Analysis and Problem Tackling

# 📌 Overview
ADAPT (Automated Drive-Test Analysis and Problem Tackling) — Graduation project sponsored by Vodafone. A Python-based telecom optimization tool with two stages: (1) detect low-throughput areas using Random Forest and expert thresholds, (2) suggest KPI improvements via ML models.

It leverages Python, Pandas, and PyQt5 to analyze LTE drive-test datasets and provide actionable insights into network performance.
The tool automates data processing, identifies problem areas, and generates intuitive visualizations and dashboards for decision-making.


# ✨ Features
Automated Data Processing
Cleans and organizes raw LTE drive-test data
Integrates multiple dataset formats (.xlsx, .csv, .pkl)
KPI Analysis & Insights
Identifies key performance indicators (PRB utilization, coverage, handovers, etc.)
Provides trend analysis and anomaly detection
Visualization Dashboards
Interactive PyQt5-based GUI
Coverage, handover, and utilization dashboards (.ui layouts)
Graph generation for performance metrics
Problem Detection
Flags bad coverage and high-load areas
Automates detection of handover and throughput issues


# 📂 Project Structure
ADAPT/
│── Main.py                 # Main application entry point

│── *.ui                    # PyQt5 UI layouts (Coverage, Handover, HighLoad, HistogramPage, etc.)

│── Graphs_filtering_*.py   # Scripts for filtering & visualization

│── *.xlsx / *.csv          # Sample LTE and drive-test data

│── database_sheet.xlsx      # Main database reference

│── Export.csv               # Processed output file

🛠️ Tech Stack
Programming Language: Python
Libraries: Pandas, Matplotlib/Seaborn (for graphs), PyQt5 (for GUI)
Data Sources: LTE drive-test datasets, KPI reports, network logs

# 📖 Example Use Cases
Detecting bad coverage areas from drive-test data
Analyzing handover performance between LTE cells
Identifying PRB utilization hotspots in urban clusters
Visualizing KPI trends for optimization reports

# 🎓 Acknowledgements
This project was developed as part of a graduation project in telecom optimization using data analytics, sponsored by Vodafone.
