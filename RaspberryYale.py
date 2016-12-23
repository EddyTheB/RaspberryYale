from __future__ import print_function
from sys import stdout, argv
from os import makedirs, path
from time import sleep
from datetime import datetime, timedelta
from apiclient import discovery, errors
from httplib2 import Http
from oauth2client import file, client, tools
from subprocess import Popen
import socket, ssl
try:
  from picamera import PiCamera
  Pi = True
except ImportError:
  from pygame import camera, image
  Pi = False
#from multiprocessing import Process
import re
homeDir = path.expanduser('~')
dropBoxUploader = homeDir + '/Documents/Development/Dropbox-Uploader/dropbox_uploader.sh'

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
    
def createServiceGMAIL():
  print('Creating new GMAIL service.')
  a = discovery.build('gmail', 'v1', http=creds.authorize(Http()))
  return a

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
      response = service.users().messages().list(userId=user_id, q=query,
                                         pageToken=page_token).execute()
      try:
        messages.extend(response['messages'])
      except KeyError:
        pass
    
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
  
def assessAlarmStatus(service):
  if not checkInternet():
    return 'NoInternet', timedelta(minutes=0)
  messageTypes = {}
  #allowedSenders = ['report@yalehomesystem.co.uk', 'me']
  allowedSubjects = ['Yale Home Notification', 'RaspberryYale Test']
  messageTypes['TestStart'] = 'RaspberryYale System Test - Start'
  messageTypes['TestEnd'] = 'RaspberryYale System Test - End'
  messageTypes['DisArm'] = 'Disarm From Account'
  messageTypes['HomeArm'] = 'Home Arm From Account'
  messageTypes['Arm'] = 'Arm From Account'
  messageTypes['Burglar'] = 'Burglar From Account'
  TestOrder = ["Burglar", "DisArm", "Arm", "HomeArm", "TestEnd", "TestStart"]

  includeTestType = True
  # Get all messages.
  messages = listMessages(service, 'me')
  for message in messages:
    messageID = message['id']
    messageGot = service.users().messages().get(userId='me', id=messageID).execute()

    # Ensure that the sender is one of the allowed Senders.
    # Ensure that the Subject is one of the allowd Subjects.
    # If not either of those, then look at the next email untill one is found.
    # Then go through the messageTypes, to see what type it is.
    # if type is found to be 'TestEnd' then go to last non-test type.
    # otherwise, set status to be type found.
    #From = 'Unknown'
    Subject = 'Unknown'
    for header in messageGot['payload']['headers']:
      #print(header['name'], ' : ', header['value'])
      #if header['name'] == u'X-Sender':
      #  From = header['value']
      #if header['name'] == u'To':
      #  To = header['value']
      if header['name'] == u'Subject':
        Subject = header['value']
      elif header['name'] == u'Date':
        Date = header['value']
    #if From == To:
    #  From = 'me'
    #print(Date[:25])
    #print(datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z'))
    #print('ssss')
    Date = datetime.strptime(Date[:25], '%a, %d %b %Y %H:%M:%S')
    Age = datetime.now() - Date
      
    if True: #From in allowedSenders:
      if Subject in allowedSubjects:
        # Check snippet contents. They're short emails so the snippets are plenty.
        Snippet = messageGot['snippet']
        for Test in TestOrder:
          testStr = messageTypes[Test]
          match = re.search(testStr, Snippet)
          if match:
            Type = Test
            if Type == 'TestEnd':
              includeTestType = False
              continue
            elif Type == 'TestStart':
              if includeTestType:
                return Type, Age
              else:
                continue
            else:
              return Type, Age
          else:
            continue
      
def initCamera():
  if Pi:      
    cam = PiCamera()
    cam.start_preview()
  else:
    camera.init()
    cam = camera.Camera(camera.list_cameras()[0])
    cam.start()
  return cam
  
def closeCamera(cam):
  if Pi:
    cam.stop_preview()
  else:
    cam.stop()  
      
def takePhotos(directory, timeBetween=1, timeFor=60):
  if timeBetween > timeFor:
    print('Taking 1 photo and pausing for {} seconds.'.format(timeFor))
  else:
    print('Taking 1 photo every {} seconds for up to {} seconds.'.format(timeBetween, timeFor))
  print('Saving them to {}.'.format(directory))
  if not path.exists(directory):
    makedirs(directory)
  TimeEnd = datetime.now() + timedelta(seconds=timeFor)
  cam = initCamera()
  takePhoto(cam, directory)
  NumPhotos = 1
  if timeBetween > timeFor:
    upLoadToDropBox(directory)
    sleep(timeFor)
  else:
    while datetime.now() < TimeEnd:
      sleep(timeBetween)
      takePhoto(cam, directory)
      NumPhotos += 1
      if NumPhotos%5 == 0:
        upLoadToDropBox(directory)
  closeCamera(cam)
  upLoadToDropBox(directory)
  print('Done. Took {} photos.'.format(NumPhotos))
    
