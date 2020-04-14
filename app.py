import boto3
import os
import json
import requests
import sys
from dotenv import load_dotenv
from icalendar import Calendar, Event
import recurring_ical_events
from datetime import date, datetime, timedelta


def getSSMParameter(nameSSMParameter):
    print("Start: Get SSMParameter")
    try:    
        response = client_ssm.get_parameter(Name=nameSSMParameter, WithDecryption=True)
        print("Finish: Get SSMParameter")
        return (response['Parameter']['Value'])
    except Exception as e: 
        print(e)
        print ("Error getting SSMParameter")
        sys.exit(1)
def updateSSMParameter(nameSSMParameter,currentSSMParameter,newSSMParameter):
    print("Start: Update SSMParameter")
    try:
        currentValues = json.loads(currentSSMParameter)
        currentValues['pd_token'] = newSSMParameter['access_token']
        currentValues['pd_refresh_token'] = newSSMParameter['refresh_token']
        newValues = json.dumps(currentValues)
        response = client_ssm.put_parameter(Name=os.environ["SSM_PARAMETERS"], Type='SecureString', Value=str(newValues), Overwrite=True)
        print("Finish: Update SSMParameter")
        return (response)
    except Exception as e: 
        print(e)
        print ("Error updating SSMParameter")
        sys.exit(1)
def refreshToken(valueSSMParameter):
    print("Start: Refresh Access Token")
    try:
        auth_parameters = json.loads(valueSSMParameter)
        params = {'grant_type':'refresh_token',
                    'client_id':auth_parameters['client_id'],
                    'client_secret':auth_parameters['client_secret'],
                    'refresh_token':auth_parameters['pd_refresh_token']
                    }
        print("Start: External API connection")
        refreshRequest = requests.post(url=os.environ["URL_AUTH"], params=params)
        print("Start connection")
        response = refreshRequest.json()
        if refreshRequest.status_code == 200:
            print ("Successful connection. HTTP STATUS: "+str(refreshRequest.status_code))
        else:
            print("Some error occurs in connection. HTTP STATUS: "+str(refreshRequest.status_code))
            raise
        print("Finish: Refresh Access Token")
        return (response)
    except Exception as e: 
        print(e)
        print ("Error refreshing Access Token ")
        sys.exit(1)
def getUserId(valueSSMParameter,analystEmail):
    print("Start: Get User ID")
    try:
        auth_parameters = json.loads(valueSSMParameter)
        headers = {'authorization':"Bearer "+auth_parameters['pd_token'],
                    'accept':"application/vnd.pagerduty+json;version=2"
                    }
        params = {'query':analystEmail}
        print("Start: External API connection")
        responseApi = requests.get(url=os.environ["URL_API"]+"/users", headers=headers , params=params)
        if responseApi.status_code == 200:
            print ("Successful connection. HTTP STATUS: "+str(responseApi.status_code))
        else:
            print("Some error occurs in connection. HTTP STATUS: "+str(responseApi.status_code))
        userInfo = responseApi.json()
        response = str(userInfo['users'][0]['id'])
        print ("UserID: "+response)
        print("Finish: Get User ID")
        return (response)
    except Exception as e: 
        print(e)
        print ("Error getting User ID ")
        sys.exit(1)
def icsParser():
    #Adept this part according to your need
    print ("Start: Calendar Parser")
    icsURL=os.environ["URL_ICS"]
    print("Start Calendar connection ")
    icsCalendar = requests.get(url=icsURL)
    if icsCalendar.status_code == 200:
        print ("Successful connection. HTTP STATUS: "+str(icsCalendar.status_code))
    else:
        print("Some error occurs in connection. HTTP STATUS: "+str(icsCalendar.status_code))
    icsCalendar = Calendar.from_ical(icsCalendar.text)
    today = datetime.today()
    events = recurring_ical_events.of(icsCalendar).at(today)
    for event in events:
        #Update strech if event signature update
        if "Sobreaviso" in event["SUMMARY"]:
            print ("Today: "+str(today))
            print ("START ON-CALL: "+str(event['DTSTART'].dt))
            print ("END ON-CAL: "+str(event['DTEND'].dt))
            summary = event['SUMMARY'].splitlines()
            email = summary[2].split(" - ")
            print ("ANALYST: "+email[1])
            return (email[1])

def lambda_handler(event, lambda_context):
    print ("Start Lambda")
    currentSSMParameter = getSSMParameter(os.environ["SSM_PARAMETERS"])
    analystEmail = icsParser()
    oncallAnalystID = getUserId(currentSSMParameter,analystEmail)
    newSSMParameter = refreshToken(currentSSMParameter)
    updateToken = updateSSMParameter(os.environ["SSM_PARAMETERS"],currentSSMParameter,newSSMParameter)
    print("Finish Lambda")

if 'OS' in os.environ:
    load_dotenv()
    session = boto3.Session(profile_name='dev', region_name='us-east-1')
    client_ssm = session.client('ssm')
    event="1"
    lambda_context=""
    lambda_handler(event, lambda_context)
else:
    client_ssm = boto3.client('ssm')