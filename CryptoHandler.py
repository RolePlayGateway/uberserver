import os

import base64

from Crypto import Random
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Hash import MD5
from Crypto.Hash import SHA
from Crypto.Hash import SHA256

## needs to be imported from hashlib, libcrypto
## versions do not have a block_size member var
from hashlib import sha256 as HMAC_HASH
from hmac import HMAC as HMAC_FUNC

try:
	from Crypto.Cipher import PKCS1_OAEP as RSA_PAD_SCHEME
except ImportError:
	RSA_PAD_SCHEME = None
try:
	from Crypto.Signature import PKCS1_v1_5 as RSA_SGN_SCHEME
except ImportError:
	RSA_SGN_SCHEME = None

## needed because RSAobj::operator== fails on None
RSA_NULL_KEY_OBJ = RSA._RSAobj(None, None)



AES_KEY_BIT_SIZE = 32 * 8
AES_KEY_DIR_NAME = "./"
AES_RAW_KEY_FILE = "aes_key.dat"
AES_MSG_PAD_SIZE = 64
RSA_KEY_BIT_SIZE = 8192
RSA_KEY_FMT_NAME = "PEM"
RSA_KEY_DIR_NAME = "./"
RSA_PUB_KEY_FILE = "rsa_pub_key.pem"
RSA_PRI_KEY_FILE = "rsa_pri_key.pem"

DATA_MARKER_BYTE = "\x01"
DATA_PARTIT_BYTE = "\n"
UNICODE_ENCODING = "utf-8"

PWRD_HASH_ROUNDS = 1024 ## stretching KDF (anti-BFA)
USR_DB_SALT_SIZE =   16 ## bytes
MIN_AES_KEY_SIZE =   16 ## bytes
MIN_PASSWORD_LEN =   12 ## bytes

## hashlib.sha{1,256}
MD5LEG_HASH_FUNC = MD5.new
SHA256_HASH_FUNC = SHA256.new

GLOBAL_RAND_POOL = Random.new()


def safe_decode(s, decode_func = base64.b64decode):
	try:
		r = decode_func(s)
	except:
		## if <s> is not a base64-encoded string, then
		## it probably contains plaintext (UTF-8) data
		r = s

	return r


def encrypt_authenticate_message(aes_obj, raw_msg, add_mac):
	assert(type(raw_msg) == str)
	assert(isinstance(aes_obj, aes_cipher))

	pay = aes_obj.encrypt_encode_bytes(raw_msg)
	mac = ""

	if (add_mac):
		mac = calc_message_auth_code(pay, aes_obj.get_key())

	return (DATA_MARKER_BYTE + pay + mac + DATA_PARTIT_BYTE)

def extract_message_and_auth_code(raw_data_blob):
	if (raw_data_blob[0] != DATA_MARKER_BYTE):
		return ("", "")

	i = 1
	j = raw_data_blob.find(DATA_MARKER_BYTE, i)

	## check if a MAC is included after the payload
	if (j != -1):
		msg = raw_data_blob[i    : j]
		mac = raw_data_blob[j + 1:  ]
	else:
		msg = raw_data_blob[i: ]
		mac = ""

	return (msg, mac)


def calc_message_auth_code(msg, key, encode_func = base64.b64encode):
	## calculate crypto-checksum over msg (H((K ^ O) | H((K ^ I) | M)))
	mac = HMAC_FUNC(key, msg, HMAC_HASH)
	mac = DATA_MARKER_BYTE + encode_func(mac.digest())
	return mac

def check_message_auth_code(enc_msg, msg_mac, key, decode_func = safe_decode):
	msg_mac = decode_func(msg_mac)
	our_mac = HMAC_FUNC(key, enc_msg, HMAC_HASH)
	our_mac = our_mac.digest()
	return (our_mac == msg_mac)


def int32_to_str(n):
	assert(n >= (0      ))
	assert(n <  (1 << 32))

	s = ""
	s += "%c" % ((n >>  0) & 0xff)
	s += "%c" % ((n >>  8) & 0xff)
	s += "%c" % ((n >> 16) & 0xff)
	s += "%c" % ((n >> 24) & 0xff)

	return s

def str_to_int32(s):
	n = 0
	n += (ord(s[0]) <<  0)
	n += (ord(s[1]) <<  8)
	n += (ord(s[2]) << 16)
	n += (ord(s[3]) << 24)
	return n


def pad_str(msg, bs):
	num = bs - (len(msg) % bs)
	ext = num * chr(num)
	return (msg + ext)

def unpad_str(msg, bs):
	idx = len(msg) - 1
	cnt = ord(msg[idx: ])
	return msg[0: -cnt]


def read_file(file_name, file_mode):
	try:
		f = open(file_name, file_mode)
		s = f.read()
		f = f.close()
		return s
	except IOError:
		pass

	return ""

