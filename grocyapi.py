import appdaemon.plugins.hass.hassapi as hass
import requests
import json

class GrocyApi(hass.Hass):
    verify_ssl = True
    port = "9192"
    debug = False

    def initialize(self):
        self.host = self.args["host"]
        if 'DEBUG' in self.args:
            self.debug = self.args["DEBUG"]
        self.port = self.args["port"]
        self.api_key = self.args["api_key"]
        self.verify_ssl = self.args["verify_ssl"]
        self.headers = { "GROCY-API-KEY": self.api_key }
        self.base_url = self.host + ':' + self.port
        
    def get_product(self , product_id):
        if self.debug:
            self.log("Product Id : " + product_id, level = "INFO")
        url = self.base_url + '/api/stock/products/' + product_id
        r = requests.get(url, verify=self.verify_ssl, headers=self.headers)
        if r.status_code == 200:
            product = r.json()
            if self.debug:
                self.log("Grocy product : " + product['product']['name'] , level = "INFO")
        else:
            self.log(r.json()['error_message'], level = "INFO")
        return product
    
    def get_shopping_list(self):
        url = self.base_url + '/api/objects/shopping_list'
        r = requests.get(url, verify=self.verify_ssl, headers=self.headers )
        if r.status_code == 200:
            if self.debug:
                self.log("Get shopping list succes" , level = "INFO")
        else:
            self.log(r, level = "INFO")
            
        return r.json()
        
    def purchase_product(self, grocy_item_id, best_date,price,amount):
        if best_date is None:
            best_date = '2999-12-31'
        payload = { 'amount': amount , 'best_before_date': best_date , 'transaction_type': 'purchase' , 'price': price }
        url = self.base_url + '/api/stock/products/' + grocy_item_id + '/add'
        r =requests.post(url, verify=self.verify_ssl, headers=self.headers , json=payload)
        if r.status_code == 200:
            if self.debug:
                self.log("Product " + grocy_item_id + " purchased successful", level = "INFO")
            return True
        else:
            self.log(r.json()['error_message'], level = "INFO")
            return False
    
    def delete_product_in_sl(self, product_sl_id):
        url = self.base_url + '/api/objects/shopping_list/' + product_sl_id
        r = requests.delete(url, verify=self.verify_ssl, headers=self.headers )
        if r.status_code == 204:
            if self.debug:
                self.log("Product " + product_sl_id + " delete successful", level = "INFO")
            return True
        else:
            self.log(r.json()['error_message'], level = "INFO")
            return False
            
    def get_chore(self, chore_id):
        url =  self.base_url + '/api/chores/' + chore_id
        if self.debug:
            self.log(url)
        r = requests.get(url, verify=self.verify_ssl, headers=self.headers )
        if self.debug:
            self.log(r)
        if r.status_code == 200:
            if self.debug:
                self.log(r.json() , level = "INFO")
        else:
            self.log(r.json()['error_message'], level = "ERROR")
        return r.json()
        
    def get_linked_product_id(self, chore_id):
        url =  self.base_url + '/api/userfields/chores/' + chore_id
        if self.debug:
            self.log(url)
        r = requests.get(url, verify=self.verify_ssl, headers=self.headers )
        if self.debug:
            self.log(r)
        if r.status_code == 200:
            if self.debug:
                self.log(r.json() , level = "INFO")
        else:
            self.log(r.json()['error_message'], level = "ERROR")
        return r.json()['productid']
        
    def get_chores(self):
        url =  self.base_url + '/api/chores'
        r = requests.get(url, verify=self.verify_ssl, headers=self.headers )
        if not r.json():
            self.log("Chores list empty..." , level = "WARNING")
        return r.json()