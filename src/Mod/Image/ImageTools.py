#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2015                                                    *
#*   Jon Nordby <jononor@gmail.com>                                        *
#*                                                                         *
#*   This program is free software; you can redistribute it and/or modify  *
#*   it under the terms of the GNU Lesser General Public License (LGPL)    *
#*   as published by the Free Software Foundation; either version 2 of     *
#*   the License, or (at your option) any later version.                   *
#*   for detail see the LICENCE text file.                                 *
#*                                                                         *
#*   This program is distributed in the hope that it will be useful,       *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#*   GNU Library General Public License for more details.                  *
#*                                                                         *
#*   You should have received a copy of the GNU Library General Public     *
#*   License along with this program; if not, write to the Free Software   *
#*   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
#*   USA                                                                   *
#*                                                                         *
#***************************************************************************


import os, math, re
from PySide import QtGui, QtCore
import FreeCAD, FreeCADGui
from DraftTools import DraftTool
from FreeCAD import Vector
from pivy import coin

def translate(context,text):
    "convenience function for Qt translator"
    return QtGui.QApplication.translate(context, text, None, QtGui.QApplication.UnicodeUTF8).encode("utf8")

class ScaleReference(object):
    "The Line FreeCAD command definition"

    def __init__(self):
        pass

    def GetResources(self):
        return {'Pixmap'  : 'Draft_Line',
                'Accel' : "L,I",
                'MenuText': QtCore.QT_TRANSLATE_NOOP("Image_Scale_Reference", "Image scale to reference"),
                'ToolTip': QtCore.QT_TRANSLATE_NOOP("Image_Scale_Reference", "Scale an ImagePlane by specifying dimensions between two points")}

    def IsActive(self):
        return bool(FreeCADGui.ActiveDocument)

    def Activated(self,name=translate("draft","Line")):
        self.doc = FreeCAD.ActiveDocument
        self.view = Draft.get3DView()
        if self.doc:
            self.callback = self.view.addEventCallback("SoEvent",self.action)
            msg(translate("draft", "Pick first point:\n"))


    def finish(self):
        "terminates the operation and closes the poly if asked"
        self.view.removeEventCallback("SoEvent",self.callback)
        self.callback = None
        self.doc = None
        self.view = None

    def action(self,arg):
        "scene event handler"
        if arg["Type"] == "SoKeyboardEvent":
            # key detection
            if arg["Key"] == "ESCAPE":
                self.finish()
        elif arg["Type"] == "SoLocation2Event":
            # mouse movement detection
            self.point,ctrlPoint,info = getPoint(self,arg)
        elif arg["Type"] == "SoMouseButtonEvent":
            # mouse button detection
            if (arg["State"] == "DOWN") and (arg["Button"] == "BUTTON1"):
                if (arg["Position"] == self.pos):
                    self.finish(False,cont=True)
                else:
                    if (not self.node) and (not self.support):
                        getSupport(arg)
                        self.point,ctrlPoint,info = getPoint(self,arg)
                    if self.point:
                        self.ui.redraw()
                        self.pos = arg["Position"]
                        self.node.append(self.point)
                        self.drawSegment(self.point)
                        if (not self.isWire and len(self.node) == 2):
                            self.finish(False,cont=True)
                        if (len(self.node) > 2):
                            if ((self.point-self.node[0]).Length < Draft.tolerance()):
                                self.undolast()
                                self.finish(True,cont=True)
                                msg(translate("draft", "DWire has been closed\n"))







FreeCADGui.addCommand('Image_Scale_Reference',ScaleReference())
