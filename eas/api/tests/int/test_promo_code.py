from django.urls import reverse
from rest_framework import status
from rest_framework.test import APILiveServerTestCase

from eas.api import models
from eas.api.management.commands.promocode import create_code, get_all_codes


class TestBackup(APILiveServerTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.url = reverse("redeem-promo-code")
        self.draw = models.Letter()
        self.draw.save()
        code = models.PromoCode()
        code.save()
        self.code = code.code

    def test_promo_code_management(self):
        assert get_all_codes() == [self.code]
        code = create_code()
        assert get_all_codes() == [self.code, code]

    def test_repr(self):
        code = models.PromoCode()
        code.code = "AAAAAAAA"
        code.id = "1"
        assert str(code) == "<PromoCode('1') 'AAAAAAAA')>"

    def test_redeem_valid_promo_code_success(self):
        response = self.client.post(
            self.url,
            {
                "draw_id": self.draw.id,
                "code": self.code,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_unknown_code_fails(self):
        response = self.client.post(
            self.url, {"draw_id": self.draw.id, "code": "AAAAAAAA"}
        )
        self.assertEqual(
            response.status_code, status.HTTP_404_NOT_FOUND, response.content
        )

    def test_unknown_draw_fails(self):
        response = self.client.post(
            self.url, {"draw_id": "AAAAAAAA", "code": self.code}
        )
        self.assertEqual(
            response.status_code, status.HTTP_404_NOT_FOUND, response.content
        )
