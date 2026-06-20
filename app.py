"""PHIMA Streamlit application entry point."""

import streamlit as st


st.set_page_config(
    page_title="PHIMA",
    page_icon="🧪",
    layout="wide",
)

st.title("PHIMA")
st.caption("A Streamlit app ready for Community Cloud deployment.")

st.markdown(
    """
    Welcome to **PHIMA**. This starter app is configured so it can be deployed
    directly to Streamlit Community Cloud.

    Use this page as the browser-testable entry point while the full PHIMA
    experience is built out.
    """
)

with st.sidebar:
    st.header("Deployment")
    st.success("Streamlit Community Cloud files are present.")
    st.write("Main file: `app.py`")

st.subheader("Health check")
st.write("If you can see this message, the Streamlit app is running correctly.")
