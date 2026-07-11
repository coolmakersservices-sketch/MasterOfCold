from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model for Booking Requests (Calibrated with new tracking keys)
class DispatchRequest(BaseModel):
    client_name: str
    contact_number: str
    client_address: str
    fridge_layout: str
    engine_tech: str
    anomaly_core: str
    performance_logs: str

# Model for Separate Customer Ratings
class ReviewRequest(BaseModel):
    reviewer_name: str
    rating_score: str
    review_text: str

DB_FILE = "dispatches.json"
REVIEWS_FILE = "customer_ratings.json"

# =====================================================================
# CREDENTIAL CONFIGURATION MATRIX (MAINTAIN YOUR TOKENS HERE)
# =====================================================================
SENDER_EMAIL = "coolmakers.services@gmail.com"
SENDER_PASSWORD = "puqa fqmo uoux zhtv" 
RECEIVER_EMAIL = "coolmakers.services@gmail.com" 

TWILIO_ACCOUNT_SID = "AC27d1db5787ef38151b9f0f52644e486e"
TWILIO_AUTH_TOKEN = "6992e693b5d49d801c7738951bd0e5de"
TWILIO_SMS_NUMBER = "+12299464508"
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"

FATHER_PHONE_NUMBER = "+919986632037"
# =====================================================================

def send_telecom_alert(alert_text, subject_line):
    # Email Pipeline
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject_line
        msg.attach(MIMEText(alert_text, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"-> Email Failure: {str(e)}")

    # Twilio Pipeline
    try:
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        # SMS
        twilio_client.messages.create(body=alert_text, from_=TWILIO_SMS_NUMBER, to=FATHER_PHONE_NUMBER)
        # WhatsApp
        twilio_client.messages.create(body=alert_text, from_=TWILIO_WHATSAPP_NUMBER, to=f"whatsapp:{FATHER_PHONE_NUMBER}")
    except Exception as e:
        print(f"-> Telecom Failure: {str(e)}")

@app.post("/api/dispatch")
async def receive_dispatch(data: DispatchRequest):
    try:
        current_logs = []
        if os.path.exists(DB_FILE) and os.path.getsize(DB_FILE) > 0:
            with open(DB_FILE, "r") as file:
                try: current_logs = json.load(file)
                except json.JSONDecodeError: pass
        
        current_logs.append(data.model_dump())
        with open(DB_FILE, "w") as file:
            json.dump(current_logs, file, indent=4)
            
        # Refactored alert log parameters incorporating all specific metadata tags cleanly
        alert = (
            f"🚨 NEW BOOKING DISPATCH\n"
            f"Client: {data.client_name}\n"
            f"Phone: {data.contact_number}\n"
            f"Address: {data.client_address}\n"
            f"Fridge Unit: {data.fridge_layout.upper()} DOOR\n"
            f"System Tech: {data.engine_tech.upper()}\n"
            f"Diagnosis: {data.anomaly_core.upper()}\n"
            f"Notes: {data.performance_logs}"
        )
        send_telecom_alert(alert, f"🚨 NEW DISPATCH: {data.client_name}")
        return {"status": "SUCCESS"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Fetch all saved reviews from the JSON database
@app.get("/api/reviews")
async def get_reviews():
    try:
        if os.path.exists(REVIEWS_FILE) and os.path.getsize(REVIEWS_FILE) > 0:
            with open(REVIEWS_FILE, "r") as file:
                return json.load(file)
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/review")
async def receive_review(data: ReviewRequest):
    try:
        current_reviews = []
        if os.path.exists(REVIEWS_FILE) and os.path.getsize(REVIEWS_FILE) > 0:
            with open(REVIEWS_FILE, "r") as file:
                try: current_reviews = json.load(file)
                except json.JSONDecodeError: pass
                
        current_reviews.append(data.model_dump())
        with open(REVIEWS_FILE, "w") as file:
            json.dump(current_reviews, file, indent=4)
            
        alert = f"⭐ NEW CUSTOMER RATING\nUser: {data.reviewer_name}\nRating: {data.rating_score}/10 Stars\nReview: {data.review_text}"
        send_telecom_alert(alert, f"⭐ NEW RATING LOADED: {data.rating_score}/10")
        return {"status": "SUCCESS"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)