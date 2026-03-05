"""
InvoiceService 단위 테스트 (F4-10)
"""
import unittest
from services.payment.invoice_service import InvoiceService


class TestInvoiceService(unittest.TestCase):

    def setUp(self):
        self.svc = InvoiceService()

    def test_create_invoice(self):
        items = [{'description': 'Pro 플랜', 'amount': 29000, 'quantity': 1}]
        result = self.svc.create_invoice('user-1', items)
        self.assertIn('id', result)
        self.assertEqual(result['total'], 29000)
        self.assertEqual(result['status'], 'draft')

    def test_create_empty_items_rejected(self):
        result = self.svc.create_invoice('user-1', [])
        self.assertIn('error', result)

    def test_list_invoices(self):
        self.svc.create_invoice('user-1', [{'description': 'A', 'amount': 1000, 'quantity': 1}])
        self.svc.create_invoice('user-2', [{'description': 'B', 'amount': 2000, 'quantity': 1}])
        self.assertEqual(len(self.svc.list_invoices('user-1')), 1)

    def test_mark_paid(self):
        inv = self.svc.create_invoice('user-1', [{'description': 'A', 'amount': 1000, 'quantity': 1}])
        result = self.svc.mark_paid(inv['id'])
        self.assertEqual(result['status'], 'paid')
        self.assertIsNotNone(result['paid_at'])

    def test_mark_paid_not_found(self):
        result = self.svc.mark_paid('INV-NOTFOUND')
        self.assertIn('error', result)

    def test_multi_item_total(self):
        items = [
            {'description': 'A', 'amount': 100, 'quantity': 2},
            {'description': 'B', 'amount': 300, 'quantity': 1},
        ]
        result = self.svc.create_invoice('user-1', items)
        self.assertEqual(result['total'], 500)


if __name__ == '__main__':
    unittest.main()
