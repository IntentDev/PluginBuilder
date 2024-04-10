/* Shared Use License: This file is owned by Derivative Inc. (Derivative)
* and can only be used, and/or modified for use, in conjunction with
* Derivative's TouchDesigner software, and only if you are a licensee who has
* accepted Derivative's TouchDesigner license or assignment agreement
* (which also govern the use of this file). You may share or redistribute
* a modified version of this file provided the following conditions are met:
*
* 1. The shared file or redistribution must retain the information set out
* above and this list of conditions.
* 2. Derivative's name (Derivative Inc.) or its trademarks may not be used
* to endorse or promote products derived from this file without specific
* prior written permission from Derivative.
*/

#include "CHOPWithPythonClass.h"

#include <stdio.h>
#include <string.h>
#include <cmath>
#include <assert.h>
#ifdef _WIN32
	#include <Python.h>
	#include <structmember.h>
#else
	#include <Python/Python.h>
	#include <Python/structmember.h>
#endif

static PyObject*
pyReset(PyObject* self)
{
	PY_Struct* me = (PY_Struct*)self;

	PY_GetInfo info;
	// We don't want to cook the node before we set this, since it doesn't depend on it's current state
	info.autoCook = false;
	CHOPWithPythonClass* inst = (CHOPWithPythonClass*)me->context->getNodeInstance(info);
	// It's possible the instance will be nullptr, such as if the node has been deleted
	// while the Python class is still being held on and used elsewhere.
	if (inst)
	{
		inst->resetFilter();
		// Make the node dirty so it will cook an output a newly reset filter when asked next
		me->context->makeNodeDirty();
	}

	// We need to inc-ref the None object if we are going to return it.
	Py_INCREF(Py_None);
	return Py_None;
}

static PyMethodDef methods[] =
{
	{"reset", (PyCFunction)pyReset, METH_NOARGS, "Resets the Filter."},
	{0}
};

static PyObject*
pyGetSpeedMod(PyObject* self, void*)
{
	PY_Struct* me = (PY_Struct*)self;

	PY_GetInfo info;
	// Since thie variable is internally held in the class instance and not a product of the 'cook'
	// we don't need to cook the node before getting it.
	info.autoCook = false;
	CHOPWithPythonClass* inst = (CHOPWithPythonClass*)me->context->getNodeInstance(info);
	// It's possible the instance will be nullptr, such as if the node has been deleted
	// while the Python class is still being held on and used elsewhere.
	if (inst)
	{
		return PyFloat_FromDouble(inst->getSpeedMod());
	}

	// an error has occured
	return nullptr;
}

static int
pySetSpeedMod(PyObject* self, PyObject* value, void*)
{
	// Do nothing in this case
	if (!value)
		return 0;

	PY_Struct* me = (PY_Struct*)self;

	PY_GetInfo info;
	info.autoCook = false;
	CHOPWithPythonClass* inst = (CHOPWithPythonClass*)me->context->getNodeInstance(info);
	// It's possible the instance will be nullptr, such as if the node has been deleted
	// while the Python class is still being held on and used elsewhere.
	if (inst)
	{
		// Try to cast it to a double object
		PyObject* cast = PyNumber_Float(value);

		if (cast && !PyErr_Occurred())
		{
			double v = PyFloat_AsDouble(cast);
			inst->setSpeedMod(v);
			me->context->makeNodeDirty();
			Py_XDECREF(cast);
			// success
			return 0;
		}
	}
	else
	{
		// getNodeInstance() will have already added a Python error if it returned a null
	}

	// an error has occured
	return -1;
}

static PyObject*
pyGetExecuteCount(PyObject* self, void*)
{
	PY_Struct* me = (PY_Struct*)self;

	PY_GetInfo info;
	// We want to cook the node in this case before getting the execute count
	// so we have an accurate result.
	info.autoCook = true;
	CHOPWithPythonClass* inst = (CHOPWithPythonClass*)me->context->getNodeInstance(info);
	// It's possible the instance will be nullptr, such as if the node has been deleted
	// while the Python class is still being held on and used elsewhere.
	if (inst)
	{
		return PyLong_FromLong(inst->getExecuteCount());
	}

	// an error has occured
	return nullptr;
}

