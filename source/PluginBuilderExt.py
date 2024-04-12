import configparser
import os
import shutil
import subprocess
import threading
import queue

cmds = {
	'build_cmake': 'cmake -B build -G Ninja',
	'build_ninja': 'ninja -C build',

	# 'build': 'ninja -C {build_dir} {target}',
	# 'clean': 'ninja -C {build_dir} clean',
	# 'install': 'ninja -C {build_dir} install',
	# 'configure': 'cmake -S {source_dir} -B {build_dir} -G "Ninja" -DCMAKE_BUILD_TYPE={build_type} -DCMAKE_INSTALL_PREFIX={install_dir}',
	# 'vcvarsall': 'cmd.exe /K {vcvarsall} x64'
}

class PluginBuilderExt:
	"""
	Creates, builds, compiles and installs plugins for TouchDesigner.

	"""
	def __init__(self, ownerComp):
		self.ownerComp = ownerComp
		self.parent = ownerComp.parent()
		self.settingsDat = ownerComp.op('settings')

		self.config = configparser.ConfigParser()
		self.config.read_string(self.settingsDat.text)
		self.user_home = os.environ.get('USERPROFILE', os.environ.get('HOME', ''))

		self.on_par_value_change_map = {
			'Outputto': self.onOutputto,
		}

		self.on_par_pulse_map = {
			'Createplugin': self.create_plugin,
			'Buildplugin': self.build_plugin,
		}

		# self.create_plugin_map = {
		# 	'CHOP': {'func': self.create_chop_plugin, 'replace': 'CPlusPlusCHOPExample'},
		# 	'TOP':  {'func': self.create_top_plugin, 'replace': 'CPlusPlusTOPExample'},
		# 	'DAT':  {'func': self.create_dat_plugin, 'replace': 'CPlusPlusDATExample'},
		# 	'SOP':  {'func': self.create_sop_plugin, 'replace': 'CPlusPlusSOPExample'},
		# }
  
		self.template_map = {
			'BasicCHOP': 		   {'type': 'CHOP', 'replace': 'BasicCHOP', 		  'func': self.create_chop_plugin},
			'CHOPWithPythonClass': {'type': 'CHOP', 'replace': 'CHOPWithPythonClass', 'func': self.create_chop_plugin},
			'CPUMemoryTOP': 	   {'type': 'TOP',  'replace': 'CPUMemoryTOP', 		  'func': self.create_top_plugin},
			'CudaTOP': 			   {'type': 'TOP',  'replace': 'CudaTOP', 			  'func': self.create_top_plugin},
			'BasicDAT': 		   {'type': 'DAT',  'replace': 'BasicDAT', 			  'func': self.create_dat_plugin},
			'SimpleShapesSOP': 	   {'type': 'SOP',  'replace': 'SimpleShapesSOP', 	  'func': self.create_sop_plugin},
		}

		self.plugin_projects_dir = 'PluginProjects'

		self.start_subprocess(self.cmake_build_cmd)

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
		cmd = f"cmake -B build -G Ninja -DPLUGIN_BUILDER_DIR={self.PluginBuilderDir} -DCMAKE_BUILD_TYPE=Release"
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
		
		if not os.path.exists(self.plugin_projects_dir):
			os.makedirs(self.plugin_projects_dir)

		if os.path.exists(self.working_dir):
			raise FileExistsError(f"Directory {self.working_dir} already exists. Rename plugin, change working directory or delete existing directory.")
		
		template_name = self.ownerComp.par.Plugintemplate.eval()
		template_info = self.template_map.get(template_name)

		os.makedirs(self.working_dir)

		try:
			with open(f"{self.template_dir}/{template_name}/CMakeLists.txt", 'r') as f:
				cmake_text = f.read()
			
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

			self.start_subprocess()
			self.build_plugin()
		
		except Exception as e:
			shutil.rmtree(self.working_dir)
			raise e
		
	# not used...
	def create_chop_plugin(self):
		pass

	def create_top_plugin(self):
		pass

	def create_dat_plugin(self):
		pass

	def create_sop_plugin(self):
		pass

	def build_plugin(self):
		"""Builds the plugin project."""
		
		print(f"Building {self.ownerComp.par.Pluginname.eval()}...")
		if not os.path.exists(self.working_dir):
			raise FileNotFoundError(f"Directory {self.working_dir} does not exist.")
		
		self.SendCommand(self.cmake_build_cmd)

		print(f"Compiling {self.ownerComp.par.Pluginname.eval()}...")
		self.SendCommand(self.cmake_build_plugin_cmd)

		



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


	############## Subprocess #####################################################################

	def start_subprocess(self, append_cmd=None):
		"""Starts a subprocess and reads its output."""

		# check if directory exists
		if not os.path.exists(self.working_dir):
			return

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