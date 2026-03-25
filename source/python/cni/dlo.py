########################################################################
#
# Copyright 2024 IHP PDK Authors
#
# Licensed under the GNU General Public License, Version 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.gnu.org/licenses/gpl-3.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
########################################################################

from __future__ import annotations

from cni.constants import *
from cni.numeric import *
from cni.orientation import *
from cni.location import *
from cni.layer import *
from cni.pathstyle import *
from cni.signaltype import *
from cni.termtype import *
from cni.font import *
from cni.point import *
from cni.pointlist import *
from cni.box import *
from cni.shape import *
from cni.text import *
from cni.polygon import *
from cni.dlogen import *
from cni.transform import *
from cni.instance import *
from cni.paramarray import *
from cni.pin import *
from cni.term import *
from cni.path import *
from cni.shapefilter import *
from cni.net import *
from cni.ellipse import *
from cni.physicalrule import *

import pya

import sys
import traceback
import tkinter
import re
import pathlib
import os
import json


class ChoiceConstraint(list):

    def __init__(self, choices, action = REJECT):
        super().__init__(choices)


class RangeConstraint:

    def __init__(self, low, high, resolution = None, action = REJECT):
        self.low = low
        self.high = high
        self.resolution = resolution
        self.action = action

        if low is not None:
            if not isinstance(low, (int, float)):
                raise Exception(f"Invalid RangeConstraint: low type: '{type(low)})'")

        if high is not None:
            if not isinstance(high, (int, float)):
                raise Exception(f"Invalid RangeConstraint: high type: '{type(high)})'")

        if low is not None and high is not None and low > high:
            raise Exception(f"Invalid RangeConstraint: {low}(low) > {high}(high)")

        if action is not None and type(action) is not int:
            raise Exception(f"Invalid RangeConstraint: action type: '{type(action)})'")


class PyCellContext(object):

    # stack of PyCellContext for cell hierarchy
    _pyCellContexts = []

    @classmethod
    def getCurrentPyCellContext(cls) -> PyCellContext:
        if len(cls._pyCellContexts) == 0:
            raise Exception("No current PyCellContext")
        return cls._pyCellContexts[-1]

    def __init__(self, tech, cell, impl):
        PyCellContext._pyCellContexts.append(self)
        self._tech = tech
        self._cell = cell
        self._impl = impl

    def __enter__(self):
        Layer.layout = self._cell.layout()

    def __exit__(self, *params):
        PyCellContext._pyCellContexts.pop()
        Layer.layout = None
        self._cell = None
        self._tech = None
        self._impl = None

    @property
    def cell(self):
        if self._cell is None:
            raise Exception("Cell not set!")
        return self._cell

    @property
    def tech(self):
        if self._tech is None:
            raise Exception("Tech not set!")
        return self._tech

    @property
    def layout(self):
        if self._cell is None:
            raise Exception("Layout not set!")
        return self._cell.layout()

    @property
    def impl(self):
        if self._impl is None:
            raise Exception("Impl not set!")
        return self._impl

    @property
    def cell(self):
        if self._cell is None:
            raise Exception("Cell not set!")
        return self._cell


