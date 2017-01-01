# ***************************************************************************
# * (c) Jon Nordby (jononor@gmail.com) 2017                                 *
# * Based on linuxcnc_post.py by                                            *
# * (c) sliptonic (shopinthewoods@gmail.com) 2014                           *
# *                                                                         *
# *   This file is part of the FreeCAD CAx development system.              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   FreeCAD is distributed in the hope that it will be useful,            *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Lesser General Public License for more details.                   *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with FreeCAD; if not, write to the Free Software        *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************/


TOOLTIP='''
This is a postprocessor file for the Path workbench. It is used to
take a pseudo-gcode fragment outputted by a Path object, and output
real GCode suitable for a 3-axis CNC mill running Redeeem/Replicate with
a spindle based on a brushless ESC.

This postprocessor, once placed in the appropriate PathScripts folder, can be used directly from inside
FreeCAD, via the GUI importer or via python scripts with:

import shopbotgcode_post
shopbotgcode_post.export(object,"/path/to/file.ncc","")
'''

TOOLTIP_ARGS='''
Arguments for shopbotgcode:
    --header,--no-header             ... output headers (--header)
    --comments,--no-comments         ... output comments (--comments)
    --line-numbers,--no-line-numbers ... prefix with line numbers (--no-lin-numbers)
    --show-editor, --no-show-editor  ... pop up editor before writing output(--show-editor)
'''

import datetime
from PathScripts import PostUtils

now = datetime.datetime.now()

# These globals set common customization preferences
OUTPUT_COMMENTS = True
OUTPUT_HEADER = True
OUTPUT_LINE_NUMBERS = False
SHOW_EDITOR = True
MODAL = False  # if true commands are suppressed if the same as previous line.
COMMAND_SPACE = " "
LINENR = 100  # line number starting value

# These globals will be reflected in the Machine configuration of the project
UNITS = "G21"  # G21 for metric, G20 for us standard
MACHINE_NAME = "Redeem"
CORNER_MIN = {'x': 0, 'y': 0, 'z': 0}
CORNER_MAX = {'x': 300, 'y': 300, 'z': 30}

# Preamble text will appear at the beginning of the GCODE output file.
PREAMBLE = '''G17 G91
'''

# Postamble text will appear following the last operation.
POSTAMBLE = '''M05
G00 X0.0 Y0.0
G17 G91
M2
'''


# Pre operation text will be inserted before every operation
PRE_OPERATION = ''''''

# Post operation text will be inserted after every operation
POST_OPERATION = ''''''

# Tool Change commands will be inserted before a tool change
TOOL_CHANGE = ''''''


# to distinguish python built-in open function from the one declared below
if open.__module__ == '__builtin__':
    pythonopen = open

def processArguments(argstring):
    global OUTPUT_HEADER
    global OUTPUT_COMMENTS
    global OUTPUT_LINE_NUMBERS
    global SHOW_EDITOR
    for arg in argstring.split():
        if arg == '--header':
            OUTPUT_HEADER = True
        elif arg == '--no-header':
            OUTPUT_HEADER = False
        elif arg == '--comments':
            OUTPUT_COMMENTS = True
        elif arg == '--no-comments':
            OUTPUT_COMMENTS = False
        elif arg == '--line-numbers':
            OUTPUT_LINE_NUMBERS = True
        elif arg == '--no-line-numbers':
            OUTPUT_LINE_NUMBERS = False
        elif arg == '--show-editor':
            SHOW_EDITOR = True
        elif arg == '--no-show-editor':
            SHOW_EDITOR = False

