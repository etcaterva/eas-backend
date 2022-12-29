import datetime as dt

import freezegun
from rest_framework.test import APILiveServerTestCase

from eas.api import models
from eas.api.management.commands import purge

from .. import factories

NOW = dt.datetime(1989, 4, 24, tzinfo=dt.timezone.utc)


class PurgeMixin:
    FACTORY = None

    def create(self):
        draw = self.FACTORY.create()
        draw.created_at = NOW
        draw.save()
        return draw

    def setUp(self) -> None:
        self.draw = self.create()
        self._ftime = freezegun.freeze_time(NOW)
        self.time = self._ftime.__enter__()
        return super().setUp()

    def tearDown(self) -> None:
        self._ftime.__exit__()
        return super().tearDown()

    def tick(self, days=31 * 3):
        self.time.tick(delta=dt.timedelta(days=days))

    def test_draw_without_results(self):
        deleted = purge.delete_old_records()
        assert deleted == 0

        self.tick(60)
        deleted = purge.delete_old_records()
        assert deleted == 0

        self.tick(31)
        deleted = purge.delete_old_records()
        assert deleted == 1

    def test_draw_with_results(self):
        self.draw.toss()
        self.draw.toss()
        self.draw.toss()
        deleted = purge.delete_old_records()
        assert deleted == 0

        self.tick()
        deleted = purge.delete_old_records()
        assert deleted == 1

    def test_draw_with_schedule(self):
        self.draw.schedule_toss(NOW + dt.timedelta(days=30))
        self.tick()
        deleted = purge.delete_old_records()
        assert deleted == 0

        self.tick(30)
        deleted = purge.delete_old_records()
        assert deleted == 1

    def test_multiple(self):
        self.draw1 = self.create()
        self.draw2 = self.create()

        self.tick()
        deleted = purge.delete_old_records()
        assert deleted == 3

    def test_multiple_new_result_not_deleted(self):
        self.draw1 = self.create()
        self.draw2 = self.create()

        self.tick()
        self.draw.toss()
        deleted = purge.delete_old_records()
        assert deleted == 2

    def test_far_future_schedule_result_not_deleted(self):
        self.draw.schedule_toss(NOW + dt.timedelta(days=300))

        self.tick()
        deleted = purge.delete_old_records()
        assert deleted == 0


class TestLetterPurge(PurgeMixin, APILiveServerTestCase):
    FACTORY = factories.LetterFactory


class TestCoinPurge(PurgeMixin, APILiveServerTestCase):
    FACTORY = factories.CoinFactory


class TestGroupsPurge(PurgeMixin, APILiveServerTestCase):
    FACTORY = factories.GroupsFactory


class TestLinkPurge(PurgeMixin, APILiveServerTestCase):
    FACTORY = factories.LinkFactory


class TestLotteryPurge(PurgeMixin, APILiveServerTestCase):
    FACTORY = factories.LotteryFactory


class TestRafflePurge(PurgeMixin, APILiveServerTestCase):
    FACTORY = factories.RaffleFactory


class TestRandomNumberPurge(PurgeMixin, APILiveServerTestCase):
    FACTORY = factories.RandomNumberFactory


class TestSpinnerPurge(PurgeMixin, APILiveServerTestCase):
    FACTORY = factories.SpinnerFactory


class TestSecretSantaPurge(APILiveServerTestCase):
    def test_purge_old_secret_santa(self):
        with freezegun.freeze_time(NOW) as time:
            result = models.SecretSantaResult(source="From name", target="To name")
            result.save()
            deleted = purge.delete_old_records()
            assert deleted == 0

            time.tick(delta=dt.timedelta(days=31 * 3))
            deleted = purge.delete_old_records()
            assert deleted == 1


class TestShiftsPurge(PurgeMixin, APILiveServerTestCase):
    FACTORY = factories.ShiftsFactory
