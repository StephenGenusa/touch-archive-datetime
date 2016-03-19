#!/usr/bin/env python


import os
import sys
import time
import datetime
import tarfile
import gzip
import zipfile
import re
import dateutil.parser
from dateutil.tz import tzutc, tzoffset

# isoparser from https://github.com/barneygale/isoparser
import isoparser
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
import exifread


# Can optionally use send2trash module if installed

only_test_validity_of_archive = False
delete_empty_files = True
delete_invalid_archives = True
datestamp_github_archive_filenames = True
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


def rename_github_archives(file_name):
    """Add a timestamp like 2015_03_01 to the filename of GitHub archives
       touch_filename() should always be called first to make sure the archive
       has the correct datetime on it.
    """
    for partial_filename in ['-master.zip', '-develop.zip', '-devel.zip', '-gh-pages.zip']:
        if partial_filename in file_name:
            mod_time = time.localtime(os.path.getmtime(file_name))
            time_stamp = time.strftime("%Y_%m_%d", mod_time)
            if time_stamp not in file_name: # file does not already have timestamp
                new_file_name = file_name.replace('.zip', '') + \
                    '_' + time_stamp + '.zip'
                if not os.path.isfile(new_file_name):
                    os.rename(file_name, new_file_name)
                    print "  Archive renamed", new_file_name


def touch_gem_file(file_name):
    """Looks for a valid date/time in the Ruby file archive directory first, 
       if not found it looks in metadata.gz next, and then touches the 
       archive with that date/time   
    """
    # Try and grab the date/time from the file directory. Old gem files all 
    # have invalid date/times, apparently due to the gem package manager
    tarfile_mod_time = get_time_for_tarfile(file_name)
    if tarfile_mod_time > 0:
        touch_file(file_name, tarfile_mod_time)
    else:
        # Not found so try and grab it from the metadata file
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


def touch_ioc_file(file_name):
    """Gets the author date/time found in the IOC file and then touches
    the .ioc with that date/time   
    www.openioc.com iocbucket.com
    """
    # Try and grab the date/time from the file contents.
    try:
        content = open(file_name,'rb').read()
        match = re.search("<authored_date>(.{5,20}?)<", content, re.DOTALL | re.MULTILINE)
        if match:
            parsed_datetime = match.groups(0)[0]
        else:
            parsed_datetime = ''
        dt = dateutil.parser.parse(parsed_datetime)
        touch_file(file_name, time.mktime(dt.timetuple()))
    except:
        pass

def iso_parse_path_rec(parent_rec, latest_datetime):
    for rec in parent_rec:
        cur_datetime = dateutil.parser.parse(rec.datetime)
        if rec.is_directory:
            if cur_datetime > latest_datetime:
                latest_datetime = cur_datetime
            iso_parse_path_rec(rec.children,latest_datetime)
        else:
            if cur_datetime > latest_datetime:
                latest_datetime = cur_datetime
    return latest_datetime

def touch_iso_file(file_name):
    """Gets the latest date/time found in the ISO file and then touches the .iso 
    with that date/time
    """
    # Try and grab the date/time from the file contents.
    try:
        iso = isoparser.parse(file_name)
        early_datetime = datetime.datetime(1960,1,1,0,0)
        isofile_mod_time = iso_parse_path_rec(iso.record().children, early_datetime)
        if isofile_mod_time > early_datetime:
            touch_file(file_name, time.mktime(isofile_mod_time.timetuple()))
    except:
        pass

   
    