// This struct lists the different getters and/or settings the Custom Operator will expose.
static PyGetSetDef getSets[] =
{
	{"speedMod", pyGetSpeedMod, pySetSpeedMod, "Get or Set the speed modulation.", nullptr},
	// This one doesn't define a 'setter', so it's a read-only value.
	{"executeCount", pyGetExecuteCount, nullptr, "Get execute count.", nullptr},
	{0}
};

const char* PythonCallbacksDATStubs =
"# This is an example callbacks DAT.\n"
"\n"
"# op - The OP that is doing the callback.\n"
"# curSpeed - The current speed value the node will be using.\n"
"#\n"
"# Change the 0.0 to make the speed get adjusted by this callback.\n"
"def getSpeedAdjust(op, curSpeed):\n"
"	return curSpeed + 0.0\n";

// These functions are basic C function, which the DLL loader can find
// much easier than finding a C++ Class.
// The DLLEXPORT prefix is needed so the compile exports these functions from the .dll
// you are creating
extern "C"
{

DLLEXPORT
void
FillCHOPPluginInfo(CHOP_PluginInfo *info)
{
	// Always set this to CHOPCPlusPlusAPIVersion.
	info->apiVersion = CHOPCPlusPlusAPIVersion;

	// The opType is the unique name for this CHOP. It must start with a 
	// capital A-Z character, and all the following characters must lower case
	// or numbers (a-z, 0-9)
	info->customOPInfo.opType->setString("Customsignalpython");

	// The opLabel is the text that will show up in the OP Create Dialog
	info->customOPInfo.opLabel->setString("Custom Signal Python");

	// Information about the author of this OP
	info->customOPInfo.authorName->setString("Author Name");
	info->customOPInfo.authorEmail->setString("email@email.com");

	// This CHOP can work with 0 inputs
	info->customOPInfo.minInputs = 0;

	// It can accept up to 1 input though, which changes it's behavior
	info->customOPInfo.maxInputs = 1;

	info->customOPInfo.pythonVersion->setString(PY_VERSION);
	info->customOPInfo.pythonMethods = methods;
	info->customOPInfo.pythonGetSets = getSets;
	info->customOPInfo.pythonCallbacksDAT = PythonCallbacksDATStubs;
}

DLLEXPORT
CHOP_CPlusPlusBase*
CreateCHOPInstance(const OP_NodeInfo* info)
{
	// Return a new instance of your class every time this is called.
	// It will be called once per CHOP that is using the .dll
	return new CHOPWithPythonClass(info);
}

DLLEXPORT
void
DestroyCHOPInstance(CHOP_CPlusPlusBase* instance)
{
	// Delete the instance here, this will be called when
	// Touch is shutting down, when the CHOP using that instance is deleted, or
	// if the CHOP loads a different DLL
	delete (CHOPWithPythonClass*)instance;
}

};


CHOPWithPythonClass::CHOPWithPythonClass(const OP_NodeInfo* info) : myNodeInfo(info)
{
	myExecuteCount = 0;
	myOffset = 0.0;
	mySpeedMod = 1.0;
}

CHOPWithPythonClass::~CHOPWithPythonClass()
{
}

void
CHOPWithPythonClass::resetFilter()
{
	myOffset = 0;
}

void
CHOPWithPythonClass::getGeneralInfo(CHOP_GeneralInfo* ginfo, const OP_Inputs* inputs, void* reserved1)
{
	// This will cause the node to cook every frame
	ginfo->cookEveryFrameIfAsked = true;

	// Note: To disable timeslicing you'll need to turn this off, as well as ensure that
	// getOutputInfo() returns true, and likely also set the info->numSamples to how many
	// samples you want to generate for this CHOP. Otherwise it'll take on length of the
	// input CHOP, which may be timesliced.
	ginfo->timeslice = true;

	ginfo->inputMatchIndex = 0;
}

