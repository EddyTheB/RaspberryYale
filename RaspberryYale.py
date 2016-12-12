from os.path import expanduser
from apiclient import discovery, errors
from httplib2 import Http
from oauth2client import file, client, tools
homeDir = expanduser('~')

def ListMessages(service, user_id, sender=None, subject=None, newer_than=None, text=None):
  query = None
  if sender:
    query = 'from:' + sender
  if subject:
    query = query + ' subject:' + subject
  if newer_than:
    query = query + ' newer_than:' + newer_than
  if text:
    query = query + ' ' + text
    
  try:
    response = service.users().messages().list(userId=user_id,q=query).execute()
    messages = []
    if 'messages' in response:
      messages.extend(response['messages'])
    
    while 'nextPageToken' in response:
      page_token = response['nextPageToken']
      response = GMAIL.users().messages().list(userId='me').execute()
      messages.extend(response['messages'])
    
    return messages
  except errors.HttpError, error:
    print 'An error occurred: %s' % error
  


# Want read only access to my 'stuff' gmail account.
SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'

# Get the OAuth2 credentials
secretFile =  homeDir + '/.api/AlphonsoOak.json'
store = file.Storage('storage.json')
creds = store.get()
if not creds or creds.invalid:
  flow = client.flow_from_clientsecrets(secretFile, SCOPES)
  creds = tools.run_flow(flow, store)

# Get the stuff!
GMAIL = discovery.build('gmail', 'v1', http=creds.authorize(Http()))

# Now check the messages to see if any "Burglar" messages have been sent.
messages = ListMessages(GMAIL, 'me', sender='report@yalehomesystem.co.uk', subject='"Yale Home Notification"', newer_than='1m', text='"Burglar From Account"')
  
print messages