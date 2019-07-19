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

class SyncGTasksAndGrocy(hass.Hass):
    # If modifying these scopes, delete the file token.pickle.
    SCOPES = ['https://www.googleapis.com/auth/tasks.readonly' , 'https://www.googleapis.com/auth/tasks']
    new_auth = True
    creds = None
    flow = None
    return_code = None
    tl_name = 'Corvées'
    tl_id = None
    tl_main = None
    debug = False
    inputtxt_id = ''
    gr_cl = None
    service = None
    tl_lastup = None

    def initialize(self):
        
        if 'DEBUG' in self.args:
            self.debug = self.args["DEBUG"]
        self.tl_name = self.args['chores_list']
        self.inputtxt_id = self.args['input_txt_id']
        self.grocy_key = self.args['grocy_key']
        self.host = self.args['host']
        self.ssl = self.args['ssl_verify']
        self.grocy_port = self.args['grocy_port']
        self.credentials_json = self.args['credentials_json']
        self.token_pickle = self.args['token_pickle']
        self.connect()
        if self.new_auth:
            self.handle = self.listen_state(self.return_code_cb, self.inputtxt_id)
        else:
            self.init_tasklist()
            self.handle = self.run_every(self.sync_cb , datetime.datetime.now() , 300)
        
    def terminate(self):
        creds = None
        flow = None
        tl_id = None
        tl_main = None
        gr_cl = None
        service = None
        tl_lastup = None
        
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
                    self.creds = self.flow.credentials()
                    if self.debug:
                        self.log(self.creds)
                    # Save the credentials for the next run
                    with open(self.token_pickle, 'wb') as token:
                        pickle.dump(self.creds, token)
                        
                        
    def init_tasklist(self):
        self.build_service()
        # Call the Tasks API
        all_tl = self.service.tasklists().list().execute()    
        if not all_tl['items']:
            self.log('No task lists found.' , level = 'ERROR')
            return
        else:
            if self.debug:
                self.log('Task lists:')
            for task_list in all_tl['items']:
                if self.debug:
                    self.log(u'{0} ({1})'.format(task_list['title'], task_list['id']))
                if task_list['title'] == self.tl_name:
                    self.tl_id = task_list['id']
                    if self.debug:
                        self.log("Task list found : " + task_list['title'])
                        self.log(self.tl_id)
                    break
            else:
                self.log("No list found")
                    
    def complete_chore(self, chore_id, completed):
        str = completed.strftime('%Y-%m-%d %H:%M:%S')
        payload = { "tracked_time": str }
        url =  self.host + ':' + self.grocy_port + '/api/chores/' + chore_id + '/execute'
        r = requests.post(url, verify=self.ssl, headers={'GROCY-API-KEY': self.grocy_key } , json=payload)
        if r.status_code == 200:
            if self.debug:
                self.log("Chore " + chore_id + " tracks successful", level = "INFO")
            return True
        else:
            self.log(r.json()['error_message'], level = "ERROR")
            return False

    def get_tasklist(self):
        tl = self.service.tasklists().get(tasklist=self.tl_id).execute()
        if self.debug:
            self.log(tl)
        self.tl_lastup = self.rfc3339_to_utc(tl['updated'])
        tasklist = self.service.tasks().list(tasklist=self.tl_id, showCompleted= True, showHidden= True).execute()
        if self.debug:
            self.log(tasklist)
        return tasklist
        
    def sync(self):
        chores_list = self.get_g_sc()
        task_list = self.get_tasklist()
        for chore in chores_list:
            has_lastc = False
            track_date_only = False
            if chore['next_estimated_execution_time'] is None:
                if self.debug:
                    self.log("No next date, skipping this chore : " + chore['chore_id'])
                continue
            chore_due_d = pytz.utc.localize(datetime.datetime.strptime(chore['next_estimated_execution_time'] , '%Y-%m-%d %H:%M:%S' )).date()
            if chore['track_date_only'] == "1":
                track_date_only = True
            c = self.get_chore(chore['chore_id'])
            
            if self.debug:
                self.log("Chore due date : ")
                self.log(chore_due_d)
                self.log("Gtasks list last update : ")
                self.log(self.tl_lastup)
                self.log(c)
            if chore['last_tracked_time'] is not None:
                chore_lastc_d = pytz.utc.localize(datetime.datetime.strptime(chore['last_tracked_time'] , '%Y-%m-%d %H:%M:%S' ))
                has_lastc = True
                if self.debug:
                    self.log("Chore last done : ")
                    self.log(chore_lastc_d)
                if chore_lastc_d > self.tl_lastup:
                    if self.debug:
                        self.log("Waiting GTasks synchro")
                    continue
                if track_date_only:
                    chore_lastc_d = chore_lastc_d.date()
            if 'items' not in task_list:
                if self.debug:
                        self.log("List empty, add it to gtasks")
                self.add_task(c['chore']['name'],chore_due_d)
                continue
            for task in task_list['items']:
                if self.debug:
                    self.log(task)
                task_due_d = self.rfc3339_to_utc(task['due']).date()
                if self.debug:
                    self.log(task['title'] + " " + c['chore']['name'])
                    self.log("Task date : ")
                    self.log(task_due_d)
                if task['title'] == c['chore']['name'] and task_due_d == chore_due_d:
                    if self.debug:
                        self.log("Task found with status : " + task['status'] )
                    if task['status'] == "completed":
                        if self.debug:
                            self.log(task['title'] + "is completed")
                        task_c_d = self.rfc3339_to_utc(task['completed'])
                        if has_lastc:
                            if self.debug:
                                self.log(task_c_d)
                                self.log(task_c_d.date())
                            if track_date_only:
                                if task_c_d.date() < chore_lastc_d:
                                    if self.debug:
                                        self.log("Waiting for gtask clear")
                                    break
                            else:
                                if task_c_d < chore_lastc_d:
                                    if self.debug:
                                        self.log("Waiting for gtask clear")
                                    break
                        else:
                            if self.debug:
                                self.log("First completion : ")
                        self.complete_chore(chore['chore_id'],task_c_d)
                        self.service.tasks().delete(tasklist=self.tl_id , task=task['id']).execute()
                        break
                    else:
                        if self.debug:
                            self.log("Task " + task['title'] + " is waiting for action")
                        break
            else:
                if self.debug:
                    self.log("No task found, add it to gtasks")
                self.add_task(c['chore']['name'],chore_due_d)
            continue
        
    def get_chore(self, chore_id):
        url =  self.host + ':' + self.grocy_port + '/api/chores/' + chore_id
        if self.debug:
            self.log(url)
        r = requests.get(url, verify=self.ssl, headers={'GROCY-API-KEY': self.grocy_key } )
        if self.debug:
            self.log(r)
        if r.status_code == 200:
            if self.debug:
                self.log(r.json() , level = "INFO")
        else:
            self.log(r.json()['error_message'], level = "ERROR")
        return r.json()
        
    def add_task(self, name, due_date):
        str_date = self.d_to_rstr(due_date)
        task = {
            'title': name ,
            'due': str_date
            }
        if self.debug:
            self.log(task)
        return self.service.tasks().insert(tasklist=self.tl_id , body=task).execute()
        
    def return_code_cb(self, entity, attribute, old, new, kwargs):
        self.return_code = new
        self.new_auth = False
        if self.debug:
            self.log("___function___")
            self.log(self.return_code)
        self.cancel_listen_state(self.handle)
        self.set_state(entity, date = '')
        self.connect()
        self.init_tasklist()
        self.handle = self.run_every(self.sync_cb , datetime.datetime.now() , 120)
        
        
    def build_service(self):
        if self.debug:
            self.log("___function___")
        self.service = build('tasks', 'v1', credentials=self.creds)
    
    def sync_cb(self , kwargs):
        self.sync()
        
    def d_to_rstr(self, date):
        if self.debug:
            self.log("___function___")
            self.log(date)
        str = date.strftime('%Y-%m-%dT%H:%M:%S.0000Z')
        return str
        
    def rfc3339_to_utc(self, date_rfc3339):
        if self.debug:
            self.log("___function___")
            self.log(date_rfc3339)
        date = pytz.utc.localize(datetime.datetime.strptime(date_rfc3339 , '%Y-%m-%dT%H:%M:%S.%fZ' ))
        return date
        
    def get_g_sc(self):
        url =  self.host + ':' + self.grocy_port + '/api/chores'
        r = requests.get(url, verify=self.ssl, headers={'GROCY-API-KEY': self.grocy_key } )
        if not r.json():
            self.log("Chores list empty..." , level = "WARNING")
        return r.json()