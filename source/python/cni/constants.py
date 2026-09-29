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

import sys

REJECT = 1
ACCEPT = 2
USE_DEFAULT = 3
INT_MAX = sys.maxsize
INT_MIN = -sys.maxsize-1

# property keys for connectivity information 
PROPERTY_KEY__PIN_INFO__VERSION = 'PIN_INFO__VERSION'
PROPERTY_KEY__PIN_INFO__LIB_NAME = 'PIN_INFO__LIB_NAME'
PROPERTY_KEY__PIN_INFO__CELL_NAME = 'PIN_INFO__CELL_NAME'
PROPERTY_KEY__PIN_INFO__PIN_NAME = 'PIN_INFO__PIN_NAME'
PROPERTY_KEY__PIN_INFO__TERM_NAME = 'PIN_INFO__TERM_NAME'
PROPERTY_VALUE__PIN_INFO__CURRENT_VERSION = '0.1'
