from twilio.rest import Client
from app.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE

'''
def send_sms(phone, message):

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    client.messages.create(
        body=message,
        from_=TWILIO_PHONE,
        to=phone
    )
'''

def generate_winback_message(client):
    return f"Hey {client.name}, haven’t seen you in a while! Want to book your next cut?"
