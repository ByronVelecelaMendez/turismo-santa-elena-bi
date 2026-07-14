import os
import streamlit as st
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()


@st.cache_resource
def get_engine():
    # En Streamlit Cloud lee desde st.secrets,
    # en local lee desde el archivo .env
    try:
        url = st.secrets["database"]["url"]
    except Exception:
        host     = os.getenv("DB_HOST")
        port     = os.getenv("DB_PORT", "5432")
        database = os.getenv("DB_NAME")
        user     = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        url = f"postgresql://{user}:{password}@{host}:{port}/{database}"

    engine = create_engine(url)
    return engine


def get_connection():
    engine = get_engine()
    return engine.connect()