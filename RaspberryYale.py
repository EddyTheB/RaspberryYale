from __future__ import print_function
from sys import stdout
from os import makedirs
from os.path import expanduser, exists
from time import sleep
from datetime import datetime,timedelta
from apiclient import discovery, errors
from httplib2 import Http
from oauth2client import file, client, tools
import socket
from pygame import camera, image
homeDir = expanduser('~')

def checkInternet(host="8.8.8.8", port=53, timeout=3):
  """
  See if an internet connection is available.
  Host: 8.8.8.8 (google-public-dns-a.google.com)
  OpenPort: 53/tcp
  Service: domain (DNS/TCP)
  """
  try:
    socket.setdefaulttimeout(timeout)
    socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
    return True
  except: #Exception as ex:
    #print(ex.message)
    return False

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
      page_token = response['nextPageToken'] # I think this line tells code to go to next message.
      response = GMAIL.users().messages().list(userId='me').execute()
      messages.extend(response['messages'])
    
    return messages
  except errors.HttpError, error:
    print('An error occurred: %s' % error)
  
def checkMessages(service, GotMessageIDs=[]):
  if not checkInternet():
    return None, 'NoInternet'
  messages = listMessages(service, 'me', sender='report@yalehomesystem.co.uk', subject='"Yale Home Notification"', newer_than='1d', text='"Burglar From Account"')
  if messages:
    message = messages[1];
    messageID = message['id']
    if messageID not in GotMessageIDs:
      return messageID, 'Real'
  testmessages = listMessages(GMAIL, 'me', newer_than='1d', text='"RaspberryYale System Test"')
  if testmessages:
    message = testmessages[1]
    messageID = message['id']
    if messageID not in GotMessageIDs:
      return messageID, 'Test'
  return None, None
  
def takePhotos(minutes, directory, timeBetweenPhotos=1):
  print('Taking 1 photo every {} seconds for {} minutes.'.format(timeBetweenPhotos, minutes))
  print('And saving them to {}.'.format(directory))
  if not exists(directory):
    makedirs(directory)
  TimeEnd = datetime.now() + timedelta(minutes=minutes) 
  camera.init()
  cam = camera.Camera(camera.list_cameras()[0])
  cam.start()
  takePhoto(cam, directory)
  NumPhotos = 1
  while datetime.now() < TimeEnd:
    sleep(timeBetweenPhotos)
    takePhoto(cam, directory)
    NumPhotos += 1
  cam.stop()
  print('Done. Took {} photos.'.format(NumPhotos))
  
  
def takePhoto(cam, directory):
  img = cam.get_image()
  image.save(img, "{}/p{}.jpg".format(directory, datetime.now().strftime('%Y%m%d%H%M%S')))

if __name__ == '__main__':
  print('Programme started on {}.'.format(datetime.now().strftime('%Y %b %d at %H:%M:%S')))
  
  TakePhotosFor = 1 # Minutes
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
  gotInternet = checkInternet()
  if not gotInternet:
    print('No internet connection.')
    exit()
  GMAIL = discovery.build('gmail', 'v1', http=creds.authorize(Http()))

  # Define a save directory
  saveDirectory = homeDir + '/Pictures/Apps/RaspberryYale'

  triggeredMessages = []
  # Check the messages once, and do nothing with what you find (so that messages
  # that exist when the code was started do not trigger any thing.)
  messageID, messageType = checkMessages(GMAIL, GotMessageIDs=triggeredMessages)
  if messageID:
    triggeredMessages.append(messageID)
  # Now, continuesly check the messages to see if any "Burglar" messages have been sent.  
  while True:
    # Sleep for 5 seconds. Do this first to ensure that, no matter what, the
    # infinite loop doesn't crash the email server.
    sleep(5)
    messageID, messageType = checkMessages(GMAIL, GotMessageIDs=triggeredMessages)
    if messageType == 'NoInternet':
      # Not connected to the internet. This potentially means that thieves have
      # cut my broadband connection in order to disable the alarm system. So we
      # want to take photos, they will be saved locally only but atleast it 
      # might be possible to recover them at a latter date, if the thieves don't
      # nick the raspberry pi too!
      if gotInternet:    
        print('No internet connection available on {}.'.format(datetime.now().strftime('%Y %b %d at %H:%M:%S')))
        gotInternet = False
        saveDirectory_ = '{}/R{}_IntDown'.format(saveDirectory, datetime.now().strftime('%Y%m%d%H%M%S'))
        takePhotos(TakePhotosFor, saveDirectory_) # Take photos for 5 minutes, and then check again.
        TimesIntDown = 1
      else:
        print('Still no internet connection available on {}.'.format(datetime.now().strftime('%Y %b %d at %H:%M:%S')), end='\r')
        TimesIntDown += 1
        if TimesIntDown <= 3:
          saveDirectory_ = '{}/R{}_IntDown'.format(saveDirectory, datetime.now().strftime('%Y%m%d%H%M%S'))
          takePhotos(TakePhotosFor, saveDirectory_) # Do this a maximum of 3 times (for 15 minutes) total
                        # to avoid filling the memory card.
    else:
      gotInternet = True
      if messageID:
        triggeredMessages.append(messageID)      
        print('\nTrigger email detected on {}.'.format(datetime.now().strftime('%Y %b %d at %H:%M:%S')))
        if messageType == 'Real':
          print('Caught a burgler.')
          saveDirectory_ = '{}/R{}_Burgler'.format(saveDirectory, datetime.now().strftime('%Y%m%d%H%M%S'))
        elif messageType == 'Test':
          print('Test message detected.')
          saveDirectory_ = '{}/R{}_Test'.format(saveDirectory, datetime.now().strftime('%Y%m%d%H%M%S'))
        takePhotos(TakePhotosFor, saveDirectory_)
      else:
        print('Checked and found nothing on {}.'.format(datetime.now().strftime('%Y %b %d at %H:%M:%S')), end='\r')      
    stdout.flush()
        
      
    