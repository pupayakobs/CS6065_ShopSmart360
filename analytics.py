"""Shared data loading and analysis used by the analytics pages (4-7)."""
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sqlalchemy import text

from db import get_engine

DEMOGRAPHICS = ["L", "AGE_RANGE", "MARITAL", "INCOME_RANGE", "HOMEOWNER",
                "HSHD_COMPOSITION", "HH_SIZE", "CHILDREN"]


def require_login():
    if not st.session_state.get("authenticated"):
        st.warning("Please log in on the main page first.")
        st.stop()


@st.cache_data(ttl=600, show_spinner="Loading data from Azure SQL...")
def load_data():
    with get_engine().connect() as conn:
        t, p, h = [pd.read_sql(text(f"SELECT * FROM {name}"), conn)
                   for name in ("transactions", "products", "households")]
    return prepare(t, p, h)


def _clean(d):
    # The raw CSVs pad names and values with spaces and use "null" for missing values.
    d = d.rename(columns=lambda c: c.strip())
    for c in d.select_dtypes(include=["object", "string"]).columns:
        d[c] = d[c].astype("string").str.strip().replace({"null": pd.NA, "": pd.NA})
    return d


def prepare(t, p, h):
    """Clean the three tables and join them into one row per purchased item."""
    t, p, h = _clean(t), _clean(p), _clean(h)
    for d, cols in ((t, ["HSHD_NUM", "PRODUCT_NUM", "BASKET_NUM", "SPEND", "UNITS"]),
                    (p, ["PRODUCT_NUM"]), (h, ["HSHD_NUM"])):
        for c in cols:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    df = t.merge(p, on="PRODUCT_NUM", how="left").merge(h, on="HSHD_NUM", how="left")
    # The raw files store dates like "17-AUG-18"; anything else falls back to a slower general parser.
    df["DATE"] = pd.to_datetime(df["PURCHASE_"], format="%d-%b-%y", errors="coerce")
    missing = df["DATE"].isna()
    df.loc[missing, "DATE"] = pd.to_datetime(df.loc[missing, "PURCHASE_"], format="mixed", errors="coerce")
    df = df.dropna(subset=["DATE", "HSHD_NUM", "BASKET_NUM"])
    df["MONTH"] = df["DATE"].dt.strftime("%Y-%m")
    return df


@st.cache_data
def basket_rules(df, level="COMMODITY", min_together=20):
    """Association rules for item pairs: support, confidence and lift."""
    items = df[["BASKET_NUM", level]].dropna().drop_duplicates()
    n_baskets = items["BASKET_NUM"].nunique()
    counts_one = items[level].value_counts()
    cat = items[level].astype("category")
    # Integer codes keep the basket self-join small enough for a free-tier server.
    small = pd.DataFrame({"b": items["BASKET_NUM"].to_numpy(),
                          "i": cat.cat.codes.to_numpy().astype("int32")})
    pairs = small.merge(small, on="b")
    pairs = pairs[pairs["i_x"] < pairs["i_y"]]
    together = pairs.groupby(["i_x", "i_y"]).size().reset_index(name="n")
    together = together[together["n"] >= min_together]
    both = pd.concat([together.rename(columns={"i_x": "a", "i_y": "c"}),
                      together.rename(columns={"i_x": "c", "i_y": "a"})], ignore_index=True)
    names = cat.cat.categories
    rules = pd.DataFrame({
        "If customer buys": names.take(both["a"].to_numpy()),
        "They also buy": names.take(both["c"].to_numpy()),
        "Baskets together": both["n"].to_numpy(),
    })
    rules["Support"] = rules["Baskets together"] / n_baskets
    rules["Confidence"] = rules["Baskets together"] / rules["If customer buys"].map(counts_one).to_numpy()
    rules["Lift"] = rules["Confidence"] / (rules["They also buy"].map(counts_one).to_numpy() / n_baskets)
    return rules.sort_values(["Lift", "Baskets together"], ascending=False).reset_index(drop=True)


def monthly_spend(df):
    return df.pivot_table(index="HSHD_NUM", columns="MONTH", values="SPEND",
                          aggfunc="sum", fill_value=0).sort_index(axis=1)


