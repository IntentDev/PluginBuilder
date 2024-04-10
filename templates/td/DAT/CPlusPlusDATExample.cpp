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

#include "CPlusPlusDATExample.h"

#include <stdio.h>
#include <string.h>
#include <math.h>
#include <assert.h>
#include <array>

// These functions are basic C function, which the DLL loader can find
// much easier than finding a C++ Class.
// The DLLEXPORT prefix is needed so the compile exports these functions from the .dll
// you are creating
extern "C"
{

DLLEXPORT
void
FillDATPluginInfo(DAT_PluginInfo *info)
{
	// Always return DAT_CPLUSPLUS_API_VERSION in this function.
	info->apiVersion = DATCPlusPlusAPIVersion;

	// The opType is the unique name for this TOP. It must start with a
	// capital A-Z character, and all the following characters must lower case
	// or numbers (a-z, 0-9)
	info->customOPInfo.opType->setString("Customdat");

	// The opLabel is the text that will show up in the OP Create Dialog
	info->customOPInfo.opLabel->setString("Custom DAT");

	// Will be turned into a 3 letter icon on the nodes
	info->customOPInfo.opIcon->setString("CDT");

	// Information about the author of this OP
	info->customOPInfo.authorName->setString("Author Name");
	info->customOPInfo.authorEmail->setString("email@email.com");

	// This DAT works with 0 or 1 inputs
	info->customOPInfo.minInputs = 0;
	info->customOPInfo.maxInputs = 1;

}

DLLEXPORT
DAT_CPlusPlusBase*
CreateDATInstance(const OP_NodeInfo* info)
{
	// Return a new instance of your class every time this is called.
	// It will be called once per DAT that is using the .dll
	return new CPlusPlusDATExample(info);
}

DLLEXPORT
void
DestroyDATInstance(DAT_CPlusPlusBase* instance)
{
	// Delete the instance here, this will be called when
	// Touch is shutting down, when the DAT using that instance is deleted, or
	// if the DAT loads a different DLL
	delete (CPlusPlusDATExample*)instance;
}

};

CPlusPlusDATExample::CPlusPlusDATExample(const OP_NodeInfo* info) : myNodeInfo(info)
{
	myExecuteCount = 0;
	myOffset = 0.0;

	myChop = "";

	myChopChanName = "";
	myChopChanVal = 0;
}

CPlusPlusDATExample::~CPlusPlusDATExample()
{
}

void
CPlusPlusDATExample::getGeneralInfo(DAT_GeneralInfo* ginfo, const OP_Inputs* inputs, void* reserved1)
{
	// This will cause the node to cook every frame
	ginfo->cookEveryFrameIfAsked = false;
}

void
CPlusPlusDATExample::makeTable(DAT_Output* output, int numRows, int numCols)
{
	output->setOutputDataType(DAT_OutDataType::Table);
	output->setTableSize(numRows, numCols);

	std::array<const char*, 5> data = { "this", "is", "some", "test", "data"};

	for (int i = 0; i < numRows; i++)
	{
		for (int j = 0; j < numCols; j++)
		{
			int j2 = j;

			// If we are asked to make more columns than we have data for
			if (j2 >= data.size())
				j2 = j2 % data.size();

			output->setCellString(i, j, data[j2]);
		}
	}
}

void
CPlusPlusDATExample::makeText(DAT_Output* output)
{
	output->setOutputDataType(DAT_OutDataType::Text);
	output->setText("This is some test data.");
}

void
CPlusPlusDATExample::execute(DAT_Output* output,
							const OP_Inputs* inputs,
							void* reserved)
{
	myExecuteCount++;

	if (!output)
		return;

	if (inputs->getNumInputs() > 0)
	{
		inputs->enablePar("Rows", 0);		// not used
		inputs->enablePar("Cols", 0);		// not used
		inputs->enablePar("Outputtype", 0);	// not used

		const OP_DATInput	*cinput = inputs->getInputDAT(0);

		int numRows = cinput->numRows;
		int numCols = cinput->numCols;
		bool isTable = cinput->isTable;

		if (!isTable) // is Text
		{
			const char* str = cinput->getCell(0, 0);
			output->setText(str);
		}
		else
		{
			output->setOutputDataType(DAT_OutDataType::Table);
			output->setTableSize(numRows, numCols);

			for (int i = 0; i < cinput->numRows; i++)
			{
				for (int j = 0; j < cinput->numCols; j++)
				{
					const char* str = cinput->getCell(i, j);
					output->setCellString(i, j, str);
				}
			}
		}

	}
	else // If no input is connected, lets output a custom table/text DAT
	{
		inputs->enablePar("Rows", 1);
		inputs->enablePar("Cols", 1);
		inputs->enablePar("Outputtype", 1);

		int outputDataType = inputs->getParInt("Outputtype");
		int	 numRows = inputs->getParInt("Rows");
		int	 numCols = inputs->getParInt("Cols");

		switch (outputDataType)
		{
			case 0:		// Table
				makeTable(output, numRows, numCols);
				break;

			case 1:		// Text
				makeText(output);
				break;

			default: // table
				makeTable(output, numRows, numCols);
				break;
		}

		// if there is an input chop parameter:
		const OP_CHOPInput	*cinput = inputs->getParCHOP("Chop");
		if (cinput)
		{
			int numSamples = cinput->numSamples;
			int ind = 0;
			for (int i = 0; i < cinput->numChannels; i++)
			{
				myChopChanName = std::string(cinput->getChannelName(i));
				myChop = inputs->getParString("Chop");

				static char tempBuffer[50];
				myChopChanVal = float(cinput->getChannelData(i)[ind]);

#ifdef _WIN32
				sprintf_s(tempBuffer, "%g", myChopChanVal);
#else // macOS
				snprintf(tempBuffer, sizeof(tempBuffer), "%g", myChopChanVal);
#endif
				if (numCols == 0)
					numCols = 2;
				output->setTableSize(numRows + i + 1, numCols);
				output->setCellString(numRows + i, 0, myChopChanName.c_str());
				output->setCellString(numRows + i, 1, &tempBuffer[0]);
			}

		}

	}
}

