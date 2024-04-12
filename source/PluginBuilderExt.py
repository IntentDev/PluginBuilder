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
		self.settingsDat = self.builderComp.op('settings')

		self.config = configparser.ConfigParser()
		self.config.read_string(self.settingsDat.text)
		self.user_home = os.environ.get('USERPROFILE', os.environ.get('HOME', ''))

		self.on_par_value_change_map = {
			'Outputto': self.onOutputto,
		}

		self.on_par_pulse_map = {
			'Createplugin': self.create_plugin,
			'Buildplugin': self.build_plugin,
			'Compileplugin': self.compile_plugin,
		}

		self.template_map = {
			'BasicCHOP': 		   {'type': 'CHOP', 'replace': 'BasicCHOP', 		  'assemble_cmake': self.assemble_cmake_text_basic},
			'CHOPWithPythonClass': {'type': 'CHOP', 'replace': 'CHOPWithPythonClass', 'assemble_cmake': self.assemble_cmake_text_basic},
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

		if self.start_subprocess():
			self.build_plugin()

		self.loader_op = self.ownerComp.op('loader')


	def __del__(self):
		"""Destructor that calls the CloseSubprocess method."""
		self.CloseSubprocess()

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
		return f"{self.plugin_projects_dir}/{self.ownerComp.par.Pluginname.eval()}"
	
	@property
	def plugin_dir(self):
		return f"{self.plugins_dir}/{self.ownerComp.par.Pluginname.eval()}"

	@property
	def PluginBuilderDir(self):
		return self.get_path('Paths', 'PluginBuilderDir')
	
	@property
	def source_dir(self):
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
	
	def get_path(self, section, key):
		return self.config.get(section, key).replace('${USER_PATH}', self.user_home)
	
	############## Methods ########################################################################
 
	def create_plugin(self):
		"""Creates a new plugin project and configure builder."""

		name = self.ownerComp.par.Pluginname.eval()
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
			with open(f"{self.template_dir}/{template_name}/CMakeLists.txt", 'r') as f:
				cmake_text = f.read()
			
			cmake_text = template_info.get('assemble_cmake')()
			cmake_text = cmake_text.replace('PLUGIN_NAME', self.ownerComp.par.Pluginname.eval())

			with open(f"{self.working_dir}/CMakeLists.txt", 'w') as f:
				f.write(cmake_text)

			os.makedirs(f"{self.working_dir}/source")
			template_replace_name = template_info.get('replace')

			for file_name in os.listdir(f"{self.template_dir}/{template_name}/source"):
				with open(f"{self.template_dir}/{template_name}/source/{file_name}", 'r') as f:
					text = f.read()
				
				text = text.replace(template_replace_name, self.ownerComp.par.Pluginname.eval())
				file_name = file_name.replace(template_replace_name, self.ownerComp.par.Pluginname.eval())

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
		
	def create_plugin_loader(self, plugin_type):
		"""Creates a new plugin loader."""

		children = self.ownerComp.findChildren(name='^builder', depth=1)
		for child in children:
			if child.name != self.ownerComp.name:
				child.destroy()

		loader_op_info = self.loader_op_map.get(plugin_type)

		in_op = self.ownerComp.create(loader_op_info.get('in'), 'in1')
		self.loader_op = self.ownerComp.create(loader_op_info.get('loader'), 'loader')
		out_op = self.ownerComp.create(loader_op_info.get('out'), 'out1')

		in_op.nodeX = -200
		self.loader_op.nodeX = 0
		out_op.nodeX = 200

		in_op.outputConnectors[0].connect(self.loader_op.inputConnectors[0])
		self.loader_op.outputConnectors[0].connect(out_op.inputConnectors[0])

		self.loader_op.par.unloadplugin = True
		self.loader_op.par.plugin = f"{self.plugin_dir}/{self.ownerComp.par.Pluginname.eval()}.dll"
		self.loader_op = self.loader_op

		pass

	def assemble_cmake_text_basic(self):
		cmake_text = CMakeBlocks.start_block + CMakeBlocks.project_block + CMakeBlocks.core_block
		return cmake_text
	
	def assemble_cmake_text_cuda(self):
		cmake_text = CMakeBlocks.start_block + CMakeBlocks.cuda_project_block + CMakeBlocks.core_block + CMakeBlocks.cuda_block
		return cmake_text

	def build_plugin(self):
		"""Builds the plugin project."""
		
		print(f"Building {self.ownerComp.par.Pluginname.eval()}...")
		if not os.path.exists(self.working_dir):
			raise FileNotFoundError(f"Directory {self.working_dir} does not exist.")
		
		self.SendCommand(self.cmake_build_cmd)

	def compile_plugin(self):
		print(f"Compiling {self.ownerComp.par.Pluginname.eval()}...")
		self.SendCommand(self.cmake_build_plugin_cmd)

	def BuildAndCompile(self):
		self.build_plugin()
		self.compile_plugin()

		
	############## Par Callbacks ##################################################################
	
	def OnParValueChange(self, par, prev):
		if par.name in self.on_par_value_change_map:
			self.on_par_value_change_map[par.name](par.eval(), prev)

	def OnParPulse(self, par):
		if par.name in self.on_par_pulse_map:
			
			self.on_par_pulse_map[par.name]()

	def onOutputto(self, value, prev):
		self.CloseSubprocess()
		self.start_subprocess()


	############## File Callbacks #################################################################
 
	def OnPluginUpdate(self):
		"""copy the plugin to the plugin directory"""

		if self.loader_op is None:
			return
		
		self.loader_op.par.unloadplugin = True
		self.loader_op.cook(force=True)

		build_dir = f"{self.working_dir}/build"
		plugin_name = self.ownerComp.par.Pluginname.eval()
		build_path = f"{build_dir}/{plugin_name}.dll"
		plugin_path = f"{self.plugin_dir}/{plugin_name}.dll"

		if os.path.exists(build_path):
			# copy the plugin to the plugin directory
			shutil.copyfile(build_path, plugin_path)

		self.loader_op.par.plugin = plugin_path
		self.loader_op.par.unloadplugin = False

		



	############## Subprocess #####################################################################

	def start_subprocess(self, append_cmd=None):
		"""Starts a subprocess and reads its output."""

		# check if directory exists
		if not os.path.exists(self.working_dir):
			return False

		mode = self.ownerComp.par.Outputto.eval()

		cmd = self.start_subprocess_base_cmd

		if append_cmd is not None:
			cmd.append('&&')
			if type(append_cmd) == list:
				cmd.extend(append_cmd)
			else:
				cmd.append(append_cmd)
			
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
				cwd = 'test'
			)

			self.queue = queue.Queue()
			self.output_thread = threading.Thread(target=self._output_reader)
			self.output_thread.start()

			run("args[0].PrintOutput()", self.ownerComp, delayFrames=30)

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
		
		# run("args[0].PrintOutput()", self.ownerComp, delayFrames=30)

	def GetOutput(self):
		"""Retrieves available output from the subprocess."""
		output_lines = []
		while not self.queue.empty():
			output_lines.append(self.queue.get_nowait())
		return output_lines
	
	def PrintOutput(self):
		"""Prints available output from the subprocess."""
		output_lines = self.GetOutput()
		for line in output_lines:
			print(line, end='')

	def CloseSubprocess(self):
		"""Closes the subprocess."""
		if hasattr(self, "process"):
			if self.process.poll() is None:
				self.process.terminate() 
				self.process.kill()
				
			if self.process.stdin is not None:
				self.process.stdin.close()

			if self.process.stdout is not None:
				self.process.stdout.close()

			if self.process.stderr is not None:
				self.process.stderr.close()

		if hasattr(self, "output_thread") and self.output_thread.is_alive():
			self.output_thread.join()