@st.cache_data
def churn_scores(df):
    """Flag households whose spending is falling or who stopped shopping."""
    monthly = monthly_spend(df)
    earlier = monthly.iloc[:, :-2].mean(axis=1)
    recent = monthly.iloc[:, -2:].mean(axis=1)
    change = np.where(earlier > 0, (recent - earlier) / earlier.where(earlier > 0, 1), 0.0)
    slope = np.polyfit(np.arange(monthly.shape[1]), monthly.to_numpy().T, 1)[0]
    shopped_last = monthly.iloc[:, -1] > 0
    shopped_recent = (monthly.iloc[:, -2:] > 0).any(axis=1)
    out = pd.DataFrame({
        "Earlier avg monthly spend": earlier.round(2),
        "Recent avg monthly spend": recent.round(2),
        "Change %": (change * 100).round(1),
        "Trend ($ per month)": slope.round(2),
        "Last month shopped": (monthly > 0).iloc[:, ::-1].idxmax(axis=1),
    }, index=monthly.index)
    out["Risk"] = np.select(
        [~shopped_recent | (change <= -0.5), ~shopped_last | (change <= -0.2)],
        ["High", "Medium"], "Low")
    return out


def _behavior(df):
    """Per-household behavior, averaged per month so any time window is comparable."""
    months = sorted(df["MONTH"].unique())
    position = {m: i for i, m in enumerate(months)}
    g = df.groupby("HSHD_NUM")
    spend, baskets = g["SPEND"].sum(), g["BASKET_NUM"].nunique()
    return pd.DataFrame({
        "avg_monthly_spend": spend / len(months),
        "avg_monthly_visits": baskets / len(months),
        "avg_basket_value": spend / baskets,
        "share_of_months_active": g["MONTH"].nunique() / len(months),
        "months_since_last_visit": len(months) - 1 - g["MONTH"].max().map(position),
    })


@st.cache_data
def clv_model(df):
    """Random Forest that predicts each household's spend over the next two months."""
    months = sorted(df["MONTH"].unique())
    past, future = df[df["MONTH"].isin(months[:-2])], df[df["MONTH"].isin(months[-2:])]
    demo = df.groupby("HSHD_NUM")[DEMOGRAPHICS].first().astype("string").fillna("Unknown")
    demo = pd.get_dummies(demo).astype(int)
    X = _behavior(past).join(demo)
    y = future.groupby("HSHD_NUM")["SPEND"].sum().reindex(X.index, fill_value=0)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=42)
    model = RandomForestRegressor(n_estimators=200, min_samples_leaf=3, random_state=42)
    pred = model.fit(X_tr, y_tr).predict(X_te)
    metrics = {"R2": r2_score(y_te, pred), "MAE": mean_absolute_error(y_te, pred),
               "train": len(X_tr), "test": len(X_te)}
    model.fit(X, y)  # refit on every household before scoring
    X_all = _behavior(df).join(demo)[X.columns]
    clv = pd.Series(model.predict(X_all), index=X_all.index, name="Predicted spend next 2 months ($)")
    importance = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
    return clv.round(2), metrics, importance


def retention_offers(df, churn, rules, clv):
    """Personalized offer for each at-risk household, most valuable first."""
    at_risk = churn[churn["Risk"] != "Low"]
    fav = (df[df["HSHD_NUM"].isin(at_risk.index)]
           .groupby(["HSHD_NUM", "COMMODITY"])["SPEND"].sum().reset_index()
           .sort_values("SPEND", ascending=False).drop_duplicates("HSHD_NUM")
           .set_index("HSHD_NUM")["COMMODITY"].rename("Favorite commodity"))
    best_pair = (rules.drop_duplicates("If customer buys")
                 .set_index("If customer buys")["They also buy"])
    out = at_risk[["Risk", "Change %"]].join(fav).join(clv)
    out["Pair with"] = out["Favorite commodity"].map(best_pair)
    out["Suggested offer"] = np.where(
        out["Pair with"].notna(),
        "Discount on " + out["Pair with"].fillna("") + " when buying " + out["Favorite commodity"].fillna(""),
        "Loyalty coupon on " + out["Favorite commodity"].fillna("their usual items"))
    out["_order"] = out["Risk"].map({"High": 0, "Medium": 1})
    return out.sort_values(["_order", clv.name], ascending=[True, False]).drop(columns="_order")
