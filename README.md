# PluginBuilder

PluginBuilder is a development tool designed to accelerate the process of building, developing, and compiling plugins for TouchDesigner. It facilitates real-time, script-like editing of plugins by leveraging CMake and Ninja for rapid compilation. The system automatically recompiles and reloads the plugin upon any source changes, with extremely fast build times that typically are under a second.

## Requirements

- **TouchDesigner**: Version 2023.11600 or newer, with a commercial or pro license.
- **Visual Studio**: C++ development tools installed.
- **CMake**: Installed and added to the system or user PATH.
- **Ninja**: Installed and recognized in the system PATH.
- **OS**: Windows only at this time.
   ### Optional
   - In order to build and compile plugins that depend on Cuda you'll need to install Cuda Toolkit. Currently TD uses [CUDA 11.8](https://developer.nvidia.com/cuda-11-8-0-download-archive) so that will be the easiest CUDA version to get working without requiring copying .dll's to the plugin or project path. 

## Installation

1. **PluginBuilder**:
   Clone or download PluginBuilder from its repository.
2. **Visual Studio**:
   Ensure Visual Studio with C++ tools is installed [Visual Studio](https://visualstudio.microsoft.com).
3. **CMake**:
   Install CMake if not already installed [CMake Download](https://cmake.org/download). Ensure it is added to your system path.
4. **Ninja**:
   If `ninja.exe` is not in your PATH, download it from [Ninja Releases](https://github.com/ninja-build/ninja/releases/tag/v1.12.0), unzip, and copy `ninja.exe` to `${USER_PATH}/ninja`.
5. **Configure settings.ini**:
   - In the PluginBuilder directory open `SetSettings.toe`.
   - Navigate to the textDAT named `settings`.
   - Edit the fields as instructed in the comments.
   - The `settings.ini` file will be saved to `${USER_PATH}/AppData/Roaming/IntentDev/PluginBuilder`.

## Usage

1. **Load PluginBuilder**:
   Drag `PluginBuilder.tox` into an existing TouchDesigner project saved on disk. (PluginBuilder can also be added to palette, but do not delete the PluginBuilder directory that is set in settings.ini...)
2. **Set Plugin Name**:
   Enter a name for your plugin in the `Plugin Name` parameter.
3. **Select a Template**:
   Choose a template from the `Plugin Template` menu.
4. **Create Plugin**:
   Click `Create Plugin`. This will generate:
   - A `PluginProjects` folder in your project directory, containing a subfolder for your plugin. This subfolder includes a source folder with the copied template source.
   - A `Plugins` folder containing the `.dll` files. These are managed by PluginBuilder and loaded in `plugin_loader` CPlusPlus operator inside PluginBuilder.
5. **Edit Source Files**:
   If `Compile On Update` is Active, any source change will automatically trigger a rebuild and compile. Ensure to save changes in your .toe before editing any source files - crashes due to a dll compiled with coding errors can happen...
7. **Edit CMake**:
   Edit CMakelists.txt as required to include additional libraries.
8. **Install Plugin**:
   This will install a completed plugin in the global plugins folder located in `Documents/Derivative/Plugins` for use in other projects.

The build and compile processes are non-blocking, allowing TouchDesigner to run without any major stalls. The initial build (triggered by Create Plugin) is usually the longest where subsequent updates are completed in less than a second with minimal frame drops, depending on the caching and the scope of changes.

## Contributing

Contributions to PluginBuilder are welcome and appreciated! If you're interested in improving the tool or adding new features please start a discussion!
