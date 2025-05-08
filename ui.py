# title.py
import streamlit as st

def display_title():
    # Customize the title with HTML and CSS
    st.markdown("""
        <h1 style='text-align: center; color: #4CAF50; font-family: Arial, sans-serif; font-size: 3em; margin-top: 20px;'>
            No-Fly Zone Enforcement
        </h1>
    """, unsafe_allow_html=True)
