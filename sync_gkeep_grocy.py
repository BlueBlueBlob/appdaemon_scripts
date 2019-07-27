import appdaemon.plugins.hass.hassapi as hass
import requests
import json
import gkeepapi
import datetime
import pytz
class SyncGKeepandGrocy(hass.Hass):
    grocy_key = ""
    host = ""
    keep = None
    app_timezone = ""
    gk_username = ""
    gk_token = ""
    gk_list = ""
    app_timezone = ""
    debug = False
    grocy_port = "9192"
    timezones = None
    
    def initialize (self):
        self.gk_list = self.args["gkeep_list"]
        self.grocy_key = self.args["grocy_key"]
        self.grocy_port = self.args["grocy_port"]
        self.ssl = self.args['ssl_verify']
        self.gk_username = self.args["google_username"]
        self.gk_token = self.args["gkeep_token"]
        self.host = self.args["host"]
        if 'DEBUG' in self.args:
            self.debug = self.args["DEBUG"]
        self.keep = gkeepapi.Keep()
        self.app_timezone = self.args["app_timezone"]
        self.timezone = pytz.timezone(self.app_timezone)

        # Attempt to login
        try:
            login_success = self.keep.login(self.gk_username, self.gk_token)
        except gkeepapi.exception.ParseException as e:
            self.log(e.raw, level = "ERROR")
        if not login_success:
            self.log("ERROR : Google Keep login failed.", level = "INFO")
            return False

        self.sync_lists()
        self.handle = self.run_every(self.callback_sync , datetime.datetime.now() , 120)


    def terminate(self):
        keep = None
        
    def callback_sync(self, kwargs):
        self.sync_lists()
        
    def get_product_grocy(self , product_id):
        if self.debug:
            self.log("Product Id : " + product_id, level = "INFO")
        url= self.host + ':' + self.grocy_port + '/api/stock/products/' + product_id
        r = requests.get(url, verify=self.ssl, headers={'GROCY-API-KEY': self.grocy_key })
        if r.status_code == 200:
            product = r.json()
            if self.debug:
                self.log("Grocy product : " + product['product']['name'] , level = "INFO")
        else:
            self.log(r.json()['error_message'], level = "INFO")
        return product
    
    def get_g_sl(self):
        url =  self.host + ':' + self.grocy_port + '/api/objects/shopping_list'
        r = requests.get(url, verify=self.ssl, headers={'GROCY-API-KEY': self.grocy_key } )
        if r.status_code == 200:
            if self.debug:
                self.log("Get shopping list succes" , level = "INFO")
        else:
            self.log(r, level = "INFO")
            
        return r.json()
        
    def purchase_product_grocy(self, grocy_item_id, best_date,price,amount):
        if best_date is None:
            best_date = '2999-12-31'
        payload = { 'amount': amount , 'best_before_date': best_date , 'transaction_type': 'purchase' , 'price': price }
        url =  self.host + ':' + self.grocy_port + '/api/stock/products/' + grocy_item_id + '/add'
        r =requests.post(url, verify=self.ssl, headers={'GROCY-API-KEY': self.grocy_key } , json=payload)
        if r.status_code == 200:
            if self.debug:
                self.log("Product " + grocy_item_id + " purchased successful", level = "INFO")
            return True
        else:
            self.log(r.json()['error_message'], level = "INFO")
            return False
    
    def delete_product_sl_grocy(self, product_sl_id):
        url =  self.host + ':' + self.grocy_port + '/api/objects/shopping_list/' + product_sl_id
        r = requests.delete(url, verify=self.ssl, headers={'GROCY-API-KEY': self.grocy_key } )
        if r.status_code == 204:
            if self.debug:
                self.log("Product " + product_sl_id + " delete successful", level = "INFO")
            return True
        else:
            self.log(r.json()['error_message'], level = "INFO")
            return False
    
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
            self.log("GKeep sync")
        self.keep.sync()
        gk_tmp_l = self.get_gk_list()
        grocy_tmp_l = self.get_g_sl()
        update_gk = False
        update_grocy = False
        gk_date_up = pytz.utc.localize(gk_tmp_l.timestamps.updated)
        for p in grocy_tmp_l:
            p_time = self.timezone.localize(datetime.datetime.strptime(p['row_created_timestamp'] , '%Y-%m-%d %H:%M:%S' ))
            p_obj = self.get_product_grocy(p['product_id'])
            if self.debug:
                self.log("Grocy product time")
                self.log(p_time)
                self.log("Google keep last update time")
                self.log(gk_date_up)
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
            else:
                if self.debug:
                    self.log("Looking in GKeep checked list")
                for ic in gk_tmp_l.checked:
                    if p_obj['product']['name'] == ic.text:
                        instock_amount = str(int(int(p['amount']) * float(p_obj['product']['qu_factor_purchase_to_stock'])))
                        if self.debug:
                            self.log("Amount : " + instock_amount)
                        if self.purchase_product_grocy(p['product_id'],p_obj['next_best_before_date'],p_obj['last_price'],instock_amount ):
                            self.delete_product_sl_grocy(p['id'])
                            break
        if self.debug:
            self.log("GKeep sync")
        self.keep.sync()
        
