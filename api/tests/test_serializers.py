from django.test import TestCase

from api.serializers import RandomNumberSerializer
from .factories import RandomNumberFactory


class TestSerializers(TestCase):

    def setUp(self):
        self.draw = RandomNumberFactory()

    def test_serialize_draw(self):
        res = RandomNumberSerializer(self.draw).data

        self.assertEqual(sorted(res), sorted([
            'id', 'created_at', 'updated_at', 'title',
            'description', 'results',
            'range_min', 'range_max',
        ]))

        self.assertEqual(res["title"], self.draw.title)
        self.assertEqual(res["results"], [])

    def test_serialize_draw_with_results(self):  # pylint: disable=invalid-name
        num_results = 3
        for _ in range(num_results):
            self.draw.toss()
        res = RandomNumberSerializer(self.draw).data

        self.assertEqual(len(res["results"]), 3)
        for draw_result, serialized_result in zip(
                self.draw.results.order_by("-created_at"),
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