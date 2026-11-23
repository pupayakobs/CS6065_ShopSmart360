import streamlit as st

import analytics as a

a.require_login()
st.title("Basket Analysis: What Do Customers Buy Together?")
st.write(
    "We use association rule mining on every basket. **Support** is the share of baskets "
    "that contain both items. **Confidence** is how often customers who buy the first item "
    "also buy the second. **Lift** above 1 means the pair is bought together more often than by chance."
)

df = a.load_data()
level = st.radio("Analyze by", ["COMMODITY", "DEPARTMENT"], horizontal=True, format_func=str.title)
min_together = st.slider("Minimum number of baskets containing both items", 5, 200, 20)

rules = a.basket_rules(df, level, min_together)
if rules.empty:
    st.info("No pairs reach this minimum. Lower the slider.")
    st.stop()

st.subheader("Strongest product relationships")
st.dataframe(rules.head(25).style.format({"Support": "{:.2%}", "Confidence": "{:.1%}", "Lift": "{:.2f}"}),
             width="stretch", hide_index=True)

# Each pair appears in both directions, so keep one row per pair for the chart.
pairs = rules.assign(Pair=rules.apply(lambda r: " + ".join(sorted([r["If customer buys"], r["They also buy"]])), axis=1))
pairs = pairs.drop_duplicates("Pair").head(10)
st.subheader("Top 10 pairs by lift")
st.bar_chart(pairs.set_index("Pair")["Lift"], horizontal=True, x_label="Lift")

st.subheader("Cross-selling opportunities")
for _, r in pairs.head(3).iterrows():
    st.markdown(f"- **{r['Confidence']:.0%}** of baskets with **{r['If customer buys']}** also contain "
                f"**{r['They also buy']}**, which is **{r['Lift']:.1f}x** more often than chance.")

st.subheader("How the retailer can use this")
st.markdown(
    "- **Store layout:** place strongly linked items near each other to make shopping faster.\n"
    "- **Bundles and promotions:** discount the second item when the first is in the cart.\n"
    "- **Recommendations:** suggest the paired item at online checkout or on receipts.\n"
    "- **Stock planning:** promote both items together so neither runs out during a promotion."
)
