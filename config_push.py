import requests, logging, json, sys
from akamai.edgegrid import EdgeGridAuth
import urllib
import json
import configparser


config = configparser.ConfigParser()
config.read('config.txt')
client_token = config['CREDENTIALS']['client_token']
client_secret = config['CREDENTIALS']['client_secret']
access_token = config['CREDENTIALS']['access_token']
access_url = config['CREDENTIALS']['access_url']
DigitalProperty = config['PROPERTY_NAME']['configuration_name']


#output_file = open('Prod_Json_file.json','w')


propertyConfigCount = 0


#Invoke csv to Json parser to convert redirect input URLs to JSON format
#csvTojsonParser.parseCSVFile()

class PapiObjects(object):
    session = requests.Session()
    baseUrl = access_url+'/papi/v0'
    propertyFound = "NOT_FOUND"
    propertyDetails = {}


    headers_activation = {
        "Content-Type": "application/json"
    }

    print("Establishing connection and authenticating the user\n")
    session.auth = EdgeGridAuth(
				client_token = client_token,
				client_secret = client_secret,
				access_token = access_token
                )
    print("Connection Established.\n")

    def getContracts(self):
        contractUrl = self.baseUrl + '/contracts'
        contractResponse = self.session.get(contractUrl)

    def getGroup(self):
        groupUrl = self.baseUrl + '/groups/'
        groupResponse = self.session.get(groupUrl)
        return groupResponse

    def getProperties(self,groupsInfo):
        global propertyConfigCount
        dummy = {}
        propertyListIdentifier = {}
        groupsInfoJson = groupsInfo.json()
        groupItems = groupsInfoJson['groups']['items']
        print("Finding the property under contracts and groups\n")
        for item in groupItems:
            if propertyConfigCount != 1:
                try:
                    contractId = [item['contractIds'][0]]
                    groupId = [item['groupId']]
                    url = self.baseUrl + '/properties/' + '?contractId=' + contractId[0] +'&groupId=' + groupId[0]
                    propertiesResponse = self.session.get(url)
                    if propertiesResponse.status_code == 200:
                        propertiesResponseJson = propertiesResponse.json()
                        propertiesList = propertiesResponseJson['properties']['items']
                        for propertyInfo in propertiesList:
                            propertyName = propertyInfo['propertyName']
                            propertyId = propertyInfo['propertyId']
                            propertyContractId = propertyInfo['contractId']
                            propertyGroupId = propertyInfo['groupId']
                            self.propertyDetails[propertyName] = propertyName #This is used to populate all property names
                            if propertyName == DigitalProperty :
                                propertyConfigCount += 1
                                self.activateProperty(DigitalProperty,propertyContractId,propertyGroupId,propertyId)
                                break
                except KeyError:
                    continue

        if propertyConfigCount != 1:
            #This is executed when given property name is not found in any groups
            print("\nOne of the configurations is not found. Following are the list of property Names in this contract:\n")
            serial_number=1
            for name in self.propertyDetails:
                print(str(serial_number) + ". "+name)
                serial_number+=1
        else:
            #This is executed when propertyName matches one of the properties in contract
            print("\n\n\nProgram completed successfully \n")

    def activateProperty(self,DigitalProperty,propertyContractId,propertyGroupId,propertyId):
        emails = input("Enter the email addresses to be notified seperated by comma(,)\n")
        emails = emails.split(',')
        emails = json.dumps(emails)
        notes = input("Enter the activation notes\n")
        versionsUrl = self.baseUrl + '/properties/'+ propertyId + "/versions/" + '?contractId=' + propertyContractId +'&groupId=' + propertyGroupId
        versionResponse = self.session.get(versionsUrl)
        versionResponseJson = versionResponse.json()
        for eachVersion in versionResponseJson['versions']['items']:
            print("Property Version: " + str(eachVersion['propertyVersion']))
            if eachVersion['stagingStatus'] == "ACTIVE":
                Version = eachVersion['propertyVersion']
        if not 'Version' in locals():
            Version = input("There was no configuration active in staging. Please enter the version number: ")


        #The details has to be within the three double quote or comment format
        activationDetails = """
             {
                "propertyVersion": %s,
                "network": "STAGING",
                "note": "%s",
                "notifyEmails": %s,
                "acknowledgeWarnings": [
                    "msg_baa4560881774a45b5fd25f5b1eab021d7c40b4f"
                ]
            } """ % (Version,notes,emails)

        #print(activationDetails)
        activationurl = self.baseUrl + '/properties/'+ propertyId + "/activations/" + '?contractId=' + propertyContractId +'&groupId=' + propertyGroupId
        activationResponse = self.session.post(activationurl,data=activationDetails,headers=self.headers_activation)
        print("Activation Response Details\n")
        #print("Response code: " + str(activationResponse.status_code))
        #print("Response text: " + activationResponse.text)
        if activationResponse.status_code == 404:
            print("The requested property version is not available.\n")
        elif activationResponse.status_code == 400 and activationResponse.json()['detail'].find("acknowledged"):
            acknowledgeWarnings = []
            print("Following are the WARNINGS...\n")
            for eachWarning in activationResponse.json()['warnings']:
                print("WARNING: " + eachWarning['detail'])
                acknowledgeWarnings.append(eachWarning['messageId'])
                acknowledgeWarningsJson = json.dumps(acknowledgeWarnings)
            acknowledged = input("\nPress 1 if you acknowledge the warnings.\n")
            if acknowledged == "1":
                #acknowledgeWarnings = json.dumps(acknowledgeWarnings)
                #The details has to be within the three double quote or comment format
                updatedactivationDetails = """
                     {
                        "propertyVersion": %s,
                        "network": "STAGING",
                        "note": "%s",
                        "notifyEmails": %s,
                        "acknowledgeWarnings": %s
                    } """ % (Version,notes,emails,acknowledgeWarningsJson)
                #print(activationDetails)
                updatedactivationResponse = self.session.post(activationurl,data=updatedactivationDetails,headers=self.headers_activation)
                #print("Response code: " + str(updatedactivationResponse.status_code))
                #print("Response text: " + updatedactivationResponse.text)
                print("Please wait while we activate the config for you.. Hold on... \n")
                if updatedactivationResponse.status_code == 201:
                    print("Here is the activation link, that can be used to track\n")
                    print(updatedactivationResponse.json()['activationLink'])


papiObj = PapiObjects()
papiObj.getContracts()
print("Fetching all the contracts and groups\n")
groupsInfo = papiObj.getGroup()
papiObj.getProperties(groupsInfo)
