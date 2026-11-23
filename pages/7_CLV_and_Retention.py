import streamlit as st

import analytics as a

a.require_login()
st.title("Customer Lifetime Value and Retention Recommender")

df = a.load_data()
clv, metrics, importance = a.clv_model(df)

st.header("Which customers will generate the most revenue?")
st.write(
    "A **Random Forest** model learns from each household's earlier behavior (spend, visits, "
    "basket size, recency) and demographics to predict how much it will spend in the next two months. "
    "We train on the earlier months, test on the last two, then score every household."
)
k1, k2, k3 = st.columns(3)
k1.metric("Model R² on test households", f"{metrics['R2']:.2f}")
k2.metric("Average error", f"${metrics['MAE']:,.2f}")
k3.metric("Households (train / test)", f"{metrics['train']} / {metrics['test']}")

left, right = st.columns(2)
with left:
    st.subheader("Top 10 most valuable households")
    st.dataframe(clv.nlargest(10), width="stretch")
with right:
    st.subheader("What drives customer value")
    st.bar_chart(importance.head(10), horizontal=True, x_label="Importance")

st.header("Retention Recommender")
st.write(
    "We combine churn risk, basket analysis and predicted value. Each at-risk household gets an "
    "offer on its favorite commodity paired with the item most often bought with it. "
    "High risk, high value households are listed first, so the retailer knows who to contact first."
)
offers = a.retention_offers(df, a.churn_scores(df), a.basket_rules(df, "COMMODITY", 20), clv)
st.dataframe(offers, width="stretch")
st.download_button("Download offers as CSV", offers.to_csv().encode(), "retention_offers.csv", "text/csv")
