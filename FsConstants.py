class FsConstants:
    # File system related constants
    CLUSTER_SIZE = 1024  # Size of a cluster in bytes
    CLUSTER_COUNT = 1024  # Total number of clusters in the virtual disk
    SUPERBLOCK_CLUSTER = 0  # Cluster index for the superblock
    FAT_START_CLUSTER = 1  # Starting cluster index for the FAT
    FAT_END_CLUSTER = 4  # Ending cluster index for the FAT
    ROOT_DIR_FIRST_CLUSTER = 5  # First cluster index for the root directory
    CONTENT_START_CLUSTER = 6  # Starting cluster index for file content
    