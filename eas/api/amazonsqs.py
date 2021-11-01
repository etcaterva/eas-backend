import json
import logging

import boto3
from django.conf import settings

LOGGER = logging.getLogger(__name__)


def send_secret_santa_message(message):
    sqs_client = boto3.client(
        "sqs",
        region_name="us-east-2",
        aws_access_key_id=settings.AWS_KEY_ID,
        aws_secret_access_key=settings.AWS_KEY_SECRET,
    )

    response = sqs_client.send_message(
        QueueUrl=settings.SECRET_SANTA_QUEUE_URL,
        MessageBody=json.dumps(message),
    )
    LOGGER.info("Sent SQS message, response: %s", response)
