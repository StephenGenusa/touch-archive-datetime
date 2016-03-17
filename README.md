touch-archive-datetime
======================

Sets the datetime stamp of an archive file (zip/tar/tar.gz/tar.bz2/tgz/egg/whl/gem/ioc/iso/pdf) to the newest datetime of files inside the archive/container or modification/creation time in the case of PDF files. Stores a list of *apparently* invalid archives and offers the option to delete or send-to-trash those files. Note: Some platforms may have a version of Python compiled that does not include, say the zlib library, so the archive may appear invalid when it is actually valid but unreadable by that version of Python. You'll want to make sure that this isn't the cause of failure before wiping out a bunch of files. Can optionally use the send2trash module if it is installed.
