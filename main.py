from fastapi import FastAPI, HTTPException, BackgroundTasks
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

# Model for Booking Requests
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
# CREDENTIAL CONFIGURATION MATRIX (DYNAMIC ENVIRONMENT VARIABLES)
# =====================================================================
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "coolmakers.services@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD") 
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", "coolmakers.services@gmail.com") 

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

FATHER_PHONE_NUMBER = os.environ.get("FATHER_PHONE_NUMBER", "+919986632037")
# =====================================================================

def send_telecom_alert(whatsapp_text, subject_line, raw_email_text):
    # 1. Email Pipeline (Isolated so SMTP block on Render won't stop WhatsApp)
    if SENDER_PASSWORD:
        try:
            msg = MIMEMultipart()
            msg['From'] = SENDER_EMAIL
            msg['To'] = RECEIVER_EMAIL
            msg['Subject'] = subject_line
            msg.attach(MIMEText(raw_email_text, 'plain'))
            
            print("-> Attempting SMTP connection over SSL (Port 465)...")
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=5) as server:
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
            print("-> Email Delivered Successfully via SSL")
        except Exception as e:
            print(f"-> Email Failure (Safely Skipped): {str(e)}")
    else:
        print("-> SENDER_PASSWORD missing, skipping SMTP email delivery.")

    # 2. Twilio Pure WhatsApp Pipeline
    try:
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            print("-> Critical Error: Twilio Credentials Missing in Environment Variables!")
            return

        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Ensure recipient phone has country code formatting
        recipient = FATHER_PHONE_NUMBER if FATHER_PHONE_NUMBER.startswith("+") else f"+{FATHER_PHONE_NUMBER}"

        message = twilio_client.messages.create(
            body=whatsapp_text, 
            from_=TWILIO_WHATSAPP_NUMBER, 
            to=f"whatsapp:{recipient}"
        )
        print(f"-> WhatsApp Sandbox Delivery Triggered Successfully! SID: {message.sid}")
    except Exception as e:
        print(f"-> Twilio WhatsApp Critical Failure: {str(e)}")


@app.post("/api/dispatch")
async def receive_dispatch(data: DispatchRequest, background_tasks: BackgroundTasks):
    try:
        current_logs = []
        if os.path.exists(DB_FILE) and os.path.getsize(DB_FILE) > 0:
            with open(DB_FILE, "r") as file:
                try: current_logs = json.load(file)
                except json.JSONDecodeError: pass
        
        current_logs.append(data.model_dump())
        with open(DB_FILE, "w") as file:
            json.dump(current_logs, file, indent=4)
            
        clean_formatted_body = (
            f"🚨 NEW BOOKING DISPATCH\n"
            f"Client: {data.client_name}\n"
            f"Phone: {data.contact_number}\n"
            f"Address: {data.client_address}\n"
            f"Refrigerator Type: {data.fridge_layout.upper()} DOOR\n"
            f"System Type: {data.engine_tech.upper()}\n"
            f"Issue: {data.anomaly_core.upper()}\n"
            f"Notes: {data.performance_logs}"
        )
        
        # Offload delivery to background worker to prevent client timeout
        background_tasks.add_task(
            send_telecom_alert, 
            clean_formatted_body, 
            f"🚨 NEW DISPATCH: {data.client_name}", 
            clean_formatted_body
        )
        
        return {"status": "SUCCESS"}
    except Exception as e:
        print(f"-> Critical Error in route: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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
async def receive_review(data: ReviewRequest, background_tasks: BackgroundTasks):
    try:
        current_reviews = []
        if os.path.exists(REVIEWS_FILE) and os.path.getsize(REVIEWS_FILE) > 0:
            with open(REVIEWS_FILE, "r") as file:
                try: current_reviews = json.load(file)
                except json.JSONDecodeError: pass
                
        current_reviews.append(data.model_dump())
        with open(REVIEWS_FILE, "w") as file:
            json.dump(current_reviews, file, indent=4)
            
        clean_review_body = (
            f"⭐ NEW CUSTOMER RATING\n"
            f"User: {data.reviewer_name}\n"
            f"Rating: {data.rating_score}/10 Stars\n"
            f"Review: {data.review_text}"
        )
        
        background_tasks.add_task(
            send_telecom_alert, 
            clean_review_body, 
            f"⭐ NEW RATING LOADED: {data.rating_score}/10", 
            clean_review_body
        )
        
        return {"status": "SUCCESS"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
