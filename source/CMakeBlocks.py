start_block = '''# {'plugin_type': __PLUGIN_TYPE__}
cmake_minimum_required (VERSION 3.21)

# Enable Hot Reload for MSVC compilers if supported.
if (POLICY CMP0141)
  cmake_policy(SET CMP0141 NEW)
  set(CMAKE_MSVC_DEBUG_INFORMATION_FORMAT "$<IF:$<AND:$<C_COMPILER_ID:MSVC>,$<CXX_COMPILER_ID:MSVC>>,$<$<CONFIG:Debug,RelWithDebInfo>:EditAndContinue>,$<$<CONFIG:Debug,RelWithDebInfo>:ProgramDatabase>>")
endif()

if (NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Choose the type of build." FORCE)
  set_property(CACHE CMAKE_BUILD_TYPE PROPERTY STRINGS "Debug" "Release" "RelWithDebInfo")
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)
set(CMAKE_CXX_EXTENSIONS ON)

if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin/Debug)
    set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib/Debug)
    set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib/Debug)
elseif(CMAKE_BUILD_TYPE STREQUAL "Release")
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin/Release)
    set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib/Release)
    set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib/Release)
elseif(CMAKE_BUILD_TYPE STREQUAL "RelWithDebInfo")
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin/RelWithDebInfo)
    set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib/RelWithDebInfo)
    set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib/RelWithDebInfo)
endif()

'''

project_block = '''
project (PLUGIN_NAME LANGUAGES CXX)
'''

cuda_project_block = '''
set(CMAKE_CUDA_ARCHITECTURES 75;80;86;89)
project (PLUGIN_NAME LANGUAGES CXX CUDA)
'''

core_block = '''
# set(PLUGIN_BUILDER_DIR "D:/TD/PluginBuilder")
set(PLUGIN_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../Plugins/PLUGIN_NAME")
set(SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/source)

set(PRINT_SOURCE_FILES On)
if(PRINT_SOURCE_FILES)
    foreach(source IN LISTS PROJ_SOURCE_FILES)
      message(STATUS "PLUGIN_NAME source: ${source}")
    endforeach()
endif()

set(INCLUDE_DIR "${PLUGIN_BUILDER_DIR}/include")
# print expanded INCLUDE_DIR
message(STATUS "INCLUDE_DIR: ${INCLUDE_DIR}")

# Collect all source files and exclude gtest files.
file(GLOB_RECURSE PROJ_SOURCE_FILES "${SOURCE_DIR}/*.cpp" "${SOURCE_DIR}/*.c" "${SOURCE_DIR}/*.cu" "${SOURCE_DIR}/*.h")

add_library(PLUGIN_NAME SHARED ${PROJ_SOURCE_FILES})
target_include_directories(PLUGIN_NAME PRIVATE ${SOURCE_DIR} ${INCLUDE_DIR})

'''

cuda_block = '''
# CUDA
#################################################################################################
find_package(CUDAToolkit REQUIRED)
message(STATUS CUDAToolkit_INCLUDE_DIRS=${CUDAToolkit_INCLUDE_DIRS})
target_include_directories(PLUGIN_NAME PRIVATE ${CUDAToolkit_INCLUDE_DIRS})
target_link_libraries(PLUGIN_NAME PRIVATE CUDA::cudart)

# Post-build command to copy the CUDA runtime DLL to the output directory
# set(cuda_runtime_dll "${CUDAToolkit_BIN_DIR}/cudart64_110.dll")
# add_custom_command(TARGET PLUGIN_NAME POST_BUILD
#     COMMAND ${CMAKE_COMMAND} -E copy_if_different
#     ${cuda_runtime_dll} $<TARGET_FILE_DIR:PLUGIN_NAME>)

'''

python_block = '''
# Python
#################################################################################################
target_include_directories(PLUGIN_NAME PRIVATE "${PLUGIN_BUILDER_DIR}/3rdParty/Python/Include" "${PLUGIN_BUILDER_DIR}/3rdParty/Python/Include/PC")
target_link_directories(PLUGIN_NAME PRIVATE "${PLUGIN_BUILDER_DIR}/3rdParty/Python/lib/x64")

'''