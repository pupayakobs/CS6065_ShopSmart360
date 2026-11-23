"""Checks the analysis logic on small made-up data shaped like the real CSVs.
Run from the repo root: python -m pytest tests"""
import numpy as np
import pandas as pd

import analytics as a


def fake_tables(seed=0):
    rng = np.random.default_rng(seed)
    products = pd.DataFrame({
        "PRODUCT_NUM ": range(1, 21),  # padded column name, like the raw CSV
        "DEPARTMENT": ["FOOD     "] * 15 + ["NON-FOOD "] * 5,
        "COMMODITY": [f"C{i % 10}  " for i in range(20)],
        "BRAND_TY": ["PRIVATE", "NATIONAL"] * 10,
        "NATURAL_ORGANIC_FLAG": "N",
    })
    households = pd.DataFrame({
        "HSHD_NUM": range(1, 41), "L": rng.choice(["Y", "N"], 40),
        "AGE_RANGE": rng.choice(["35-44", "45-54", "null"], 40), "MARITAL": "Married",
        "INCOME_RANGE": rng.choice(["35-49K", "50-74K", "100-150K"], 40), "HOMEOWNER": "Homeowner",
        "HSHD_COMPOSITION": "2 Adults", "HH_SIZE": rng.choice(["1", "2", "5+"], 40),
        "CHILDREN": rng.choice(["1", "null"], 40),
    })
    rows, basket = [], 0
    for year in (18, 19):
        for mi, month in enumerate(["AUG", "SEP", "OCT", "NOV", "DEC"]):
            for hh in range(1, 41):
                if hh <= 8 and (year, mi) >= (19, 3):
                    continue  # households 1-8 stop shopping in the last two months
                for _ in range(2):
                    basket += 1
                    prods = set(rng.choice(np.arange(3, 21), 4, replace=False).tolist())
                    if hh % 2:
                        prods |= {1, 2}  # odd households always buy C0 and C1 together
                    for p in prods:
                        rows.append({"BASKET_NUM": basket, "HSHD_NUM": hh, "PURCHASE_": f"2{mi + 3}-{month}-{year}",
                                     "PRODUCT_NUM": p, "SPEND": round(rng.uniform(1, 20), 2), "UNITS": 1,
                                     "STORE_R": "EAST ", "WEEK_NUM": 1, "YEAR": 2000 + year})
    return pd.DataFrame(rows), products, households


def test_prepare_cleans_and_joins():
    df = a.prepare(*fake_tables())
    assert df["DATE"].notna().all()
    assert df["MONTH"].nunique() == 10
    assert df["COMMODITY"].str.endswith(" ").sum() == 0
    assert df["AGE_RANGE"].isna().any()  # "null" became missing


def test_churn_flags_households_that_stopped():
    churn = a.churn_scores(a.prepare(*fake_tables()))
    assert (churn.loc[1:8, "Risk"] == "High").all()
    assert len(churn) == 40


def test_basket_rules_find_planted_pair():
    rules = a.basket_rules(a.prepare(*fake_tables()), "COMMODITY", 10)
    pair = rules[(rules["If customer buys"] == "C0") & (rules["They also buy"] == "C1")]
    assert len(pair) == 1 and pair["Lift"].iloc[0] > 1
    assert rules["Confidence"].between(0, 1).all()


def test_clv_and_offers():
    df = a.prepare(*fake_tables())
    clv, metrics, importance = a.clv_model(df)
    assert len(clv) == 40 and (clv >= 0).all()
    churn = a.churn_scores(df)
    offers = a.retention_offers(df, churn, a.basket_rules(df, "COMMODITY", 10), clv)
    assert set(range(1, 9)) <= set(offers.index)
    assert offers["Suggested offer"].notna().all()


def test_weather_join_and_forecast():
    df = a.prepare(*fake_tables())
    dates = pd.date_range(df["DATE"].min(), df["DATE"].max())
    weather = pd.DataFrame({"DATE": dates, "STORE_R": "EAST", "Temperature (F)": np.linspace(80, 20, len(dates)),
                            "Rain (in)": 0.1, "Snow (in)": 0.0})
    d = a.weather_daily(df, weather)
    assert len(d) == df["DATE"].nunique() and np.isclose(d["Spend"].sum(), df["SPEND"].sum())
    metrics, preds, effect = a.weather_forecast(d)
    assert set(metrics) == {"Without weather", "With weather"} and len(preds) > 0 and len(effect) == 3
    assert len(a.weather_by_commodity(df, weather, min_spend=0)) == 10
