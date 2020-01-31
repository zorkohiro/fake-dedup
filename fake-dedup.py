#!/usr/bin/env python3
#
# Copyright (c) 2020 by Matthew Jacob
# All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of The Version 2 GNU General Public License as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
import hashlib
import os
import time
import sys
from stat import *

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print ("usage: rdlink root-directory")
        sys.exit(1)

    dbdir =  "./.rdlinkdb"

    os.chdir(sys.argv[1])

    try:
        os.mkdir(dbdir)
    except:
        pass

    cutoff = int(time.time()) - (7 * 24 * 60 * 60)
    toplev = True

    for (dirpath, dirnames, filenames) in os.walk("."):
        if dirpath == dbdir:
            continue
        if toplev:
            for d in dirnames:
                path = os.path.join(dirpath, d)
                dirstat = os.stat(path)
                if dirstat.st_mtime > cutoff:
                    print ("skipping", path, "because it is too new")
                    del dirnames[dirnames.index(d)]
            toplev = False
            continue
        dirstat = os.stat(dirpath)
        for f in filenames:
            path = os.path.join(dirpath, f)
            filestat = os.stat(path, follow_symlinks=False)
            if not S_ISREG(filestat.st_mode):
                continue
            if filestat.st_size == 0:
                continue
            hash = hashlib.md5(open(path, "rb").read()).hexdigest()
            file = dbdir + '/' + hash
            try:
                hashstat = os.stat(file)
                if filestat.st_ino != hashstat.st_ino:
                    print ("add", path, "to", hash)
                    #
                    # Remove this file and link to the common link point.
                    # This is where we start reclaiming disk space.
                    # Pick the earliest of time stamps to set the
                    # common link point to.
                    #
                    os.unlink(path)
                    os.link(file, path)
                    if filestat.st_mtime < hashstat.st_mtime:
                        os.utime(path, (filestat.st_mtime, filestat.st_atime))
            except:
                print ("create hash", hash, "for", path)
                #
                # First time we've encountered this hash- create the common link point
                #
                os.link(path, file)
        # restore any timestamps to the containing directory
        os.utime(dirpath, (dirstat.st_mtime, dirstat.st_atime))

    for (dirpath, dirnames, filenames) in os.walk(dbdir):
        for f in filenames:
            path = os.path.join(dirpath, f)
            stat = os.stat(path)
            if stat.st_nlink == 1:
                print (path, "has only one link so removing")
                os.unlink(path)
