from os import environ
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail



def send_email(to, subject, content):
    sg = SendGridAPIClient(environ.get('SENDGRID_API_KEY'))
    message = Mail(
        from_email = '123awesomeface123@gmail.com',
        to_emails = to,
        subject = subject,
        html_content = content)
    
    try:
        response = sg.send(message)
    except Exception as e:
        print(e)

