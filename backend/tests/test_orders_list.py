from datetime import datetime, timezone
from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock, patch
from uuid import uuid4
import unittest

from app.orders import list_orders


class TestOrderListQuery(TestCase):
    def test_list_projects_page_and_items_in_one_query(self) -> None:
        customer_id = uuid4()
        first_order_id = uuid4()
        second_order_id = uuid4()
        restaurant_id = uuid4()
        first_product_id = uuid4()
        second_product_id = uuid4()
        created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        rows = [
            {
                "id": first_order_id,
                "customer_id": customer_id,
                "restaurant_id": restaurant_id,
                "status": "PLACED",
                "subtotal_satang": 1000,
                "delivery_fee": Decimal("15.00"),
                "total_satang": 2500,
                "created_at": created_at,
                "item_product_id": first_product_id,
                "product_name": "Rice",
                "item_quantity": 1,
                "unit_price_satang": 500,
                "line_total_satang": 500,
            },
            {
                "id": first_order_id,
                "customer_id": customer_id,
                "restaurant_id": restaurant_id,
                "status": "PLACED",
                "subtotal_satang": 1000,
                "delivery_fee": Decimal("15.00"),
                "total_satang": 2500,
                "created_at": created_at,
                "item_product_id": second_product_id,
                "product_name": "Tea",
                "item_quantity": 1,
                "unit_price_satang": 500,
                "line_total_satang": 500,
            },
            {
                "id": second_order_id,
                "customer_id": customer_id,
                "restaurant_id": restaurant_id,
                "status": "CANCELLED",
                "subtotal_satang": 0,
                "delivery_fee": Decimal("15.00"),
                "total_satang": 1500,
                "created_at": created_at,
                "item_product_id": None,
                "product_name": None,
                "item_quantity": None,
                "unit_price_satang": None,
                "line_total_satang": None,
            },
        ]
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.execute.return_value.fetchall.return_value = rows

        with patch("app.orders._connection", return_value=connection):
            result = list_orders(customer_id, limit=2, offset=0)

        self.assertEqual([item["id"] for item in result["items"]], [str(first_order_id), str(second_order_id)])
        self.assertEqual(
            [item["product_id"] for item in result["items"][0]["items"]],
            [str(first_product_id), str(second_product_id)],
        )
        self.assertEqual(result["items"][0]["delivery_fee_satang"], 1500)
        self.assertEqual(result["items"][1]["items"], [])
        self.assertEqual(connection.execute.call_count, 1)
        query, params = connection.execute.call_args.args
        self.assertIn("LEFT JOIN order_items", query)
        self.assertIn("WITH page AS", query)
        self.assertEqual(params, (customer_id, 2, 0))


if __name__ == "__main__":
    unittest.main()
