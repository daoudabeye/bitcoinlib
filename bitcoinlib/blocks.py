# -*- coding: utf-8 -*-
#
#    BitcoinLib - Python Cryptocurrency Library
#    BLOCK parsing and construction
#    © 2020 Juni - 1200 Web Development <http://1200wd.com/>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from bitcoinlib.encoding import *
from bitcoinlib.networks import Network
from bitcoinlib.transactions import transaction_deserialize, Transaction


class Block:

    def __init__(self, block_hash, version, prev_block, merkle_root, time, bits, nonce, transactions=None,
                 height=None, confirmations=None, network=DEFAULT_NETWORK):
        """
        Create a new Block object with provided parameters.

        >>> b = Block('0000000000000000000154ba9d02ddd6cee0d71d1ea232753e02c9ac6affd709', version=0x20000000, prev_block='0000000000000000000f9578cda278ae7a2002e50d8e6079d11e2ea1f672b483', merkle_root='20e86f03c24c53c12014264d0e405e014e15a02ad02c174f017ee040750f8d9d', time=1592848036, bits=387044594, nonce=791719079)
        >>> b
        <Block(0000000000000000000154ba9d02ddd6cee0d71d1ea232753e02c9ac6affd709, None, transactions: None)>

        :param block_hash: Hash value of serialized block
        :type block_hash: bytes, str
        :param version: Block version to indicate which software / BIPs are used to create block
        :type version: bytes, str, in
        :param prev_block: Hash of previous block in blockchain
        :type prev_block: bytes, str
        :param merkle_root: Merkle root. Top item merkle chain tree to validate transactions.
        :type merkle_root: bytes, str
        :param time: Timestamp of time when block was included in blockchain
        :type time: int, bytes
        :param bits: Bits are used to indicate target / difficulty
        :type bits: bytes, str, int
        :param nonce: Number used once, n-once is used to create randomness for miners to find a suitable block hash
        :type nonce: bytes, str, int
        :param transactions: List of transaction included in this block. As list of transaction objects or list of transaction IDs strings
        :type transactions: list of Transaction, list of str
        :param height: Height of this block in the Blockchain
        :type height: int
        :param confirmations: Number of confirmations for this block, or depth. Increased when new blocks are found
        :type confirmations: int
        :param network: Network, leave empty for default network
        :type network: str, Network
        """

        self.block_hash = to_bytes(block_hash)
        if isinstance(version, int):
            self.version = struct.pack('>L', version)
            self.version_int = version
        else:
            self.version = to_bytes(version)
            self.version_int = 0 if not self.version else struct.unpack('>L', self.version)[0]
        self.prev_block = to_bytes(prev_block)
        self.merkle_root = to_bytes(merkle_root)
        self.time = time
        if not isinstance(time, int):
            self.time = struct.unpack('>L', time)[0]
        if isinstance(bits, int):
            self.bits = struct.pack('>L', bits)
            self.bits_int = bits
        else:
            self.bits = to_bytes(bits)
            self.bits_int = 0 if not self.bits else struct.unpack('>L', self.bits)[0]
        if isinstance(nonce, int):
            self.nonce = struct.pack('>L', nonce)
            self.nonce_int = nonce
        else:
            self.nonce = to_bytes(nonce)
            self.nonce_int = 0 if not self.nonce else struct.unpack('>L', self.nonce)[0]
        self.transactions = transactions
        self.txs_data = None
        self.confirmations = confirmations
        self.network = network
        if not isinstance(network, Network):
            self.network = Network(network)
        self.tx_count = None
        self.page = 1
        self.limit = 0
        self.height = height
        if self.transactions and len(self.transactions) and isinstance(self.transactions[0], Transaction) \
                and self.version_int > 1:
            # first bytes of unlocking script of coinbase transaction contains block height (BIP0034)
            if self.transactions[0].inputs[0].unlocking_script:
                calc_height = struct.unpack('<L', self.transactions[0].inputs[0].unlocking_script[1:4] + b'\x00')[0]
                if height and calc_height != height:
                    raise ValueError("Specified block height is different than calculated block height according to "
                                     "BIP0034")
                self.height = calc_height

    def check_proof_of_work(self):
        """
        Check proof of work for this block. Block hash must be below target.

        This library is not optimised for mining, but you can use this for testing or learning purposes.

        >>> b = Block('0000000000000000000154ba9d02ddd6cee0d71d1ea232753e02c9ac6affd709', version=0x20000000, prev_block='0000000000000000000f9578cda278ae7a2002e50d8e6079d11e2ea1f672b483', merkle_root='20e86f03c24c53c12014264d0e405e014e15a02ad02c174f017ee040750f8d9d', time=1592848036, bits=387044594, nonce=791719079)
        >>> b.check_proof_of_work()
        True

        :return bool:
        """
        if not self.block_hash or not self.bits:
            return False
        if change_base(self.block_hash, 256, 10) < self.target:
            return True
        return False

    def __repr__(self):
        return "<Block(%s, %s, transactions: %s)>" % (to_hexstring(self.block_hash), self.height, self.tx_count)

    @classmethod
    def from_raw(cls, raw, block_hash=None, height=None, parse_transactions=False, limit=0, network=DEFAULT_NETWORK):
        """
        Create Block object from raw serialized block in bytes.

        Get genesis block:

        >>> from bitcoinlib.services.services import Service
        >>> srv = Service()
        >>> b = srv.getblock(0)
        >>> b.block_hash.hex()
        '000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f'
        
        :param raw: Raw serialize block
        :type raw: bytes
        :param block_hash: Specify block hash if known to verify raw block. Value error will be raised if calculated block hash is different than specified.
        :type block_hash: bytes
        :param height: Specify height if known. Will be derived from coinbase transaction if not provided.
        :type height: int
        :param parse_transactions: Indicate if transactions in raw block need to be parsed and converted to Transaction objects. Default is False
        :type parse_transactions: bool
        :param limit: Maximum number of transactions to parse. Default is 0: parse all transactions. Only used if parse_transaction is set to True
        :type limit: int
        :param network: Name of network
        :type network: str

        :return Block:
        """
        block_hash_calc = double_sha256(raw[:80])[::-1]
        if not block_hash:
            block_hash = block_hash_calc
        elif block_hash != block_hash_calc:
            raise ValueError("Provided block hash does not correspond to calculated block hash %s" %
                             to_hexstring(block_hash_calc))

        version = raw[0:4][::-1]
        prev_block = raw[4:36][::-1]
        merkle_root = raw[36:68][::-1]
        time = raw[68:72][::-1]
        bits = raw[72:76][::-1]
        nonce = raw[76:80][::-1]
        tx_count, size = varbyteint_to_int(raw[80:89])
        txs_data = raw[80+size:]

        # Parse coinbase transaction so we can extract extra information
        transactions = [transaction_deserialize(txs_data, network=network, check_size=False)]
        txs_data = txs_data[transactions[0].size:]

        while parse_transactions and txs_data:
            if limit != 0 and len(transactions) >= limit:
                break
            t = transaction_deserialize(txs_data, network=network, check_size=False)
            transactions.append(t)

            # t.rawtx = b''
            # traw = t.raw_hex()
            # tblock = txs_data[:t.size].hex()
            # if traw != tblock:
            #     print(t.txid)
            #     print(traw)
            #     print(tblock)
            txs_data = txs_data[t.size:]
            # TODO: verify transactions, need input value from previous txs
            # if verify and not t.verify():
            #     raise ValueError("Could not verify transaction %s in block %s" % (t.txid, block_hash))

        if parse_transactions and limit == 0 and tx_count != len(transactions):
            raise ValueError("Number of found transactions %d is not equal to expected number %d" %
                             (len(transactions), tx_count))

        block = cls(block_hash, version, prev_block, merkle_root, time, bits, nonce, transactions, height,
                    network=network)
        block.txs_data = txs_data
        block.tx_count = tx_count
        return block

    def parse_transactions(self, limit=0):
        """
        Parse raw transactions from Block, if transaction data is available in txs_data attribute. Creates
        Transaction objects in Block.transactions list

        :param limit: Maximum number of transactions to parse

        :return:
        """
        n = 0
        while self.txs_data and (limit == 0 or n < limit):
            t = transaction_deserialize(self.txs_data, network=self.network, check_size=False)
            self.transactions.append(t)
            self.txs_data = self.txs_data[t.size:]
            n += 1

    def as_dict(self):
        """
        Get representation of current Block as dictionary.

        :return dict:
        """
        return {
            'block_hash': to_hexstring(self.block_hash),
            'height': self.height,
            'version': self.version_int,
            'prev_block': None if not self.prev_block else to_hexstring(self.prev_block),
            'merkle_root': to_hexstring(self.merkle_root),
            'timestamp': self.time,
            'bits': self.bits_int,
            'nonce': self.nonce_int,
            'target': self.target_hex,
            'difficulty': self.difficulty,
            'tx_count': self.tx_count,
            'transactions': self.transactions,
            'confirmations': self.confirmations
        }

    @property
    def target(self):
        """
        Block target calculated from block's bits. Block hash must be below this target. Used to calculate
        block difficulty.

        :return int:
        """
        if not self.bits:
            return 0
        exponent = self.bits[0]
        coefficient = struct.unpack('>L', b'\x00' + self.bits[1:])[0]
        return coefficient * 256 ** (exponent - 3)

    @property
    def target_hex(self):
        """
        Block target in hexadecimal string of 64 characters.

        :return str:
        """
        if not self.bits:
            return ''
        return hex(self.target)[2:].zfill(64)

    @property
    def difficulty(self):
        """
        Block difficulty calculated from bits / target. Human readable representation of block's target.

        Genesis block has difficulty of 1.0

        >>> from bitcoinlib.services.services import Service
        >>> srv = Service()
        >>> b = srv.getblock(0)
        >>> b.difficulty
        1.0

        :return float:
        """
        if not self.bits:
            return 0
        return 0xffff * 256 ** (0x1d - 3) / self.target

    def serialize(self):
        """
        Serialize raw block in bytes.

        A block consists of a 80 bytes header:
        * version - 4 bytes
        * previous block - 32 bytes
        * merkle root - 32 bytes
        * timestamp - 4 bytes
        * bits - 4 bytes
        * nonce - 4 bytes

        Followed by a list of raw serialized transactions.

        Method will raise an error if one of the header fields is missing or has an incorrect size.

        :return bytes:
        """
        if len(self.transactions) != self.tx_count or len(self.transactions) < 1:
            raise ValueError("Block contains incorrect number of transactions, can not serialize")
        rb = self.version[::-1]
        rb += self.prev_block[::-1]
        rb += self.merkle_root[::-1]
        rb += struct.pack('>L', self.time)[::-1]
        rb += self.bits[::-1]
        rb += self.nonce[::-1]
        if len(rb) != 80:
            raise ValueError("Missing or incorrect length of 1 of the block header variables: version, prev_block, "
                             "merkle_root, time, bits or nonce.")
        rb += int_to_varbyteint(len(self.transactions))
        for t in self.transactions:
            rb += t.raw()
        return rb

    def version_bin(self):
        """
        Get the block version as binary string. Since BIP9 protocol changes are signaled by changing one of the 29
        last bits of the version number.

        >>> from bitcoinlib.services.services import Service
        >>> srv = Service()
        >>> b = srv.getblock(450001)
        >>> print(b.version_bin())
        00100000000000000000000000000010

        :return str:
        """
        return bin(self.version_int)[2:].zfill(32)

    def version_bips(self):
        """
        Extract version signaling information from the block's version number.

        The block version shows which software the miner used to create the block. Changes to the bitcoin
        protocol are described in Bitcoin Improvement Proposals (BIPs) and a miner shows which BIPs it supports
        in the block version number.

        This method returns a list of BIP version number as string.

        Example: This block uses the BIP9 versioning system and signals BIP141 (segwit)
        >>> from bitcoinlib.services.services import Service
        >>> srv = Service()
        >>> b = srv.getblock(450001)
        >>> print(b.version_bips())
        ['BIP9', 'BIP141']

        :return list of str:
        """
        bips = []
        if self.version_int >> 29 == 0b001 and self.height >= 407021:
            bips.append('BIP9')
            if self.version_int >> 0 & 1 == 1:
                bips.append('BIP68')   # BIP112, BIP113 (CSV)
            if self.version_int >> 1 & 1 == 1:
                bips.append('BIP141')  # BIP143, BIP147 (Segwit)
            if self.version_int >> 4 & 1 == 1:
                bips.append('BIP91')   # Segwit?
            if self.version_int == 0x30000000:
                bips.append('BIP109')
            mask = 0x1fffe000
            if self.version_int & mask and self.height >= 500000:
                bips.append('BIP310')   # version-rolling
        elif self.height < 500000:
            if self.version_int == 2:
                bips.append('BIP34')    # Version 2: Block Height in Coinbase
            if self.version_int == 3:
                bips.append('BIP66')    # Version 3: Relative lock-time using consensus-enforced sequence numbers
            if self.version_int == 4:
                bips.append('BIP65')    # Version 4: Introduce Checklocktimeverify
            if self.version_int == 0x30000000:
                bips.append('BIP109')   # Increase block size 2MB (rejected)
            if self.version_int == 0x20000007:
                bips.append('BIP101')   # Increase block size 8MB (rejected)

        return bips
