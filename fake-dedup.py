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

    past = 7 * 24 * 60 * 60
    s = os.getenv("DEDUP_TIME")
    if s is not None:
        past = int(s)

    nadded = 0
    ncreat = 0
    nremvd = 0
    nskipd = 0
    npassd = 0

    os.chdir(sys.argv[1])
    dbdir =  sys.argv[1] + "/.rdlinkdb"

    try:
        os.mkdir(dbdir)
    except:
        pass

    t = int(time.time())
    cutoff = t - past
    marking = ".deduped"

    #
    # Generate a list of tuples of candidate directories and mtimes to descend
    #
    topdirs = []
    for entry in os.scandir():
        if entry.name.startswith('.') or not entry.is_dir():
            topdirs.append((entry.name, False, 0, 0))
            continue
        atime = int(entry.stat().st_mtime)
        mtime = int(entry.stat().st_mtime)
        if mtime > cutoff:
            print("skipping top directory", entry.name, "because it is too new")
            nskipd = nskipd + 1
            topdirs.append((entry.name, False, mtime, atime))
            continue
        #
        # See if we've already been here to traverse this directory.
        # If we have, unless a FORCE environment variable is set, skip
        # going through this again.
        #
        try:
            if os.getenv("DEDUP_FORCE") is None:
                filestat = os.stat(entry.name + "/" + marking)
                print("skipping top directory", entry.name, "because we've already been here")
                npassd = npassd + 1
                topdirs.append((entry.name, False, mtime, atime))
                continue
        except:
            pass
        print("Will descend into", entry.name)
        topdirs.append((entry.name, True, mtime, atime))

    for topdir, dodescend, _, _ in topdirs:
        if not dodescend:
            continue
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
                        print("add to", hash, "with", path)
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
                    print("create hash", hash, "for", path)
                    #
                    # First time we've encountered this hash- create the common link point
                    #
                    os.link(path, file)
        #
        # Mark that we've been here.
        #
        with open(topdir + "/" + marking, "wb") as f:
            pass

    for (dirpath, dirnames, filenames) in os.walk(dbdir):
        for f in filenames:
            path = os.path.join(dirpath, f)
            stat = os.stat(path)
            if stat.st_nlink == 1:
                nremvd = nremvd + 1
                print(path, "has only one link so removing")
                os.unlink(path)

    # restore any timestamps to the top directories
    for topdir, _, mtime, atime in topdirs:
        if mtime != 0:
            try:
                os.utime(topdir, (mtime, atime))
            except:
                print("unable to set time on", topdir)

    print(nadded, "paths added to existing hash files")
    print(ncreat, "new hashes created")
    print(nremvd, "orphaned hash files removed")
    print(nskipd, "top directories skipped because they were too new")
    print(npassd, "top directories skipped because we've already incorporated them")
