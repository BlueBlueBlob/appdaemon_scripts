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
        r = requests.get(url , headers=self.headers)
        if r.json()['status_verbose'] == "product found":
            if self.debug:
                self.log("OFF product found : " , level = "INFO")
                self.log(r.json() , level = "INFO")
        else:
            self.log(r.json()['status_verbose'], level = "INFO")
        return r.json()