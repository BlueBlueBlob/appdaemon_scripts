import appdaemon.plugins.hass.hassapi as hass
import datetime
import pytz
import requests
import json

class SyncGTasksAndGrocy(hass.Hass):
    tl_name = 'Corvées'
    tl_id = None
    tl_main = None
    debug = False
    gr_cl = None
    service = None
    tl_lastup = None
    google_oauth_tasks = None
    grocyapi = None
    
    def initialize(self):
        
        if 'DEBUG' in self.args:
            self.debug = self.args["DEBUG"]
        self.tl_name = self.args['chores_list']
        self.google_oauth_tasks = self.get_app("google_oauth_tasks")
        self.grocyapi = self.get_app("grocy_api")
        self.handle = self.run_every(self.sync_cb , datetime.datetime.now() , 300)
        
    def terminate(self):
        tl_id = None
        tl_main = None
        gr_cl = None
        service = None
        tl_lastup = None
        google_oauth_tasks = None
        grocyapi = None
        

    def init_tasklist(self):
        self.google_oauth_tasks.build_service()
        # Call the Tasks API
        all_tl = self.google_oauth_tasks.service.tasklists().list().execute()    
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
                        self.log('Task list found, name : {} , id : {}' .format(task_list['title'], self.tl_id))
                    break
            else:
                self.log("No list found")
                    

    def get_tasklist(self):
        tl = self.google_oauth_tasks.service.tasklists().get(tasklist=self.tl_id).execute()
        if self.debug:
            self.log(tl)
        self.tl_lastup = self.rfc3339_to_utc(tl['updated'])
        tasklist = self.google_oauth_tasks.service.tasks().list(tasklist=self.tl_id, showCompleted= True, showHidden= True).execute()
        if self.debug:
            self.log(tasklist)
        return tasklist
        
    def sync(self):
        self.init_tasklist()
        chores_list = self.grocyapi.get_chores()
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
            c = self.grocyapi.get_chore(chore['chore_id'])
            
            if self.debug:
                self.log( 'Chore due date : {}' .format(chore_due_d))
                self.log( 'Gtasks list last update : {}' .format(self.tl_lastup))
                self.log(c)
            if chore['last_tracked_time'] is not None:
                chore_lastc_d = pytz.utc.localize(datetime.datetime.strptime(chore['last_tracked_time'] , '%Y-%m-%d %H:%M:%S' ))
                has_lastc = True
                if self.debug:
                    self.log('Chore last done : {}' .format(chore_lastc_d))
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
                    self.log('Task date : {} ' .format(task_due_d))
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
                        self.grocyapi.complete_chore(chore['chore_id'],task_c_d)
                        self.google_oauth_tasks.service.tasks().delete(tasklist=self.tl_id , task=task['id']).execute()
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
        
    def add_task(self, name, due_date):
        str_date = self.d_to_rstr(due_date)
        task = {
            'title': name ,
            'due': str_date
            }
        if self.debug:
            self.log(task)
        return self.google_oauth_tasks.service.tasks().insert(tasklist=self.tl_id , body=task).execute()