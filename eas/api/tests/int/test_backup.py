import datetime as dt
import tempfile

from django.test.testcases import LiveServerTestCase
from freezegun import freeze_time

from eas.api.management.commands import backup, purge
from eas.api.models import Raffle
from eas.api.models import SecretSantaResult

from ..factories import RaffleFactory

NOW = dt.datetime.now(dt.timezone.utc)
ONE_DAY = dt.timedelta(days=1)


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
        draw.schedule_toss(NOW + dt.timedelta(days=1))
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
        draw.schedule_toss(NOW - dt.timedelta(days=11))
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
        draw.schedule_toss(NOW + dt.timedelta(days=1))
        draw.schedule_toss(NOW + dt.timedelta(days=1))
        assert draw.results.all()
        assert self.raffle_count() == 1

        with tempfile.NamedTemporaryFile() as dump_file:
            backup.serialize_public_draws(open(dump_file.name, "w"))

            self.purge()
            assert self.raffle_count() == 0

            backup.deserialize_draws(open(dump_file.name))
            assert self.raffle_count() == 1

    def test_backup_delta_created(self):
        draw = self.create()
        assert not draw.results.all()
        draw.schedule_toss(NOW)
        assert self.raffle_count() == 1

        with tempfile.NamedTemporaryFile() as dump_file:
            backup.serialize_updated_delta(
                open(dump_file.name, "w"), since=NOW - ONE_DAY
            )

            self.purge()
            assert self.raffle_count() == 0

            backup.deserialize_draws(open(dump_file.name))
            assert self.raffle_count() == 1

        with tempfile.NamedTemporaryFile() as dump_file:
            backup.serialize_updated_delta(
                open(dump_file.name, "w"), since=NOW + ONE_DAY
            )

            self.purge()
            assert self.raffle_count() == 0

            backup.deserialize_draws(open(dump_file.name))
            assert self.raffle_count() == 0

    def test_backup_delta_updated(self):
        draw = self.create()
        assert not draw.results.all()
        draw.schedule_toss(NOW)
        with freeze_time(NOW + ONE_DAY):
            draw.save()
        assert self.raffle_count() == 1

        with tempfile.NamedTemporaryFile() as dump_file:
            backup.serialize_updated_delta(open(dump_file.name, "w"), since=NOW)

            self.purge()
            assert self.raffle_count() == 0

            backup.deserialize_draws(open(dump_file.name))
            assert self.raffle_count() == 1

        with tempfile.NamedTemporaryFile() as dump_file:
            backup.serialize_updated_delta(
                open(dump_file.name, "w"), since=NOW + 2 * ONE_DAY
            )

            self.purge()
            assert self.raffle_count() == 0

            backup.deserialize_draws(open(dump_file.name))
            assert self.raffle_count() == 0

    def test_backup_delta_override(self):
        draw = self.create()
        draw.schedule_toss(NOW)
        with freeze_time(NOW + ONE_DAY):
            draw.save()

        with tempfile.NamedTemporaryFile() as dump_file1, tempfile.NamedTemporaryFile() as dump_file2:
            backup.serialize_updated_delta(open(dump_file1.name, "w"), since=NOW)
            draw.schedule_toss(NOW)
            draw.save()
            backup.serialize_updated_delta(open(dump_file2.name, "w"), since=NOW)
            self.purge()
            assert self.raffle_count() == 0

            backup.deserialize_draws(open(dump_file1.name))
            assert self.raffle_count() == 1
            draw.refresh_from_db()
            assert len(draw.results.all()) == 1

            backup.deserialize_draws(open(dump_file2.name))
            assert self.raffle_count() == 1
            draw.refresh_from_db()
            assert len(draw.results.all()) == 2

    def test_backup_secret_santa(self):
        SecretSantaResult(source="Mario", target="David").save()
        assert SecretSantaResult.objects.count() == 1

        with tempfile.NamedTemporaryFile() as dump_file:
            backup.serialize_public_draws(open(dump_file.name, "w"))
            self.purge()
            assert SecretSantaResult.objects.count() == 0

            backup.deserialize_draws(open(dump_file.name))
            assert SecretSantaResult.objects.count() == 1