def write_file(file_name, file_mode, file_data):
	try:
		f = open(file_name, file_mode)
		os.fchmod(f.fileno(), 0600)
		f.write("%s" % file_data)
		f = f.close()
	except IOError:
		pass




class rsa_cipher:
	def __init__(self, key_dir = RSA_KEY_DIR_NAME):
		self.set_rnd_gen(Random.new())
		self.set_instance_keys(key_dir)
		self.set_pad_scheme(RSA_PAD_SCHEME)
		self.set_sgn_scheme(RSA_SGN_SCHEME)

	def set_rnd_gen(self, rnd_gen): self.rnd_gen = rnd_gen
	def set_pub_key(self, pub_key): self.pub_key = pub_key
	def set_pri_key(self, pri_key): self.pri_key = pri_key

	def get_pub_key(self): return self.pub_key
	def get_pri_key(self): return self.pri_key

	def sanity_test_keys(self):
		pk = (self.pri_key.publickey())
		b0 = (pk == self.pub_key)
		b1 = (pk.exportKey(RSA_KEY_FMT_NAME) == self.pub_key.exportKey(RSA_KEY_FMT_NAME))
		b2 = ((not self.pub_key.has_private()) and self.pri_key.has_private())
		return (b0 and b1 and b2)

	def set_pad_scheme(self, scheme):
		if (scheme == None):
			self.enc_pad_scheme = None
			self.dec_pad_scheme = None
		else:
			self.enc_pad_scheme = scheme.new(self.pub_key)
			self.dec_pad_scheme = scheme.new(self.pri_key)
	def set_sgn_scheme(self, scheme):
		if (scheme == None):
			self.msg_sign_scheme = None
			self.msg_auth_scheme = None
		else:
			self.msg_sign_scheme = scheme.new(self.pri_key)
			self.msg_auth_scheme = scheme.new(self.pub_key)

	def set_instance_keys(self, key_dir):
		if (key_dir == None):
			self.set_pub_key(RSA_NULL_KEY_OBJ)
			self.set_pri_key(RSA_NULL_KEY_OBJ)
			return

		if (not self.import_keys(key_dir)):
			self.generate_keys()

		assert(self.sanity_test_keys())

	def generate_keys(self, num_bits = RSA_KEY_BIT_SIZE):
		self.set_pri_key(RSA.generate(num_bits, self.rnd_gen.read))
		self.set_pub_key(self.pri_key.publickey())
		return True


	def import_key(self, key_str):
		return (RSA.importKey(key_str))

	def import_keys(self, key_dir):
		assert(len(key_dir) == 0 or key_dir[-1] == '/')

		pub_key_str = read_file(key_dir + RSA_PUB_KEY_FILE, "r")
		pri_key_str = read_file(key_dir + RSA_PRI_KEY_FILE, "r")

		if (len(pub_key_str) != 0 and len(pri_key_str) != 0):
			self.set_pub_key(self.import_key(pub_key_str))
			self.set_pri_key(self.import_key(pri_key_str))
			return True

		return False

	def export_keys(self, key_dir):
		assert(len(key_dir) != 0)
		assert(key_dir[-1] == '/')

		if (not os.path.isdir(key_dir)):
			os.mkdir(key_dir, 0700)

		write_file(key_dir + RSA_PUB_KEY_FILE, "w", self.pub_key.exportKey(RSA_KEY_FMT_NAME))
		write_file(key_dir + RSA_PRI_KEY_FILE, "w", self.pri_key.exportKey(RSA_KEY_FMT_NAME))


	## these make sure that any native unicode inputs are converted
	## to standard (UTF-8 encoded byte sequences) strings, otherwise
	## crypto operations might be undefined
	def encrypt_encode_bytes_utf8(self, raw_bytes, encode_func = base64.b64encode):
		return (self.encrypt_encode_bytes(raw_bytes.encode(UNICODE_ENCODING), encode_func))
	def decode_decrypt_bytes_utf8(self, enc_bytes, decode_func = base64.b64decode):
		return (self.decode_decrypt_bytes(enc_bytes.encode(UNICODE_ENCODING), decode_func))

	def encrypt_encode_bytes(self, raw_bytes, encode_func = base64.b64encode):
		assert(type(raw_bytes) == str)
		assert(len(raw_bytes) != 0)
		assert(self.pub_key.size() >= (len(raw_bytes) * 8))
		assert(ord(raw_bytes[0]) != 0)

		if (self.enc_pad_scheme != None):
			enc_bytes = self.enc_pad_scheme.encrypt(raw_bytes)
		else:
			## NOTE: RSAobj.encrypt() returns a tuple (!)
			enc_bytes = self.pub_key.encrypt(raw_bytes, "")[0]

		return (encode_func(enc_bytes))

	def decode_decrypt_bytes(self, enc_bytes, decode_func = base64.b64decode):
		assert(type(enc_bytes) == str)
		assert(len(enc_bytes) != 0)
		## assert((self.pri_key.size() + 1) == (len(decode_func(enc_bytes)) * 8))

		enc_bytes = decode_func(enc_bytes)

		if (self.dec_pad_scheme != None):
			dec_bytes = self.dec_pad_scheme.decrypt(enc_bytes)
		else:
			dec_bytes = self.pri_key.decrypt(enc_bytes)

		return dec_bytes


	def sign_bytes_utf8(self, msg_bytes):
		return (self.sign_bytes(msg_bytes.encode(UNICODE_ENCODING)))
	def auth_bytes_utf8(self, msg_bytes, sig_bytes):
		return (self.auth_bytes(msg_bytes.encode(UNICODE_ENCODING), sig_bytes))

	def sign_bytes(self, msg_bytes):
		assert(type(msg_bytes) == str)
		assert(len(msg_bytes) != 0)

		msg_bytes = SHA256_HASH_FUNC(msg_bytes)

		if (self.msg_sign_scheme != None):
			## scheme.sign() expects an object from Crypto.Hash
			ret = self.msg_sign_scheme.sign(msg_bytes)
		else:
			## RSAobj.sign() returns a tuple
			ret = str(self.pri_key.sign(msg_bytes.digest(), "")[0])

		assert(type(ret) == str)
		return ret

	def auth_bytes(self, msg_bytes, sig_bytes):
		assert(type(msg_bytes) == str)
		assert(type(sig_bytes) == str)
		assert(len(msg_bytes) != 0)

		msg_bytes = SHA256_HASH_FUNC(msg_bytes)

		if (self.msg_auth_scheme != None):
			## scheme.verify() expects an object from Crypto.Hash
			ret = self.msg_auth_scheme.verify(msg_bytes, sig_bytes)
		else:
			## RSAobj.verify() expects a tuple
			ret = (self.pub_key.verify(msg_bytes.digest(), (long(sig_bytes), 0L)))

		assert(type(ret) == bool)
		return ret




