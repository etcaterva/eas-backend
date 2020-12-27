import datetime as dt
import tempfile

from django.test.testcases import LiveServerTestCase

from eas.api.management.commands import backup, purge
from eas.api.models import Raffle

from ..factories import RaffleFactory


class TestBackup(LiveServerTestCase):
    def create(self):
        draw = RaffleFactory()
        draw.save()
        return draw

    def purge(self):
        purge.delete_old_records(days_to_keep=-500)

    def raffle_count(self):
        return Raffle.objects.count()

    def test_backup_purge_restore(self):
        draw = self.create()
        assert not draw.results.all()
        draw.schedule_toss(dt.datetime.now() + dt.timedelta(days=1))
        assert draw.results.all()
        assert self.raffle_count() == 1

        with tempfile.NamedTemporaryFile() as dump_file:
            backup.serialize_public_draws(open(dump_file.name, "w"))

            self.purge()
            assert self.raffle_count() == 0

            backup.deserialize_draws(open(dump_file.name))
            assert self.raffle_count() == 1

    def test_past_draw_is_not_backedup(self):
        draw = self.create()
        assert not draw.results.all()
        draw.schedule_toss(dt.datetime.now() - dt.timedelta(days=11))
        assert draw.results.all()
        assert self.raffle_count() == 1

        with tempfile.NamedTemporaryFile() as dump_file:
            backup.serialize_public_draws(open(dump_file.name, "w"))

            self.purge()
            assert self.raffle_count() == 0

            backup.deserialize_draws(open(dump_file.name))
            assert self.raffle_count() == 0

    def test_backup_restor_draw_multiple_toss(self):
        draw = self.create()
        assert not draw.results.all()
        draw.schedule_toss(dt.datetime.now() + dt.timedelta(days=1))
        draw.schedule_toss(dt.datetime.now() + dt.timedelta(days=1))
        assert draw.results.all()
        assert self.raffle_count() == 1

        with tempfile.NamedTemporaryFile() as dump_file:
            backup.serialize_public_draws(open(dump_file.name, "w"))

            self.purge()
            assert self.raffle_count() == 0

            backup.deserialize_draws(open(dump_file.name))
            assert self.raffle_count() == 1
