from django.http import JsonResponse
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler


def drf_validation_handler(exc, context):
    response = exception_handler(exc, context)
    if isinstance(exc, ValidationError):
        detail = exc.get_full_details()
        response_payload = {}
        if isinstance(detail, (list, tuple)):
            response_payload = {"general": detail}
        elif isinstance(detail, dict):
            response_payload = {"schema": detail}
        else:  # pragma: no cover
            return response
        return JsonResponse(response_payload, safe=False, status=response.status_code)
    return response  # pragma: no cover
