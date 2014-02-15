#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010; Arne Babenhauserheide

"""Waffle iron - creates waffles :)

- http://draketo.de/proj/waffles/

TODO: Differenciate sourcetree and packages: sourcetree as dir in wafdir, packages in subdir packages. 
"""

__license__ = """
This license only applies to the waffle part of the code,
which ends with
### Waffle Finished ###

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.

3. The name of the author may not be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR "AS IS" AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""

import os, sys, optparse, getpass, re, binascii
if sys.hexversion<0x204000f: raise ImportError("Waffle requires Python >= 2.4")
try:
	from hashlib import md5
except:
	from md5 import md5 # for python < 2.5

if 'PSYCOWAF' in os.environ:
	try:import psyco;psyco.full()
	except:pass

VERSION="0.1"
REVISION="x"
INSTALL="x"
cwd = os.getcwd()
join = os.path.join
HOME = os.path.expanduser('~')

WAF='waffle' #: the default name of the executable
WAFFLE='waffle' #: the default name of the dir with the sources (prepended with s when unpacked)
WAFFLE_MAKER='waffle_maker.py'

def parse_cmdline_args():
	"""@return: opts, args; opts are parsed"""
	# parse commandline arguments.
	parser = optparse.OptionParser()
	parser.add_option("-o", "--filename", 
			  help="Set the output filename", default="waffle.py", metavar="OUTPUT_FILE")
	parser.add_option("-p", "--package", action="append", dest="packages",
		  help="Package folder to include (can be used multiple times)", metavar="PACKAGE_FOLDER")
	parser.add_option("-m", "--module", action="append", dest="modules", 
			  help="Python module to include (can be used multiple times)", metavar="module_to_include.py")
	parser.add_option("-s", "--script", 
			  help="Execute this script", default="run.py", metavar="script_to_run.py")
	parser.add_option("--unpack-only", action="store_true", 
			  help="only unpack the tar.bz2 data, but don't execute anything.", default=False)
	opts, args = parser.parse_args()
	if opts.modules is None:
		opts.modules = []
	if opts.packages is None:
		opts.packages = []
			      
	return opts, args

def b(x):
	return x

if sys.hexversion>0x300000f:
	WAF='waffle3'
	def b(x):
		return x.encode()

def err(m):
	print(('\033[91mError: %s\033[0m' % m))
	sys.exit(1)

def get_waffle_data():
	f = open(sys.argv[0],'r')
	c = "corrupted waf (%d)"
	while True:
		line = f.readline()
		if not line: err("no data")
		if line.startswith('#==>'):
			txt = f.readline()
			if not txt: err("wrong data: data-line missing")
			if not f.readline().startswith('#<=='): err("wrong data: closing line missing")
			return txt

def unpack_wafdir(txt, zip_type="bz2"):
	"""@param txt: The compressed data"""
	if not txt: err(c % 3)
	if sys.hexversion>0x300000f:
		txt = binascii.a2b_base64(eval("b'" + txt[1:-1] + r"\n'"))
	else: 
		txt = binascii.a2b_base64(txt[1:])

	# select the target folder
	import shutil, tarfile

	s = '.%s-%s-%s'
	if sys.platform == 'win32': s = s[1:]

	## Firstoff we we select some possible folders, to be tested one after the other (with the appropriate precautions).
	## For the sake of readability we first note the different options here.
	#: The home folder as the best option (if the user has a writeable home)
	dirhome = join(HOME, s % (WAF, VERSION, REVISION))
	# the scripts dir
	name = sys.argv[0]
	base = os.path.dirname(os.path.abspath(name))
	#: As second option use the folder where the script resides (if writeable by us - and not yet taken, which could be, if another user started the script). 
	dirbase = join(base, s % (WAF, VERSION, REVISION), getpass.getuser())
	#: tmp as last resort
	dirtmp = join("/tmp", getpass.getuser(), "%s-%s-%s" % (WAF, VERSION, REVISION))

	def prepare_dir(d):
		"""create the needed folder"""
		os.makedirs(join(d, WAFFLE))

	def check_base(d):
		"""Check the dir in which the script resides.

		Only use the dir, if it belongs to us. If we can’t trust the scripts dir, we’re fragged anyway (someone could just tamper directly with the script itself - or rather: could compromise anything we run)."""
		prepare_dir(d)
		return d

	def check_tmp(d):
		"""Check the tmp dir - always remove the dir before startup.

		This kills the caching advantage, but is necessary for security reasons (else someone could create a compromised dir in tmp and chmod it to us)."""
		# last resort: tmp
		if os.path.exists(d):
			try: shutil.rmtree(d)
			except OSError: err("Can't remove the previously existing version in /tmp - executing would endanger your system")
			try: 
				prepare_dir(d)
				return d
			except OSError: err("Cannot unpack waf lib into %s\nMove waf into a writeable directory" % dir)

	## Now check them. 
	# first check: home
	try:
		d = dirhome
		prepare_dir(d)
	except OSError:
		# second check: base
		if base.startswith(HOME) or sys.platform == 'win32':
			try:
				d = check_base(dirbase)
			except OSError:
				d = check_tmp(dirtmp)
		else: d = check_tmp(dirtmp)

	## Now unpack the tar.bz2 stream into the chosen dir. 
	os.chdir(d)
	if zip_type == 'bz2': 
		tmp = 't.tbz2'
	elif zip_type == 'gz':
		tmp = 't.gz'
	t = open(tmp,'wb')
	t.write(txt)
	t.close()

	try:
		t = tarfile.open(tmp)
	# watch out for python versions without bzip2
	except:
		try: 
			os.system('bunzip2 t.bz2')
			t = tarfile.open('t')
		except:
			# if it doesn’t work, go back and remove the garbage we created.
			try: 
				os.unlink(tmp)
			except OSError: pass
			os.chdir(cwd)
			try: shutil.rmtree(d)
			except OSError: pass
			err("Waf cannot be unpacked, check that bzip2 support is present")

	for x in t:
		t.extract(x)
	t.close()
	os.unlink(tmp)


	#if sys.hexversion>0x300000f:
		#sys.path = [join(d, WAFFLE)] + sys.path
		#import py3kfixes
		#py3kfixes.fixdir(d)

	os.chdir(cwd)
	return join(d, WAFFLE)


def make_waffle(base_script="waffle_maker.py", packages=[], modules=[], folder=WAFFLE, executable="run.py", target="waffle.py", zip_type="bz2"):
	"""Create a waf-like waffle from the base_script (make_waffle.py), the folder and a python executable (appended to the end of the waf-light part)."""
	print("-> preparing waffle")
	mw = 'tmp-waf-'+VERSION

	import tarfile, re, shutil

	if zip_type not in ['bz2', 'gz']:
		zip_type = 'bz2'

	# copy all modules and packages into the build folder
	if not os.path.isdir(folder):
		os.makedirs(folder)
	
	for i in modules + packages:
		if i.endswith(os.path.sep): 
			i = i[:-1]
		if os.path.isdir(i) and not os.path.isdir(join(folder, i.split(os.path.sep)[-1])):
			shutil.copytree(i, join(folder, i.split(os.path.sep)[-1]))
		elif os.path.isfile(i): 
			shutil.copy(i, folder)

	#open a file as tar.[extension] for writing
	tar = tarfile.open('%s.tar.%s' % (mw, zip_type), "w:%s" % zip_type)
	tarFiles=[]

	def all_files_in(folder): 
		"""Get all paths of files inside the folder."""
		filepaths = []
		walked = [i for i in os.walk(folder)]
		for base, dirs, files in walked:
		    filepaths.extend([os.path.join(base, f) for f in files])
		return filepaths
		
	files = [f for f in all_files_in(folder) if not f.endswith(".pyc") and not f.endswith(".pyo") and not "/." in f]

	for x in files:
		tar.add(x)
	tar.close()

	# first get the basic script which sets up the path
	f = open(base_script, 'r')
	code1 = f.read()
	f.close()
	# make sure it doesn't do anything.
	code1.replace("__name__ == '__main__':", "__name__ == '__main__' and False:")
	# then append the code from the executable 
	if executable is not None:
		f = open(executable, 'r')
		code1 += f.read()
		f.close()

	# now store the revision unique number in waf
	#compute_revision()
	#reg = re.compile('^REVISION=(.*)', re.M)
	#code1 = reg.sub(r'REVISION="%s"' % REVISION, code1)

	prefix = ''
	#if Build.bld:
	#	prefix = Build.bld.env['PREFIX'] or ''

	reg = re.compile('^INSTALL=(.*)', re.M)
	code1 = reg.sub(r'INSTALL=%r' % prefix, code1)
	#change the tarfile extension in the waf script
	reg = re.compile('bz2', re.M)
	code1 = reg.sub(zip_type, code1)

	f = open('%s.tar.%s' % (mw, zip_type), 'rb')
	cnt = f.read()
	f.close()

	# the REVISION value is the md5 sum of the binary blob (facilitate audits)
	m = md5()
	m.update(cnt)
	REVISION = m.hexdigest()
	reg = re.compile('^REVISION=(.*)', re.M)
	code1 = reg.sub(r'REVISION="%s"' % REVISION, code1)
	f = open(target, 'w')
	f.write(code1)
	f.write('#==>\n')
	data = str(binascii.b2a_base64(cnt))
	if sys.hexversion>0x300000f:
		data = data[2:-3] + '\n'
	f.write("#"+data)
	f.write('#<==\n')
	f.close()

	# on windows we want a bat file for starting.
	if sys.platform == 'win32':
		f = open(target + '.bat', 'wb')
		f.write('@python -x %~dp0'+target+' %* & exit /b\n')
		f.close()

	# Now make the script executable
	if sys.platform != 'win32':
		# octal prefix changed in 3.x from 0xxx to 0oxxx. 
		if sys.hexversion>0x300000f:
			os.chmod(target, eval("0o755"))
		else:
			os.chmod(target, eval("0755"))

	# and get rid of the temporary files
	os.unlink('%s.tar.%s' % (mw, zip_type))
	shutil.rmtree(WAFFLE)
	

def test(d):
	try: 
	      os.stat(d)
	      return os.path.abspath(d)
	except OSError: pass

def find_lib():
	"""Find the folder with the modules and packages.

	@return: path to to folder."""
	name = sys.argv[0]
	base = os.path.dirname(os.path.abspath(name))

	#devs use $WAFDIR
	w=test(os.environ.get('WAFDIR', ''))
	if w: return w

	#waffle_maker.py is executed in place.
	if name.endswith(WAFFLE_MAKER):
		w = test(join(base, WAFFLE))
		# if we don’t yet have a waffle dir, just create it.
		if not w:
			os.makedirs(join(base, WAFFLE))
			w = test(join(base, WAFFLE))
		if w: return w
		err("waffle.py requires " + WAFFLE + " -> export WAFDIR=/folder")

	d = "/lib/%s-%s-%s/" % (WAF, VERSION, REVISION)
	for i in [INSTALL,'/usr','/usr/local','/opt']:
		w = test(i+d)
		if w: return w

	# first check if we can use HOME/s,
	# if not, check for s (allowed?)
	# then for /tmp/s (delete it, if it already exists,
	# else it could be used to smuggle in malicious code)
	# and finally give up. 
	
	#waf-local
	s = '.%s-%s-%s'
	if sys.platform == 'win32': s = s[1:]
	# in home
	d = join(HOME, s % (WAF, VERSION, REVISION), WAFFLE)
	w = test(d)
	if w: return w

	# in base
	if base.startswith(HOME):
		d = join(base, s % (WAF, VERSION, REVISION), WAFFLE)
		w = test(d)
		if w: return w
	# if we get here, we didn't find it.
	return None


wafdir = find_lib()
if wafdir is None: # no existing found
	txt = get_waffle_data() # from this file
	if txt is None and __name__ == "__main__": # no waffle data in file
		opts, args = parse_cmdline_args()
		make_waffle(packages=opts.packages, modules=opts.modules, executable=opts.script)
	else: 
		wafdir = unpack_wafdir(txt)
	
elif sys.argv[0].endswith(WAFFLE_MAKER) and __name__ == "__main__": # the build script called
	opts, args = parse_cmdline_args()
	if opts.filename.endswith(WAFFLE_MAKER):
		err("Creating a script whose name ends with " + WAFFLE_MAKER + " would confuse the build script. If you really want to name your script *" + WAFFLE_MAKER + " you need to adapt the WAFFLE_MAKER constant in " + WAFFLE_MAKER + " and rename " + WAFFLE_MAKER + " to that name.")
	make_waffle(packages=opts.packages, modules=opts.modules, executable=opts.script, target=opts.filename)
	# since we’re running the waffle_maker, we can stop here. 
	exit(0)

if wafdir is not None: 
	sys.path = [wafdir] + [join(wafdir, d) for d in os.listdir(wafdir)] + sys.path


## If called with --unpack-only, no further code is executed.
if "--unpack-only" in sys.argv:
	print(sys.argv[0], "unpacked to", wafdir)
	exit(0)

### Waffle Finished ###

