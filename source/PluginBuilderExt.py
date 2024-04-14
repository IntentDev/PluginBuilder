"""MIT License

Copyright (c) 2024 Keith Lostracco

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import configparser
import os
import shutil
import subprocess
import threading
import queue

import CMakeBlocks

class PluginBuilderExt:
	"""
	Creates, builds, compiles and installs plugins for TouchDesigner.

	"""
	def __init__(self, ownerComp):
		self.ownerComp = ownerComp
		self.builderComp = ownerComp.op('builder')
		self.parent = ownerComp.parent()
		self.SettingsDat = self.builderComp.op('settings')
		self.folder_binDat = self.builderComp.op('folder_bin')

		self.sourceComp = ownerComp.op('source')
		self.folder_sourceDat = self.sourceComp.op('sync/folder_source')

		self.CMakeListsDat = self.ownerComp.op('CMakeLists')

		self.user_home = os.environ.get('USERPROFILE', os.environ.get('HOME', ''))
		self.config = configparser.ConfigParser()
		self.config.read_string(self.SettingsDat.text)
		self.PathsValid = False
		self.PathsValid = self.check_paths()

		self.on_par_value_change_map = {
			'Outputto': self.onOutputto,
			'Pluginname': self.onPluginname,
		}

		self.on_par_pulse_map = {
			'Createplugin': self.create_plugin,
			'Buildplugin': self.build_plugin,
			'Compileplugin': self.compile_plugin,
			'Closesubprocess': self.close_subprocess,
			'Installplugin': self.install_plugin,
		}

		self.template_map = {
			'BasicCHOP': 		   {'type': 'CHOP', 'replace': 'BasicCHOP', 		  'assemble_cmake': self.assemble_cmake_text_basic},
			'CHOPWithPythonClass': {'type': 'CHOP', 'replace': 'CHOPWithPythonClass', 'assemble_cmake': self.assemble_cmake_text_python},
			'CPUMemoryTOP': 	   {'type': 'TOP',  'replace': 'CPUMemoryTOP', 		  'assemble_cmake': self.assemble_cmake_text_basic},
			'CudaTOP': 			   {'type': 'TOP',  'replace': 'CudaTOP', 			  'assemble_cmake': self.assemble_cmake_text_cuda},
			'BasicDAT': 		   {'type': 'DAT',  'replace': 'BasicDAT', 			  'assemble_cmake': self.assemble_cmake_text_basic},
			'SimpleShapesSOP': 	   {'type': 'SOP',  'replace': 'SimpleShapesSOP', 	  'assemble_cmake': self.assemble_cmake_text_basic},
		}

		self.loader_op_map = {
			'CHOP': {'loader': cplusplusCHOP, 'in': inCHOP, 'out': outCHOP},
			'TOP':  {'loader': cplusplusTOP,  'in': inTOP,  'out': outTOP},
			'DAT':  {'loader': cplusplusDAT,  'in': inDAT,  'out': outDAT},
			'SOP':  {'loader': cplusplusSOP,  'in': inSOP,  'out': outSOP},
		}

		self.plugin_projects_dir = 'PluginProjects'
		self.plugins_dir = 'Plugins'

		self.process = None
		self.queue = None
		if self.start_subprocess():
			self.build_plugin()

		self.loader_op = self.ownerComp.op('plugin_loader')
		run("args[0].RefreshDats()", self.ownerComp, delayFrames=120)


	def __del__(self):
		"""Destructor that calls the close_subprocess method."""
		self.close_subprocess()

	############## Properties #####################################################################

	@property
	def start_subprocess_base_cmd(self):
		cmd = ['cmd.exe', '/K', self.vcvarsall, 'x64']

		# add ninja to path
		cmd.append('&&')
		cmd.append(f'set PATH=%PATH%;{self.ninja_dir}')

		return cmd

	@property
	def cmake_build_cmd(self):
		config = self.ownerComp.par.Buildconfig.eval()

		cmd = f"cmake -B build -G Ninja -DPLUGIN_BUILDER_DIR={self.PluginBuilderDir} -DPLUGIN_DIR={self.plugin_dir} -DCMAKE_BUILD_TYPE={config}"
		return cmd
	
	@property
	def cmake_clean_cmd(self):
		cmd = f"ninja -C build clean"
		return cmd
	
	@property
	def cmake_build_plugin_cmd(self):
		cmd = f"ninja -C build"
		return cmd

	@property
	def working_dir(self):
		return f"{self.plugin_projects_dir}/{self.Pluginname}"
	
	@property
	def plugin_dir(self):
		return f"{self.plugins_dir}/{self.Pluginname}"
	
	@property
	def Pluginname(self):
		return self.ownerComp.par.Pluginname.eval()
	
	@property
	def CMakeListsPath(self):
		return f"{self.working_dir}/CMakeLists.txt"
	
	@property
	def CMakeListsExists(self):
		return os.path.exists(self.CMakeListsPath)
	
	@property
	def build_config(self):
		return self.ownerComp.par.Buildconfig.eval()

	@property
	def PluginBuilderDir(self):
		return self.get_path('Paths', 'PluginBuilderDir')
	
	@property
	def SourceDir(self):
		return f"{self.working_dir}/source"
	
	@property
	def ninja_dir(self):
		return self.get_path('Paths', 'NinjaDir')
	
	@property
	def template_dir(self):
		return f"{self.PluginBuilderDir}/templates"
	
	@property
	def vcvarsall(self):
		return self.get_path('Paths', 'VCVarsall')
	
	@property
	def CurrentBinDir(self):
		return f"PluginProjects/{self.Pluginname}/build/bin/{self.build_config}"
	
	@property
	def PluginPath(self):	
		return f"{self.plugin_dir}/{self.Pluginname}.dll"
	
	@property
	def build_path(self):
		return f"{self.CurrentBinDir}/{self.Pluginname}.dll"

	@property
	def CompileOnUpdate(self):
		return self.ownerComp.par.Compileonupdate.eval()
	

	

	
	############## External Methods ###############################################################
 


	############## Internal Methods ###############################################################
 
	def get_path(self, section, key):
		return self.config.get(section, key).replace('${USER_PATH}', self.user_home)

	def create_plugin(self):
		"""Creates a new plugin project and configure builder."""

		name = self.Pluginname
		if name == '':
			raise ValueError("Plugin name is empty.")
		
		if name in [o.name for o in self.parent.findChildren()]:
			raise ValueError(f"operator {name} already exists.")
		
		os.makedirs(self.plugin_projects_dir, exist_ok=True)
		
		if os.path.exists(self.working_dir):
			raise FileExistsError(f"Directory {self.working_dir} already exists. Rename plugin, change working directory or delete existing directory.")
		
		template_name = self.ownerComp.par.Plugintemplate.eval()
		template_info = self.template_map.get(template_name)

		os.makedirs(self.working_dir)

		try:
			cmake_text = template_info.get('assemble_cmake')()
			cmake_text = cmake_text.replace('PLUGIN_NAME', self.Pluginname)
			cmake_text = cmake_text.replace('__PLUGIN_TYPE__', f"'{template_info.get('type')}'")

			with open(f"{self.working_dir}/CMakeLists.txt", 'w') as f:
				f.write(cmake_text)

			os.makedirs(f"{self.working_dir}/source")
			template_replace_name = template_info.get('replace')

			for file_name in os.listdir(f"{self.template_dir}/{template_name}/source"):
				with open(f"{self.template_dir}/{template_name}/source/{file_name}", 'r') as f:
					text = f.read()

				text = text.replace(template_replace_name, self.Pluginname)

				if file_name == f"{template_replace_name}.cpp":
					text = text.replace('#__OP_TYPE__#', self.Pluginname.capitalize())
					text = text.replace('#__OP_LABEL__#', self.Pluginname)
					text = text.replace('#__OP_ICON__#', self.Pluginname[:3].upper())
					text = text.replace('#__OP_AUTHOR__#', self.config.get('PluginInfo', 'Author'))
					text = text.replace('#__OP_EMAIL__#', self.config.get('PluginInfo', 'Email'))


				file_name = file_name.replace(template_replace_name, self.Pluginname)

				with open(f"{self.working_dir}/source/{file_name}", 'w') as f:
					f.write(text)

			os.makedirs(self.plugins_dir, exist_ok=True)
			os.makedirs(f"{self.plugin_dir}", exist_ok=True)

			if self.start_subprocess():
				self.build_plugin()
				self.compile_plugin()
		
		except Exception as e:
			shutil.rmtree(self.working_dir)
			raise e
		
		self.create_plugin_loader(template_info.get('type'))

	def destroy_children(self):
		children = self.ownerComp.findChildren(depth=1)
		for child in children:
			if child.name not in ['builder', 'source', 'CMakeLists']:
				child.destroy()

	def create_plugin_loader(self, plugin_type):
		"""Creates a new plugin loader."""

		self.destroy_children()

		loader_op_info = self.loader_op_map.get(plugin_type)

		create_input_op = self.ownerComp.par.Createinputop.eval()
		if create_input_op: in_op = self.ownerComp.create(loader_op_info.get('in'), 'in1')
		self.loader_op = self.ownerComp.create(loader_op_info.get('loader'), 'plugin_loader')
		out_op = self.ownerComp.create(loader_op_info.get('out'), 'out1')

		if create_input_op: in_op.nodeX = -200
		self.loader_op.nodeX = 0
		out_op.nodeX = 200

		if create_input_op: in_op.outputConnectors[0].connect(self.loader_op.inputConnectors[0])
		self.loader_op.outputConnectors[0].connect(out_op.inputConnectors[0])

		self.loader_op.par.unloadplugin = True
		self.loader_op.par.plugin = f"{self.plugin_dir}/{self.Pluginname}.dll"
		self.loader_op = self.loader_op

		pass

	def assemble_cmake_text_basic(self):
		cmake_text = CMakeBlocks.start_block + CMakeBlocks.project_block + CMakeBlocks.core_block
		return cmake_text
	
	def assemble_cmake_text_cuda(self):
		cmake_text = CMakeBlocks.start_block + CMakeBlocks.cuda_project_block + CMakeBlocks.core_block + CMakeBlocks.cuda_block
		return cmake_text
	
	def assemble_cmake_text_python(self):
		cmake_text = CMakeBlocks.start_block + CMakeBlocks.project_block + CMakeBlocks.core_block + CMakeBlocks.python_block
		return cmake_text

	def build_plugin(self):
		"""Builds the plugin project."""
		
		print(f"Building {self.Pluginname}...")
		if not os.path.exists(self.working_dir):
			raise FileNotFoundError(f"Directory {self.working_dir} does not exist.")
		
		self.SendCommand(self.cmake_build_cmd)

	def compile_plugin(self):
		print(f"Compiling {self.Pluginname}...")
		self.SendCommand(self.cmake_build_plugin_cmd)

	def BuildAndCompile(self):
		self.build_plugin()
		self.compile_plugin()

	def RefreshDats(self):
		self.folder_binDat.cook(force=True)
		self.folder_sourceDat.cook(force=True)

		self.CMakeListsDat.cook(force=True)

	def clear_plugin_builder(self):
		self.loader_op = self.ownerComp.op('plugin_loader')
		if self.loader_op is not None:
			self.loader_op.par.unloadplugin = True
			self.loader_op.cook(force=True)

		self.destroy_children()

		if self.Pluginname != '':
			self.ownerComp.par.Pluginname = ''

	def install_plugin(self):
		"""Installs the plugin to the TouchDesigner plugins directory."""
		if not os.path.exists(self.plugin_dir):
			print(f"Folder {self.plugin_dir} does not exist.")
			return
		
		install_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'Derivative', 'Plugins')
		if not os.path.exists(install_dir):
			print(f"Folder {install_dir} does not exist.")
			return
		
		shutil.copytree(self.plugin_dir, os.path.join(install_dir, self.Pluginname))
		print(f"Plugin {self.Pluginname} installed to {install_dir}.")

	def check_paths(self):
		"""Check if paths set in the config are valid."""

		value = self.get_path('Paths', 'PluginBuilderDir')
		if not os.path.exists(value):
			raise FileNotFoundError(f"settings.ini [paths] PluginBuilderDir: {value} does not exist.")
		
		value = self.get_path('Paths', 'NinjaDir')
		if not os.path.exists(value):
			raise FileNotFoundError(f"settings.ini [paths] NinjaDir: {value} does not exist.")
		
		value = self.get_path('Paths', 'VCVarsall')
		if not os.path.exists(value):
			raise FileNotFoundError(f"settings.ini [paths] VCVarsall: {value} does not exist.")
		
		return True


	############## Par Callbacks ##################################################################
	
	def OnParValueChange(self, par, prev):
		if par.name in self.on_par_value_change_map:
			self.on_par_value_change_map[par.name](par.eval(), prev)

	def OnParPulse(self, par):
		if par.name in self.on_par_pulse_map:
			
			self.on_par_pulse_map[par.name]()

	def onOutputto(self, value, prev):
		self.close_subprocess()
		self.start_subprocess()

	def onPluginname(self, value, prev):
		if value == '':
			self.clear_plugin_builder()
		elif os.path.exists(self.CMakeListsPath):
			with open(self.CMakeListsPath, 'r') as f:
				first_line = f.readline()
			if first_line.startswith('#'):
				info = None
				try:
					info = eval(first_line[2:])
				except:
					pass
				if info is not None:
					plugin_type = info.get('plugin_type')
					if plugin_type is not None:
						print("Loading PluginProject:", f"{self.Pluginname}...", f"Type: {plugin_type}")
						self.create_plugin_loader(plugin_type)
						self.start_subprocess()
						self.ownerComp.cook(force=True, recurse=True)
						return

			

		self.loader_op = self.ownerComp.op('plugin_loader')
		if self.loader_op is not None:
			self.loader_op.par.unloadplugin = True
			self.loader_op.cook(force=True)

		self.RefreshDats()
		


	############## File Callbacks #################################################################
 
	def OnPluginUpdate(self):
		"""copy the plugin to the plugin directory"""

		if self.loader_op is None or self.Pluginname == '':
			return
		
		print(f"Reloading {self.Pluginname}...")
		
		self.loader_op.par.unloadplugin = True
		self.loader_op.cook(force=True)

		plugin_name = self.Pluginname
		build_path = self.build_path
		plugin_path = f"{self.plugin_dir}/{plugin_name}.dll"

		if not os.path.exists(build_path):
			print(f"File {build_path} does not exist.")
			return
		
		if not os.path.exists(self.plugin_dir):
			os.makedirs(self.plugin_dir)

		shutil.copyfile(build_path, plugin_path)

		if os.path.exists(plugin_path):
			self.loader_op.par.plugin = plugin_path
			self.loader_op.par.unloadplugin = False

	def OnSourceUpdate(self):
		# self.BuildAndCompile()
		self.compile_plugin()


	def OnCMakeListsUpdate(self):
		"""Update the CMakeLists.txt file."""

		if not os.path.exists(self.CMakeListsPath):
			print(f"File {self.CMakeListsPath} does not exist.")
			return

		self.build_plugin()

		



	############## Subprocess #####################################################################

	def start_subprocess(self):
		"""Starts a subprocess and reads its output."""

		# check if directory exists
		if not os.path.exists(self.working_dir):
			return False

		mode = self.ownerComp.par.Outputto.eval()
		cmd = self.start_subprocess_base_cmd

		if mode == 'TOUCH_TEXT_CONSOLE':
			self.process = subprocess.Popen(
				cmd,
				stdin=subprocess.PIPE,
				text=True,
				shell=True,
				cwd = self.working_dir
			)
		else:
			self.process = subprocess.Popen(
				cmd,
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE, 
				text=True,
				shell=True,
				bufsize=1,  # Line-buffered
				cwd = self.working_dir
			)

			self.queue = queue.Queue()
			self.output_thread = threading.Thread(target=self._output_reader)
			self.output_thread.start()

		return True

	def _output_reader(self):
		"""Reads output from the subprocess and stores it in a queue."""
		for line in self.process.stdout:
			self.queue.put(line)
		self.process.stdout.close()

	def SendCommand(self, command):
		"""Sends a command to the subprocess."""

		if self.process.poll() is None:  # Check if process is still running
			self.process.stdin.write(command + '\n')
			self.process.stdin.flush()
		else:
			raise Exception("Subprocess is not running.")

	def CheckAndPrintOutput(self):
		if self.queue is None or self.queue.empty():
			return
		self.PrintOutput()

	def GetOutput(self):
		"""Retrieves available output from the queue."""
		output_lines = []
		while not self.queue.empty():
			output_lines.append(self.queue.get_nowait())
		return output_lines
	
	def PrintOutput(self):
		output_lines = self.GetOutput()

		for line in output_lines:
			print(line, end='')

	def close_subprocess(self):
		
		if self.process is not None:

			print("Closing subprocess...")
			if self.process.poll() is None:  # Check if process is still running

				if self.process.stdin is not None:
					self.process.stdin.close()

				if self.process.stdout is not None:
					self.process.stdout.close()

				if self.process.stderr is not None:
					self.process.stderr.close()

				self.process.terminate() 
				del(self.process)
				self.process = None
				


		if hasattr(self, "output_thread") and self.output_thread.is_alive():
			self.output_thread.join()