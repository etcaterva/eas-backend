import copy

from django.conf import settings
from django.core.mail import EmailMessage
from django.template import loader

CONTENT_VALUES = {
    "es": (
        "Amigo Invisible | EchaloASuerte.com",
        {
            "HOMEPAGE_URL": "https://echaloasuerte.com/?utm_source=logo&amp;utm_medium=email",
            "BRAND_NAME": "ÉchaloASuerte",
            "TITLE": "Sorteo del Amigo Invisible",
            "SUMMARY": "Has participado en un sorteo amigo invisible. Haz click en el botón a continuación para saber a quién tienes que hacerle tu regalo.",
            "CTA_LABEL": "Averigua quién te ha tocado",
            "CTA_URL": "https://echaloasuerte.com/secret-santa/",
            "DETAILS": "Mensaje enviado automáticamente a través de la web www.echaloasuerte.com. Has recibido este e-mail porque alguien ha sorteado un Amigo Invisible y ha incluido tu email como participante. Tu email no ha sido incluído en ninguna base de datos y no cedemos tus datos a otras empresas.",
        },
    ),
    "en": (
        "Secret Santa | ChooseRandom.com",
        {
            "HOMEPAGE_URL": "https://chooserandom.com/?utm_source=logo&amp;utm_medium=email",
            "BRAND_NAME": "ChooseRandom",
            "TITLE": "Secret Santa",
            "SUMMARY": "You are part of a secret santa. Click on the button below to know who is the person that you should gift something to.",
            "CTA_LABEL": "Reveal who is the lucky person",
            "CTA_URL": "https://chooserandom.com/secret-santa/",
            "DETAILS": "This message has been sent automatically via www.chooserandom.com. You have received this email as someone has included you in a Secret Santa as a participant. Your email has not been saved in any database nor your data has been shared with third-party companies.",
        },
    ),
}


def send_secret_santa_mail(to, result_id, language):  # pragma: no cover
    subject, content_values = copy.deepcopy(CONTENT_VALUES[language])
    content_values["CTA_URL"] += result_id
    template = loader.get_template("secret-santa-result-mail.html")
    content = template.render(content_values)
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
