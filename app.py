import streamlit as st
import bcrypt
from sqlalchemy import text
from db import get_engine

st.set_page_config(page_title="ShopSmart 360", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = ""

def verify_login(username, password):
    with get_engine().connect() as conn:
        row = conn.execute(
            text("SELECT password_hash FROM users WHERE username = :u"),
            {"u": username}
        ).fetchone()
    if row and bcrypt.checkpw(password.encode(), row[0].encode()):
        st.session_state.authenticated = True
        st.session_state.username = username
        st.rerun()
    else:
        st.error("Invalid username or password.")

def register_user(username, email, password):
    if not username or not email or not password:
        st.warning("Please fill in all fields.")
        return
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        with get_engine().begin() as conn:
            conn.execute(
                text("INSERT INTO users (username, email, password_hash) VALUES (:u, :e, :p)"),
                {"u": username, "e": email, "p": hashed}
            )
        st.success("Account created! You can now log in.")
    except Exception:
        st.error("Username already exists. Please choose another.")

if not st.session_state.authenticated:
    st.title("ShopSmart 360 — Retail Analytics Platform")
    tab_login, tab_register = st.tabs(["Log In", "Register"])

    with tab_login:
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Log In"):
                verify_login(u, p)

    with tab_register:
        with st.form("register_form"):
            new_u = st.text_input("Choose Username")
            new_e = st.text_input("Email Address")
            new_p = st.text_input("Choose Password", type="password")
            if st.form_submit_button("Create Account"):
                register_user(new_u, new_e, new_p)
    st.stop()

st.sidebar.success(f"Logged in as {st.session_state.username}")
if st.sidebar.button("Log Out"):
    st.session_state.authenticated = False
    st.rerun()

st.title("Welcome to ShopSmart 360")
st.write("Select a page from the left sidebar to explore Household #10, search households, or upload new CSV files.")
