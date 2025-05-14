import streamlit as st
import requests
import pandas as pd

API_URL = "http://localhost:8000"

# --- Table Polishing Functions ---
def polish_symptoms_table(symptoms):
    if not symptoms:
        st.info("No symptoms submitted by this patient.")
        return

    df = pd.DataFrame(symptoms)
    if "diagnosis" not in df.columns:
        df["diagnosis"] = ""
    if "treatment_guidance" not in df.columns:
        df["treatment_guidance"] = ""
    df = df.rename(columns={
        "symptom": "Symptom",
        "user_severity": "Patient Rating",
        "calculated_severity": "Calculated Severity",
        "timestamp": "Timestamp",
        "diagnosis": "Diagnosis",
        "treatment_guidance": "Treatment Guidance"
    })
    df = df[["Symptom", "Patient Rating", "Diagnosis", "Treatment Guidance", "Calculated Severity", "Timestamp"]]
    st.dataframe(df, use_container_width=True)
    edited_df = st.experimental_data_editor(df, use_container_width=True)
    if st.button("Save"):
        updated_symptoms = []
        for index, row in edited_df.iterrows():
            updated_symptoms.append({
                "symptom": row["Symptom"],
                "user_severity": row["Patient Rating"],
                "calculated_severity": row["Calculated Severity"],
                "timestamp": row["Timestamp"],
                "diagnosis": row["Diagnosis"],
                "treatment_guidance": row["Treatment Guidance"]
            })
        try:
            response = requests.post(
                f"{API_URL}/update-diagnosis",
                headers={"Authorization": f"Bearer {st.session_state.token}"},
                json=updated_symptoms
            )
            response.raise_for_status()
            st.success("Changes saved successfully!")
        except Exception as e:
            st.error(f"Error saving changes: {e}")

# --- Auth State ---
if 'token' not in st.session_state:
    st.session_state.token = None
if 'user' not in st.session_state:
    st.session_state.user = None
if 'role' not in st.session_state:
    st.session_state.role = None