class PCellWrapper(pya.PCellDeclaration):
    _tcl = None
    _callBackPath = None
    _callbackMap = {}
    _tech = None
    _intType = type(1)
    _floatType = type(1.1)
    _strType = type("str")
    _boolType = type(True)
    _parameterTypeList = []

    _klayoutRootPath = pathlib.Path(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
    for file in _klayoutRootPath.rglob("parameters.tcl"):
        if _callBackPath is not None:
            raise Exception("multiple callback location found!")
        _callBackPath = pathlib.Path(os.path.normpath(file)).parent

    def __init__(self, impl, tech, preProcPath = None, origPath = None):
        super(PCellWrapper, self).__init__()

        self._impl = impl
        self._impl.setTech(tech)
        self._preProcPath = preProcPath
        self._origPath = origPath
        self._changedCell = None
        self._changedParameter = None

        self.tech = tech
        PCellWrapper._tech = tech

        Tech.techInUse = tech.getTechParams()['libName']

        self._paramDecls = []

        # NOTE: the PCellWrapper acts as the "specs" object
        try:
            type(impl).defineParamSpecs(self)
        except Exception:
            self._printTraceBack()
            exit(1)

    def __call__(self, name, value, description = None, constraint = None):
        # NOTE: this is calles from inside defineParamSpecs as we
        # supply the "specs" object through self.

        if type(value) is float:
            value_type = pya.PCellParameterDeclaration.TypeDouble
        elif type(value) is int:
            value_type = pya.PCellParameterDeclaration.TypeInt
        elif type(value) is str:
            value_type = pya.PCellParameterDeclaration.TypeString
        elif type(value) is bool:
            value_type = pya.PCellParameterDeclaration.TypeBoolean
        else:
            print(f"Invalid parameter type for parameter {name} (value is {repr(value)})")
            assert(False)

        paramDecl = pya.PCellParameterDeclaration(name, value_type, description, value)

        if type(constraint) is ChoiceConstraint:
            for v in constraint:
                paramDecl.add_choice(repr(v), v)
        elif type(constraint) is RangeConstraint:
            if constraint.action is REJECT:
                if constraint.low is not None:
                    paramDecl.min_value = constraint.low
                if constraint.high is not None:
                    paramDecl.max_value = constraint.high

        self._paramDecls.append(paramDecl)

    @staticmethod
    def _initializeCallbacks():
        callbacksDefPath = os.path.join(PCellWrapper._callBackPath, "callbacks.json")

        if os.path.exists(callbacksDefPath):
            try:
                with open(callbacksDefPath, "r") as callbackFile:
                    jsData = json.load(callbackFile)

                    modules = jsData["moduleList"]
                    for module in modules:
                        modulePath = os.path.join(PCellWrapper._callBackPath, f"{module}")
                        PCellWrapper._tcl.eval(f"source {modulePath}")

                    callbackList = jsData["callbackDefinition"]["callbackList"]
                    for callback in callbackList:
                        PCellWrapper._callbackMap[callback["device"]] = callback

                parameters = {}
                for key, value in PCellWrapper._tech.getTechParams().items():
                    parameters[key] = value

                PCellWrapper._tcl.eval(f"setTechParameters {parameters}")
                PCellWrapper._tcl.eval(f"setCniPythonPath {os.path.normpath(os.path.dirname(__file__))}")

            except Exception as exc:
                raise Exception(f"Invalid Json syntax: '{exc}' in {callbacksDefPath}")

    def _printTraceBack(self):
        lines = traceback.format_exc().splitlines()
        firstLine = True
        for line in lines:
            if self._preProcPath is not None:
                line = line.replace(self._preProcPath, self._origPath)
            if firstLine:
                line = "ERROR: " + line
                firstLine = False
            self._printRed(line)

    def _printRed(self, text):
        print("\033[91m {}\033[00m" .format(text))

    def get_parameters(self):
        return self._paramDecls

    def params_as_hash(self, parameters):
        params = {}
        for i in range(0, len(self._paramDecls)):
            params[self._paramDecls[i].name] = parameters[i]
        return params

    def display_text(self, parameters):
        params = self.params_as_hash(parameters)
        # TODO: form a display string from "important" parameters in a class-specific fashion
        return self.name() + " (...)"

    def produce(self, layout, layers, parameters, cell):
        params = self.params_as_hash(parameters)
        try:
            with (PyCellContext(self.tech, cell, self._impl)):
                self._impl.addCellContext(cell)
                self._impl.setupParams(params)
                self._impl.genLayout()
        except Exception:
            self._printTraceBack()

    def callback(self, layout, name, pcellParameterStates):
        if self.name() in PCellWrapper._callbackMap.keys():
            if pcellParameterStates.has_parameter(name):
                self._changedCell = self.name()
                self._changedParameter = name

    def coerce_parameters(self, layout, parameterValues):
        if PCellWrapper._tcl is None:
            PCellWrapper._tcl = tkinter.Tcl()
            PCellWrapper._initializeCallbacks()

        if self.name() in PCellWrapper._callbackMap.keys():
            PCellWrapper._tcl.eval(f"setCurrentInstancedName {self.name()}")

            parameters = {}
            PCellWrapper._parameterTypeList.clear()
            idx = 0

            for paramDecl in self._paramDecls:
                parameterValue = parameterValues[idx]
                parameterType = type(parameterValue)
                PCellWrapper._parameterTypeList.append(parameterType)
                if parameterType == PCellWrapper._strType:
                    numSpaces = len(parameterValue)
                    if parameterValue.isspace() or numSpaces == 0:
                        parameterValue = f"__isspace__{numSpaces}__"
                parameters[paramDecl.name] = parameterValue
                idx = idx + 1

            PCellWrapper._tcl.eval(f"setCurrentCellParameters {parameters}")

            deviceCallbacks = PCellWrapper._callbackMap[self.name()]
            for callback in deviceCallbacks["callbacks"]:
                parameterToUse = self._changedParameter
                if parameterToUse is None:
                    parameterToUse = callback['pcellParameters'][0]
                #print(f"enter callback {callback['callback']} for parameter {parameterToUse}")
                PCellWrapper._tcl.eval(f"{callback['callback']} {parameterToUse}")
            self._changedParameter = None

            coercedParameters = PCellWrapper._tcl.eval(f"getCurrentCellParameters")

            coercedParameters = coercedParameters.split();

            isValue = False
            parameterValues.clear();
            idx = 0
            for value in coercedParameters:
                if isValue:
                    valueType = type(value)
                    groups = re.search(r"__isspace__(\d+)", value)
                    if groups != None:
                        value = ' ' * int(groups.group(1))
                    elif PCellWrapper._parameterTypeList[idx] == PCellWrapper._intType:
                        value = int(value)
                    elif PCellWrapper._parameterTypeList[idx] == PCellWrapper._floatType:
                        value = float(value)
                    elif PCellWrapper._parameterTypeList[idx] == PCellWrapper._strType:
                        value = str(value)
                    elif PCellWrapper._parameterTypeList[idx] == PCellWrapper._boolType:
                        value = bool(value)

                    parameterValues.append(value)
                    idx = idx + 1
                isValue = not isValue

        return parameterValues

    def wants_lazy_evaluation(self):
        return True
