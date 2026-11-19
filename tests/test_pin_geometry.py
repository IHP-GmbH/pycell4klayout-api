########################################################################
#
# Copyright 2026 IHP PDK Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
########################################################################

"""Run with python3 -m unittest discover -s tests (requires klayout)."""

from pathlib import Path
import sys
import unittest

import pya

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source/python'))

from cni.dlo import Box, DloGen, Layer, Orientation, PyCellContext, Rect, Transform  # noqa: E402


class TestTech:
    dataBaseUnits = 0.001

    def stream_layers(self):
        return {'Metal1.pin': (8, 2), 'Metal2.pin': (10, 2)}

    def getTechParams(self):
        return {'libName': 'test_lib'}


class PinGeometryTest(unittest.TestCase):
    def setUp(self):
        self.layout = pya.Layout()
        self.cell = self.layout.create_cell('test_cell')
        self.impl = DloGen()
        self.impl.addCellContext(self.cell)
        self.context = PyCellContext(TestTech(), self.cell, self.impl)
        self.context.__enter__()
        self.addCleanup(self.context.__exit__, None, None, None)
        self.layer = Layer('Metal1', 'pin')

    def test_rectangle_properties_survive_moves_and_transforms(self):
        rect = Rect(self.layer, Box(1, 2, 3, 5))
        properties = {'PIN_INFO__PIN_NAME': 'S', 'custom_property': 42}
        rect.getShape().set_properties(properties)
        expected = pya.DBox(1, 2, 3, 5)

        for orientation in (Orientation.R0, Orientation.R90, Orientation.R180,
                            Orientation.R270, Orientation.MX, Orientation.MY,
                            Orientation.MXR90, Orientation.MYR90):
            with self.subTest(orientation=orientation):
                rect.moveBy(0.125, -0.25)
                expected = pya.DTrans(0.125, -0.25) * expected
                self.assertEqual(rect.getShape().dbox, expected)
                self.assertEqual(rect.getShape().properties(), properties)

                transform = Transform(0.5, -0.75, orientation)
                rect.transform(transform)
                expected = expected.transformed(transform.transform)
                self.assertEqual(rect.getShape().dbox, expected)
                self.assertEqual(rect.getBBox().box, expected)
                self.assertEqual(rect.getShape().properties(), properties)
                self.assertEqual(self.cell.shapes(self.layer.number).size(), 1)
                self.assertEqual(self.impl.getShapes(), [rect])

    def test_rectangle_without_properties_stays_unannotated(self):
        rect = Rect(self.layer, Box(1, 2, 3, 5))
        rect.moveBy(1.0, 2.0)
        rect.transform(Transform(0, 0, Orientation.R90))
        self.assertFalse(rect.getShape().has_prop_id())
        self.assertEqual(rect.getShape().dbox, pya.DBox(-7, 2, -4, 4))

    def test_pin_geometry_follows_cell_shapes(self):
        pin = self.impl.addPin('S', 'SOURCE', Box(1, 2, 3, 5), self.layer)
        shapes = self.impl.getShapes()
        self.assertEqual(len(shapes), 1)
        self.assertIs(shapes[0].getPin(), pin)
        properties = {
            'PIN_INFO__VERSION': '0.1',
            'PIN_INFO__LIB_NAME': 'test_lib',
            'PIN_INFO__CELL_NAME': 'test_cell',
            'PIN_INFO__PIN_NAME': 'S',
            'PIN_INFO__TERM_NAME': 'SOURCE',
        }
        expected = pya.DBox(1, 2, 3, 5)
        for orientation in (Orientation.R0, Orientation.R90, Orientation.MX, Orientation.MY):
            transform = Transform(0, 0, orientation)
            for shape in self.impl.getShapes():
                shape.transform(transform)
                shape.moveBy(1.25, 2.5)
            expected = pya.DTrans(1.25, 2.5) * expected.transformed(transform.transform)
            self.assertEqual(pin.getBBox().box, expected)
            self.assertEqual(shapes[0].getShape().dbox, expected)
            self.assertEqual(shapes[0].getShape().properties(), properties)
            self.assertEqual(self.cell.shapes(self.layer.number).size(), 1)

    def test_pin_does_not_take_ownership_of_input_box(self):
        box = Box(1, 2, 3, 5)
        original = Rect(self.layer, box)
        pin = self.impl.addPin('S', 'S', box, self.layer)
        for shape in self.impl.getShapes():
            shape.moveBy(10.0, 20.0)
        expected = pya.DBox(11, 22, 13, 25)
        self.assertEqual(original.getShape().dbox, expected)
        self.assertEqual(pin.getBBox().box, expected)
        self.assertEqual(self.cell.shapes(self.layer.number).size(), 2)
        for shape in self.cell.shapes(self.layer.number).each():
            self.assertEqual(shape.dbox, expected)

    def test_multiple_pin_boxes_remain_tracked(self):
        pin = self.impl.addPin('S', 'S', Box(1, 2, 3, 5), self.layer)
        second_layer = Layer('Metal2', 'pin')
        pin.setBBox(Box(6, 7, 8, 9), second_layer)
        shapes = self.impl.getShapes()
        self.assertEqual(len(shapes), 2)
        for shape in shapes:
            self.assertIs(shape.getPin(), pin)
            shape.moveBy(1.0, 2.0)
            self.assertEqual(shape.getShape().property('PIN_INFO__PIN_NAME'), 'S')
        self.assertEqual(next(self.cell.shapes(self.layer.number).each()).dbox, pya.DBox(2, 4, 4, 7))
        self.assertEqual(pin.getBBox().box, pya.DBox(7, 9, 9, 11))


if __name__ == '__main__':
    unittest.main()
