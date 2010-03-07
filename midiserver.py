# Midi Server - Create Midi files based on URL parameters
# Copyright 2010 Brian Slesinsky


import logging
import os

from google.appengine.dist import use_library
from google.appengine.ext import webapp
import wsgiref.handlers

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
use_library('django', '1.1')
from django.template.loader import render_to_string

from MidiFile import MIDIFile


# === Midi generation ===


def GenerateMidi(notes, tempo, out):
  song = MIDIFile(1)
  track = 0
  time = 0
  song.addTrackName(track, time, "Sample Track")
  song.addTempo(track, time, tempo)
  channel = 0
  def AddNote(pitch, time, duration):
    song.addNote(track, channel, pitch, time, duration, 100)
  def SetEndTime(time):
    # add a no-op event to make sure we wait one beat the end,
    # to add time for the last note to fade
    song.addTempo(track, time + 1, 120)
  Parse(notes, AddNote, SetEndTime)
  song.writeFile(out)

letters = 'CDEFGAB'
pitches = [60, 62, 64, 65, 67, 69, 71]
letter_to_pitch = dict(zip(letters + letters.lower(), 
                      pitches + [p + 12 for p in pitches]))

REST = "rest"

def Parse(music, addNote, setEndTime):
  class State(object):
    def __init__(self):
      self.time = 0
      self.pitch = None
      self.accidental = 0
      self.number = 0
      self.slash = False
    def Parse(self, music):
      for c in music:
        if c in "CDEFGABcdefgab":
          self.FinishNote()
          self.pitch = letter_to_pitch[c]
        elif c == "'":
          self.pitch += 12
        elif c == ",":
          self.pitch -= 12
        elif c == 'z':
          self.FinishNote()
          self.pitch = REST
        elif c in "0123456789":
          self.number = self.number * 10 + int(c)
        elif c == '/':
          self.slash = True
          self.number = 0
        elif c == '^':
          self.accidental += 1
        elif c == '_':
          self.accidental -= 1
      self.FinishNote()
      setEndTime(self.time)
    def FinishNote(self):
      if self.slash:
        if self.number == 0:
          beats = 0.5
        else:
          beats = 1.0 / self.number
      else:
        if self.number == 0:
          beats = 1
        else:
          beats = self.number
      if self.pitch == REST:
        self.time += beats
      elif self.pitch is not None:
        pitch = self.pitch + self.accidental
        if pitch >= 0 and pitch <= 127:
          addNote(pitch, self.time, beats)
        self.time += beats
      self.pitch = None
      self.accidental = 0
      self.number = 0
      self.slash = False

  State().Parse(music)


# === pages ===


class MainPage(webapp.RequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/html'
    self.response.out.write(render_to_string('frontpage.html', {}))


class SendMidiFile(webapp.RequestHandler):
  def get(self):
    notes = self.request.get('n')
    tempo = int(self.request.get('t'))
    self.response.headers['Content-Type'] = 'audio/mid'
    GenerateMidi(notes, tempo, self.response.out)

def main_nocache():
  app = webapp.WSGIApplication([
      ('/', MainPage), ('/midi', SendMidiFile)
      ], debug=True)
  wsgiref.handlers.CGIHandler().run(app)


if __name__ == '__main__':
  main_nocache()
