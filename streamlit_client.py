import os

import streamlit as st
import requests

# FastAPI server URL
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL","http://localhost:8000")  # Replace with your FastAPI server URL

# Page configuration
st.set_page_config(page_title="gRPC Query Service", layout="wide")

# App title
st.title("NCERT Class X Science")

# Section: Submit a Query
st.header("Submit a Query")
query_input = st.text_input("Enter your query(Hindi/English):")

if st.button("Submit Query"):
    if query_input.strip():
        try:
            response = requests.post(f"{FASTAPI_BASE_URL}/submit-query", json={"query": query_input})
            if response.status_code == 200:
                query_id = response.text.strip('"')
                st.success(f"Query submitted successfully! Query ID: {query_id}")
            else:
                st.error(f"Error: {response.json()['detail']}")
        except Exception as e:
            st.error(f"Error connecting to the FastAPI server: {e}")
    else:
        st.warning("Query input cannot be empty.")

# Section: View Responses
st.header("View Responses")

if st.button("Get Responses"):
    try:
        response = requests.get(f"{FASTAPI_BASE_URL}/get-response")
        if response.status_code == 200:
            st.write("**Response:**")
            st.json(response.json())
        elif response.status_code == 404:
            st.warning("No responses available yet.")
        else:
            st.error(f"Error: {response.json()['detail']}")
    except Exception as e:
        st.error(f"Error connecting to the FastAPI server: {e}")

# Sidebar: Information
st.sidebar.title("About")
st.sidebar.info(
    """
    This is a simple interface to interact with the gRPC Query Service using FastAPI.
    - Submit queries to the service.
    - View responses streamed from the gRPC server.
    """
)
