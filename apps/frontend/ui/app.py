"""UI en Streamlit. Solo habla con el Flask BFF (nunca directo con AWS)."""

import json
import os
from pathlib import Path

import requests
import streamlit as st

BFF_URL = os.getenv("BFF_URL", "http://localhost:5000").rstrip("/")
SAMPLE = Path(__file__).resolve().parents[3] / "mocks" / "entrypoint" / "payloads" / "sample_job.json"

st.set_page_config(page_title="Goble", layout="wide")
st.title("Goble")

default_payload = SAMPLE.read_text(encoding="utf-8") if SAMPLE.exists() else "{}"

with st.form("create_job"):
    raw = st.text_area("Payload (JSON)", value=default_payload, height=220)
    submitted = st.form_submit_button("Procesar")

if submitted:
    try:
        resp = requests.post(f"{BFF_URL}/api/jobs", json=json.loads(raw), timeout=30)
        if resp.ok:
            st.success(f"HTTP {resp.status_code}")
        else:
            st.error(f"HTTP {resp.status_code}")
        st.json(resp.json())
    except json.JSONDecodeError:
        st.error("El payload no es JSON válido")
    except requests.RequestException as exc:
        st.error(f"No se pudo contactar el BFF en {BFF_URL}: {exc}")

st.divider()
job_id = st.text_input("Consultar job por ID")
if job_id:
    resp = requests.get(f"{BFF_URL}/api/jobs/{job_id}", timeout=15)
    st.json(resp.json())
