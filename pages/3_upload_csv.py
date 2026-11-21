import streamlit as st
import pandas as pd
from db import get_engine

if not st.session_state.get("authenticated"):
    st.warning("Please log in on the main page first.")
    st.stop()

st.title("Upload New CSV Data")

table_choice = st.selectbox("Select Target Table", ["transactions", "households", "products"])
uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.strip() for c in df.columns]
    st.write("Preview of uploaded data:", df.head())

    if st.button("Load into Azure SQL Database"):
        with st.spinner("Uploading rows to Azure SQL..."):
            df.to_sql(table_choice, get_engine(), if_exists="append", index=False, chunksize=1000)
        st.success(f"Successfully loaded {len(df)} rows into `{table_choice}`! You can now search this data on the Household Search page.")
