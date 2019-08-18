import appdaemon.plugins.hass.hassapi as hass
import requests
import json

class OpenFoodFactApi(hass.Hass):
    
    headers = { "User-Agent": "OpenFoodFactApi - Appdaemon - Version 4.0.2 - https://github.com/BlueBlueBlob/appdaemon_scripts" }
    base_url = ".openfoodfacts.org/api/v0/product/"
    debug = False
    
    def initialize (self):
        self.domain = self.args["domain"]
        self.main_url = "https://" + self.domain + self.base_url + ".json"
        if 'DEBUG' in self.args:
            self.debug = self.args["DEBUG"]
          
    def get_product(self, barcode):
        url = self.main_url + barcode
        if self.debug:
            self.log('barcode : {} , url : {}' .format(barcode,url), level = "INFO")
        r = requests.get(url , headers=self.headers)
        
        if r.json()['status_verbose'] == "product found":
            if self.debug:
                self.log("OFF product found : " , level = "INFO")
                self.log(r.json() , level = "INFO")
        else:
            self.log(r.json()['status_verbose'], level = "ERROR")
            self.log('url : {}' .format(url), level = "ERROR")
        return r.json()['product']
        
    def get_product_attr(self, barcode, attribute):
        product = self.get_product(barcode)
        if attribute in product:
            self.log('Product attribute : {}'.format(product[attribute]) , level = "INFO")
            return product[attribute]
        else:
            self.log('Attribute {} not found'.format(attribute), level = "ERROR")