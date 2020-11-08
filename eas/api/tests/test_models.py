from django.test import TestCase

from eas.api.models import RandomNumber

from .factories import RandomNumberFactory


class TestModels(TestCase):
    def setUp(self):
        self.draw = RandomNumberFactory()

    @staticmethod
    def get_random_number(id_):
        return RandomNumber.objects.get(id=id_)

    def test_creation_success(self):
        draw = RandomNumberFactory(
            range_min=1,
            range_max=1,
        )
        draw.save()
        draw.toss()

        self.assertEqual([1], self.get_random_number(draw.id).results.first().value)

    def test_limit_of_results(self):
        res1 = self.draw.toss()
        for _ in range(RandomNumber.RESULTS_LIMIT - 1):
            self.draw.toss()

        self.assertIn(res1, self.draw.results.all())

        self.assertEqual(self.draw.results.count(), 50)
        self.draw.toss()
        self.assertEqual(self.draw.results.count(), 50)
        self.assertNotIn(res1, self.draw.results.all())

    def test_repr(self):
        repr(self.draw)
        repr(self.draw.toss())
