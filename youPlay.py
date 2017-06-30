# Author: Brandon Paw
# File: youPlay.py

									# IMPORTS

# Imports used for basic system operations and html/url parsing
import os
import sys
import httplib2
import urllib2
from urlparse import urlparse
from urlparse import parse_qs
from bs4 import BeautifulSoup, SoupStrainer

# Imports for the YouTube API
from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

						# Definitions and Initializations

# Create a reference to dev/null and a reference to old stdout
ogOut = sys.stdout
devNull = open(os.devnull, 'w')

CLIENT_SECRETS_FILE = "client_secret.json"
YOUTUBE_READ_WRITE_SSL_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
YOUTUBE_READ_WRITE_SCOPE = "https://www.googleapis.com/auth/youtube"
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
MISSING_CLIENT_SECRETS_MESSAGE = "WARNING: Please configure OAuth 2.0"

# Authorize the request and store authorization credentials.
def get_authenticated_service(args):
  flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE, scope=YOUTUBE_READ_WRITE_SSL_SCOPE,
    message=MISSING_CLIENT_SECRETS_MESSAGE)

  storage = Storage("youtube-api-snippets-oauth2.json")
  credentials = storage.get()

  if credentials is None or credentials.invalid:
    credentials = run_flow(flow, storage, args)

  # Trusted testers can download this discovery document from the developers page
  # and it should be in the same directory with the code.
  return build(API_SERVICE_NAME, API_VERSION,
      http=credentials.authorize(httplib2.Http()))

args = argparser.parse_args()
service = get_authenticated_service(args)

def print_results(results):
  print(results)

# Build a resource based on a list of properties given as key-value pairs.
# Leave properties with empty values out of the inserted resource.
def build_resource(properties):
  resource = {}
  for p in properties:
    # Given a key like "snippet.title", split into "snippet" and "title", where
    # "snippet" will be an object and "title" will be a property in that object.
    prop_array = p.split('.')
    ref = resource
    for pa in range(0, len(prop_array)):
      is_array = False
      key = prop_array[pa]
      # Convert a name like "snippet.tags[]" to snippet.tags, but handle
      # the value as an array.
      if key[-2:] == '[]':
        key = key[0:len(key)-2:]
        is_array = True
      if pa == (len(prop_array) - 1):
        # Leave properties without values out of inserted resource.
        if properties[p]:
          if is_array:
            ref[key] = properties[p].split(',')
          else:
            ref[key] = properties[p]
      elif key not in ref:
        # For example, the property is "snippet.title", but the resource does
        # not yet have a "snippet" object. Create the snippet object here.
        # Setting "ref = ref[key]" means that in the next time through the
        # "for pa in range ..." loop, we will be setting a property in the
        # resource's "snippet" object.
        ref[key] = {}
        ref = ref[key]
      else:
        # For example, the property is "snippet.description", and the resource
        # already has a "snippet" object.
        ref = ref[key]
  return resource

# Remove keyword arguments that are not set
def remove_empty_kwargs(**kwargs):
  good_kwargs = {}
  if kwargs is not None:
    for key, value in kwargs.iteritems():
      if value:
        good_kwargs[key] = value
  return good_kwargs

def playlist_items_insert(properties, **kwargs):
    resource = build_resource(properties) # See full sample for function
    kwargs = remove_empty_kwargs(**kwargs) # See full sample for function
    results = service.playlistItems().insert(
        body=resource,
        **kwargs
    ).execute()

    print_results(results)

def video_id(value):

    query = urlparse(value)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch':
            p = parse_qs(query.query)
            return p['v'][0]
        if query.path[:7] == '/embed/':
            return query.path.split('/')[2]
        if query.path[:3] == '/v/':
            return query.path.split('/')[2]
    # fail?
    return None

                        # Beginning of User Interactie mode

# Error Check the command line arguments 
page = raw_input("What is the name of the HTML file you would like to parse?\n")
if len(page) > 0:

    # Loop used to continually prompt the user until a valid playlist name is entered
    noName = None
    while noName == None:
    
        # Prompt user for name of the playlist  
        playlist_name = raw_input("Name your new playlist: ")

        try:
            # This code creates a new, private playlist in the authorized user's channel.
            playlists_insert_response = service.playlists().insert(
                part="snippet,status",
                body=dict(
                    snippet=dict(
                        title=str(playlist_name),
                        description="A private playlist created with the YouTube API v3"
                    ),
                    status=dict(
                        privacyStatus="private"
                    )
                )
            ).execute()
            noName = True
        except HttpError:
            print "Invalid YouTube playlist name"

    playlist_id = playlists_insert_response["id"]
    print "New playlist id: %s" % playlist_id

    # Open the html file
    file = open(page, "r")
    html = file.read()

    # Use BeautifulSoup to grab all the youtube links
    soup = BeautifulSoup(html, "html.parser")

    for link in soup.findAll('a'):
        url = link.get('href')
        if str(url[:19]) == "https://www.youtube":
            try:
                sys.stdout = ogOut
                print "Uploading: %s" % link.string
                sys.stdout = devNull
                playlist_items_insert(
                    {'snippet.playlistId': playlist_id,
                     'snippet.resourceId.kind': 'youtube#video',
                     'snippet.resourceId.videoId': video_id(url),
                     'snippet.position': ''},
                    part='snippet',
                    onBehalfOfContentOwner='')
            except HttpError:
                sys.stdout = ogOut
                print "Unfortuneately, a video was not found."

    # Confirmation for the user that the script has finished running
    print "Your playlist should be completed! Thank you for using youPlay :)"
else:
    print "Please input a file"
