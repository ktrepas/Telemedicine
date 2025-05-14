from fastapi import FastAPI, Depends, HTTPException, status, Body, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
import logging
import os
import pyodbc
import pandas as pd
import json
from sentinelsat import SentinelAPI
import requests
from contextlib import asynccontextmanager
import uuid

logging.basicConfig(level=logging.INFO)

SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
SUPPLIES_FILE = "medical_supplies.json"
COUNTS_FILE = "supply_update_counts.json"

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    yield
    print("Shutting down...")

app = FastAPI(title="Telemedicine API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class User(BaseModel):
    username: str
    role: str

class UserInDB(User):
    hashed_password: str

class DeleteSupplyRequest(BaseModel):
    item: str    
    quantity: int

class DeliveryRequest(BaseModel):
    destination: str
    item: str
    quantity: int
    vehicle: str
    delivery_time: str

class SARRequest(BaseModel):
    emergency_type: str
    location: str
    urgency: str
    description: Optional[str] = None
    contact_number: Optional[str] = None
    satellite_data: Optional[dict] = None
    id: Optional[int] = None

fake_users_db = {
    "patient1": {
        "username": "patient1",
        "role": "patient",
        "hashed_password": pwd_context.hash("patientpass")
    },
    "medic1": {
        "username": "medic1",
        "role": "medical_staff",
        "hashed_password": pwd_context.hash("medicpass")
    }
}

def get_db_connection():
    try:
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=DESKTOP-4F2MQM0\\SQLEXPRESS;"
            "DATABASE=Telemedicine;"
            "Trusted_Connection=yes;"
        )
        return conn
    except pyodbc.Error as e:
        print("Error:", e)
        return None

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_user(db, username: str):
    if username in db:
        return UserInDB(**db[username])

def authenticate_user(username: str, password: str):
    user = get_user(fake_users_db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username)
    if user is None:
        raise credentials_exception
    return user

def require_role(required_role: str):
    async def role_checker(current_user: User = Depends(get_current_user)):
        if (current_user.role != required_role):
            raise HTTPException(status_code=403, detail="Operation not permitted")
        return current_user
    return role_checker

def fetch_satellite_data(area, start_date, end_date):
    api = SentinelAPI('your_username', 'your_password', 'https://scihub.copernicus.eu/dhus')
    try:
        products = api.query(
            area=area,
            date=(start_date, end_date),
            platformname='Sentinel-2',
            cloudcoverpercentage=(0, 30)
        )
        logging.info(f"Satellite data fetched: {products}")
        return products
    except Exception as e:
        logging.error(f"Error fetching satellite data: {e}")
        return {}

def reverse_geocode(lat, lon):
    try:
        response = requests.get(f"https://nominatim.openstreetmap.org/reverse", params={
            "lat": lat,
            "lon": lon,
            "format": "json"
        })
        response.raise_for_status()
        data = response.json()
        logging.info(f"Reverse geocoding response: {data}")
        return data.get("display_name", f"{lat}, {lon}")
    except Exception as e:
        logging.error(f"Error in reverse geocoding: {e}")
        return f"{lat}, {lon}"

def geocode_location(location_name):
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": location_name, "format": "json"}
        )
        response.raise_for_status()
        results = response.json()
        logging.info(f"Geocoding '{location_name}' results: {results}")
        if results:
            lat = results[0]["lat"]
            lon = results[0]["lon"]
            return float(lat), float(lon)
        else:
            return None, None
    except Exception as e:
        logging.error(f"Error in geocoding: {e}")
        return None, None

def format_json_column(df, column_name):
    df[column_name] = df[column_name].apply(lambda x: json.dumps(json.loads(x), indent=2) if x else "{}")
    return df

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role
    }

@app.post("/submit-symptoms")
async def submit_symptoms(
    symptoms: dict,
    current_user: User = Depends(get_current_user)
):
    if (current_user.role != "patient"):
        raise HTTPException(status_code=403, detail="Only patients can submit symptoms.")
    symptom = symptoms.get("symptom", "").lower()
    user_severity = symptoms.get("severity", 1)
    severity_map = {
        "cough": lambda x: min(x, 3),
        "fever": lambda x: x * 2 if x > 3 else x,
        "headache": lambda x: x + 1 if x > 5 else x,
        "shortness_of_breath": lambda x: x * 3
    }
    calculated_severity = severity_map.get(symptom, lambda x: x)(user_severity)
    entry = {
        "patient": current_user.username,
        "symptom": symptom,
        "user_severity": user_severity,
        "calculated_severity": min(calculated_severity, 10),
        "timestamp": datetime.now().isoformat()
    }
    # TODO: Save to database if needed
    return entry

@app.get("/patient-symptoms")
async def get_patient_symptoms(
    patient: str,
    current_user: User = Depends(require_role("medical_staff"))
):
    # TODO: Fetch from database if needed
    return []

@app.post("/create-video-session")
async def create_video_session(current_user: User = Depends(get_current_user)):
    room_id = str(uuid.uuid4())
    jitsi_url = f"https://meet.jit.si/{room_id}"
    return {
        "message": f"Video session created by {current_user.username}",
        "video_url": jitsi_url
    }

@app.post("/trigger-alert")
async def trigger_alert(current_user: User = Depends(get_current_user)):
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    query = """
    INSERT INTO Alerts (alert_id, patient, status)
    VALUES (?, ?, ?)
    """
    alert_id = f"ALERT-{uuid.uuid4().hex[:6].upper()}"
    conn.execute(query, (alert_id, current_user.username, "active"))
    conn.commit()
    conn.close()
    return {"message": f"Alert triggered by {current_user.username}", "alert_id": alert_id}

