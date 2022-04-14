from flask import current_app, render_template
from flask_mail import Message
from . import mail
from threading import Thread

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)
        current_app.logger.debug(f"sent email, from {current_app.config['RAGTIME_MAIL_SENDER']} to {msg.recipients[0]}")


def send_email(to, subject, template, **kwargs):
    msg = Message(subject=current_app.config['RAGTIME_MAIL_SUBJECT_PREFIX'] + subject,
                  recipients=[to],
                  sender=current_app.config['RAGTIME_MAIL_SENDER'])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thread = Thread(target=send_async_email, args=[current_app._get_current_object(), msg])
    thread.start()