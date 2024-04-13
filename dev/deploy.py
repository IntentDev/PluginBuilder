import os

print('Deploying PluginBuilder.tox')

PluginBuilderComp = op('PluginBuilder')

PluginBuilderComp.par.Pluginname = ''
PluginBuilderComp.par.Plugintemplate.menuIndex = 0
PluginBuilderComp.par.Createinputop = False
PluginBuilderComp.par.Compileonupdate = True
PluginBuilderComp.par.Buildconfig = 'Release'
PluginBuilderComp.op('CMakeLists').text = ''

PluginBuilderComp.save('../PluginBuilder.tox')