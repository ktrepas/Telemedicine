# Remote Health Telemedicine Platform

A web-based telemedicine and emergency response platform built with **Streamlit** (frontend) and **FastAPI** (backend), using SQL Server for data storage.

---

## Features

- **User Authentication** (patients & medical staff)
- **Symptom Submission** (patients)
- **Medical Record Viewing** (medics)
- **Diagnosis & Treatment Guidance** (medics)
- **Video & Chat Sessions**
- **Trigger & View Alerts**
- **Medical Supplies Management** (view, update, delete)
- **Delivery Logistics** (request and track deliveries)
- **Search and Rescue (SAR) Requests** (with satellite/geolocation support)
- **Dashboard** (admin/medic utility)

---

## Space Technologies Used

- **GNSS/Geolocation:** Accurate mapping and location management.
- **Satellite Earth Observation:** Sentinel-2 for SAR operations.
- **Satellite-based SAR Services:** Enhanced emergency coordination.

---

## Requirements

- Python 3.8+
- [Streamlit](https://streamlit.io/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Uvicorn](https://www.uvicorn.org/)
- [pandas](https://pandas.pydata.org/)
- [requests](https://docs.python-requests.org/)
- [pyodbc](https://github.com/mkleehammer/pyodbc) (for SQL Server)
- SQL Server (for production mode)

Install dependencies:
```sh
pip install streamlit fastapi uvicorn pandas requests pyodbc

Here is your complete **README.md** file, including the corrected Nominatim link and a section for the space technologies used:

---

```markdown

## Requirements

- Python 3.8+
- [Streamlit](https://streamlit.io/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Uvicorn](https://www.uvicorn.org/)
- [pandas](https://pandas.pydata.org/)
- [requests](https://docs.python-requests.org/)
- [pyodbc](https://github.com/mkleehammer/pyodbc) (for SQL Server)
- SQL Server (for production mode)

Install dependencies:
```sh
pip install streamlit fastapi uvicorn pandas requests pyodbc
```

---

## Running the App

### 1. Start the Backend

In the folder with `telemedicine.py`:
```sh
uvicorn telemedicine:app --reload
```

### 2. Start the Frontend

In the folder with `app.py`:
```sh
streamlit run app.py
```

The app will open in your browser at [http://localhost:8501](http://localhost:8501).

---

## Configuration

- Edit `API_URL` in `app.py` if your backend runs on a different host/port.
- Database connection settings are in `telemedicine.py` (edit for your SQL Server).

---

## Usage

- **Patients:** Log in and submit symptoms, join video/chat sessions, and trigger alerts.
- **Medical Staff:** Log in to view patient records, manage supplies, respond to alerts, and coordinate SAR operations.

---

## Database Schema

You should have at least the following tables in your SQL Server database:

### Symptoms

```sql
CREATE TABLE Symptoms (
    id INT IDENTITY(1,1) PRIMARY KEY,
    patient NVARCHAR(100) NOT NULL,
    symptom NVARCHAR(100) NOT NULL,
    user_severity INT NOT NULL,
    calculated_severity INT NOT NULL,
    timestamp DATETIME NOT NULL,
    diagnosis NVARCHAR(255) NULL,
    treatment_guidance NVARCHAR(255) NULL
);
```

### MedicalSupplies

```sql
CREATE TABLE MedicalSupplies (
    id INT IDENTITY(1,1) PRIMARY KEY,
    item NVARCHAR(100) NOT NULL,
    quantity INT NOT NULL,
    updates INT NOT NULL DEFAULT 0
);
```

### Alerts

```sql
CREATE TABLE Alerts (
    alert_id INT IDENTITY(1,1) PRIMARY KEY,
    patient NVARCHAR(100) NOT NULL,
    status NVARCHAR(50) NOT NULL,
    trigger_time DATETIME NOT NULL
);
```

### SARRequests

```sql
CREATE TABLE SARRequests (
    id INT IDENTITY(1,1) PRIMARY KEY,
    emergency_type NVARCHAR(100) NOT NULL,
    location NVARCHAR(255) NOT NULL,
    urgency NVARCHAR(50) NOT NULL,
    description NVARCHAR(255),
    contact_number NVARCHAR(50),
    satellite_data NVARCHAR(MAX)
);
```

---

## API Endpoints

Some key backend endpoints:

- `POST /token` — User authentication
- `POST /submit-symptoms` — Submit symptoms (patient)
- `GET /patient-symptoms` — Get symptoms for a patient (medic)
- `POST /update-diagnosis` — Update diagnosis/treatment (medic)
- `GET /medical-supplies` — List medical supplies
- `POST /update-supply` — Update/add supply
- `DELETE /delete-supply` — Delete supply
- `POST /trigger-alert` — Trigger alert
- `GET /active-alerts` — List active alerts
- `POST /sar-request` — Submit SAR request
- `GET /sar-requests` — List SAR requests
- `GET /tables` — List all tables
- `GET /table/{table_name}` — Dashboard table view
- `DELETE /delete-row/{table_name}` — Delete a row by id

---

## Notes

- Make sure your SQL Server database is set up with the required tables.
- For geolocation, the app uses the [Nominatim OpenStreetMap API](https://nominatim.openstreetmap.org/).
- For satellite features, see the SAR and satellite request sections.
- The app can be accessed from a mobile device browser as well as desktop.

---

## License

MIT License


## Authors

- [Konstantinos Trepas](mail to:ktrepas@gmail.com)

---

## Acknowledgements

- European Space Agency (ESA) Copernicus/Sentinel-2
- OpenStreetMap Nominatim
- Streamlit, FastAPI, Uvicorn, Pandas

