#***************************************************************************
#*   (c) Jon Nordby (jononor@gmail.com) 2016                               *
#*   Based on linuxcnc_post.py by                                          *
#*   (c) sliptonic (shopinthewoods@gmail.com) 2014                         *
#*                                                                         *
#*   This file is part of the FreeCAD CAx development system.              *
#*                                                                         *
#*   This program is free software; you can redistribute it and/or modify  *
#*   it under the terms of the GNU Lesser General Public License (LGPL)    *
#*   as published by the Free Software Foundation; either version 2 of     *
#*   the License, or (at your option) any later version.                   *
#*   for detail see the LICENCE text file.                                 *
#*                                                                         *
#*   FreeCAD is distributed in the hope that it will be useful,            *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#*   GNU Lesser General Public License for more details.                   *
#*                                                                         *
#*   You should have received a copy of the GNU Library General Public     *
#*   License along with FreeCAD; if not, write to the Free Software        *
#*   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
#*   USA                                                                   *
#*                                                                         *
#***************************************************************************/


'''
This is a postprocessor file for the Path workbench.
It takes pseudo-gcode fragments outputted by a Path object,
and output real GCode suitable for use with a Shopbot.
'''

# For testing with standard FreeCAD, using this file from git
# import sys
# sys.path.append('/home/jon/contrib/code/freecad/Mod/Path/PathScripts/')
# import shopbotgcode_post; reload(shopbotgcode_post)

import datetime
now = datetime.datetime.now()
from PathScripts import PostUtils

#These globals set common customization preferences
OUTPUT_COMMENTS = True
OUTPUT_HEADER = True
OUTPUT_LINE_NUMBERS = False
SHOW_EDITOR = False
MODAL = False #if true commands are suppressed if the same as previous line.
COMMAND_SPACE = " "
LINENR = 100 #line number starting value
REV = "0.0.2"

#These globals will be reflected in the Machine configuration of the project
UNITS = "G21" #G21 for metric, G20 for us standard

#Preamble text will appear at the beginning of the GCODE output file.
PREAMBLE = '''G17
G91
'''

#Postamble text will appear following the last operation.
POSTAMBLE = '''
G00 X0.0 Y0.0
G17
G91
M2
'''


#Pre operation text will be inserted before every operation
PRE_OPERATION = ''''''
 
#Post operation text will be inserted after every operation
POST_OPERATION = ''''''

#Tool Change commands will be inserted before a tool change
TOOL_CHANGE = ''''''


# to distinguish python built-in open function from the one declared below
if open.__module__ == '__builtin__':
    pythonopen = open


def export(objectslist, filename):
    global UNITS
    for obj in objectslist:
        if not hasattr(obj,"Path"):
            print "the object " + obj.Name + " is not a path. Please select only path and Compounds."
            return

    print "postprocessing..."
    gcode = ""

    #Find the machine.  
    #The user my have overriden post processor defaults in the GUI.  Make sure we're using the current values in the Machine Def.
    myMachine = None
    for pathobj in objectslist:
        if hasattr(pathobj,"Group"): #We have a compound or project.
            for p in pathobj.Group:
                if p.Name == "Machine":
                    myMachine = p
    if myMachine is None: 
        print "No machine found in this project"
    else:
        if myMachine.MachineUnits == "Metric":
           UNITS = "G21"
        else:
           UNITS = "G20"
            

    # write header
    if OUTPUT_HEADER:
        gcode += linenumber() + "(Exported by FreeCAD)\n"
        gcode += linenumber() + "(Post Processor: %s %s)\n" % (__name__, REV)
        gcode += linenumber() + "(Output Time:"+str(now)+")\n"
    
    #Write the preamble 
    if OUTPUT_COMMENTS: gcode += linenumber() + "(begin preamble)\n"
    for line in PREAMBLE.splitlines(True):
        gcode += linenumber() + line
    gcode += linenumber() + UNITS + "\n" 

    for obj in objectslist:
        
        #do the pre_op
        if OUTPUT_COMMENTS: gcode += linenumber() + "(begin operation: " + obj.Label + ")\n"
        for line in PRE_OPERATION.splitlines(True):
            gcode += linenumber() + line

        gcode += parse(obj)

        #do the post_op
        if OUTPUT_COMMENTS: gcode += linenumber() + "(finish operation: " + obj.Label + ")\n"
        for line in POST_OPERATION.splitlines(True):
            gcode += linenumber() + line

    #do the post_amble

    if OUTPUT_COMMENTS: gcode += "(begin postamble)\n" 
    for line in POSTAMBLE.splitlines(True):
        gcode += linenumber() + line

    if SHOW_EDITOR:
        dia = PostUtils.GCodeEditorDialog()
        dia.editor.setText(gcode)
        result = dia.exec_()
        if result:
            final = dia.editor.toPlainText()
        else:
            final = gcode
    else:
        final = gcode

    gfile = pythonopen(filename,"wb")
    gfile.write(gcode)
    gfile.close()
    print "%s done postprocessing %s" % (REV, filename)


