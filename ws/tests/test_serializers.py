from django.test import TestCase
from .factories import RandomNumberFactory

from ws.serializers import RandomNumberSerializer


class TestSerializers(TestCase):

    def setUp(self):
        self.rn = RandomNumberFactory()

    def test_serialize_draw(self):
        res = RandomNumberSerializer(self.rn).data

        self.assertEqual(sorted(res), sorted([
            'id', 'created_at', 'updated_at', 'title',
            'description', 'results',
            'range_min', 'range_max',
        ]))

        self.assertEqual(res["title"], self.rn.title)
        self.assertEqual(res["results"], [])

    def test_serialize_draw_with_results(self):
        num_results = 3
        for _ in range(num_results):
            self.rn.toss()
        res = RandomNumberSerializer(self.rn).data

        self.assertEqual(len(res["results"]), 3)
        for draw_result, serialized_result in zip(
                self.rn.results.order_by("-created_at"),
                res["results"],
        ):
            self.assertEqual(draw_result.value, serialized_result["value"])

    def test_deserialize_success(self):
        rn_data = RandomNumberFactory.dict()
        serializer = RandomNumberSerializer(data=rn_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        assert 'private_id' not in serializer.validated_data
        assert 'title' in serializer.validated_data
        assert 'range_min' in serializer.validated_data
