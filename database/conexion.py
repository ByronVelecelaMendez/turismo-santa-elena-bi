import streamlit as st
from sqlalchemy import create_engine


@st.cache_resource
def get_engine():
    url = st.secrets["database"]["url"]
    engine = create_engine(url)
    return engine


def get_connection():
    engine = get_engine()
    return engine.connect()