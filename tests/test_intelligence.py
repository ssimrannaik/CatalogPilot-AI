import unittest
from catalogpilot.intelligence import DEFAULT_RULES, rule_issues, copilot_answer, margin_analysis, catalog_insights, channel_readiness

class IntelligenceTests(unittest.TestCase):
    def test_required_fields_rule(self):
        p={'name':'Sample', 'description':'short', 'sku':'', 'images':[], 'categories':[], 'regular_price':'10'}
        issues=rule_issues(p, DEFAULT_RULES)
        self.assertTrue(any(x['field']=='sku' for x in issues))
        self.assertTrue(any(x['field']=='images' for x in issues))

    def test_copilot_audit_intent(self):
        products=[{'id':1,'name':'Sample'}]
        audits=[{'product_id':1,'issue_count':1,'score':40,'issues':[{'message':'Missing'}]}]
        out=copilot_answer('find incomplete products',products,audits)
        self.assertEqual(out['intent'],'catalog_audit')
        self.assertEqual(len(out['items']),1)

    def test_margin_math(self):
        out=margin_analysis([{'id':1,'name':'Sample','regular_price':'100','cost_price':'60'}])
        self.assertEqual(out['rows'][0]['gross_profit_per_unit'],40)
        self.assertEqual(out['rows'][0]['gross_margin_percent'],40)

    def test_inventory_alerts_split_low_and_out_of_stock(self):
        products=[
            {'id':1,'name':'Low','manage_stock':True,'stock_quantity':3,'categories':[{'name':'Home'}]},
            {'id':2,'name':'Out','manage_stock':True,'stock_quantity':0,'categories':[{'name':'Home'}]},
        ]
        audits=[
            {'product_id':1,'score':80},
            {'product_id':2,'score':40},
        ]
        out=catalog_insights(products,audits)
        self.assertEqual([item['id'] for item in out['alerts']['low_stock']],[1])
        self.assertEqual([item['id'] for item in out['alerts']['out_of_stock']],[2])
        self.assertEqual(out['average_health'],60)

    def test_channel_readiness_checks_profile_fields_and_scores(self):
        product={
            'id':1,
            'name':'Sample',
            'description':'A detailed and factual product description for everyday use. Review the verified product specifications to confirm its materials, dimensions, and included items before publishing.',
            'sku':'SAMPLE-1',
            'regular_price':'25.00',
            'categories':[{'name':'Home'}],
            'images':[{'src':'https://example.test/product.jpg'}],
            'attributes':[{'name':'Color','options':['Blue']}],
        }
        amazon=channel_readiness([product], 'amazon')
        shopify=channel_readiness([product], 'shopify')
        self.assertEqual(amazon['ready_count'],1)
        self.assertEqual(amazon['results'][0]['score'],100)
        self.assertEqual(shopify['results'][0]['score'],100)
        self.assertEqual(len(amazon['requirements']),7)
        self.assertEqual(len(shopify['requirements']),5)

    def test_channel_readiness_reports_gaps_and_rejects_unknown_channel(self):
        result=channel_readiness([{'id':2,'name':'Incomplete'}], 'amazon')
        self.assertEqual(result['ready_count'],0)
        self.assertEqual(result['needs_work_count'],1)
        self.assertEqual(result['results'][0]['score'],14)
        self.assertIn('sku',{issue['field'] for issue in result['results'][0]['issues']})
        with self.assertRaises(ValueError):
            channel_readiness([], 'unsupported')

if __name__=='__main__': unittest.main()
