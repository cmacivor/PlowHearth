import smtplib, ssl
from email.message import EmailMessage

def sendErrorMessage(content):
    port = 587
    sender_email = "support@pendantautomation.com"
    receiver_email = "support@pendantautomation.com"
#     message = """\
#             Subject: Hi, testing!
#             This message is sent from Python."""

    #message = "test test test"

    #ssl context
    context = ssl.create_default_context()

    with smtplib.SMTP("smtp.office365.com", port) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login("support@pendantautomation.com", "Pendant0505")
        #server.sendmail(sender_email, receiver_email, message)

        msg = EmailMessage()
        msg.set_content(content)
        
        msg['Subject'] = 'Error in PlowHearth middleware'
        msg['From'] = sender_email
        msg['To'] = receiver_email

        server.send_message(msg)




