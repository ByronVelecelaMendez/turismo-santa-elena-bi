import os
import streamlit as st
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()


@st.cache_resource
def get_engine():
    host     = os.getenv("DB_HOST")
    port     = os.getenv("DB_PORT")
    database = os.getenv("DB_NAME")
    user     = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    engine = create_engine(url)
    return engine


def get_connection():
    engine = get_engine()
    return engine.connect()