bool
CHOPWithPythonClass::getOutputInfo(CHOP_OutputInfo* info, const OP_Inputs* inputs, void* reserved1)
{
	// If there is an input connected, we are going to match it's channel names etc
	// otherwise we'll specify our own.
	if (inputs->getNumInputs() > 0)
	{
		return false;
	}
	else
	{
		info->numChannels = 1;

		// Since we are outputting a timeslice, the system will dictate
		// the numSamples and startIndex of the CHOP data
		//info->numSamples = 1;
		//info->startIndex = 0

		// For illustration we are going to output 120hz data
		info->sampleRate = 120;
		return true;
	}
}

void
CHOPWithPythonClass::getChannelName(int32_t index, OP_String *name, const OP_Inputs* inputs, void* reserved1)
{
	name->setString("chan1");
}

void
CHOPWithPythonClass::execute(CHOP_Output* output, const OP_Inputs* inputs, void* reserved1)
{
	myExecuteCount++;

	double	 scale = inputs->getParDouble("Scale");

	// In this case we'll just take the first input and re-output it scaled.

	if (inputs->getNumInputs() > 0)
	{
		// We know the first CHOP has the same number of channels
		// because we returned false from getOutputInfo. 

		inputs->enablePar("Speed", 0);	// not used
		inputs->enablePar("Reset", 0);	// not used
		inputs->enablePar("Shape", 0);	// not used

		int ind = 0;
		const OP_CHOPInput	*cinput = inputs->getInputCHOP(0);

		for (int i = 0 ; i < output->numChannels; i++)
		{
			for (int j = 0; j < output->numSamples; j++)
			{
				output->channels[i][j] = float(cinput->getChannelData(i)[ind] * scale);
				ind++;

				// Make sure we don't read past the end of the CHOP input
				ind = ind % cinput->numSamples;
			}
		}

	}
	else // If not input is connected, lets output a sine wave instead
	{
		inputs->enablePar("Speed", 1);
		inputs->enablePar("Reset", 1);

		double speed = inputs->getParDouble("Speed");

		// Apply Python class modifications
		speed *= mySpeedMod;

		// We'll only be adding one extra argument
		PyObject* args = myNodeInfo->context->createArgumentsTuple(1, nullptr);
		// The first argument is already set to the 'op' variable, so we set the second argument to our speed value
		PyTuple_SET_ITEM(args, 1, PyFloat_FromDouble(speed));

		PyObject *result = myNodeInfo->context->callPythonCallback("getSpeedAdjust", args, nullptr, nullptr);
		// callPythonCallback doesn't take ownership of the args
		Py_DECREF(args);

		// We own result now, so we need to Py_DECREF it unless we want to hold onto it
		if (result)
		{
			// If we got a float back, replace our current speed with the returned on
			if (PyFloat_Check(result))
			{
				speed = PyFloat_AsDouble(result);
			}
			Py_DECREF(result);
		}

		double step = speed * 0.01f;

		// menu items can be evaluated as either an integer menu position, or a string
		int shape = inputs->getParInt("Shape");
//		const char *shape_str = inputs->getParString("Shape");

		// keep each channel at a different phase
		double phase = 2.0f * 3.14159f / (float)(output->numChannels);

		// Notice that startIndex and the output->numSamples is used to output a smooth
		// wave by ensuring that we are outputting a value for each sample
		// Since we are outputting at 120, for each frame that has passed we'll be
		// outputing 2 samples (assuming the timeline is running at 60hz).

		for (int i = 0; i < output->numChannels; i++)
		{
			double offset = myOffset + phase*i;
			double v = 0.0f;
			switch(shape)
			{
				case 0:		// sine
					v = sin(offset);
					break;

				case 1:		// square
					v = fabs(fmod(offset, 1.0)) > 0.5;
					break;

				case 2:		// ramp	
					v = fabs(fmod(offset, 1.0));
					break;
			}

			v *= scale;
			for (int j = 0; j < output->numSamples; j++)
			{
				output->channels[i][j] = float(v);
				offset += step;
			}
		}
		myOffset += step * output->numSamples; 
	}
}