def takePhoto(cam, directory):
  FileName = "{}/p{}.jpg".format(directory, datetime.now().strftime('%Y%m%d%H%M%S'))
  if Pi:
    cam.capture(FileName)
  else:     
    img = cam.get_image()
    image.save(img, FileName)
  return FileName
  
def upLoadToDropBox(source):
  gotInternet = checkInternet()
  if gotInternet:
    LastBit = path.basename(path.normpath(source))
    # Check, is a directory
    if path.isdir(source):      
      ToDir = socket.gethostname() + '/' + LastBit + '/'
      dropboxCommand = dropBoxUploader + ' upload -s ' + source + '/* ' + ToDir
    elif path.isfile(source):
      ToFile = socket.gethostname() + '/' + LastBit
      dropboxCommand = dropBoxUploader + ' upload ' + source + ' ' + ToFile
    Popen(dropboxCommand, shell=True)  

if __name__ == '__main__':
  print('Programme started on {}.'.format(datetime.now().strftime('%Y %b %d at %H:%M:%S')))
  
  args = argv[1:]
  if 'saveDirectory' in args:
    saveDirectory = args[args.index('saveDirectory') + 1]
  else:
    saveDirectory = homeDir + '/Pictures/Apps/RaspberryYale'    
  if '--takeSingle' in args:
    cam = initCamera()
    FN = takePhoto(cam, saveDirectory)  
    closeCamera(cam)
    print('Single image captured and saved as {}.'.format(FN))
    print('Uploading to dropbox.')
    upLoadToDropBox(FN)
    exit()
  if 'takePhotosFor' in args:
    takePhotosFor = args[args.index('takePhotosFor') + 1]
  else:
    takePhotosFor = 1 # Minutes
  print('When a trigger is detected, photos will be taken for {} minutes.'.format(takePhotosFor))        
  if 'cancelTime' in args:
    cancelTime = args[args.index('cancelTime') + 1]
  else:
    cancelTime = 10 # Minutes
  print('Triggers more than {} minutes old will be ignored.'.format(cancelTime))            
  maxAge = timedelta(minutes=cancelTime)
  print('Photos will be saved in {}.'.format(saveDirectory))  
  
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
  GMAIL = createServiceGMAIL()

  statusTimes = 0
  statusLast = 'random'
  while True:
    # Sleep for 5 seconds. Do this first to ensure that, no matter what, the
    # infinite loop doesn't crash the email server.
    sleep(5)
    # Check the alarm status.
    try:
      status, age = assessAlarmStatus(GMAIL)
    except ssl.SSLError as E:
      if E.args[0] == 'The read operation timed out':
        print('\nThe read operation timed out')
        GMAIL = createServiceGMAIL()
      else:
        raise(E)
      
    if (age > maxAge) or (status in ["DisArm", "Arm", "HomeArm", "TestEnd"]):
      # Nothing happening, carry on.
      print('Checked and found nothing on {}.'.format(datetime.now().strftime('%Y %b %d at %H:%M:%S')), end='\r')      
      statusTimes = 0
      statusLast = 'random'
    else:
      if status == "Burglar":
        print('\nBurglar detected on {}.'.format(datetime.now().strftime('%Y %b %d at %H:%M:%S')))        
        saveDirectory_N = '{}/R{}_Burgler'.format(saveDirectory, datetime.now().strftime('%Y%m%d%H%M%S'))
      elif status == "TestStart":
        print('\nTest message detected on {}.'.format(datetime.now().strftime('%Y %b %d at %H:%M:%S')))
        saveDirectory_N = '{}/R{}_Test'.format(saveDirectory, datetime.now().strftime('%Y%m%d%H%M%S'))      
      elif status == "NoInternet":
        print('\nInternet Down on {}.'.format(datetime.now().strftime('%Y %b %d at %H:%M:%S')))
        saveDirectory_N = '{}/R{}_IntDown'.format(saveDirectory, datetime.now().strftime('%Y%m%d%H%M%S'))
      if statusLast == status:
        statusTimes += 1
      else:
        saveDirectoryToUse = saveDirectory_N;
      takePhotos(saveDirectoryToUse, timeBetween=2**statusTimes, timeFor=takePhotosFor*60)
      statusLast = status;
    stdout.flush()
    
        