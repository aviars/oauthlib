# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from ....unittest import TestCase

import json
import mock
from oauthlib.common import Request
from oauthlib.oauth2.rfc6749.grant_types import ResourceOwnerPasswordCredentialsGrant
from oauthlib.oauth2.rfc6749.tokens import BearerToken
from oauthlib.oauth2.rfc6749 import errors


class ResourceOwnerPasswordCredentialsGrantTest(TestCase):

    def setUp(self):
        mock_client = mock.MagicMock()
        mock_client.user.return_value = 'mocked user'
        self.request = Request('http://a.b/path')
        self.request.grant_type = 'password'
        self.request.username = 'john'
        self.request.password = 'doe'
        self.request.client = mock_client
        self.request.scopes = ('mocked', 'scopes')
        self.mock_validator = mock.MagicMock()
        self.auth = ResourceOwnerPasswordCredentialsGrant(
                request_validator=self.mock_validator)

    def set_client(self, request, *args, **kwargs):
        request.client = mock.MagicMock()
        request.client.client_id = 'mocked'
        return True

    def test_create_token_response(self):
        bearer = BearerToken(self.mock_validator)
        headers, body, status_code = self.auth.create_token_response(
                self.request, bearer)
        token = json.loads(body)
        self.assertEqual(self.mock_validator.save_token.call_count, 1)
        self.assertIn('access_token', token)
        self.assertIn('token_type', token)
        self.assertIn('expires_in', token)
        self.assertIn('refresh_token', token)
        # ensure client_authentication_required() is properly called
        self.mock_validator.client_authentication_required.assert_called_once_with(self.request)
        # fail client authentication
        self.mock_validator.reset_mock()
        self.mock_validator.validate_user.return_value = True
        self.mock_validator.authenticate_client.return_value = False
        status_code = self.auth.create_token_response(self.request, bearer)[2]
        self.assertEqual(status_code, 401)
        self.assertEqual(self.mock_validator.save_token.call_count, 0)

        # mock client_authentication_required() returning False then fail
        self.mock_validator.reset_mock()
        self.mock_validator.client_authentication_required.return_value = False
        self.mock_validator.authenticate_client_id.return_value = False
        status_code = self.auth.create_token_response(self.request, bearer)[2]
        self.assertEqual(status_code, 401)
        self.assertEqual(self.mock_validator.save_token.call_count, 0)

    def test_create_token_response_without_refresh_token(self):
        # self.auth.refresh_token = False so we don't generate a refresh token
        self.auth = ResourceOwnerPasswordCredentialsGrant(
                request_validator=self.mock_validator, refresh_token=False)
        bearer = BearerToken(self.mock_validator)
        headers, body, status_code = self.auth.create_token_response(
                self.request, bearer)
        token = json.loads(body)
        self.assertEqual(self.mock_validator.save_token.call_count, 1)
        self.assertIn('access_token', token)
        self.assertIn('token_type', token)
        self.assertIn('expires_in', token)
        # ensure no refresh token is generated
        self.assertNotIn('refresh_token', token)
        # ensure client_authentication_required() is properly called
        self.mock_validator.client_authentication_required.assert_called_once_with(self.request)
        # fail client authentication
        self.mock_validator.reset_mock()
        self.mock_validator.validate_user.return_value = True
        self.mock_validator.authenticate_client.return_value = False
        status_code = self.auth.create_token_response(self.request, bearer)[2]
        self.assertEqual(status_code, 401)
        self.assertEqual(self.mock_validator.save_token.call_count, 0)
        # mock client_authentication_required() returning False then fail
        self.mock_validator.reset_mock()
        self.mock_validator.client_authentication_required.return_value = False
        self.mock_validator.authenticate_client_id.return_value = False
        status_code = self.auth.create_token_response(self.request, bearer)[2]
        self.assertEqual(status_code, 401)
        self.assertEqual(self.mock_validator.save_token.call_count, 0)

    def test_custom_token_validators(self):
        self.authval1, self.authval2 = mock.Mock(), mock.Mock()
        self.tknval1, self.tknval2 = mock.Mock(), mock.Mock()
        self.auth.register_token_validator(self.tknval1, after_standard=False)
        self.auth.register_token_validator(self.tknval2, after_standard=True)
        self.auth.register_authorization_validator(self.authval1, after_standard=False)
        self.auth.register_authorization_validator(self.authval2, after_standard=True)

        bearer = BearerToken(self.mock_validator)
        self.auth.create_token_response(self.request, bearer)
        self.assertTrue(self.tknval1.called)
        self.assertTrue(self.tknval2.called)
        self.assertFalse(self.authval1.called)
        self.assertFalse(self.authval2.called)

    def test_error_response(self):
        pass

    def test_scopes(self):
        pass

    def test_invalid_request_missing_params(self):
        del self.request.grant_type
        self.assertRaises(errors.InvalidRequestError, self.auth.validate_token_request,
                          self.request)

    def test_invalid_request_duplicates(self):
        request = mock.MagicMock(wraps=self.request)
        request.duplicate_params = ['scope']
        self.assertRaises(errors.InvalidRequestError, self.auth.validate_token_request,
                          request)

    def test_invalid_grant_type(self):
        self.request.grant_type = 'foo'
        self.assertRaises(errors.UnsupportedGrantTypeError,
                          self.auth.validate_token_request, self.request)

    def test_invalid_user(self):
        self.mock_validator.validate_user.return_value = False
        self.assertRaises(errors.InvalidGrantError, self.auth.validate_token_request,
                          self.request)

    def test_client_id_missing(self):
        del self.request.client.client_id
        self.assertRaises(NotImplementedError, self.auth.validate_token_request,
                          self.request)

    def test_valid_token_request(self):
        self.mock_validator.validate_grant_type.return_value = True
        self.auth.validate_token_request(self.request)
