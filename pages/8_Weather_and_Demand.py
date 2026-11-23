import streamlit as st

import analytics as a

a.require_login()
st.title("External Data: Does Weather Change How People Shop?")
st.write(
    "We combine the retail transactions with **historical daily weather** (temperature, rain, snow) from the "
    "free Open-Meteo REST API. Each store region is matched to one representative city, and the two datasets "
    "are joined on **date and region**. We then check which products sell more in cold or warm weather and "
    "test whether adding weather improves a daily spend forecast."
)
st.caption("Region to city: " + ", ".join(f"{r} = {c}" for r, (c, _, _) in a.REGION_CITIES.items()))

df = a.load_data()
try:
    weather = a.load_weather(df["DATE"].min().strftime("%Y-%m-%d"), df["DATE"].max().strftime("%Y-%m-%d"))
except Exception as e:
    st.error(f"Could not reach the weather API: {e}")
    st.stop()

d = a.weather_daily(df, weather)
if d.empty:
    st.warning("No store regions matched the weather cities.")
    st.stop()

st.subheader("Temperature vs daily spend")
st.scatter_chart(d, x=a.WEATHER[0], y="Spend", color="STORE_R", y_label="Daily spend in region ($)")
corr = d[["Spend", "Baskets"]].corrwith(d[a.WEATHER[0]])
st.caption(f"Correlation of temperature with daily spend: {corr['Spend']:.2f}, with number of baskets: "
           f"{corr['Baskets']:.2f} (0 = no relationship, -1 or 1 = perfect).")

st.subheader("Which products depend on the weather?")
by_commodity = a.weather_by_commodity(df, weather)
left, right = st.columns(2)
with left:
    st.markdown("**Bigger share of the basket on cold days**")
    st.bar_chart(-by_commodity.head(8), horizontal=True, x_label="Strength (negative correlation with temperature)")
with right:
    st.markdown("**Bigger share of the basket on warm days**")
    st.bar_chart(by_commodity.tail(8), horizontal=True, x_label="Strength (correlation with temperature)")
st.caption("Weather and season move together here (August is warm, December is cold), "
           "so these results show seasonal and weather driven demand combined.")

st.subheader("Forecasting daily spend with weather")
metrics, preds, effect = a.weather_forecast(d)
st.write("A linear regression predicts each region's daily spend from the day of the week and region. "
         "We train it on the earlier months, test it on the last two, and compare it with and without weather.")
c1, c2, c3, c4 = st.columns(4)
c1.metric("R² without weather", f"{metrics['Without weather']['R2']:.2f}")
c2.metric("R² with weather", f"{metrics['With weather']['R2']:.2f}",
          f"{metrics['With weather']['R2'] - metrics['Without weather']['R2']:+.2f}")
c3.metric("Avg error without weather", f"${metrics['Without weather']['MAE']:,.0f}")
c4.metric("Avg error with weather", f"${metrics['With weather']['MAE']:,.0f}",
          f"{metrics['With weather']['MAE'] - metrics['Without weather']['MAE']:+,.0f}", delta_color="inverse")
st.line_chart(preds.groupby("DATE")[["Spend", "Predicted"]].sum(), x_label="Date",
              y_label="Total daily spend, all regions ($)")
st.markdown(
    f"- Every **10°F warmer** changes a region's daily spend by **${effect[a.WEATHER[0]] * 10:+,.0f}**.\n"
    f"- Every **inch of rain** changes it by **${effect[a.WEATHER[1]]:+,.0f}**.\n"
    f"- Every **inch of snow** changes it by **${effect[a.WEATHER[2]]:+,.0f}**."
)
st.caption("The dataset covers only the last week of five months in two years, so these estimates are rough.")

st.subheader("How the retailer can use this")
st.markdown(
    "- **Inventory planning:** stock more of the cold-weather products when a cold front is forecast.\n"
    "- **Demand forecasting:** feed the 7-day weather forecast into the model to plan staff and deliveries.\n"
    "- **Promotions:** time promotions on warm-weather items for warm weeks, comfort food for cold weeks.\n"
    "- **Product availability:** move weather-sensitive stock between regions as their weather differs.\n"
    "- **Customer experience:** fewer empty shelves when shoppers need seasonal items most."
)