def export(objectslist, filename, argstring):
    processArguments(argstring)
    global UNITS
    for obj in objectslist:
        if not hasattr(obj, "Path"):
            print "the object " + obj.Name + " is not a path. Please select only path and Compounds."
            return

    print "postprocessing..."
    gcode = ""

    # Find the machine.
    # The user my have overriden post processor defaults in the GUI.  Make
    # sure we're using the current values in the Machine Def.
    myMachine = None
    for pathobj in objectslist:
        if hasattr(pathobj,"MachineName"):
            myMachine = pathobj.MachineName
        if hasattr(pathobj, "MachineUnits"):
            if pathobj.MachineUnits == "Metric":
               UNITS = "G21"
            else:
               UNITS = "G20"
    if myMachine is None:
        print "No machine found in this selection"

    # write header
    if OUTPUT_HEADER:
        gcode += linenumber() + "(Exported by FreeCAD)\n"
        gcode += linenumber() + "(Post Processor: " + __name__ + ")\n"
        gcode += linenumber() + "(Output Time:" + str(now) + ")\n"

    # Write the preamble
    if OUTPUT_COMMENTS:
        gcode += linenumber() + "(begin preamble)\n"
    for line in PREAMBLE.splitlines(True):
        gcode += linenumber() + line
    gcode += linenumber() + UNITS + "\n"

    for obj in objectslist:

        # do the pre_op
        if OUTPUT_COMMENTS:
            gcode += linenumber() + "(begin operation: " + obj.Label + ")\n"
        for line in PRE_OPERATION.splitlines(True):
            gcode += linenumber() + line

        gcode += parse(obj)

        # do the post_op
        if OUTPUT_COMMENTS:
            gcode += linenumber() + "(finish operation: " + obj.Label + ")\n"
        for line in POST_OPERATION.splitlines(True):
            gcode += linenumber() + line

    # do the post_amble

    if OUTPUT_COMMENTS:
        gcode += "(begin postamble)\n"
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

    print "done postprocessing."

    if not filename == '-':
        gfile = pythonopen(filename, "wb")
        gfile.write(final)
        gfile.close()

    return final


def linenumber():
    global LINENR
    if OUTPUT_LINE_NUMBERS is True:
        LINENR += 10
        return "N" + str(LINENR) + " "
    return ""

def parse(pathobj):
    out = ""
    lastcommand = None

    # params = ['X','Y','Z','A','B','I','J','K','F','S'] #This list control
    # the order of parameters
    # linuxcnc doesn't want K properties on XY plane  Arcs need work.
    params = ['X', 'Y', 'Z', 'A', 'B', 'I', 'J', 'F', 'S', 'T', 'Q', 'R', 'L']

    if hasattr(pathobj, "Group"):  # We have a compound or project.
        # if OUTPUT_COMMENTS:
        #     out += linenumber() + "(compound: " + pathobj.Label + ")\n"
        for p in pathobj.Group:
            out += parse(p)
        return out
    else:  # parsing simple path

        # groups might contain non-path things like stock.
        if not hasattr(pathobj, "Path"):
            return out

        # if OUTPUT_COMMENTS:
        #     out += linenumber() + "(" + pathobj.Label + ")\n"

        for c in pathobj.Path.Commands:
            outstring = []
            command = c.Name
            outstring.append(command)
            # if modal: only print the command if it is not the same as the
            # last one
            if MODAL is True:
                if command == lastcommand:
                    outstring.pop(0)

            # Now add the remaining parameters in order
            for param in params:
                if param in c.Parameters:
                    if param == 'F':
                        if c.Name not in ["G0", "G00"]: #linuxcnc doesn't use rapid speeds
                            outstring.append(
                                param + format(c.Parameters['F'], '.2f'))
                    elif param == 'T':
                        outstring.append(param + str(c.Parameters['T']))
                    else:
                        outstring.append(
                            param + format(c.Parameters[param], '.4f'))

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
                if speed and int(speed):
                    outstring.pop(0) # remove parm
                    if OUTPUT_COMMENTS: out += "(set spindle speed)\n"
                    out += linenumber() + "(spindle speed %d ignored)\n" % (int(speed))

                if command == 'M5':
                    if OUTPUT_COMMENTS: out += "(turn spindle off)\n"
                    out += linenumber() + "G4 S3\n" # avoid stopping while performing last motion command
                    out += linenumber() + "M280 S-90 P0 F3000 R\n"
                else:
                    if OUTPUT_COMMENTS: out += "(turn spindle on)\n"
                    # First signal to turn off, so that ESC can wake up
                    out += linenumber() + "M280 S-90 P0 F3000 R\n"
                    out += linenumber() + "G4 S1\n"
                    out += linenumber() + "M280 S90 P0 F3000 R\n"
                    out += linenumber() + "G4 S2\n" # Time to spin up

            if command == "message":
                if OUTPUT_COMMENTS is False:
                    out = []
                else:
                    outstring.pop(0)  # remove the command

            # prepend a line number and append a newline
            if len(outstring) >= 1:
                if OUTPUT_LINE_NUMBERS:
                    outstring.insert(0, (linenumber()))

                # append the line to the final output
                for w in outstring:
                    out += w + COMMAND_SPACE
                out = out.strip() + "\n"

        return out


print __name__ + " gcode postprocessor loaded."
