import streamlit as st

import analytics as a

a.require_login()
st.title("Retail Analytics Dashboard")
st.write("How are households spending, and who spends the most? Use the filters on the left to focus on a customer group.")

df = a.load_data()

with st.sidebar:
    st.header("Filters")
    for col, label in {"INCOME_RANGE": "Income range", "AGE_RANGE": "Age range",
                       "HH_SIZE": "Household size", "CHILDREN": "Children",
                       "L": "Loyalty member", "STORE_R": "Store region"}.items():
        chosen = st.multiselect(label, sorted(df[col].dropna().unique()))
        if chosen:
            df = df[df[col].isin(chosen)]

if df.empty:
    st.info("No purchases match these filters.")
    st.stop()

total, baskets = df["SPEND"].sum(), df["BASKET_NUM"].nunique()
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total spend", f"${total:,.0f}")
k2.metric("Households", f"{df['HSHD_NUM'].nunique():,}")
k3.metric("Baskets", f"{baskets:,}")
k4.metric("Average basket", f"${total / baskets:,.2f}")

st.subheader("Are customers spending more or less over time?")
by_month = df.groupby("MONTH")["SPEND"].sum()
st.line_chart(by_month, x_label="Month", y_label="Spend ($)")
if len(by_month) > 1:
    change = (by_month.iloc[-1] - by_month.iloc[0]) / by_month.iloc[0]
    st.caption(f"Spend changed {change:+.0%} from {by_month.index[0]} to {by_month.index[-1]}. "
               f"The busiest month was {by_month.idxmax()}.")

left, right = st.columns(2)
with left:
    st.subheader("Spend by department")
    dept = df.groupby("DEPARTMENT")["SPEND"].sum().sort_values(ascending=False)
    st.bar_chart(dept, y_label="Spend ($)")
    st.caption(f"{dept.index[0]} brings in {dept.iloc[0] / total:.0%} of all spending.")
with right:
    st.subheader("Private label or national brand?")
    brand = df.groupby("BRAND_TY")["SPEND"].sum()
    st.bar_chart(brand, y_label="Spend ($)")
    st.caption(f"{brand.idxmax()} brands get {brand.max() / brand.sum():.0%} of brand spending.")

left, right = st.columns(2)
with left:
    st.subheader("Top 10 commodities")
    top = df.groupby("COMMODITY")["SPEND"].sum().nlargest(10)
    st.bar_chart(top, horizontal=True, x_label="Spend ($)")
with right:
    st.subheader("Average spend per household by income")
    per_hh = df.groupby(["INCOME_RANGE", "HSHD_NUM"])["SPEND"].sum().groupby(level=0).mean()
    st.bar_chart(per_hh, y_label="Spend per household ($)")
    st.caption(f"Households earning {per_hh.idxmax()} spend the most on average.")

left, right = st.columns(2)
with left:
    st.subheader("Average spend per household by size")
    st.bar_chart(df.groupby(["HH_SIZE", "HSHD_NUM"])["SPEND"].sum().groupby(level=0).mean(),
                 y_label="Spend per household ($)")
with right:
    st.subheader("Loyalty members vs non-members")
    loyal = df.groupby(["L", "HSHD_NUM"])["SPEND"].sum().groupby(level=0).mean()
    st.bar_chart(loyal, y_label="Spend per household ($)")
