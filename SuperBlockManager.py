from FsConstants import FsConstants

class SuperBlockManager:
    def __init__(self, disk):
        self.disk = disk
        

    def read_superblock(self):
        # Read the superblock from the disk
        superblock_data = self.disk.read_cluster(FsConstants.SUPERBLOCK_CLUSTER)
        return superblock_data

    def write_superblock(self, data):
        # Write the superblock to the disk
        self.disk.write_cluster(FsConstants.SUPERBLOCK_CLUSTER, data)