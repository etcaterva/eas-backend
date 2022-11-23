# Code from https://adw0rd.github.io/instagrapi/usage-guide/challenge_resolver.html

import contextlib
import datetime as dt
import email
import imaplib
import logging
import random
import re
import shutil

from django.conf import settings
from instagrapi.mixins.challenge import ChallengeChoice


def challenge_code_handler(username, choice):  # pragma: no cover
    if choice == ChallengeChoice.EMAIL:
        return get_code_from_email(username)
    logging.error("Challenge resolver only works by email")
    return False


def change_password_handler(username):  # pragma: no cover
    # Simple way to generate a random string
    chars = list("abcdefghijklmnopqrstuvwxyz1234567890!&£@#")
    password = "".join(random.sample(chars, 10))
    logging.info("Setting new password for %s", username)

    password_file = settings.INSTAGRAM_PASSWORD_FILE
    extension = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    with contextlib.suppress(Exception):
        shutil.move(password_file, f"{password_file}.{extension}")

    with open(password_file, "w") as f:
        f.write(password)
    logging.info("Saved new password in %s", password_file)
    return password


def get_code_from_email(username):  # pragma: no cover
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(settings.INSTAGRAM_EMAIL_USERNAME, settings.INSTAGRAM_EMAIL_PASSWORD)
    logging.info(
        "Resolving instagram challenge with %s", settings.INSTAGRAM_EMAIL_USERNAME
    )
    mail.select("inbox")
    result, data = mail.search(None, "(UNSEEN)")
    assert result == "OK", "Error1 during get_code_from_email: %s" % result
    ids = data.pop().split()
    for num in reversed(ids):
        mail.store(num, "+FLAGS", "\\Seen")  # mark as read
        result, data = mail.fetch(num, "(RFC822)")
        assert result == "OK", "Error2 during get_code_from_email: %s" % result
        msg = email.message_from_string(data[0][1].decode())
        payloads = msg.get_payload()
        if not isinstance(payloads, list):
            payloads = [msg]
        code = None
        for payload in payloads:
            body = payload.get_payload(decode=True).decode()
            if "<div" not in body:
                continue
            match = re.search(">([^>]*?({u})[^<]*?)<".format(u=username), body)
            if not match:
                continue
            logging.info("Match from email: %s", match.group(1))
            match = re.search(r">(\d{6})<", body)
            if not match:
                logging.info('Skip this email, "code" not found')
                continue
            code = match.group(1)
            if code:
                return code
    logging.error("Could not find an email to match the code")
    return False
