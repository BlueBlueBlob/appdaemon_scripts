# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START tasks_quickstart]
from __future__ import print_function
import appdaemon.plugins.hass.hassapi as hass
import pickle
import os.path
import datetime
import pytz
import requests
import json
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

class GoogleOauth(hass.Hass):
    # If modifying these scopes, delete the file token.pickle.
    SCOPES = []
    new_auth = True
    creds = None
    flow = None
    return_code = None
    debug = False
    inputtxt_id = ''
    service = None
    service_name = ""
    service_version = ""

    def initialize(self):
        
        if 'DEBUG' in self.args:
            self.debug = self.args["DEBUG"]
        self.inputtxt_id = self.args['input_txt_id']
        self.credentials_json = self.args['credentials_json']
        self.token_pickle = self.args['token_pickle']
        self.SCOPES = self.args['scopes']
        self.service_name = self.args['service_name']
        self.service_version = self.args['service_version']
        self.connect()
        if self.new_auth:
            self.handle = self.listen_state(self.return_code_cb, self.inputtxt_id)

    def terminate(self):
        creds = None
        flow = None
        service = None
        
    def connect(self):
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization self.flow completes for the first
        # time.
        if os.path.exists(self.token_pickle):
            self.new_auth = False
            with open(self.token_pickle, 'rb') as token:
                self.creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if self.debug:
                    self.log("Connection")
                if self.new_auth:
                    if self.debug:
                        self.log("New auth")
                    self.flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_json, self.SCOPES,redirect_uri='urn:ietf:wg:oauth:2.0:oob')
                    if self.debug:
                        self.log(self.flow)
                    auth_url, _ = self.flow.authorization_url(prompt='consent')
                    if self.debug:
                        self.log(auth_url)
                    self.call_service("persistent_notification/create", message = "Please do authentication from this url : " + auth_url , title = "User authentication needed !", notification_id = "gtasks_auth_notify" )
                    return
                else:
                    self.flow.fetch_token(code=self.return_code)
                    self.creds = self.flow.credentials
                    if self.debug:
                        self.log(self.creds)
                    # Save the credentials for the next run
                    with open(self.token_pickle, 'wb') as token:
                        pickle.dump(self.creds, token)

    def return_code_cb(self, entity, attribute, old, new, kwargs):
        self.return_code = new
        self.new_auth = False
        if self.debug:
            self.log("___function___")
            self.log(self.return_code)
        self.cancel_listen_state(self.handle)
        self.set_textvalue(entity, ' ')
        self.connect()
        
        
    def build_service(self):
        if self.debug:
            self.log("___function___")
        self.service = build(self.service_name, self.service_version, credentials=self.creds)
    