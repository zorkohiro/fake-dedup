# fake-dedup
simple python script to perform de-duplication on mostly identical directories

This is a somewhat limited use case and not well tested. It came about
because I was keeping about 2.5TiB of nearly identical buildroot build
trees. I was hanging onto the last 6 months of builds of each commit
for the place I worked.

Now, disk space has gotten very cheap, but this had a ridiculous amount of
identical data and files and it annoyed me to consume this much. Even if
I trimmed builds and just kept the images, .git and source tree for things
older than a week, it's still a ridiculous amount of identical data.

I tried ZFS on linux for a while and got a superb amount of deduplication
with that, but for my taste ZFS is far to memory consumptive and unstable
to be trusted in linux at this time, so I went back to using XFS.

I'd had a similar problem to solve when trying to keep online every single
version of the linux kernel and had written some shell scripts to just
do hard links with the previous lkml version if the files were identical.

For this, I took a different approach and decided that md5sum was
an adequate file fingerprint mechanism. The idea here is to walk a
base directory and for each regular file in a file path, look up in a
dictionary whether it exists. If not, do an md5sum on it and put it in
the dictionary. If the md5sum name is a file under the special directory
under the base directory exist, remove the path link and replace it with
a hardlink to this file, else create one with a hard link. Rather than
250 versions of Makefile in the top of each nearly identical build tree,
one suffices with hardlinks into the directories keeping things the same.

There are obvious limitations here. The timestamp is the most obvious
one. Because there was already a policy in place of deleting build
data for builds over a week old, doing this only on week old or older
trees made sense- the weren't going to be rebuilt out of this source
tree anyway. The trees stayed populated with files and the git repo
was intact so, for forensic purposes, you could biseect some problem
to this release and look at the state of the source for it (the whole
object of this exercise, really). If you needed to rebuild and modify,
you can do that elsewhere.

There are other obvious problems. If you remove some object file or
otherwise unlink things, the dictionary gets some challenges. I've mostly
dealt with that by checking for the hash named common file for having
a single link- removing that and cleaning it from the database.