# --- Login ---
def login():
    st.title("Telemedicine Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            try:
                st.session_state.clear()
                response = requests.post(
                    f"{API_URL}/token",
                    data={"username": username, "password": password},
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
                data = response.json()
                st.session_state.token = data["access_token"]
                st.session_state.user = username
                st.session_state.role = data.get("role", "")
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {str(e)}")

# --- Health Monitoring (Medic) ---
def health_monitoring():
    st.header("Health Monitoring")
    patients = ["patient1"]
    selected_patient = st.selectbox("Select Patient", patients)
    if st.button("Medical Record"):
        try:
            response = requests.get(
                f"{API_URL}/patient-symptoms",
                headers={"Authorization": f"Bearer {st.session_state.token}"},
                params={"patient": selected_patient}
            )
            response.raise_for_status()
            symptoms = response.json()
            polish_symptoms_table(symptoms)
        except Exception as e:
            st.error(f"Error: {e}")

# --- Submit Symptoms (Patient) ---
def submit_symptoms():
    st.header("Submit Symptoms")
    symptom = st.selectbox("Symptom", ["Cough", "Fever", "Headache", "Shortness of Breath"])
    severity = st.slider("Severity (1-10)", 1, 10, 3)
    if st.button("Submit Symptoms"):
        try:
            response = requests.post(
                f"{API_URL}/submit-symptoms",
                headers={"Authorization": f"Bearer {st.session_state.token}"},
                json={"symptom": symptom.lower(), "severity": severity}
            )
            response.raise_for_status()
            data = response.json()
            calculated_severity = data.get('calculated_severity', 0)
            user_severity = data.get('user_severity', 0)
            symptom_name = data.get('symptom', '')
            if calculated_severity <= 3:
                color = "green"
            elif calculated_severity <= 7:
                color = "yellow"
            else:
                color = "red"
            st.markdown(
                f"Submitted: {symptom_name} | Your rating: {user_severity}/10 | "
                f"Clinical: <span style='color:{color}'>{calculated_severity}/10</span>",
                unsafe_allow_html=True
            )
        except Exception as e:
            st.error(f"Error: {e}")

# --- Video Session ---
def create_video_session():
    st.header("Create Video Session")
    if st.button("Start Session"):
        try:
            response = requests.post(
                f"{API_URL}/create-video-session",
                headers={"Authorization": f"Bearer {st.session_state.token}"}
            )
            response.raise_for_status()
            data = response.json()
            st.success(data.get("message", "Session started"))
            video_url = data.get("video_url")
            if video_url:
                st.markdown(f"[Click here to join the video session]({video_url})", unsafe_allow_html=True)
                st.components.v1.iframe(video_url, height=600)
        except Exception as e:
            st.error(f"Error: {e}")

# --- Trigger Alert ---
def trigger_alert():
    st.header("Trigger Alert")
    if st.button("Trigger Alert"):
        try:
            response = requests.post(
                f"{API_URL}/trigger-alert",
                headers={"Authorization": f"Bearer {st.session_state.token}"}
            )
            response.raise_for_status()
            st.success(response.json().get("message", "Alert triggered"))
        except Exception as e:
            st.error(f"Error: {e}")

# --- Active Alerts ---
def active_alerts():
    st.header("Active Alerts")
    status_filter = st.selectbox("Filter Alerts by Status", ["all", "active", "inactive"])
    params = {}
    if status_filter != "all":
        params["status"] = status_filter
    try:
        response = requests.get(
            f"{API_URL}/active-alerts",
            headers={"Authorization": f"Bearer {st.session_state.token}"},
            params=params
        )
        response.raise_for_status()
        alerts = response.json()
        if not alerts:
            st.info("No alerts to display.")
            return
        df = pd.DataFrame(alerts)
        if not df.empty:
            df = df.rename(columns={
                'alert_id': 'Alert ID',
                'patient': 'User',
                'status': 'Status'
            })
            df.index = df.index + 1
            df = df.reset_index(drop=True)
            st.dataframe(df[["id"]], use_container_width=True)
        else:
            st.info("No alerts to display.")
    except Exception as e:
        st.error(f"Error loading alerts: {e}")

# --- Medical Supplies (Medic) ---
def update_supply():
    st.header("Update Supply")
    try:
        response = requests.get(
            f"{API_URL}/medical-supplies",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        response.raise_for_status()
        supplies = response.json()
        supply_items = [supply['item'] for supply in supplies]
    except Exception as e:
        st.error(f"Error fetching supplies: {e}")
        supplies = []
        supply_items = []
    item = st.selectbox("Select Item to Update", supply_items + ["Add New Item"])
    if item == "Add New Item":
        item = st.text_input("Enter New Item Name")
    quantity = st.number_input("Quantity", min_value=0, step=1)
    if st.button("Update Supply"):
        try:
            response = requests.post(
                f"{API_URL}/update-supply",
                headers={"Authorization": f"Bearer {st.session_state.token}"},
                json={"item": item, "quantity": quantity}
            )
            response.raise_for_status()
            result = response.json()
            st.success(f"{result['message']}: {item} = {quantity}")
        except Exception as e:
            st.error(f"Error: {e}")

def delete_supply():
    st.header("Delete Supply")
    try:
        response = requests.get(
            f"{API_URL}/medical-supplies",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        response.raise_for_status()
        supplies = response.json()
        supply_items = {supply['item']: supply['quantity'] for supply in supplies}
    except Exception as e:
        st.error(f"Error fetching supplies: {e}")
        return
    item_to_delete = st.selectbox("Select Item to Delete", list(supply_items.keys()))
    max_quantity = supply_items[item_to_delete]

    if max_quantity == 0:
        st.warning(f"No '{item_to_delete}' left to delete.")
    else:
        quantity_to_delete = st.number_input(
            "Quantity to Delete",
            min_value=1,
            max_value=max_quantity,
            step=1
        )
        if st.button("Delete Supply"):
            try:
                response = requests.delete(
                    f"{API_URL}/delete-supply",
                    headers={"Authorization": f"Bearer {st.session_state.token}"},
                    json={"item": item_to_delete, "quantity": quantity_to_delete}
                )
                response.raise_for_status()
                st.success(f"Successfully deleted {quantity_to_delete} of {item_to_delete}")
            except Exception as e:
                st.error(f"Error deleting supply: {e}")

def medical_supplies():
    st.header("Medical Supplies")
    if st.button("Load Supplies"):
        try:
            response = requests.get(
                f"{API_URL}/medical-supplies",
                headers={"Authorization": f"Bearer {st.session_state.token}"}
            )
            response.raise_for_status()
            supplies = response.json()
            if not supplies:
                st.info("No supplies found.")
            for supply in supplies:
                st.write(f"{supply['item']}: {supply['quantity']}")
        except Exception as e:
            st.error(f"Error: {e}")

# --- Delivery Logistics ---
def delivery_logistics():
    st.header("Medical Services Delivery and Logistics")
    with st.form("delivery_form"):
        destination = st.text_input("Destination (location, coordinates, or region)")
        item = st.selectbox(
            "Item to Deliver",
            ["Vaccine", "Medical Aid Kit", "Antibiotics", "IV Fluids", "Bandages"]
        )
        quantity = st.number_input("Quantity", min_value=1, step=1)
        vehicle = st.selectbox(
            "Delivery Method",
            ["Drone", "Autonomous Land Vehicle", "Autonomous Water Vehicle"]
        )
        delivery_time = st.text_input("Delivery Time (e.g., '2025-05-07 14:00', 'ASAP', or 'Tomorrow')")
        submit = st.form_submit_button("Request Delivery")
        if submit:
            if not destination.strip():
                st.error("Destination cannot be empty.")
                return
            if not item.strip():
                st.error("Item cannot be empty.")
                return
            if quantity <= 0:
                st.error("Quantity must be greater than 0.")
                return
            if not delivery_time.strip():
                st.error("Delivery time cannot be empty.")
                return
            delivery_payload = {
                "destination": destination,
                "item": item,
                "quantity": quantity,
                "vehicle": vehicle,
                "delivery_time": delivery_time
            }
            st.write("Payload being sent:", delivery_payload)
            try:
                response = requests.post(
                    f"{API_URL}/request-delivery",
                    json=delivery_payload
                )
                response.raise_for_status()
                st.success("Delivery request submitted successfully!")
            except Exception as e:
                st.error(f"Error submitting delivery request: {e}")
    # Show existing delivery requests
    try:
        resp = requests.get(
            f"{API_URL}/deliveries",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        resp.raise_for_status()
        deliveries = resp.json()
        if deliveries:
            st.subheader("Recent Delivery Requests")
            st.table(deliveries)
    except Exception as e:
        st.info("No deliveries found or error loading deliveries.")

# --- Search and Rescue ---
def search_and_rescue():
    st.header("Support Search and Rescue Operations")
    st.markdown(
        "<b>Support Search and Rescue Operations:</b> Leverage Galileo’s Search and Rescue (SAR) services to provide emergency medical aid to individuals in danger and develop tools to streamline the coordination between rescue teams and healthcare providers.",
        unsafe_allow_html=True,
    )
    with st.form("sar_form"):
        emergency_type = st.selectbox("Type of Emergency", [
            "Medical Emergency", "Natural Disaster", "Lost Person", "Other"
        ])
        if emergency_type == "Other":
            emergency_type = st.text_input("Describe the Emergency")
        location = st.text_input("Location (address or coordinates)")
        urgency = st.selectbox("Urgency Level", ["Low", "Medium", "High", "Critical"])
        submit = st.form_submit_button("Request SAR")
        if submit:
            try:
                response = requests.post(
                    f"{API_URL}/sar-request",
                    headers={"Authorization": f"Bearer {st.session_state.token}"},
                    json={
                        "emergency_type": emergency_type,
                        "location": location,
                        "urgency": urgency
                    }
                )
                response.raise_for_status()
                st.success("SAR request submitted!")
            except Exception as e:
                st.error(f"Error: {e}")
    # Show existing SAR requests in a polished, expandable table
    try:
        resp = requests.get(
            f"{API_URL}/sar-requests",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        resp.raise_for_status()
        sar_requests = resp.json()
        if sar_requests:
            df = pd.DataFrame(sar_requests)
            # Optional: Rename columns for clarity
            df = df.rename(columns={
                "id": "ID",
                "emergency_type": "Emergency Type",
                "location": "Location",
                "urgency": "Urgency",
                "description": "Description",
                "contact_number": "Contact Number",
                "satellite_data": "Satellite Data"
            })
            # Show in an expander for "pop-up" effect
            with st.expander("Show Active SAR Requests Table", expanded=True):
                st.dataframe(df, use_container_width=True)
        else:
            st.info("No SAR requests found.")
    except Exception as e:
        st.info("No SAR requests found or error loading SAR requests.")

def submit_sar_with_satellite():
    st.header("SAR Request with Satellite Data")
    with st.form("sar_sat_form"):
        emergency_type = st.selectbox("Type of Emergency", [
            "Medical Emergency", "Natural Disaster", "Lost Person", "Other"
        ])
        if emergency_type == "Other":
            emergency_type = st.text_input("Describe the Emergency")
        location_input = st.text_input(
            "Location (place name or latitude,longitude)",
            help="You can enter a place name (e.g. 'Athens') or coordinates (e.g. '37.9838,23.7275')."
        )
        coords = None
        if location_input and "," not in location_input:
            if st.form_submit_button("Convert Place Name to Coordinates"):
                coords = address_to_coordinates(location_input)
                if coords:
                    st.info(f"Coordinates for '{location_input}': {coords}")
                else:
                    st.warning("Could not find coordinates for that address.")
        urgency = st.selectbox("Urgency Level", ["Low", "Medium", "High", "Critical"])
        description = st.text_area("Description of the Emergency")
        contact_number = st.text_input("Contact Number")
        submit = st.form_submit_button("Request SAR with Satellite")
        if submit:
            location = coords if coords else location_input
            payload = {
                "emergency_type": emergency_type,
                "location": location,
                "urgency": urgency,
                "description": description,
                "contact_number": contact_number
            }
            st.write("Payload being sent:", payload)  # For debugging
            try:
                response = requests.post(
                    f"{API_URL}/sar-with-satellite",
                    headers={"Authorization": f"Bearer {st.session_state.token}"},
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                st.success("SAR request with satellite data submitted!")
                st.write("**Stored Location:**", data.get("location", "N/A"))
                st.write("**Satellite data:**")
                st.json(data.get("satellite_data", {}))
            except Exception as e:
                if hasattr(e, 'response') and e.response is not None:
                    st.error(f"Backend error: {e.response.text}")
                else:
                    st.error(f"Error submitting SAR request: {e}")
    # Show existing SAR requests with satellite in a polished table
    try:
        resp = requests.get(
            f"{API_URL}/sar-requests",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        resp.raise_for_status()
        sar_requests = resp.json()
        if sar_requests:
            df = pd.DataFrame(sar_requests)
            df = df.rename(columns={
                "id": "ID",
                "emergency_type": "Emergency Type",
                "location": "Location",
                "urgency": "Urgency",
                "description": "Description",
                "contact_number": "Contact Number",
                "satellite_data": "Satellite Data"
            })
            with st.expander("Show All SAR Requests Table", expanded=False):
                st.dataframe(df, use_container_width=True)
        else:
            st.info("No SAR requests found.")
    except Exception as e:
        st.info("No SAR requests found or error loading SAR requests.")

import requests
import streamlit as st

def address_to_coordinates(address):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json"}
    headers = {"User-Agent": "RemoteHealthApp/1.0 (ktrepas@gmail.com)"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code != 200:
            st.warning(f"Geocoding API error: {response.status_code}")
            return None
        results = response.json()
        if results:
            lat = results[0]["lat"]
            lon = results[0]["lon"]
            return f"{lat},{lon}"
        else:
            return None
    except Exception as e:
        st.warning(f"Geocoding failed: {e}")
        return None

# --- Chat Session ---
def chat_session():
    st.header("Chat Session")
    if st.session_state.role == "medical_staff":
        diagnosis = st.text_area("Diagnosis", placeholder="Enter diagnosis here...")
        treatment_guidance = st.text_area("Treatment Guidance", placeholder="Enter treatment guidance here...")
        if st.button("Submit"):
            if not diagnosis.strip() or not treatment_guidance.strip():
                st.error("Both fields are required.")
                return
            st.success("Diagnosis and Treatment Guidance submitted successfully!")
            st.write("### Submitted Data")
            st.write(f"**Diagnosis:** {diagnosis}")
            st.write(f"**Treatment Guidance:** {treatment_guidance}")
    else:
        st.text_area("Diagnosis (Read-Only)", "No diagnosis available yet.", disabled=True)
        treatment_guidance = st.text_area("Treatment Guidance", placeholder="Enter treatment guidance here...")
        if st.button("Submit"):
            if not treatment_guidance.strip():
                st.error("Treatment Guidance is required.")
                return
            st.success("Treatment Guidance submitted successfully!")
            st.write("### Submitted Data")
            st.write(f"**Treatment Guidance:** {treatment_guidance}")

def view_any_table():
    st.header("View Any SQL Server Table")
    # Dropdown for known tables
    table_options = ["MedicalSupplies", "Alerts", "SARRequests"]
    table_name = st.selectbox("Select table to view:", table_options)
    limit = st.number_input("Max rows to fetch", min_value=1, max_value=10000, value=1000)
    if st.button("Load Table"):
        try:
            response = requests.get(
                f"{API_URL}/table/{table_name}",
                params={"limit": limit},
                headers={"Authorization": f"Bearer {st.session_state.token}"}
            )
            response.raise_for_status()
            records = response.json()
            if records:
                df = pd.DataFrame(records)
                with st.expander(f"Show Table: {table_name}", expanded=True):
                    st.dataframe(df.reset_index(drop=True), use_container_width=True)
            else:
                st.info("No records found.")
        except Exception as e:
            st.error(f"Error loading table: {e}")

# --- Main App ---
def main():
    if not st.session_state.token:
        login()
        return
    st.sidebar.title(f"Logged in as {st.session_state.user}")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()
    if st.session_state.role == "medical_staff":
        menu_options = [
            "Health Monitoring",
            "Chat Session",
            "Create Video Session",
            "Trigger Alert",
            "Active Alerts",
            "Medical Supplies",
            "Update Supply",
            "Delete Supply",
            "Delivery Logistics",
            "Search and Rescue",
            "Submit SAR with Satellite",
            "View Any Table"  # <-- Add this line
        ]
    else:
        menu_options = [
            "Chat Session",
            "Submit Symptoms",
            "Create Video Session",
            "Trigger Alert",
            "Active Alerts"
        ]
    menu = st.sidebar.radio("Menu", menu_options)
    if menu == "Health Monitoring":
        health_monitoring()
    elif menu == "Submit Symptoms":
        submit_symptoms()
    elif menu == "Create Video Session":
        create_video_session()
    elif menu == "Trigger Alert":
        trigger_alert()
    elif menu == "Active Alerts":
        active_alerts()
    elif menu == "Medical Supplies":
        medical_supplies()
    elif menu == "Update Supply":
        update_supply()
    elif menu == "Delete Supply":
        delete_supply()
    elif menu == "Delivery Logistics":
        delivery_logistics()
    elif menu == "Search and Rescue":
        search_and_rescue()
    elif menu == "Submit SAR with Satellite":
        submit_sar_with_satellite()
    elif menu == "Chat Session":
        chat_session()
    elif menu == "View Any Table":
        view_any_table()

if __name__ == "__main__":
    main()