def linenumber():
    global LINENR
    if OUTPUT_LINE_NUMBERS == True:
        LINENR += 10 
        return "N" + str(LINENR) + " "
    return ""

def parse(pathobj):
    out = ""
    lastcommand = None

    #params = ['X','Y','Z','A','B','I','J','K','F','S'] #This list control the order of parameters
    params = ['X','Y','Z','A','B','I','J','F','S','T','Q','R','L'] #linuxcnc doesn't want K properties on XY plane  Arcs need work.
    
    if hasattr(pathobj,"Group"): #We have a compound or project.
        if OUTPUT_COMMENTS: out += linenumber() + "(compound: " + pathobj.Label + ")\n" 
        for p in pathobj.Group:
            out += parse(p)
        return out      
    else: #parsing simple path

        if not hasattr(pathobj,"Path"): #groups might contain non-path things like stock.
            return out

        if OUTPUT_COMMENTS: out += linenumber() + "(Path: " + pathobj.Label + ")\n"

        for c in pathobj.Path.Commands:
            outstring = []    
            command = c.Name
            outstring.append(command) 
            # if modal: only print the command if it is not the same as the last one
            if MODAL == True:
                if command == lastcommand:
                    outstring.pop(0) 
            

            # Now add the remaining parameters in order
            for param in params:
                if param in c.Parameters:
                    if param == 'F': 
                        outstring.append(param + format(c.Parameters['F'], '.2f'))
                    elif param == 'T':
                        outstring.append(param + str(c.Parameters['T']))
                    else:
                        outstring.append(param + format(c.Parameters[param], '.4f'))

            # store the latest command
            lastcommand = command

            # Check for Tool Change: 
            if command == 'M6':
                outstring.pop(0) #remove the original command
                outstring.pop(0) # remove parm
                if OUTPUT_COMMENTS: out += linenumber() + "(toolchange ignored)\n"

            # Spindle control
            if command == 'M3' or command == 'M5':
                outstring.pop(0) #remove the original command
                speed = c.Parameters.get('S')
                if speed:
                    outstring.pop(0) # remove parm
                    if OUTPUT_COMMENTS: out += "(set spindle speed)\n"
                    out += linenumber() + "TR,%d,1\n" % (int(speed))

                if command == 'M5':
                    if OUTPUT_COMMENTS: out += "(turn spindle off)\n"
                    out += linenumber() + "SO,1,0\n"
                else:
                    if OUTPUT_COMMENTS: out += "(turn spindle on)\n"
                    out += linenumber() + "SO,1,1\n"
                    out += linenumber() + "PAUSE 1\n" # Needed for Shopbot control software to wait reliably


            if command == "message":
                if OUTPUT_COMMENTS == False:
                    out = []
                else:
                    outstring.pop(0) #remove the command

            #prepend a line number and append a newline
            if len(outstring) >= 1:
                if OUTPUT_LINE_NUMBERS: 
                    outstring.insert(0,(linenumber()))

                #append the line to the final output
                for w in outstring:
                    out += w + COMMAND_SPACE
                out = out.strip() + "\n"
    
        return out
   
    
print __name__ + " postprocessor loaded."

