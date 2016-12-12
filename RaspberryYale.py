from os.path import expanduser
from time import sleep
from apiclient import discovery, errors
from httplib2 import Http
from oauth2client import file, client, tools
homeDir = expanduser('~')

def listMessages(service, user_id, sender=None, subject=None, newer_than=None, text=None):
  query = ''
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
  
def checkMessages(service, GotMessageIDs=[]):
  messages = listMessages(service, 'me', sender='report@yalehomesystem.co.uk', subject='"Yale Home Notification"', newer_than='1d', text='"Burglar From Account"')
  if messages:
    message = messages[-1];
    messageID = message['id']
    if messageID not in GotMessageIDs:
      print "You're being robbed!"
      return messageID
  testmessages = listMessages(GMAIL, 'me', newer_than='1d', text='"RaspberryYale System Test"')
  if testmessages:
    message = testmessages[-1];
    messageID = message['id']
    if messageID not in GotMessageIDs:
      print "The test worked!"
      return messageID
    else:
      print "Nothing to report at TTTTTT"
  return None

if __name__ == '__main__':

  # Want read only access to my 'stuff' gmail account.
  SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'

  # Get the OAuth2 credentials
  secretFile =  homeDir + '/.api/AlphonsoOak.json'
  store = file.Storage('storage.json')
  creds = store.get()
  if not creds or creds.invalid:
    flow = client.flow_from_clientsecrets(secretFile, SCOPES)
    creds = tools.run_flow(flow, store)

  # Create the gmail service
  GMAIL = discovery.build('gmail', 'v1', http=creds.authorize(Http()))

  triggeredMessages = []
  # Now, continuesly check the messages to see if any "Burglar" messages have been sent.
  while True:
    # Sleep for 20 seconds. Do this first to ensure that, no matter what, the
    # infinite loop doesn't crash the email server.
    sleep(5)
    messageID = checkMessages(GMAIL, GotMessageIDs=triggeredMessages)
    if messageID:
      print messageID
      triggeredMessages.append(messageID)
    