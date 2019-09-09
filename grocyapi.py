import appdaemon.plugins.hass.hassapi as hass
import requests
import json
import os
import base64

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
        
    def all_product(self):
        url =  self.base_url + '/api/objects/products'
        r = requests.get(url, verify=self.verify_ssl, headers=self.headers )
        if r.status_code == 200:
            if self.debug:
                self.log(r.json() , level = "INFO")
        else:
            self.log(r.json()['error_message'], level = "ERROR")
        return r.json()
        
    def get_product_group(self, id = "" , name = ""):
        url =  self.base_url + '/api/objects/product_groups'
        r = requests.get(url, verify=self.verify_ssl, headers=self.headers )
        if r.status_code == 200:
            if self.debug:
                self.log(r.json() , level = "INFO")
        else:
            self.log(r.json()['error_message'], level = "ERROR")
            return
        
        for pg in r.json():
            if id != "":
                if pg['id'] == id:
                    if self.debug:
                        self.log('id : {} , name : {}'.format(pg['id'], pg['name']) , level = "INFO")
                    return pg['name']
            if name != "":
                if pg['name'] == name:
                    if self.debug:
                        self.log('id : {} , name : {}'.format(pg['id'], pg['name']) , level = "INFO")
                    return pg['id']
        else:
            if self.debug:
                if id != "":
                    self.log('id {} not found'.format(id), level = "ERROR")
                else:
                    self.log('name {} not found'.format(name), level = "ERROR")
            
    def update_product(self, product_id, payload):
        up_header = self.headers
        up_header['accept'] = '*/*'
        up_header['Content-Type'] = 'application/json'
        if self.debug:
            self.log('product id : {} , payload : {}' .format(product_id, payload))
        url = self.base_url + '/api/objects/products/' + product_id
        r =requests.put(url, verify=self.verify_ssl, headers=up_header , data=json.dumps(payload))
        if r.status_code == 204:
            if self.debug:
                self.log("Product " + product_id + " succefully, updated", level = "INFO")
            return True
        else:
            self.log(r.json()['error_message'], level = "ERROR")
            return False
    
    def upload_product_picture(self, product_id, pic_file):
        if not os.path.exists(pic_file):
            self.log('{} not found !' .format(pic_file), level = "ERROR")
            return False
        up_header = self.headers
        up_header['accept'] = '*/*'
        up_header['Content-Type'] = 'application/octet-stream'
        b64fn = base64.b64encode('{}.jpg'.format(product_id).encode('ascii'))
        url = '{}/api/files/productpictures/{!s}' .format(self.base_url, str(b64fn, "utf-8"))
        if self.debug:
            self.log('b64 : {} , url : {}' .format(b64fn,url))
        r =requests.put(url, verify=self.verify_ssl, headers=up_header , data=open(pic_file,'rb'))
        if r.status_code == 204:
            if self.debug:
                self.log("Product " + product_id + " image succefully uploaded", level = "INFO")
            return True
        else:
            self.log(r.json()['error_message'], level = "ERROR")
            return False
    
        