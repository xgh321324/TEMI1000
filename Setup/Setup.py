#!/usr/bin/env python3

import argparse
import itertools
import os
import pathlib
import subprocess
import sys
import traceback


__version__ = '1.0.0'


class TAESetup(object):

	@classmethod
	def main(cls):
		sys.excepthook = cls._handle_exception

		args = cls.parse_args()
		offline = True  # check_offline()

		cls.install_dev_modules(args.index_url, offline)

		print('\nSuccessfully set up test development environment')

		input('Press enter to exit...')

	@staticmethod
	def parse_args():
		parser = argparse.ArgumentParser()
		parser.add_argument('--prep-dev', help='Download all dependencies for offline developer installation', action='store_true')
		parser.add_argument('--gen-variables', help='Generate Variables.robot file', action='store_true')
		parser.add_argument('--index-url', help='Base URL of Python Package Index', default='https://wsg.wnc.com.cn:8083/proxy.pac')

		return parser.parse_args()

	@classmethod
	def install_dev_modules(cls, indexURL, offline=False):
		cls._install_modules('development', ['../3rdParty-PythonLibs'], './DependencyLists/requirements.dev.txt', '../', indexURL, offline)

	@staticmethod
	def _install_modules(packageType, libraries, requirements, directory, indexURL, noIndex=False):
		print('\nInstalling {:s} packages'.format(packageType))

		libraries = [str(pathlib.Path(lib).resolve()) for lib in libraries]
		requirements = pathlib.Path(requirements).resolve()

		cwd = os.getcwd()
		os.chdir(directory)

		params = [sys.executable, '-m', 'pip', 'install', '-U', '--index-url', indexURL, '-r', str(requirements)]
		params.extend(itertools.chain.from_iterable(zip(itertools.repeat('--find-links'), libraries)))

		if noIndex:
			params.append('--no-index')

		try:
			subprocess.check_call(params)
		except subprocess.CalledProcessError as err:
			raise EnvironmentError('Unable to install all {:s} packages'.format(packageType)) from err

		os.chdir(cwd)

	@classmethod
	def check_dev_modules(cls):
		cls._check_modules('development', './DependencyLists/modules.dev.txt')

	@staticmethod
	def _check_modules(moduleType, requirements):
		print('\nChecking for successful {:s} module installation'.format(moduleType))

		errorOccured = False

		with open(requirements, 'r') as modulesList:
			for moduleIdentifier in modulesList:
				moduleIdentifier = moduleIdentifier.strip()

				try:
					subprocess.check_call([sys.executable, '-c', 'import {:s}'.format(moduleIdentifier.strip())])
					print('Module {:s} successfully installed'.format(moduleIdentifier))
				except subprocess.CalledProcessError:
					print('Module {:s} not installed'.format(moduleIdentifier))
					errorOccured = True

		if errorOccured:
			raise EnvironmentError('Some modules were not installed correctly')

	@staticmethod
	def _handle_exception(_type, _value, _traceback):
		print(' '.join(traceback.format_exception(_type, _value, _traceback)), file=sys.stderr)
		input('Press enter to exit...')
		sys.exit(1)

if __name__ == '__main__':
	TAESetup.main()
