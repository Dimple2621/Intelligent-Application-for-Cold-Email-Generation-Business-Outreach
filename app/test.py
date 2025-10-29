import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

st.title("SMTP Test")
try:
    from_email = "dimpleg2820@gmail.com"
    to_email = "dimplecs8530@gmail.com"
    subject = "Test Email"
    body = "This is a test from Streamlit."
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(from_email, st.secrets["GMAIL_PASSWORD"])
    text = msg.as_string()
    server.sendmail(from_email, to_email, text)
    server.quit()
    st.success("Test email sent! Check dimplecs8530@gmail.com.")
except Exception as e:
    st.error(f"SMTP Error: {e}")