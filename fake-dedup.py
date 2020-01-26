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
import shelve
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
    pd = shelve.open(dbdir + "/path2hash", flag='c')
    toplev = True

    for (dirpath, dirnames, filenames) in os.walk("."):
        if dirpath == dbdir:
            continue
        if toplev:
            for d in dirnames:
                path = os.path.join(dirpath, d)
                dirstat = os.stat(path, follow_symlinks=False)
                if dirstat.st_mtime > cutoff:
                    print ("skipping", path, "because it is too new")
                    del dirnames[dirnames.index(d)]
            toplev = False
            continue
        for f in filenames:
            path = os.path.join(dirpath, f)
            filestat = os.stat(path, follow_symlinks=False)
            try:
                hash = str(pd[path])
            except:
                hash = None
            hashstat = None
            if hash is None:
                if not S_ISREG(filestat.st_mode):
                    continue
                hash = hashlib.md5(open(path, "rb").read()).hexdigest()
                pd[path] = hash
                file = dbdir + '/' + hash
                try:
                    os.stat(dbdir + '/' + hash, follow_symlinks=False)
                except:
                    os.link(path, file, follow_symlinks=False)
                    os.utime(path, (filestat.st_mtime, filestat.st_atime))
                    print ("create hash", hash, "for", path)
                    continue

            # The hash is in the database and the hash file is present
            hashstat = os.stat(dbdir + '/' + hash, follow_symlinks=False)
            if filestat.st_ino != hashstat.st_ino:
                print ("add", path, "to", hash)
                os.unlink(path)
                os.link(dbdir + '/' + hash, path, follow_symlinks=False)
                os.utime(path, (hashstat.st_mtime, hashstat.st_atime))

    nukelist = []
    for (dirpath, dirnames, filenames) in os.walk(dbdir):
        for f in filenames:
            if f != "path2hash":
                path = os.path.join(dirpath, f)
                stat = os.stat(path, follow_symlinks=False)
                if stat.st_nlink == 1:
                    print (path, "has only one link")
                    nukelist.append(f)
                    os.unlink(path)
    for (k, v) in pd.items():
        if str(v) in nukelist:
            print("removing", k, "for hash", v)
            del pd[k]
