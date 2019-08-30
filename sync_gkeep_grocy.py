import appdaemon.plugins.hass.hassapi as hass
import requests
import json
import gkeepapi
import datetime
import pytz
class SyncGKeepandGrocy(hass.Hass):

    keep = None
    app_timezone = ""
    gk_username = ""
    gk_token = ""
    gk_list = ""
    app_timezone = ""
    debug = False
    timezones = None
    grocyapi = None
    
    def initialize (self):
        self.gk_list = self.args["gkeep_list"]
        self.gk_username = self.args["google_username"]
        self.gk_token = self.args["gkeep_token"]
        if 'DEBUG' in self.args:
            self.debug = self.args["DEBUG"]
        self.keep = gkeepapi.Keep()
        self.grocyapi = self.get_app("grocy_api")
        self.app_timezone = self.args["app_timezone"]
        self.timezone = pytz.timezone(self.app_timezone)

        # Attempt to login
        try:
            login_success = self.keep.login(self.gk_username, self.gk_token)
        except gkeepapi.exception.ParseException as e:
            self.log(e.raw, level = "ERROR")
        if not login_success:
            self.log("ERROR : Google Keep login failed.", level = "ERROR")
            return False

        self.sync_lists()
        self.handle = self.run_every(self.callback_sync , datetime.datetime.now() , 120)


    def terminate(self):
        keep = None
        
    def callback_sync(self, kwargs):
        self.sync_lists()
        
    
    def get_gk_list(self):
        for list_temp in self.keep.all():
            if list_temp.title == self.gk_list:
                list = list_temp
                break
        else:
            if self.debug:
                self.log("List not found : " + self.gk_list, level = "INFO")
            list = self.keep.createList(self.gk_list)
            if self.debug:
                self.log("List " + self.gk_list + " created", level = "INFO")
                
        if self.debug:
            self.log("List : " + list.title, level = "INFO")
            
        return list
  
    def sync_lists(self):
        if self.debug:
            self.log("GKeep sync on start")
        self.keep.sync()
        gk_tmp_l = self.get_gk_list()
        grocy_tmp_l = self.grocyapi.get_shopping_list()
        update_gk = False
        update_grocy = False
        gk_date_up = pytz.utc.localize(gk_tmp_l.timestamps.edited)
        for p in grocy_tmp_l:
            p_time = self.timezone.localize(datetime.datetime.strptime(p['row_created_timestamp'] , '%Y-%m-%d %H:%M:%S' ))
            p_obj = self.grocyapi.get_product(p['product_id'])
            if self.debug:
                self.log('Grocy product time : {}' .format(p_time))
                self.log('Google keep last update time : {}'.format(gk_date_up))
            if p_time > gk_date_up:
                if self.debug:
                    self.log("New product in Grocy shopping list", level = "INFO")
                for i in gk_tmp_l.items:
                    if i.text == p_obj['product']['name']:
                        if i.checked:
                            if self.debug:
                                self.log(i.text + " unchecked")
                            i.checked = False
                            break
                else:
                    if self.debug:
                        self.log("New product in GKeep : " + p_obj['product']['name'])
                    gk_tmp_l.add(p_obj['product']['name'] , False)
                continue
            else:
                if self.debug:
                    self.log("Looking in GKeep checked list")
                for ic in gk_tmp_l.checked:
                    if p_obj['product']['name'] == ic.text:
                        instock_amount = str(int(int(p['amount']) * float(p_obj['product']['qu_factor_purchase_to_stock'])))
                        if self.debug:
                            self.log("Amount : " + instock_amount)
                        if self.grocyapi.purchase_product(p['product_id'],p_obj['next_best_before_date'],p_obj['last_price'],instock_amount ):
                            self.grocyapi.delete_product_in_sl(p['id'])
                            break
        if self.debug:
            self.log("GKeep sync at end")
        self.keep.sync()
        
