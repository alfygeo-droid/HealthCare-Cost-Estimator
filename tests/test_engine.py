import base64
import unittest
import server

class CostAndClaimsTests(unittest.TestCase):
    def test_estimate_uses_tariff_and_range(self):
        result = server.estimate({'procedure':'Cataract surgery', 'tier':1, 'room':'Private', 'stay':2})
        self.assertGreater(result['tariff'], 0)
        self.assertLess(result['low'], result['midpoint'])
        self.assertGreater(result['high'], result['midpoint'])

    def test_insurance_copay_and_nonpayable_are_explained(self):
        result = server.insurance({'total':100000,'sum_insured':500000,'deductible':5000,'copay':10,'non_payable':10000})
        self.assertEqual(result['eligible'], 90000)
        self.assertLess(result['contribution'], result['eligible'])
        self.assertGreater(result['patient_share'], 10000)

    def test_duplicate_bill_line_requires_review(self):
        items=[{'name':'Diagnostic test','quantity':1,'unit_price':3000,'total':3000},{'name':'Diagnostic test','quantity':1,'unit_price':3000,'total':3000}]
        result=server.analyze_bill({'items':items})
        self.assertEqual(result['risk'], 'MEDIUM')
        self.assertTrue(any('duplicate' in x['title'].lower() for x in result['flags']))

    def test_legitimate_two_policy_allocation_is_consistent(self):
        result=server.cross_check({'bill_total':200000,'claims':[{'policy':'A','invoice':'INV-A','amount':150000},{'policy':'B','invoice':'INV-B','amount':50000}]})
        self.assertEqual(result['status'], 'CONSISTENT')

    def test_same_invoice_requires_verification(self):
        result=server.cross_check({'bill_total':200000,'claims':[{'policy':'A','invoice':'INV-1','amount':150000},{'policy':'B','invoice':'INV-1','amount':50000}]})
        self.assertEqual(result['status'], 'REQUIRES VERIFICATION')

    def test_csv_bill_scan_extracts_reviewable_items(self):
        result=server.scan_bill({'filename':'bill.csv','content':'item,quantity,unit_price,total\nRoom charge,4,5500,22000\n'})
        self.assertEqual(len(result['items']), 1)
        self.assertEqual(result['items'][0]['total'], 22000)

    def test_exposure_returns_ordered_scenarios(self):
        result=server.exposure({'base_cost':5000,'followups':2,'medicines':5000,'therapy':5000})
        self.assertLess(result['p10'], result['p50'])
        self.assertLess(result['p50'], result['p90'])

    def test_uploaded_csv_bill_extracts_items(self):
        data=base64.b64encode(b'item,quantity,unit_price,total\nRoom charge,4,5500,22000\n').decode()
        result=server.scan_uploaded_bill({'filename':'hospital-bill.csv','data':data})
        self.assertEqual(result['items'][0]['name'], 'Room charge')

    def test_provisional_bill_parser_ignores_contact_and_registration_numbers(self):
        text='''Jeevan Hospital\nReg.No.DR86486\nContact No: 9403265989\nPROVISIONAL BILL\n100000\nRoom & Nursing Charges\n1650.00\n300000\nOT Charges\n1000.00\n500000\nProfessional Fees\n1000.00\nTotal Bill Amount: 3650.00\nDETAILED BREAKUP'''
        result=server.scan_bill({'filename':'bill.txt','content':text})
        self.assertEqual([x['total'] for x in result['items']], [1650.0,1000.0,1000.0])
        self.assertEqual(sum(x['total'] for x in result['items']),3650.0)

if __name__ == '__main__':
    unittest.main()
