from django.conf import settings
from django.core.mail import EmailMessage

SECRET_SANTA_RESULT_EMAIL = {
    "es": (
        "Amigo Invisible | EchaloASuerte.com",
        """\
<h2>Amigo invisible @ echaloasuerte.com</h2>
<p>Hay un resultado de amigo invisible esperandote.</p>
<a href="https://echaloasuerte.com/secret-santa/{result_id}/"><h3>Click aqui para verlo.</h3></a>
<p>¡Buena Suerte!</p/>
""",
    ),
    "en": (
        "Secret Santa | ChooseRandom.com",
        """\
<h2>Secret Santa @ Chooserandom.com</h2>
<p>You have been assigned a person to gift.</p>
<a href="https://chooserandom.com/secret-santa/{result_id}/"><h3>Check Now</h3></a>
<p>Happy gifting!</p/>
""",
    ),
}


def send_secret_santa_mail(to, result_id, language):  # pragma: no cover
    subject, content = SECRET_SANTA_RESULT_EMAIL[language]
    content = content.format(result_id=result_id)
    email = EmailMessage(
        subject=subject,
        body=content,
        to=[to],
        from_email=settings.EMAIL_HOST_USER,
        reply_to=[settings.EMAIL_HOST_USER],
        headers={"Content-Type": "text/html"},
    )
    email.content_subtype = "html"
    email.send()
