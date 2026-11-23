import streamlit as st

import analytics as a

a.require_login()
st.title("Customer Churn Analysis: Who Might Stop Shopping?")
st.write(
    "For each household we compare average monthly spend in the last two months with the months "
    "before, fit a linear regression trend line to monthly spend, and check whether they shopped recently. "
    "**High risk:** no purchases in the last two months, or spend fell by half or more. "
    "**Medium risk:** no purchase in the latest month, or spend fell by 20% or more."
)

df = a.load_data()
churn = a.churn_scores(df)
counts = churn["Risk"].value_counts()

k1, k2, k3 = st.columns(3)
k1.metric("High risk households", int(counts.get("High", 0)))
k2.metric("Medium risk households", int(counts.get("Medium", 0)))
k3.metric("Low risk households", int(counts.get("Low", 0)))

st.subheader("Average monthly spend by risk group")
trend = (df.merge(churn["Risk"], left_on="HSHD_NUM", right_index=True)
           .groupby(["MONTH", "Risk"])["SPEND"].sum().unstack())
st.line_chart(trend.div(counts.reindex(trend.columns)), x_label="Month", y_label="Spend per household ($)")
st.caption("A line that falls toward the right shows a group whose spending is dropping.")

left, right = st.columns(2)
households = df.groupby("HSHD_NUM")[["L", "INCOME_RANGE"]].first().join(churn["Risk"])
with left:
    st.subheader("High risk share by loyalty membership")
    st.bar_chart(households.groupby("L")["Risk"].apply(lambda r: (r == "High").mean() * 100),
                 y_label="% high risk")
with right:
    st.subheader("High risk share by income")
    st.bar_chart(households.groupby("INCOME_RANGE")["Risk"].apply(lambda r: (r == "High").mean() * 100),
                 y_label="% high risk")

st.subheader("Households at risk")
risk_filter = st.multiselect("Show risk levels", ["High", "Medium", "Low"], default=["High", "Medium"])
st.dataframe(churn[churn["Risk"].isin(risk_filter)].sort_values("Change %"), width="stretch")

st.subheader("How to keep these customers")
st.markdown(
    "- **Win-back offers:** send high risk households a personal coupon on items they used to buy. "
    "See the Retention Recommender on the next page.\n"
    "- **Loyalty program:** if the chart above shows fewer high risk members, invite non-members to join.\n"
    "- **Check-ins:** a short survey to households whose spend dropped can reveal price or service problems.\n"
    "- **Watch the trend monthly:** rerun this page after each data upload to catch drops early."
)
