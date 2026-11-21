import streamlit as st
import pandas as pd
from sqlalchemy import text
from db import get_engine

if not st.session_state.get("authenticated"):
    st.warning("Please log in on the main page first.")
    st.stop()

st.title("Household #10 — Joined Retail Data")

query = text("""
    SELECT 
        h.HSHD_NUM, t.BASKET_NUM, t.PURCHASE_, t.PRODUCT_NUM, 
        p.DEPARTMENT, p.COMMODITY, t.SPEND, t.UNITS, 
        t.STORE_R, t.WEEK_NUM, t.YEAR,
        h.L, h.AGE_RANGE, h.MARITAL, 
        h.INCOME_RANGE, h.HOMEOWNER, h.HSHD_COMPOSITION, 
        h.HH_SIZE, h.CHILDREN
    FROM households h
    JOIN transactions t ON h.HSHD_NUM = t.HSHD_NUM
    JOIN products p ON t.PRODUCT_NUM = p.PRODUCT_NUM
    WHERE h.HSHD_NUM = 10
    ORDER BY h.HSHD_NUM, t.BASKET_NUM, t.PURCHASE_, t.PRODUCT_NUM, p.DEPARTMENT, p.COMMODITY
""")


with get_engine().connect() as conn:
    df = pd.read_sql(query, conn)

st.write(f"Showing **{len(df)}** records for Household #10:")
st.dataframe(df, use_container_width=True)
