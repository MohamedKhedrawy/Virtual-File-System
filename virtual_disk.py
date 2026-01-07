import os
from FsConstants import FsConstants
from SuperBlockManager import SuperBlockManager
from FATManager import FATManager

class VirtualDisk:

    def __init__(self):
        self.disk_size = 0
        self.disk_path = None
        self.disk_file = None
        self.is_open = False
        self.fat_manager = None
        self.sb_manager = None

    # ---------------------------------------------------------
    # Initializes the virtual disk.
    # - If the disk file exists, opens it for read/write access.
    # - If it does not exist and create_if_missing is True, creates a new empty virtual disk file.
    # - Raises an error if the disk is already initialized or if the file cannot be opened/created.
    #
    # Parameters:
    #   path (str): The file path of the virtual disk.
    #   create_if_missing (bool): Whether to create the file if it doesn't exist (default: True).
    #
    # Raises:
    #   RuntimeError: If the disk is already initialized.
    #   FileNotFoundError: If the disk file is missing and creation is disabled.
    #   IOError: If the disk cannot be opened or created due to I/O issues.
    # ---------------------------------------------------------
    def initialize(self, path, create_if_missing=True):
        if self.is_open:
            raise RuntimeError("Disk is already initialized")

        self.disk_path = path
        self.disk_size = FsConstants.CLUSTER_COUNT * FsConstants.CLUSTER_SIZE



        try:
            is_new_disk = not os.path.exists(self.disk_path)
            if is_new_disk:
                if create_if_missing:
                    self._create_empty_disk(self.disk_path)
                else:
                    raise FileNotFoundError("Couldn't find the specified disk path")
            
            # Always open the disk file
            self.disk_file = open(self.disk_path, "r+b")
            self.is_open = True
            
            # Initialize managers after disk file is open
            self.fat_manager = FATManager(self)
            self.sb_manager = SuperBlockManager(self)
            
            # Load FAT only if disk already existed
            if not is_new_disk:
                try:
                    self.fat_manager.LoadFatFromDisk()
                except Exception as ex:
                    print(f"Warning: Failed to load FAT from disk: {ex}")
            else:
                # Only initialize clusters for brand new disks
                for cluster_index in range(FsConstants.CLUSTER_COUNT):
                    if cluster_index == FsConstants.SUPERBLOCK_CLUSTER:
                        self.sb_manager.write_superblock(data=bytes([0x00] * FsConstants.CLUSTER_SIZE))
                    elif cluster_index >= FsConstants.CONTENT_START_CLUSTER:
                        self.write_cluster(cluster_index)
                    elif cluster_index >= FsConstants.FAT_START_CLUSTER and cluster_index <= FsConstants.FAT_END_CLUSTER:
                        self.write_cluster(cluster_index, data=bytes([0x00]) * FsConstants.CLUSTER_SIZE)


        except Exception as ex:
            self.is_open = False
            raise IOError(f"Failed to open disk: {ex}") from ex

    # ---------------------------------------------------------
    # Creates a new empty virtual disk file.
    # - The file is filled with zeroed clusters, each of size CLUSTER_SIZE.
    # - The total file size equals CLUSTERS_NUMBER × CLUSTER_SIZE.
    # - Ensures the disk structure is properly initialized before use.
    #
    # Parameters:
    #   path (str): The path where the disk file should be created.
    #
    # Raises:
    #   IOError: If disk creation fails due to file or I/O issues.
    # ---------------------------------------------------------
    def _create_empty_disk(self, path):
        f = None
        try:
            f = open(path, "wb")
            empty_cluster = bytes(FsConstants.CLUSTER_SIZE)
            for _ in range(FsConstants.CLUSTER_COUNT):
                f.write(empty_cluster)
            f.flush()
        except Exception as ex:
            raise IOError(f"Failed to create disk file: {ex}") from ex
        finally:
            if f is not None:
                f.close()
    
    # ---------------------------------------------------------
    #Write to cluster
    def write_cluster(self, cluster_index, data=None, data_offset=0, ):
        if not self.is_open:
            raise RuntimeError("Disk is not initialized")

        if not (0 <= cluster_index < FsConstants.CLUSTER_COUNT):
            raise IndexError("Cluster index out of range")
        
        if data is None:
            data = bytes([0x00]) * FsConstants.CLUSTER_SIZE
        else:
            data = bytes(data)
            # Pad short writes to full CLUSTER_SIZE so old data is fully overwritten
            if len(data) < FsConstants.CLUSTER_SIZE:
                data = data + bytes([0x00]) * (FsConstants.CLUSTER_SIZE - len(data))
        
        if len(data) > FsConstants.CLUSTER_SIZE:
            raise ValueError("Data exceeds cluster size")

        try:
            self.disk_file.seek(cluster_index * FsConstants.CLUSTER_SIZE)
            self.disk_file.write(data)
            self.disk_file.flush()
        except Exception as ex:
            raise IOError(f"Failed to write to cluster: {ex}") from ex


    # ---------------------------------------------------------
    # Read cluster
    # Reads data from a specified cluster index.
    def read_cluster(self, cluster_index):
        if not self.is_open:
            raise RuntimeError("Disk is not initialized")

        if not (0 <= cluster_index < FsConstants.CLUSTER_COUNT):
            raise IndexError("Cluster index out of range")

        try:
            self.disk_file.seek(cluster_index * FsConstants.CLUSTER_SIZE)
            data = self.disk_file.read(FsConstants.CLUSTER_SIZE)
            return data
        except Exception as ex:
            raise IOError(f"Failed to read from cluster: {ex}") from ex
        
    # ---------------------------------------------------------
    def getDiskSize(self):
        return self.disk_size
    
    # ---------------------------------------------------------
    def getDiskFreeSpaceClusters(self):
        count = 0
        # Check FAT to find free clusters (entries marked as 0)
        for i in range(FsConstants.CONTENT_START_CLUSTER, FsConstants.CLUSTER_COUNT):
            if self.fat_manager.getFatEntry(i) == 0:
                count += 1
        return count
    
    # ---------------------------------------------------------
    def getDiskFreeSpacePercent(self):
        free_clusters = self.getDiskFreeSpaceClusters()
        total_content_clusters = FsConstants.CLUSTER_COUNT - FsConstants.CONTENT_START_CLUSTER
        if total_content_clusters == 0:
            return 0.0
        percent = (free_clusters / total_content_clusters) * 100.0
        return round(percent, 2)
    # ---------------------------------------------------------
    def getDiskFreeSpacebytes(self):
        free_clusters = self.getDiskFreeSpaceClusters()
        return free_clusters * FsConstants.CLUSTER_SIZE
        
    # ---------------------------------------------------------
    # Closes the virtual disk file.
    def close(self):
        if self.is_open and self.disk_file:
            self.disk_file.flush()
            self.disk_file.close()
            self.is_open = False
            FATManager


