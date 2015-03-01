#!/usr/bin/python

import os
import sys
import time
import datetime
import tarfile
import gzip
import zipfile
import re
import dateutil.parser

only_test_validity_of_archive = False

# From http://code.activestate.com/recipes/410692/
class switch(object):
    def __init__(self, value):
        self.value = value
        self.fall = False

    def __iter__(self):
        """Return the match method once, then stop"""
        yield self.match
        raise StopIteration
    
    def match(self, *args):
        """Indicate whether or not to enter a case suite"""
        if self.fall or not args:
            return True
        elif self.value in args: # changed for v1.5, see below
            self.fall = True
            return True
        else:
            return False

# From http://stackoverflow.com/questions/16976192/whats-the-way-to-extract-file-extension-from-file-name-in-python
def splitext(path):
    for ext in ['.tar.gz', '.tar.bz2']:
        if path.endswith(ext):
            return path[:-len(ext)], path[-len(ext):]
    return os.path.splitext(path)


def touch_file(file_name, mod_time):
    try:
        if not only_test_validity_of_archive :
            if mod_time > 0 and mod_time < 1609376461:
                os.utime(file_name, ((mod_time,mod_time)))
                print "  Touched  " + file_name
            else:
                print "  Skipped  " + file_name
    except:
        pass


def log_error(message):
    open("file_errors.txt", 'a').writelines(message + '\n')
    

def get_time_for_tarfile(file_name):
    newest_time = 0
    try:
        with tarfile.TarFile.open(file_name, 'r') as tarredFile:
            members = tarredFile.getmembers()
            if not only_test_validity_of_archive :
                for member in members:
                    if member.mtime > newest_time:
                        newest_time = member.mtime
    except:
        log_error(file_name + ": " + str(sys.exc_info()[0]))
    return newest_time
    
    
def get_time_for_zipfile(file_name):
    newest_time = 0
    try:
        with zipfile.ZipFile(file_name, 'r') as zippedFile:
            members = zippedFile.infolist()
            if not only_test_validity_of_archive :
                for member in members:
                    curDT = time.mktime(datetime.datetime(*member.date_time).timetuple())
                    if curDT > newest_time:
                        newest_time = curDT
    except:
        log_error(file_name + ": " + str(sys.exc_info()[0]))
    return newest_time

def touch_gem_file(file_name):
    with tarfile.TarFile.open(file_name, 'r') as tarredFile:
        members = tarredFile.getmembers()
        for member in members:
            if member.name == 'metadata.gz':
                try:
                    tarredFile.extract(member, "/tmp")
                    content = gzip.open('/tmp/metadata.gz','rb')
                    metadata = content.read()
                    os.remove('/tmp/metadata.gz')
                    match = re.search("date:(.{0,50}?)\n", metadata, re.DOTALL | re.MULTILINE)
                    if match:
                        parsed_datetime = match.groups(0)[0]
                    else:
                        parsed_datetime = ""
                    dt = dateutil.parser.parse(parsed_datetime)
                    touch_file(file_name, time.mktime(dt.timetuple()))
                except:
                    log_error(file_name + ": " + str(sys.exc_info()[0]))
    

def process_file(filename_to_process):
    filename, file_extension = splitext(filename_to_process)
    if os.path.getsize(filename_to_process) > 0:
        for case in switch(file_extension.lower()):
            if case('.zip'):
                touch_file(filename_to_process, get_time_for_zipfile(filename_to_process))
                break
            if case('.whl'):
                touch_file(filename_to_process, get_time_for_zipfile(filename_to_process))
                break
            if case('.egg'):
                touch_file(filename_to_process, get_time_for_zipfile(filename_to_process))
                break
            if case('.tar'):
                touch_file(filename_to_process, get_time_for_tarfile(filename_to_process))
                break
            if case('.tar.gz'):
                touch_file(filename_to_process, get_time_for_tarfile(filename_to_process))
                break
            if case('.tar.bz2'):
                touch_file(filename_to_process, get_time_for_tarfile(filename_to_process))
                break
            if case('.tgz'):
                touch_file(filename_to_process, get_time_for_tarfile(filename_to_process))
                break
            if case('.gem'):
                touch_gem_file(filename_to_process)
                break
            if case(''):
                break
            if case('.html'):
                break
            if case('.htm'):
                break
            if case('.txt'):
                break
            if case('.py'):
                break
            if case('.md5'):
                break
            if case(''): # default, could also just omit condition or 'if True'
                print "Extension '" + file_extension.lower() + "' not handled."
    else:
        log_error('Empty file: ' + filename_to_process)


def main(root_path):
    for root, dirs, files in os.walk(root_path):
        print 'Processing Path ' + root
        for file in files:
            process_file(root + "/" + file)
    print "\nStephen's Archive Re-Touch Utility Complete\n"


##########################################
# Change this later to a command-line param
##########################################
if __name__ == "__main__":
    main(root_path='/data/rubygems/gems')
