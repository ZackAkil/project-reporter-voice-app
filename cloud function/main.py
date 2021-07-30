
import requests
import json

import firebase_admin
from firebase_admin import firestore

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# test doc id  if you want all outputs to go to the same doc, otherwise set to None 
TEST_DOC = '1Zih_uBYhTI6VCeUcjkbU3KJEkosRokI'
TEST_DOC = None

AUTH0_CLIENT_ID = 'GAudL-your Auth0 client id-CtbPq'
AUTH0_CLIENT_SECRET = '-B5hJKld5HhB-your Auth0 client secret-dwJdJDId'

GOOGLE_CLIENT_ID = '4812603959-- your google client id7e6.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = 'dGxy8-yoru google client secret-6nOdwE'


if (not firebase_admin._apps):
   app = firebase_admin.initialize_app()
   db = firestore.client()


def hello_world(request):
   """Responds to any HTTP request.
   Args:
       request (flask.Request): HTTP request object.
   Returns:
       The response text or any set of values that can be turned into a
       Response object using
       `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
   """



   request_json = request.get_json()
   
   print(request_json)
   print(request.headers)
   
   auth0_token = request.headers.get('Authorization').split(' ')[-1]
   session_id = request_json['session']['id']
   
   noted = False
   
   if request_json['handler']['name'] == 'start':
       start(request_json, auth0_token, session_id)
   # elif request_json['handler']['name'] == 'abstract':
   elif request_json['handler']['name'] == 'verified':
       pass
   else:
       noted = True
       write(request_json, auth0_token, session_id)

       
   response =  {"session": {
                           "id": session_id,
                           "params": {}
                         }
              }
   
   if noted:
       response["prompt"] = {
                           "override": False,
                           "firstSimple": {
                             "speech": "Noted.",
                             "text": ""
                           }
                         }
   
   

   return json.dumps(response)


def start(request_json, auth0_token, session_id):
   
   print('TRIGGER START ACTION')
   
   if TEST_DOC:
       return 
   
   google_access_token = get_google_token_from_auth0(auth0_token) 
   
   doc_id = create_doc(google_access_token)
   
   set_doc_id(session_id, doc_id)
   
   
   
def write(request_json, auth0_token, session_id):
   
   print('TRIGGER WRITE ACTION')
   
   text = request_json['intent']['params']['text']['original']
   google_access_token = get_google_token_from_auth0(auth0_token) 
   doc_id = get_doc_id(session_id)
   
   append_to_doc(google_access_token, doc_id, request_json['handler']['name'])
   append_to_doc(google_access_token, doc_id, text)
   append_to_doc(google_access_token, doc_id, "\n")
   

   
def get_doc_id(session_id):
   # fetch doc id from firebase 
   
   if TEST_DOC:
       return TEST_DOC
   
   doc_ref = db.collection('projects').document(session_id)
   doc = doc_ref.get()
   return doc.to_dict().get('doc_id')
   
def set_doc_id(session_id, doc_id):
   # set doc id from firebase 
   if TEST_DOC:
       return 
   
   data = {
       'doc_id':doc_id,
   }
   db.collection('projects').document(session_id).set(data)

   
   
def get_google_token_from_auth0(auth0_token):
   
   auth0_user_id = get_auth0_user_id(auth0_token)
   auth0_api_token = get_auth0_api_token()
   google_refresh_token = get_google_refresh_token(auth0_user_id, auth0_api_token)
   google_access_token = get_google_access_token(google_refresh_token)
   return google_access_token
   

def get_auth0_user_id(token):

   user_info_req = requests.get(url='https://dev-chkwy0ws.eu.auth0.com/userinfo',
                            headers={"Authorization":"Bearer "+token})
   user_info_req_json = user_info_req.json()
   return user_info_req_json['sub']


def get_auth0_api_token():
   
   auth0_token_data = {
              'grant_type':'client_credentials',
              'client_id':AUTH0_CLIENT_ID,
              'client_secret':AUTH0_CLIENT_SECRET,
              'audience':'https://dev-chkwy0ws.eu.auth0.com/api/v2/'
          }

   auth0_token_req = requests.post(url='https://dev-chkwy0ws.eu.auth0.com/oauth/token',
                                   headers={"content-type":"application/x-www-form-urlencoded"},
                                   data=auth0_token_data)
   
   auth0_token_req_json = auth0_token_req.json()
   return auth0_token_req_json['access_token']
   
   
def get_google_refresh_token(auth0_user_id, auth0_api_token):

   user_profile_req = requests.get(url='https://dev-chkwy0ws.eu.auth0.com/api/v2/users/' + auth0_user_id,
                                   headers={"Authorization":"Bearer "+auth0_api_token})

   user_profile_req_json = user_profile_req.json()

   google_identity = [i for i in user_profile_req_json['identities'] if i['provider'] == 'google-oauth2'][0]
   google_refresh_token = google_identity['refresh_token']
   return google_refresh_token


def get_google_access_token(google_refresh_token):
   
   google_refresh_token_data = {
          'grant_type': 'refresh_token',
          'client_id': GOOGLE_CLIENT_ID,
          'client_secret': GOOGLE_CLIENT_SECRET,
          'refresh_token': google_refresh_token
      }

   google_refresh_token_req = requests.post(url='https://www.googleapis.com/oauth2/v4/token',
                                   headers={"content-type":"application/x-www-form-urlencoded"},
                                   data=google_refresh_token_data)

   google_refresh_token_req_json = google_refresh_token_req.json()
   google_access_token = google_refresh_token_req_json['access_token']
   return google_access_token


def create_doc(google_access_token):
   
   creds = Credentials(google_access_token)
   service = build('docs', 'v1', credentials=creds)
   
   title = 'Pragmatic Doc create'
   body = {
       'title': title,
   }
   doc = service.documents().create(body=body).execute()
   doc_id = doc['documentId']
   
   return doc_id

def append_to_doc(google_access_token, doc_id, text):
   
   creds = Credentials(google_access_token)
   service = build('docs', 'v1', credentials=creds)
   
   
   # get document
   document = service.documents().get(documentId=doc_id).execute()
   # find last index     
   last_index = document['body']['content'][-1]['endIndex']
   
   # insert text to doc

   requests = [
        {
           'insertText': {
               'location': {
                   'index': last_index - 1,
               },
               'text': "\n" + text
           }
       }
   ]

   service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()


