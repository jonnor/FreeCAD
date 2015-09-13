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

class Creator(DraftTool):
    "A generic Draft Creator Tool used by creation tools such as line or arc"

    def __init__(self):
        DraftTool.__init__(self)

    def Activated(self,name="None"):
        DraftTool.Activated(self)
        self.support = getSupport()

class ScaleReference(Creator):
    "The Line FreeCAD command definition"

    def __init__(self, wiremode=False):
        Creator.__init__(self)
        self.isWire = wiremode

    def GetResources(self):
        return {'Pixmap'  : 'Draft_Line',
                'Accel' : "L,I",
                'MenuText': QtCore.QT_TRANSLATE_NOOP("Draft_Line", "Line"),
                'ToolTip': QtCore.QT_TRANSLATE_NOOP("Draft_Line", "Creates a 2-point line. CTRL to snap, SHIFT to constrain")}

    def Activated(self,name=translate("draft","Line")):
        Creator.Activated(self,name)
        if self.doc:
            self.obj = None
            if self.isWire:
                self.ui.wireUi(name)
            else:
                self.ui.lineUi(name)
            self.obj=self.doc.addObject("Part::Feature",self.featureName)
            # self.obj.ViewObject.Selectable = False
            Draft.formatObject(self.obj)
            self.call = self.view.addEventCallback("SoEvent",self.action)
            msg(translate("draft", "Pick first point:\n"))

    def finish(self,closed=False,cont=False):
        "terminates the operation and closes the poly if asked"
        if self.obj:
            # remove temporary object, if any
            old = self.obj.Name
            todo.delay(self.doc.removeObject,old)
        self.obj = None
        if (len(self.node) > 1):
            if (len(self.node) == 2) and Draft.getParam("UsePartPrimitives",False):
                # use Part primitive
                p1 = self.node[0]
                p2 = self.node[-1]
                self.commit(translate("draft","Create Line"),
                            ['line = FreeCAD.ActiveDocument.addObject("Part::Line","Line")',
                             'line.X1 = '+str(p1.x),
                             'line.Y1 = '+str(p1.y),
                             'line.Z1 = '+str(p1.z),
                             'line.X2 = '+str(p2.x),
                             'line.Y2 = '+str(p2.y),
                             'line.Z2 = '+str(p2.z)])
            else:
                # building command string
                rot,sup,pts,fil = self.getStrings()
                FreeCADGui.addModule("Draft")
                self.commit(translate("draft","Create DWire"),
                            ['points='+pts,
                             'Draft.makeWire(points,closed='+str(closed)+',face='+fil+',support='+sup+')'])
        Creator.finish(self)
        if self.ui:
            if self.ui.continueMode:
                self.Activated()

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

    def undolast(self):
        "undoes last line segment"
        if (len(self.node) > 1):
            self.node.pop()
            last = self.node[len(self.node)-1]
            if self.obj.Shape.Edges:
                edges = self.obj.Shape.Edges
                if len(edges) > 1:
                    edges.pop()
                    newshape = Part.Wire(edges)
                    self.obj.Shape = newshape
                else:
                    self.obj.ViewObject.hide()
                # DNC: report on removal
                msg(translate("draft", "Last point has been removed\n"))

    def drawSegment(self,point):
        "draws a new segment"
        if (len(self.node) == 1):
            msg(translate("draft", "Pick next point:\n"))
            if self.planetrack:
                self.planetrack.set(self.node[0])
        elif (len(self.node) == 2):
            last = self.node[len(self.node)-2]
            newseg = Part.Line(last,point).toShape()
            self.obj.Shape = newseg
            self.obj.ViewObject.Visibility = True
            if self.isWire:
                msg(translate("draft", "Pick next point, or (F)inish or (C)lose:\n"))
        else:
            currentshape = self.obj.Shape.copy()
            last = self.node[len(self.node)-2]
            if not DraftVecUtils.equals(last,point):
                newseg = Part.Line(last,point).toShape()
                newshape=currentshape.fuse(newseg)
                self.obj.Shape = newshape
            msg(translate("draft", "Pick next point, or (F)inish or (C)lose:\n"))

    def wipe(self):
        "removes all previous segments and starts from last point"
        if len(self.node) > 1:
            # self.obj.Shape.nullify() - for some reason this fails
            self.obj.ViewObject.Visibility = False
            self.node = [self.node[-1]]
            if self.planetrack:
                self.planetrack.set(self.node[0])
            msg(translate("draft", "Pick next point:\n"))

    def numericInput(self,numx,numy,numz):
        "this function gets called by the toolbar when valid x, y, and z have been entered there"
        self.point = Vector(numx,numy,numz)
        self.node.append(self.point)
        self.drawSegment(self.point)
        if (not self.isWire and len(self.node) == 2):
            self.finish(False,cont=True)
        self.ui.setNextFocus()


FreeCADGui.addCommand('Image_Scale_Reference',ScaleReference())
