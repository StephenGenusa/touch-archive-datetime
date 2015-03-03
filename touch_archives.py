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

# Can optionally use send2trash module if installed

only_test_validity_of_archive = False
delete_empty_files = True
delete_invalid_archives = True
files_to_delete = []


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    From http://code.activestate.com/recipes/577058/
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = ' [y/n] '
    elif default == "yes":
        prompt = ' [Y/n] '
    elif default == "no":
        prompt = ' [y/N] '
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


def splitext(path):
    """Returns full file extension for special case extensions .tar.gz and .tar.bz2
    From http://stackoverflow.com/questions/16976192/whats-the-way-to-extract-file-extension-from-file-name-in-python
    """
    for ext in ['.tar.gz', '.tar.bz2']:
        if path.endswith(ext):
            return path[:-len(ext)], path[-len(ext):]
    return os.path.splitext(path)


def touch_file(file_name, mod_time):
    """Set the file Access time and modification time to parameter mod_time
    """
    try:
        if not only_test_validity_of_archive :
            # if mod_time is in a valid range 1980-01-01 to Now [time.time()]
            if mod_time > 315554400.0 and mod_time < time.time():
                os.utime(file_name, ((mod_time,mod_time)))
                log_info('  Touched  ' + file_name)
            else:
                log_info('  Skipped  ' + file_name)
    except:
        pass


def log_info(message, display_error=True):
    """Logs information to a file and optionally displays it to the screen
    """
    if display_error:
        print message
    open("file_errors.txt", 'a').writelines(message + "\n")
   

def get_time_for_tarfile(file_name):
    """Gets the newest file date/time for a tar archive   
    """
    newest_time = 0
    if tarfile.is_tarfile(file_name):
        try:
            with tarfile.TarFile.open(file_name, 'r') as tarredFile:
                members = tarredFile.getmembers()
                if not only_test_validity_of_archive:
                    for member in members:
                        if member.mtime > newest_time:
                            newest_time = member.mtime
        except:
            log_info(file_name + ': ' + str(sys.exc_info()[0]))
    else:
        files_to_delete.append(file_name)
    return newest_time
    
    
def get_time_for_zipfile(file_name):
    """Gets the newest file date/time for a zip archive   
    """
    newest_time = 0
    try:
        with zipfile.ZipFile(file_name, 'r') as zippedFile:
            members = zippedFile.infolist()
            if not only_test_validity_of_archive:
                for member in members:
                    curDT = time.mktime(datetime.datetime(*member.date_time).timetuple())
                    if curDT > newest_time:
                        newest_time = curDT
    except:
        log_info(file_name + ': ' + str(sys.exc_info()[0]))
        files_to_delete.append(file_name)
    return newest_time


def touch_gem_file(file_name):
    """Gets the Ruby archive date/time found in metadata.gz and then touches
    the archive with that date/time   
    """
    # Try and grab it from the file contents. Old gem files all have invalid
    # date/times, apparently due to the gem package manager
    tarfile_mod_time = get_time_for_tarfile(file_name)
    if tarfile_mod_time > 0:
        touch_file(file_name, tarfile_mod_time)
    else:
        # Try and grab it from the metadata file
        if tarfile.is_tarfile(file_name):
            with tarfile.TarFile.open(file_name, 'r') as tarredFile:
                members = tarredFile.getmembers()
                for member in members:
                    if member.name == 'metadata.gz':
                        try:
                            tarredFile.extract(member, '/tmp')
                            content = gzip.open('/tmp/metadata.gz','rb')
                            metadata = content.read()
                            os.remove('/tmp/metadata.gz')
                            match = re.search("date:(.{0,50}?)\n", metadata, re.DOTALL | re.MULTILINE)
                            if match:
                                parsed_datetime = match.groups(0)[0]
                            else:
                                parsed_datetime = ''
                            dt = dateutil.parser.parse(parsed_datetime)
                            touch_file(file_name, time.mktime(dt.timetuple()))
                        except:
                            log_info(file_name + ': ' + str(sys.exc_info()[0]))
        else:
            if delete_invalid_archives and files_to_delete.count(file_name) == 0:           
                files_to_delete.append(file_name)


def process_file(filename_to_process):
    """Determines file extension; determines if it is a kind of file that the
    program can process and if so, calls the appropriate helper functions to
    get the date/time of the archive and then touch the file   
    """
    filename, file_extension = splitext(filename_to_process)
    file_extension = file_extension.lower()
    if os.path.getsize(filename_to_process) > 0:
        if file_extension in ['.zip', '.whl', '.egg']:
            touch_file(filename_to_process, get_time_for_zipfile(filename_to_process))
        elif file_extension in ['.tar', '.tar.gz', '.tar.bz2', '.tgz']:
            touch_file(filename_to_process, get_time_for_tarfile(filename_to_process))
        elif file_extension in ['.gem']:
            touch_gem_file(filename_to_process)
        elif file_extension in ['', '.html', '.htm', '.txt', '.py', '.md5', '.pdf', '.png', '.jpg', '.doc', '.odt', '.docx', '.xml']:
            pass
        else:
            log_info('Extension "' + file_extension + '" not handled.', False)
    else:
        if file_extension in ['.zip', '.whl', '.egg', '.tar', '.tar.gz', 'tar.bz2', '.tgz', '.gem'] and delete_empty_files:
            log_info('Empty archive file deleted: ' + filename_to_process)
            os.remove(filename_to_process)
 

def main(root_path):
    for root, dirs, files in os.walk(root_path):
        log_info('Processing Path ' + root)
        for file in files:
            process_file(root +'/' + file)
    if delete_invalid_archives and len(files_to_delete) > 0:
        sys.stdout.write('*' * 80)
        sys.stdout.write('* WARNING THE FOLLOWING FILES WILL BE DELETED:')
        sys.stdout.write('*' * 80)
        for file_name in files_to_delete:
            sys.stdout.write('* WARNING: Ready to DELETE', file_name)
        sys.stdout.write('*' * 80)
        answer = query_yes_no('DELETE ALL ' + str(len(files_to_delete)) + ' (APPARENTLY) INVALID FILES?', default="no")  
        if answer:
            try:
                import send2trash
            except ImportError:
                send2trash_available = False
            else:
                send2trash_available = True
            if send2trash_available and query_yes_no('Send to trash', default="yes"):
                for file_name in files_to_delete:
                    log_info('Sending to Trash ' + file_name)
                    send2trash.send2trash(file_name)
            else:
                for file_name in files_to_delete:
                    log_info('DELETING! ' + file_name)
                    os.remove(file_name)
        else:     
            log_info('NO file deletion has occurred')
    
    sys.stdout.write("\nStephen's Archive Re-Touch Utility Complete\n")



##########################################
# Change this later to a command-line param
##########################################
if __name__ == "__main__":
    main(root_path='/data/rubygems/gems')
