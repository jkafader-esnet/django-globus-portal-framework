from unittest import mock
from urllib.parse import quote_plus

from django.test import TestCase, RequestFactory
from django.test.utils import override_settings

from globus_portal_framework.tests import get_mock_data

from globus_portal_framework import (
    get_index, IndexNotFound, get_pagination, get_filters,
    process_search_data, get_facets
)
from globus_portal_framework.gsearch import get_search_filters
from globus_portal_framework.constants import FILTER_MATCH_ALL

MOCK_RESULTS = 'globus_portal_framework/tests/data/search.json'


class MockSearchGetSubject:
    data = {'content': [{'myindex': 'search_data'}]}


class MockGlobusResponse:
    def __init__(self):
        self.data = {}


MOCK_FACETS = {
    "facet_results": [
        {
            "@datatype": "GFacetResult",
            "@version": "2017-09-01",
            "buckets": [
                {
                    "@datatype": "GBucket",
                    "@version": "2017-09-01",
                    "count": 99,
                    "value": "Problems"
                }
            ],
            "name": "Things I Got"
        }
    ],
}

MOCK_PORTAL_DEFINED_FACETS = [{
    'name': 'Things I Got',
    'type': 'terms',
    'field_name': 'things.i.got',
    'size': 10
}]


class SearchUtilsTest(TestCase):

    SEARCH_INDEXES = {'myindex': {
        # Randomly generated and not real
        'uuid': '1e0be00f-8156-499e-980d-f7fb26157c02'
    }}

    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(SEARCH_INDEXES={'foo': {}})
    def test_get_index(self):
        self.assertEqual(get_index('foo'), {})

    @override_settings(SEARCH_INDEXES={})
    def test_get_index_raises_error_on_nonexistent_index(self):
        with self.assertRaises(IndexNotFound):
            get_index('foo')

    def test_process_search_data_with_no_records(self):
        mappers, results = [], []
        data = process_search_data(mappers, results)
        self.assertEqual(data, [])

    @mock.patch('globus_portal_framework.gsearch.log')
    def test_process_search_data_zero_length_content(self, log):
        sub = get_mock_data(MOCK_RESULTS)['gmeta'][0]
        sub['content'] = []
        mappers, results = [], [sub]
        data = process_search_data(mappers, results)
        self.assertEqual(log.warning.call_count, 1)
        self.assertEqual(data, [])

    def test_process_search_data_with_one_entry(self):
        sub = get_mock_data(MOCK_RESULTS)['gmeta'][0]
        mappers, results = [], [sub]
        data = process_search_data(mappers, results)[0]
        self.assertEqual(quote_plus(sub['subject']), data['subject'])
        self.assertEqual(sub['content'], data['all'])

    def test_process_search_data_string_field(self):
        sub = get_mock_data(MOCK_RESULTS)['gmeta'][0]
        sub['content'][0]['foo'] = 'bar'
        mappers, results = ['foo'], [sub]
        data = process_search_data(mappers, results)[0]
        self.assertEqual(data['foo'], 'bar')

    def test_process_search_data_func_field(self):
        sub = get_mock_data(MOCK_RESULTS)['gmeta'][0]
        sub['content'][0]['foo'] = 'bar'
        mappers = [('foo', lambda x: x[0].get('foo').replace('b', 'c'))]
        results = [sub]
        data = process_search_data(mappers, results)[0]
        self.assertEqual(data['foo'], 'car')

    def test_process_search_data_string_field_missing(self):
        sub = get_mock_data(MOCK_RESULTS)['gmeta'][0]
        sub['content'][0]['foo'] = 'bar'
        mappers, results = ['foo'], [sub]
        data = process_search_data(mappers, results)[0]
        self.assertEqual(data['foo'], 'bar')

    @override_settings(RESULTS_PER_PAGE=10, MAX_PAGES=10)
    def test_pagination(self):
        self.assertEqual(get_pagination(1000, 0)['current_page'], 1)
        self.assertEqual(get_pagination(1000, 10)['current_page'], 2)
        self.assertEqual(get_pagination(1000, 20)['current_page'], 3)
        self.assertEqual(len(get_pagination(1000, 0)['pages']), 10)

    @mock.patch('globus_portal_framework.gsearch.log.warning')
    @override_settings(DEFAULT_FILTER_MATCH=FILTER_MATCH_ALL)
    def test_get_filters(self, warning):
        r = get_filters({'titles': ['foo']})
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['type'], 'match_all')

        r = get_filters({'titles': ['foo', 'bar']})
        self.assertEqual(len(r), 1)
        self.assertTrue(warning.called)

    @override_settings(DEFAULT_FILTER_MATCH=FILTER_MATCH_ALL,
                       SEARCH_INDEX={'foo': {'uuid': 'bar'}})
    def test_get_search_filters(self):
        # list of tests urls and expected outputdicts
        filter_tests = [
            ('/?q=*&filter.foo=bar', [{
                'field_name': 'foo',
                'type': 'match_all',
                'values': ['bar']}]
             ),
            ('/?q=*&filter-match-any.foo=bar', [{
                'field_name': 'foo',
                'type': 'match_any',
                'values': ['bar']}]
             ),
            ('/?q=*&filter-match-all.foo=bar', [{
                'field_name': 'foo',
                'type': 'match_all',
                'values': ['bar']}]
             ),
            ('/?q=*&filter-range.foo=1--2', [{
                'field_name': 'foo',
                'type': 'range',
                'values': [{'from': 1, 'to': 2}]}]
             ),
            ('/?q=*&page=1&filter-range.foo=100--*', [{
                'field_name': 'foo',
                'type': 'range',
                'values': [{'from': 100, 'to': '*'}]}]
             ),
        ]
        for query, expected_result in filter_tests:
            r = self.factory.get(query)
            filters = get_search_filters(r)
            self.assertEqual(filters, expected_result)

    def test_get_facets(self):
        search_response = MockGlobusResponse()
        search_response.data = MOCK_FACETS
        r = get_facets(search_response, MOCK_PORTAL_DEFINED_FACETS, {})
        self.assertEqual(len(r), 1)
        facet = r[0]
        self.assertEqual(set(facet.keys()), {'name', 'buckets'})
        bucket = facet['buckets'][0]
        self.assertEqual(set(bucket.keys()), {'count', 'value', 'field_name',
                                              'checked', 'filter_type',
                                              'search_filter_query_key'})
        # No filters defined in third argument, this should not be 'checked'
        self.assertFalse(bucket['checked'])

    @override_settings(DEFAULT_FILTER_MATCH=FILTER_MATCH_ALL)
    def test_checked_facet_shows_up(self):
        search_response = MockGlobusResponse()
        search_response.data = MOCK_FACETS
        request = self.factory.get('/?filter.things.i.got=Problems')
        filters = get_search_filters(request)
        r = get_facets(search_response, MOCK_PORTAL_DEFINED_FACETS, filters)
        self.assertTrue(r[0]['buckets'][0]['checked'])