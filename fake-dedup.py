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
        print("usage:", sys.argv[0], "root-directory")
        sys.exit(1)


    nadded = 0
    ncreat = 0
    nremvd = 0
    nskipd = 0

    debug = os.getenv("DEBUG")
    os.chdir(sys.argv[1])
    dbdir =  sys.argv[1] + "/.rdlinkdb"

    try:
        os.mkdir(dbdir)
    except:
        pass

    t = int(time.time())
    cutoff = t - (7 * 24 * 60 * 60)

    #
    # Generate a list of candidate directories to descend
    #
    topdirs = []
    for entry in os.scandir():
        if entry.name.startswith('.') or entry.is_file():
            continue
        mtime = int(entry.stat().st_mtime)
        if mtime > cutoff:
            if debug is not None:
                print("skipping top directory", entry.name, "because it is too new")
            nskipd = nskipd + 1
        else:
            if debug is not None:
                print("Will descend into", entry.name)
            topdirs.append(entry.name)

    for topdir in topdirs:
        topstat = os.stat(topdir)
        for (dirpath, dirnames, filenames) in os.walk(topdir):
            dirstat = os.stat(dirpath)
            assert(S_ISDIR(dirstat.st_mode))
            for f in filenames:
                path = os.path.join(dirpath, f)
                filestat = os.stat(path, follow_symlinks=False)
                if not S_ISREG(filestat.st_mode) or filestat.st_size == 0 or filestat.st_nlink != 1:
                    continue
                hash = hashlib.md5(open(path, "rb").read()).hexdigest()
                file = dbdir + '/' + hash
                try:
                    hashstat = os.stat(file)
                    if filestat.st_ino != hashstat.st_ino:
                        nadded = nadded + 1
                        if debug is not None:
                            print("add", hash, "with", path)
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
                    ncreat = ncreat + 1
                    if debug is not None:
                        print("create hash", hash, "for", path)
                    #
                    # First time we've encountered this hash- create the common link point
                    #
                    os.link(path, file)
        # restore any timestamps to the top directory
        os.utime(topdir, (topstat.st_mtime, topstat.st_atime))

    for (dirpath, dirnames, filenames) in os.walk(dbdir):
        for f in filenames:
            path = os.path.join(dirpath, f)
            stat = os.stat(path)
            if stat.st_nlink == 1:
                nremvd = nremvd + 1
                if debug is not None:
                    print(path, "has only one link so removing")
                os.unlink(path)

    print(nadded, "paths added to existing hash files")
    print(ncreat, "new hashes created")
    print(nremvd, "orphaned hash files removed")
    print(nskipd, "top directories skipped")
