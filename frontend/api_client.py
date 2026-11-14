import requests
import streamlit as st

API_BASE_URL = "http://127.0.0.1:8000/api/v1"
TIMEOUT = 60


def get_auth_headers():
    token = st.session_state.get("access_token")

    if token:
        return {"Authorization": f"Bearer {token}"}

    return {}


def api_register(data):
    response = requests.post(
        f"{API_BASE_URL}/auth/register",
        json=data,
        timeout=TIMEOUT
    )
    response.raise_for_status()
    return response.json()


def api_login(university_code, password):
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={
            "university_code": university_code,
            "password": password
        },
        timeout=TIMEOUT
    )

    response.raise_for_status()
    result = response.json()

    st.session_state["access_token"] = result["access_token"]
    st.session_state["university"] = result["university"]
    st.session_state["authenticated"] = True

    return result


def api_logout():
    for key in ["access_token", "university", "authenticated"]:
        if key in st.session_state:
            del st.session_state[key]


def api_get(endpoint, params=None):
    response = requests.get(
        f"{API_BASE_URL}{endpoint}",
        headers=get_auth_headers(),
        params=params,
        timeout=TIMEOUT
    )
    response.raise_for_status()

    if response.status_code == 204:
        return None

    return response.json()


def api_post(endpoint, data=None, files=None):
    if files:
        response = requests.post(
            f"{API_BASE_URL}{endpoint}",
            headers=get_auth_headers(),
            data=data,
            files=files,
            timeout=TIMEOUT
        )
    else:
        response = requests.post(
            f"{API_BASE_URL}{endpoint}",
            headers=get_auth_headers(),
            json=data,
            timeout=TIMEOUT
        )

    response.raise_for_status()

    if response.status_code == 204:
        return None

    return response.json()


def api_put(endpoint, data):
    response = requests.put(
        f"{API_BASE_URL}{endpoint}",
        headers=get_auth_headers(),
        json=data,
        timeout=TIMEOUT
    )
    response.raise_for_status()

    if response.status_code == 204:
        return None

    return response.json()


def get_error_message(error):
    if isinstance(error, requests.HTTPError):
        try:
            details = error.response.json().get("detail", str(error))
            return str(details)
        except Exception:
            return str(error)

    return str(error)



def api_delete(endpoint):
    response = requests.delete(
        f"{API_BASE_URL}{endpoint}",
        headers=get_auth_headers(),
        timeout=TIMEOUT
    )
    response.raise_for_status()

    if response.status_code == 204:
        return None

    return response.json()