class aes_cipher:
	def __init__(self, key_dir = AES_KEY_DIR_NAME, padding_length = AES_MSG_PAD_SIZE):
		assert(type(key_dir) == str)
		assert((padding_length % 16) == 0)

		self.pad_length = padding_length
		self.random_gen = Random.new()
		self.khash_func = SHA256_HASH_FUNC

		self.set_instance_key(key_dir)


	def set_instance_key(self, key_dir):
		if (not self.import_key(key_dir)):
			self.set_key(self.generate_key(""))


	def generate_key(self, raw_key, key_len = AES_KEY_BIT_SIZE):
		if (len(raw_key) == 0):
			key_str = self.random_gen.read(key_len / 8)
			key_str = self.khash_func(key_str)
		else:
			key_str = self.khash_func(raw_key)

		return (key_str.digest())

	def get_key(self): return self.key_string
	def set_key(self, s): self.key_string = s


	def import_key(self, key_dir):
		assert(len(key_dir) == 0 or key_dir[-1] == '/')

		key_str = read_file(key_dir + AES_RAW_KEY_FILE, "rb")

		if (len(key_str) != 0):
			self.set_key(key_str)
			return True

		return False

	def export_key(self, key_dir):
		assert(len(key_dir) != 0)
		assert(key_dir[-1] == '/')

		if (not os.path.isdir(key_dir)):
			os.mkdir(key_dir, 0700)

		write_file(key_dir + AES_RAW_KEY_FILE, "wb", self.get_key())


	def encrypt_encode_bytes_utf8(self, raw_bytes, encode_func = base64.b64encode):
		return (self.encrypt_encode_bytes(raw_bytes.encode(UNICODE_ENCODING), encode_func))
	def decode_decrypt_bytes_utf8(self, enc_bytes, decode_func = base64.b64decode):
		return (self.decode_decrypt_bytes(enc_bytes.encode(UNICODE_ENCODING), decode_func))

	def encrypt_encode_bytes(self, raw_bytes, encode_func = base64.b64encode):
		assert(type(raw_bytes) == str)
		assert(len(raw_bytes) != 0)

		ini_vector = self.random_gen.read(AES.block_size)
		aes_object = AES.new(self.key_string, AES.MODE_CBC, ini_vector)

		pad_bytes = pad_str(raw_bytes, self.pad_length)
		enc_bytes = aes_object.encrypt(pad_bytes)

		return (encode_func(ini_vector + enc_bytes))

	def decode_decrypt_bytes(self, enc_bytes, decode_func = base64.b64decode):
		assert(type(enc_bytes) == str)
		assert(len(enc_bytes) != 0)

		enc_bytes = decode_func(enc_bytes)

		ini_vector = enc_bytes[0: AES.block_size]
		aes_object = AES.new(self.key_string, AES.MODE_CBC, ini_vector)

		dec_bytes = aes_object.decrypt(enc_bytes[AES.block_size: ])
		dec_bytes = unpad_str(dec_bytes, self.pad_length)
		return dec_bytes

