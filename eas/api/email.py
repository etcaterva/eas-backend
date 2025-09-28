"""Email functionality using AWS SES"""
import logging

import boto3
from django.conf import settings

LOGGER = logging.getLogger(__name__)

SENDER = "Echalo A Suerte <no-reply@echaloasuerte.com>"


def send_magic_link(email, magic_link):
    """Send a magic link email to the user"""

    # Create SES client using existing AWS credentials
    ses_client = boto3.client(
        "ses",
        region_name="us-east-2",
        aws_access_key_id=settings.AWS_KEY_ID,
        aws_secret_access_key=settings.AWS_KEY_SECRET,
    )

    # Email subject and body
    subject = "Tu enlace mágico - Échalo A Suerte"

    # HTML email template
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Enlace Mágico - Échalo A Suerte</title>
    </head>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px;">
            <h1 style="color: #007bff; text-align: center; margin-bottom: 30px;">
                Échalo A Suerte
            </h1>

            <h2 style="color: #333; margin-bottom: 20px;">
                ¡Tu enlace mágico está listo!
            </h2>

            <p style="color: #666; font-size: 16px; line-height: 1.5; margin-bottom: 30px;">
                Haz clic en el botón de abajo para acceder a tu cuenta. Este enlace expirará por motivos de seguridad.
            </p>

            <div style="text-align: center; margin: 40px 0;">
                <a href="{magic_link}"
                   style="background-color: #007bff; color: white; padding: 15px 30px;
                          text-decoration: none; border-radius: 5px; font-weight: bold;
                          display: inline-block; font-size: 16px;">
                    Acceder a tu cuenta
                </a>
            </div>

            <p style="color: #666; font-size: 14px; line-height: 1.5; margin-top: 30px;">
                Si el botón no funciona, puedes copiar y pegar este enlace en tu navegador:
            </p>
            <p style="color: #007bff; font-size: 14px; word-break: break-all;
                      background-color: #f1f3f4; padding: 10px; border-radius: 5px;">
                {magic_link}
            </p>

            <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">

            <p style="color: #999; font-size: 12px; text-align: center;">
                Este email fue enviado desde Échalo A Suerte. Si no solicitaste este enlace mágico,
                puedes ignorar este email sin problema.
            </p>
        </div>
    </body>
    </html>
    """

    # Plain text fallback
    text_body = f"""
    Tu enlace mágico - Échalo A Suerte

    Haz clic en el enlace de abajo para acceder a tu cuenta:
    {magic_link}

    Este enlace expirará por motivos de seguridad.

    Si no solicitaste este enlace mágico, puedes ignorar este email sin problema.

    ---
    Échalo A Suerte
    """

    try:
        # Send email via SES
        response = ses_client.send_email(
            Source=SENDER,
            Destination={"ToAddresses": [email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                    "Text": {"Data": text_body, "Charset": "UTF-8"},
                },
            },
        )

        LOGGER.info(
            "Magic link email sent successfully to %s, MessageId: %s",
            email,
            response["MessageId"],
        )
        return True

    except Exception as e:  # pylint: disable=broad-except
        LOGGER.error("Failed to send magic link email to %s: %s", email, str(e))
        return False
