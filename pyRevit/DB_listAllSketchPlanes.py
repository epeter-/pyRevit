'''
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE
'''

__doc__ = 'Lists all sketch planes in this model.'

from Autodesk.Revit.DB import FilteredElementCollector, SketchPlane, Transaction
doc = __revit__.ActiveUIDocument.Document

cl = FilteredElementCollector(doc)
list = [i for i in cl.OfClass(SketchPlane).ToElements()]

for gs in list:
	print('NAME: {0} ID: {1}'.format(	gs.Name.ljust(50), gs.Id ))
