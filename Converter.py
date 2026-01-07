class Converter:
    @staticmethod
    def stringToBytes(value, length):
        b = value.encode('utf-8')
        if len(b) < length:
            b += b'\x00' * (length - len(b))
        return b[:length]

    @staticmethod
    def bytesToString(byte_data):
        return byte_data.decode('utf-8', errors='ignore').rstrip('\x00')