from FsConstants import FsConstants
from Converter import Converter



class FATManager:

    
    def __init__(self, disk):
        self.disk = disk
        self.fat = self.LoadFatFromDisk()
        # Initialize reserved clusters on first load if needed
        self._initializeReservedClusters()

    def LoadFatFromDisk(self):
        entry_size = 4  
        entries_per_cluster = FsConstants.CLUSTER_SIZE // entry_size
        fatData = []
        for clusterIndex in range(FsConstants.FAT_START_CLUSTER, FsConstants.FAT_END_CLUSTER + 1):
            cluster_bytes = self.disk.read_cluster(clusterIndex)
            for i in range(0, len(cluster_bytes), entry_size):
                entry_bytes = cluster_bytes[i:i+entry_size]
                entry_str = Converter.bytesToString(entry_bytes)
                if entry_str.strip() == '':
                    entry_value = 0
                else:
                    entry_value = int(entry_str)
                fatData.append(entry_value)
        self.fat = fatData
        return fatData
    
    def flushFatToDisk(self):
        entry_size = 4 
        entries_per_cluster = FsConstants.CLUSTER_SIZE // entry_size
        for clusterIndex in range(FsConstants.FAT_START_CLUSTER, FsConstants.FAT_END_CLUSTER + 1):
            start = (clusterIndex - FsConstants.FAT_START_CLUSTER) * entries_per_cluster
            end = start + entries_per_cluster
            fat_bytes = b''.join(
                Converter.stringToBytes(str(self.fat[i]), entry_size) for i in range(start, end)
            )
            self.disk.write_cluster(clusterIndex, fat_bytes)

    def getFatEntry(self, clusterIndex):
        return self.fat[clusterIndex]
    
    def setFatEntry(self, clusterIndex, value):
        self.fat[clusterIndex] = value

    def readAllFat(self):
        return self.fat
            
    
    def writeAllFat(self, fatData):
        self.fat = fatData

    def followChain(self, startCluster):
        clusterChain = []
        if startCluster < 0 or startCluster >= FsConstants.CLUSTER_COUNT:
            raise IndexError("Cluster index out of range")
        if startCluster <= 4:
            raise ValueError("Cannot follow reserved clusters")
        currentCluster = startCluster
        
        while True:
            clusterChain.append(currentCluster)
            nextCluster = self.getFatEntry(currentCluster)
            # Break on end-of-chain (-1) or free/uninitialized (0)
            if nextCluster == -1 or nextCluster == 0:
                break
            if nextCluster < 6 or nextCluster >= FsConstants.CLUSTER_COUNT:
                break  # Invalid next cluster (reserved or out of range), treat as end
            currentCluster = nextCluster
        return clusterChain

    def allocateChain (self, count):
        allocatedClusters = []
        for i in range(FsConstants.CONTENT_START_CLUSTER, FsConstants.CLUSTER_COUNT):
            if len(allocatedClusters) == count:
                break
            if self.getFatEntry(i) == 0:
                allocatedClusters.append(i)
        if len(allocatedClusters) < count:
            raise RuntimeError("Not enough free clusters available")
        # Link clusters in the chain
        for j in range(len(allocatedClusters) - 1):
            self.setFatEntry(allocatedClusters[j], allocatedClusters[j + 1])
        # Mark end of chain
        self.setFatEntry(allocatedClusters[-1], -1)
        # Zero-initialize all allocated clusters
        for cluster in allocatedClusters:
            self.disk.write_cluster(cluster, b'\x00' * FsConstants.CLUSTER_SIZE)
        return allocatedClusters[0]  
    
    def addClustersToChain(self, startCluster, additionalCount):
        chain = self.followChain(startCluster)
        lastCluster = chain[-1]
        newClusters = self.allocateChain(additionalCount)
        self.setFatEntry(lastCluster, newClusters)
        return newClusters
        
    def freeChain(self, startCluster):
        currentCluster = startCluster
        while True:
            nextCluster = self.getFatEntry(currentCluster)
            self.setFatEntry(currentCluster, 0)  # Mark as free
            if nextCluster == -1:
                break
            currentCluster = nextCluster

    def _initializeReservedClusters(self):
        """Initialize FAT entries for reserved clusters."""
        # Cluster 0: Superblock (reserved)
        if self.getFatEntry(0) == 0:
            self.setFatEntry(0, -1)
        
        # Clusters 1-4: FAT chain
        if self.getFatEntry(1) == 0:
            self.setFatEntry(1, 2)
        if self.getFatEntry(2) == 0:
            self.setFatEntry(2, 3)
        if self.getFatEntry(3) == 0:
            self.setFatEntry(3, 4)
        if self.getFatEntry(4) == 0:
            self.setFatEntry(4, -1)
        
        # Cluster 5: Root directory (reserved)
        if self.getFatEntry(5) == 0:
            self.setFatEntry(5, -1)
        
        # Flush the initialized FAT to disk
        self.flushFatToDisk()