def transform_pdf_date(date_str):
    """
    Convert a pdf date such as "D:20120321183444+07'00'" into a usable datetime
    http://www.verypdf.com/pdfinfoeditor/pdf-date-format.htm
    (D:YYYYMMDDHHmmSSOHH'mm')
    :param date_str: pdf date string
    :return: datetime object
    From http://stackoverflow.com/questions/16503075/convert-creationtime-of-pdf-to-a-readable-format-in-python
    """
    pdf_date_pattern = re.compile(''.join([
        r"(D:)?",
        r"(?P<year>\d\d\d\d)",
        r"(?P<month>\d\d)",
        r"(?P<day>\d\d)",
        r"(?P<hour>\d\d)",
        r"(?P<minute>\d\d)",
        r"(?P<second>\d\d)",
        r"(?P<tz_offset>[+-zZ])?",
        r"(?P<tz_hour>\d\d)?",
        r"'?(?P<tz_minute>\d\d)?'?"]))
    match = re.match(pdf_date_pattern, date_str)
    if match:
        date_info = match.groupdict()

        for k, v in date_info.iteritems():  # transform values
            if v is None:
                pass
            elif k == 'tz_offset':
                date_info[k] = v.lower()  # so we can treat Z as z
            else:
                date_info[k] = int(v)

        if date_info['tz_offset'] in ('z', None):  # UTC
            date_info['tzinfo'] = tzutc()
        else:
            multiplier = 1 if date_info['tz_offset'] == '+' else -1
            date_info['tzinfo'] = tzoffset(None, multiplier*(3600 * date_info['tz_hour'] + 60 * date_info['tz_minute']))

        for k in ('tz_offset', 'tz_hour', 'tz_minute'):  # no longer needed
            del date_info[k]

        return datetime.datetime(**date_info)

    
def touch_pdf_file(file_name):
    with open(file_name, 'rb') as pdfFile:
        pdf_parser = PDFParser(pdfFile)
        pdf_doc = PDFDocument(pdf_parser)
        if len(pdf_doc.info) and 'ModDate' in pdf_doc.info[0]:
            pdf_mod_time = transform_pdf_date(pdf_doc.info[0]['ModDate'])
            touch_file(file_name, time.mktime(pdf_mod_time.timetuple()))
        else:
            if len(pdf_doc.info) and 'CreationDate' in pdf_doc.info[0]:
                pdf_mod_time = transform_pdf_date(pdf_doc.info[0]['CreationDate'])
                touch_file(file_name, time.mktime(pdf_mod_time.timetuple()))


def touch_exif_file(file_name):
    early_datetime = datetime.datetime(1960,1,1,0,0)
    with open(file_name, 'rb') as exifFile:
        tags = exifread.process_file(exifFile)
        if len(tags) and 'EXIF DateTimeOriginal' in tags:
            exif_mod_time = dateutil.parser.parse(str(tags['EXIF DateTimeOriginal']))
            if exif_mod_time > early_datetime:            
                touch_file(file_name, time.mktime(exif_mod_time.timetuple()))


def process_file(filename_to_process):
    """Determines file extension; determines if it is a kind of file that the
    program can process and if so, calls the appropriate helper functions to
    get the date/time of the archive/container and then touch the file   
    """
    filename, file_extension = splitext(filename_to_process)
    file_extension = file_extension.lower()
    if os.path.getsize(filename_to_process) > 0:
        if file_extension in ['.zip', '.whl', '.egg', '.docx']:
            touch_file(filename_to_process, get_time_for_zipfile(filename_to_process))
            if file_extension == '.zip' and datestamp_github_archive_filenames:
                rename_github_archives(filename_to_process)                
        elif file_extension in ['.tar', '.tar.gz', '.tar.bz2', '.tgz']:
            touch_file(filename_to_process, get_time_for_tarfile(filename_to_process))
        elif file_extension in ['.jpg', '.jpeg', '.wav', '.tif', '.tiff']:
            touch_exif_file(filename_to_process)
        elif file_extension in ['.pdf']:
            touch_pdf_file(filename_to_process)
        elif file_extension in ['.gem']:
            touch_gem_file(filename_to_process)
        elif file_extension in ['.ioc']:
            touch_ioc_file(filename_to_process)
        elif file_extension in ['.iso']:
            touch_iso_file(filename_to_process)
        elif file_extension in ['', '.html', '.htm', '.txt', '.py', '.md5', '.png', '.doc', '.odt', '.xml']:
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
        sys.stdout.write('\n' + '*' * 80)
        sys.stdout.write('\n* WARNING THE FOLLOWING FILES WILL BE DELETED:')
        sys.stdout.write('\n' + '*' * 80)
        for file_name in files_to_delete:
            sys.stdout.write('\n* WARNING: Ready to DELETE'+ file_name)
        sys.stdout.write('\n' + '*' * 80)
        sys.stdout.write('\n')
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