int32_t
CHOPWithPythonClass::getNumInfoCHOPChans(void * reserved1)
{
	// We return the number of channel we want to output to any Info CHOP
	// connected to the CHOP. In this example we are just going to send one channel.
	return 2;
}

void
CHOPWithPythonClass::getInfoCHOPChan(int32_t index,
										OP_InfoCHOPChan* chan,
										void* reserved1)
{
	// This function will be called once for each channel we said we'd want to return
	// In this example it'll only be called once.

	if (index == 0)
	{
		chan->name->setString("executeCount");
		chan->value = (float)myExecuteCount;
	}

	if (index == 1)
	{
		chan->name->setString("offset");
		chan->value = (float)myOffset;
	}
}

bool		
CHOPWithPythonClass::getInfoDATSize(OP_InfoDATSize* infoSize, void* reserved1)
{
	infoSize->rows = 2;
	infoSize->cols = 2;
	// Setting this to false means we'll be assigning values to the table
	// one row at a time. True means we'll do it one column at a time.
	infoSize->byColumn = false;
	return true;
}

void
CHOPWithPythonClass::getInfoDATEntries(int32_t index,
										int32_t nEntries,
										OP_InfoDATEntries* entries, 
										void* reserved1)
{
	char tempBuffer[4096];

	if (index == 0)
	{
		// Set the value for the first column
		entries->values[0]->setString("executeCount");

		// Set the value for the second column
#ifdef _WIN32
		sprintf_s(tempBuffer, "%d", myExecuteCount);
#else // macOS
		snprintf(tempBuffer, sizeof(tempBuffer), "%d", myExecuteCount);
#endif
		entries->values[1]->setString(tempBuffer);
	}

	if (index == 1)
	{
		// Set the value for the first column
		entries->values[0]->setString("offset");

		// Set the value for the second column
#ifdef _WIN32
		sprintf_s(tempBuffer, "%g", myOffset);
#else // macOS
		snprintf(tempBuffer, sizeof(tempBuffer), "%g", myOffset);
#endif
		entries->values[1]->setString( tempBuffer);
	}
}

void
CHOPWithPythonClass::setupParameters(OP_ParameterManager* manager, void *reserved1)
{
	// speed
	{
		OP_NumericParameter	np;

		np.name = "Speed";
		np.label = "Speed";
		np.defaultValues[0] = 1.0;
		np.minSliders[0] = -10.0;
		np.maxSliders[0] =  10.0;
		
		OP_ParAppendResult res = manager->appendFloat(np);
		assert(res == OP_ParAppendResult::Success);
	}

	// scale
	{
		OP_NumericParameter	np;

		np.name = "Scale";
		np.label = "Scale";
		np.defaultValues[0] = 1.0;
		np.minSliders[0] = -10.0;
		np.maxSliders[0] =  10.0;
		
		OP_ParAppendResult res = manager->appendFloat(np);
		assert(res == OP_ParAppendResult::Success);
	}

	// shape
	{
		OP_StringParameter	sp;

		sp.name = "Shape";
		sp.label = "Shape";

		sp.defaultValue = "Sine";

		const char *names[] = { "Sine", "Square", "Ramp" };
		const char *labels[] = { "Sine", "Square", "Ramp" };

		OP_ParAppendResult res = manager->appendMenu(sp, 3, names, labels);
		assert(res == OP_ParAppendResult::Success);
	}

	// pulse
	{
		OP_NumericParameter	np;

		np.name = "Reset";
		np.label = "Reset";
		
		OP_ParAppendResult res = manager->appendPulse(np);
		assert(res == OP_ParAppendResult::Success);
	}

}

void 
CHOPWithPythonClass::pulsePressed(const char* name, void* reserved1)
{
	if (!strcmp(name, "Reset"))
	{
		myOffset = 0.0;
	}
}

