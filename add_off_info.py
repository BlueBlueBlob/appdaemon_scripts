import appdaemon.plugins.hass.hassapi as hass
import os
import requests
import datetime

class SyncOFFToGrocy(hass.Hass):
    
    grocyapi = None
    offapi = None
    food_group_id = '1'
    debug = False
    
    def initialize (self):
        self.grocyapi = self.get_app("grocy_api")
        self.offapi = self.get_app("off_api")
        if 'DEBUG' in self.args:
            self.debug = self.args["DEBUG"]
        self.food_group_id = self.grocyapi.get_product_group(name = self.args['food_group_name'])
        self.populate_grocy()
        time = datetime.time(1, 00, 0)
        self.handle = self.run_daily(self.populate_cb, time)
        
    def terminate (self):
        self.grocyapi = None
        self.offapi = None
    
    def populate_cb(self,kwargs):
        self.populate_grocy()
        
    def add_product_pic(self, product_id):
        product = self.grocyapi.get_product(product_id)['product']
        product_bc = product['barcode']
        if self.debug:
            self.log('Product barcode : {}' .format(product_bc))
        if isinstance(product_bc, list):
            bc = product_bc[0]
        else:
            bc = product_bc
        if bc == '':
            self.log('No barcode for product {}' .format(product['name']) , level = "WARNING")
            return False
        pic_url = self.offapi.get_product_attr(bc,"image_url")
        with open('/share/tmp.jpg', 'wb') as file:
            response = requests.get(pic_url, stream=True)
            if not response.ok:
                self.log( response, level = "ERROR")
            for block in response.iter_content(1024):
                if not block:
                    break
                file.write(block)
            file.close()
        if not self.grocyapi.upload_product_picture(product_id, '/share/tmp.jpg'):
            return False
        os.remove('/share/tmp.jpg')
        payload = { 'picture_file_name' :  '{}.jpg'.format( product_id) }
        if self.debug:
            self.log('id : {} , payload : {}' .format(product_id, payload))
        if not self.grocyapi.update_product(product_id, payload):
            return False
        return True
        
    def populate_grocy(self):
        for product in self.grocyapi.all_product():
            id = product['id']
            name = product['name']
            group = product['product_group_id']
            if self.debug:
                self.log(product , level = "INFO")
            if group != self.food_group_id:
                if self.debug:
                    self.log('{} skipped, not a food product. group_id : {}' .format(name , group), level = "INFO")
                continue
            if product['picture_file_name'] is not None:
                if self.debug:
                    self.log('{} skipped, picture already set up' .format(name), level = "INFO")
                continue
            if self.add_product_pic(id):
                if self.debug:
                    self.log('{} product successfully updated' .format(name), level = "INFO")
        