int32_t
CPlusPlusDATExample::getNumInfoCHOPChans(void* reserved1)
{
	// We return the number of channel we want to output to any Info CHOP
	// connected to the CHOP. In this example we are just going to send one channel.
	return 4;
}

void
CPlusPlusDATExample::getInfoCHOPChan(int32_t index,
									OP_InfoCHOPChan* chan, void* reserved1)
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

	if (index == 2)
	{
		chan->name->setString(myChop.c_str());
		chan->value = (float)myOffset;
	}

	if (index == 3)
	{
		chan->name->setString(myChopChanName.c_str());
		chan->value = myChopChanVal;
	}
}

bool
CPlusPlusDATExample::getInfoDATSize(OP_InfoDATSize* infoSize, void* reserved1)
{
	infoSize->rows = 3;
	infoSize->cols = 3;
	// Setting this to false means we'll be assigning values to the table
	// one row at a time. True means we'll do it one column at a time.
	infoSize->byColumn = false;
	return true;
}

void
CPlusPlusDATExample::getInfoDATEntries(int32_t index,
									int32_t nEntries,
									OP_InfoDATEntries* entries,
									void* reserved1)
{
	char tempBuffer[4096];

	if (index == 0)
	{
		// Set the value for the first column
#ifdef _WIN32
		strcpy_s(tempBuffer, "executeCount");
#else // macOS
		strlcpy(tempBuffer, "executeCount", sizeof(tempBuffer));
#endif
		entries->values[0]->setString(tempBuffer);

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
#ifdef _WIN32
		strcpy_s(tempBuffer, "offset");
#else // macOS
		strlcpy(tempBuffer, "offset", sizeof(tempBuffer));
#endif
		entries->values[0]->setString(tempBuffer);

		// Set the value for the second column
#ifdef _WIN32
		sprintf_s(tempBuffer, "%g", myOffset);
#else // macOS
		snprintf(tempBuffer, sizeof(tempBuffer), "%g", myOffset);
#endif
		entries->values[1]->setString(tempBuffer);
	}

	if (index == 2)
	{
		// Set the value for the first column
#ifdef _WIN32
		strcpy_s(tempBuffer, "DAT input name");
#else // macOS
		strlcpy(tempBuffer, "offset", sizeof(tempBuffer));
#endif
		entries->values[0]->setString(tempBuffer);

		// Set the value for the second column
#ifdef _WIN32
		strcpy_s(tempBuffer, myDat.c_str());
#else // macOS
		snprintf(tempBuffer, sizeof(tempBuffer), "%g", myOffset);
#endif
		entries->values[1]->setString(tempBuffer);
	}
}

void
CPlusPlusDATExample::setupParameters(OP_ParameterManager* manager, void* reserved1)
{
	// CHOP
	{
		OP_StringParameter	np;

		np.name = "Chop";
		np.label = "CHOP";

		OP_ParAppendResult res = manager->appendCHOP(np);
		assert(res == OP_ParAppendResult::Success);
	}

	// Number of Rows
	{
		OP_NumericParameter	np;

		np.name = "Rows";
		np.label = "Rows";
		np.defaultValues[0] = 4;
		np.minSliders[0] = 0;
		np.maxSliders[0] = 10;

		OP_ParAppendResult res = manager->appendInt(np);
		assert(res == OP_ParAppendResult::Success);
	}

	// Number of Columns
	{
		OP_NumericParameter	np;

		np.name = "Cols";
		np.label = "Cols";
		np.defaultValues[0] = 5;
		np.minSliders[0] = 0;
		np.maxSliders[0] = 10;

		OP_ParAppendResult res = manager->appendInt(np);
		assert(res == OP_ParAppendResult::Success);
	}

	// DAT output type
	{
		OP_StringParameter	sp;

		sp.name = "Outputtype";
		sp.label = "Output Type";

		sp.defaultValue = "Table";

		const char *names[] = {"Table", "Text"};
		const char *labels[] = {"Table", "Text"};

		OP_ParAppendResult res = manager->appendMenu(sp, 2, names, labels);
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
CPlusPlusDATExample::pulsePressed(const char* name, void* reserved1)
{
	if (!strcmp(name, "Reset"))
	{
		myOffset = 0.0;
	}
}