@app.get("/active-alerts")
def get_active_alerts(status: Optional[str] = Query(None)):
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    if status:
        query = "SELECT * FROM Alerts WHERE status = ?"
        df = pd.read_sql(query, conn, params=[status])
    else:
        query = "SELECT * FROM Alerts"
        df = pd.read_sql(query, conn)
    conn.close()
    return df.to_dict(orient="records")

@app.post("/update-supply")
def update_supply(item: str = Body(...), quantity: int = Body(...)):
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    query = """
    MERGE INTO MedicalSupplies AS target
    USING (SELECT ? AS item, ? AS quantity) AS source
    ON target.item = source.item
    WHEN MATCHED THEN
        UPDATE SET quantity = source.quantity, updates = target.updates + 1
    WHEN NOT MATCHED THEN
        INSERT (item, quantity, updates) VALUES (source.item, source.quantity, 1);
    """
    conn.execute(query, (item, quantity))
    conn.commit()
    conn.close()
    return {"message": "Supply updated successfully"}

@app.get("/medical-supplies")
def get_supplies():
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    query = "SELECT * FROM MedicalSupplies"
    df = pd.read_sql(query, conn)
    conn.close()
    return df.to_dict(orient="records")

@app.delete("/delete-supply")
def delete_supply(request: DeleteSupplyRequest):
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    query = "DELETE FROM MedicalSupplies WHERE item = ?"
    conn.execute(query, (request.item,))
    conn.commit()
    conn.close()
    return {"message": f"Deleted {request.item}"}

@app.post("/request-delivery")
def request_delivery(request: DeliveryRequest):
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    query = """
    INSERT INTO Deliveries (destination, item, quantity, vehicle, delivery_time)
    VALUES (?, ?, ?, ?, ?)
    """
    try:
        conn.execute(query, (
            request.destination,
            request.item,
            request.quantity,
            request.vehicle,
            request.delivery_time
        ))
        conn.commit()
        return {"message": "Delivery requested successfully"}
    except Exception as e:
        conn.rollback()
        # Log the error and return it in the response for debugging
        logging.error(f"Error in /request-delivery: {e}")
        raise HTTPException(status_code=500, detail=f"Error in /request-delivery: {e}")
    finally:
        conn.close()

@app.get("/deliveries")
def get_deliveries():
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    query = "SELECT * FROM Deliveries"
    df = pd.read_sql(query, conn)
    conn.close()
    if df.empty:
        return {"message": "No deliveries found"}
    return df.to_dict(orient="records")

@app.post("/sar-request")
def create_sar_request(request: SARRequest):
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    query = """
    INSERT INTO SARRequests (emergency_type, location, urgency, description, contact_number, satellite_data)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    conn.execute(query, (
        request.emergency_type,
        request.location,
        request.urgency,
        request.description,
        request.contact_number,
        json.dumps(request.satellite_data) if request.satellite_data else "{}"
    ))
    conn.commit()
    conn.close()
    return {"message": "SAR request submitted successfully"}

@app.post("/sar-with-satellite")
def sar_with_sarellite(request: SARRequest):
    # Try to parse as coordinates
    try:
        lat, lon = map(float, request.location.split(","))
        location_label = None
    except ValueError:
        # Not coordinates, try geocoding
        lat, lon = geocode_location(request.location)
        location_label = request.location
        if lat is None or lon is None:
            raise HTTPException(status_code=400, detail="Could not geocode location name.")
    area = {"type": "Point", "coordinates": [lon, lat]}
    satellite_data = fetch_satellite_data(area, '2025-01-01', '2025-01-31')
    human_readable_location = reverse_geocode(lat, lon)
    # Format as NAME[lat,lon] if label is present
    if location_label:
        stored_location = f"{location_label}[{lat},{lon}]"
    else:
        stored_location = human_readable_location
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    query = """
    INSERT INTO SARRequests (emergency_type, location, urgency, description, contact_number, satellite_data)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    conn.execute(query, (
        request.emergency_type,
        stored_location,
        request.urgency,
        request.description,
        request.contact_number,
        json.dumps(satellite_data)
    ))
    conn.commit()
    conn.close()
    return {
        "message": "SAR request submitted with satellite data",
        "satellite_data": satellite_data,
        "location": stored_location
    }

@app.get("/sar-requests")
def get_sar_requests():
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    query = "SELECT * FROM SARRequests"
    df = pd.read_sql(query, conn)
    df = format_json_column(df, "satellite_data")
    conn.close()
    return df.to_dict(orient="records")

@app.post("/update-sar-request")
def update_sar_request(request: SARRequest):
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    query = """
    UPDATE SARRequests
    SET location = ?, urgency = ?, description = ?, contact_number = ?, satellite_data = ?
    WHERE id = ?
    """
    try:
        conn.execute(query, (
            request.location,
            request.urgency,
            request.description,
            request.contact_number,
            json.dumps(request.satellite_data) if request.satellite_data else "{}",
            request.id
        ))
        conn.commit()
        return {"message": "SAR request updated successfully"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating SAR request: {e}")
    finally:
        conn.close()

@app.get("/table/{table_name}")
def get_table(table_name: str, limit: int = Query(1000, ge=1, le=10000)):
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        query = f"SELECT TOP {limit} * FROM [{table_name}]"
        df = pd.read_sql(query, conn)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@app.get("/")
async def root():
    return {"message": "Telemedicine API is running"}
