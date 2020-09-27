import arcpy, os


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [FilesWithin, UpdateAiracInfo, CalculatePolygonRotationUTM33, CalculatePolygonRotationLCC10E, SetLayoutsNorAirac, SetLayoutsSweAirac, SetLayoutsFinDnkAirac, Export330charts]


class FilesWithin(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Files Within"
        self.description = "Returns a list of TIFF files that comes in contact with any polygon in the bounding feature class"
        self.canRunInBackground = True

    def getParameterInfo(self):
        """Define parameter definitions"""

        # First parameter
        param0 = arcpy.Parameter(
            displayName="TIFF directory",
            name="MapDirString",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")

        # Second parameter
        param1 = arcpy.Parameter(
            displayName="Bounding Features",
            name="BoundaryFeatureClass",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")

        # Third parameter
        param2 = arcpy.Parameter(
            displayName="List of Files",
            name="FileList",
            datatype="DEFile",
            parameterType="Derived",
            direction="Output",
            multiValue=True)

        params = [param0, param1, param2]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        try:
            MapDirString = parameters[0].valueAsText
            BoundaryFeatureClass = parameters[1].value

            cursor = arcpy.da.SearchCursor(BoundaryFeatureClass, ['SHAPE@'])
            FilesWithinBoundary = []
            FilesOutsideBoundary = []


            for file in os.listdir(MapDirString):                                     #Loop through each file in the folder
                if file.upper().endswith(".TIF"):                                     #Only process *.tif files
                    FileExtent = arcpy.Describe(MapDirString + "\\" + file).extent    #Get the Extent object describing the extent of the tif file

                    #Create an array with the corners of the footprint to be checked
                    FootprintCorners = arcpy.Array([FileExtent.upperLeft, FileExtent.upperRight, FileExtent.lowerRight, FileExtent.lowerLeft])

                    #Create the footprint polygon to be checked
                    FootPrint = arcpy.Polygon(FootprintCorners)

                    FootPrintOverlapsBoundary = True       #Initialize the result variable
                    for row in cursor:                     #Iterate each polygon in the Boundary Feature Class
                        #Found a match if the features overlap, contains or is within eachother
                        if row[0].overlaps(FootPrint) or row[0].contains(FootPrint) or row[0].within(FootPrint):
                            break
                    else:
                        #The break never happened. The tif is outside the Boundary of the polygon.
                        FootPrintOverlapsBoundary = False

                    #Reset the cursor iterating Boundary features to the first record.
                    cursor.reset()

                    #Print the result
                    if FootPrintOverlapsBoundary:
                        FilesWithinBoundary.append(MapDirString + "\\" + file)
                    else:
                        FilesOutsideBoundary.append(MapDirString + "\\" + file)

            #Clean up.
            del cursor



        #Errorhandling
        #-------------------------
        except IOError as e:
            print("I/O error({0}): {1}".format(e.errno, e.strerror))

        except:
            print("Unexpected error:", sys.exc_info()[0])
            raise


        parameters[2].value = FilesWithinBoundary
        return


def unique_values(table, field):
    with arcpy.da.SearchCursor(table, [field]) as cursor:
        return sorted({row[0] for row in cursor})


class UpdateAiracInfo(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Update AIRAC info"
        self.description = "Updates the AIRAC labels in the map"
        self.canRunInBackground = True


    def getParameterInfo(self):
        """Define parameter definitions"""

        # First parameter
        param0 = arcpy.Parameter(
            displayName="Lag med kartinfo annotation puntker",
            name="fcAnnotationPoints",
            datatype=["DEFeatureClass", "GPFeatureLayer"],
            parameterType="Required",
            direction="Input")

        # Second parameter
        param1 = arcpy.Parameter(
            displayName="Kart som ble oppdatert",
            name="UpdatedMap",
            datatype="String",
            parameterType="Required",
            direction="Input")

	# Third parameter
        param2 = arcpy.Parameter(
            displayName="Ny kartinfo text (eks. AIRAC 11 2016)",
            name="NewInfo",
            datatype="String",
            parameterType="Required",
            direction="Input")

        params = [param0, param1, param2]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        parameters[1].filter.list = unique_values(parameters[0].value, "Map")

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        fc = parameters[0].value

        #Start an edit session
        workspace = arcpy.Describe(parameters[0].value).Path
        edit = arcpy.da.Editor(workspace)
        edit.startEditing(False, True)
        edit.startOperation()

        fields = ['Map', 'Effective']

        # Create update cursor for feature class
        NewText = "<CLR red=\"255\" green=\"0\" blue=\"197\" alpha=\"66\">" + parameters[2].value + "</CLR>"

        with arcpy.da.UpdateCursor(fc, fields) as cursor:
            # For each row, evaluate the Map value (index position
            # of 0), and update Effective (index position of 1)
            for row in cursor:
                if row[0] == parameters[1].value:
                    row[1] = NewText

                # Update the cursor with the updated list
                cursor.updateRow(row)

        #End edit session
        edit.stopOperation()
        edit.stopEditing(True)

        #Cleanup
        del edit
        del cursor

        return



class CalculatePolygonRotationUTM33(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Calculate Polygon Rotation UTM33"
        self.description = "Calculates the main angle of a polygon and inserts it into its RotationUTM33 field."
        self.canRunInBackground = True


    def getParameterInfo(self):
        """Define parameter definitions"""

        # First parameter
        param0 = arcpy.Parameter(
            displayName="Layer with polygons",
            name="fcPolygons",
            datatype=["DEFeatureClass", "GPFeatureLayer"],
            parameterType="Required",
            direction="Input")

        params = [param0]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        fc = parameters[0].value
        arcpy.CalculatePolygonMainAngle_cartography(fc, "RotationUTM33", "GEOGRAPHIC")

        return


class CalculatePolygonRotationLCC10E(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Calculate Polygon Rotation LCC 10E"
        self.description = "Calculates the main angle of a polygon and inserts it into its RotationLCC10E field."
        self.canRunInBackground = True


    def getParameterInfo(self):
        """Define parameter definitions"""

        # First parameter
        param0 = arcpy.Parameter(
            displayName="Layer with polygons",
            name="fcPolygons",
            datatype=["DEFeatureClass", "GPFeatureLayer"],
            parameterType="Required",
            direction="Input")

        params = [param0]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        fc = parameters[0].value
        arcpy.CalculatePolygonMainAngle_cartography(fc, "RotationLCC10E", "GEOGRAPHIC")

        return

    
class SetLayoutsNorAirac(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Set Layouts Nor AIRAC Number"
        self.description = "Changes AIRAC number in several layouts."
        self.canRunInBackground = True


    def getParameterInfo(self):
        """Define parameter definitions"""

        # First parameter
        param0 = arcpy.Parameter(
            displayName="New AIRAC xx xxxx (e.g. 01 2019)",
            name="AiracText",
            datatype="String",
            parameterType="Required",
            direction="Input")

        param0.value = "xx xxxx"

        params = [param0]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        aprx = arcpy.mp.ArcGISProject("CURRENT")


        arcpy.AddMessage("------------------------")
        arcpy.AddMessage("Layout titles updated")
        arcpy.AddMessage("------------------------")
        for lyt in aprx.listLayouts():
            for elm in lyt.listElements("TEXT_ELEMENT"):
                if elm.name == "AIRAC version":
                    lastAIRAC = elm.text
                    newAIRAC = parameters[0].value
                    elm.text = "AIRAC " + newAIRAC
                    arcpy.AddMessage("{0:<35} old:{1:<20} new:{2}".format(lyt.name, lastAIRAC, elm.text))


        arcpy.AddMessage("------------------------")
        arcpy.AddMessage("Basemap versions updated")
        arcpy.AddMessage("------------------------")
        for lyt in aprx.listLayouts():
            for elm in lyt.listElements("TEXT_ELEMENT"):
                if elm.name == "M517_FLMA_versions":
                    lastAIRAC = elm.text.replace("\n", " CRLF ")
                    newAIRAC = parameters[0].value
                    elm.text = "AIRAC " + newAIRAC + "\n" + "AIRAC " + newAIRAC
                    arcpy.AddMessage("{0:<35} old:{1:<40} new:{2}".format(lyt.name, lastAIRAC, newAIRAC))
        return


class SetLayoutsFinDnkAirac(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Set Layouts Fin AIRAC and Dnk Edition Number"
        self.description = "Changes AIRAC number for Finland and Editon for Denmark in several layouts."
        self.canRunInBackground = True


    def getParameterInfo(self):
        """Define parameter definitions"""

        # First parameter
        param0 = arcpy.Parameter(
            displayName="New Finland AIRAC xx xxxx (e.g. 01 2019)",
            name="FinText",
            datatype="String",
            parameterType="Required",
            direction="Input")
        # Second parameter
        param1 = arcpy.Parameter(
            displayName="New Denmark Edition xx (e.g. 37)",
            name="DnkText",
            datatype="String",
            parameterType="Required",
            direction="Input")

        param0.value = "xx xxxx"
        param1.value = "xx"

        params = [param0, param1]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        aprx = arcpy.mp.ArcGISProject("CURRENT")



        arcpy.AddMessage("------------------------")
        arcpy.AddMessage("Basemap versions updated")
        arcpy.AddMessage("------------------------")
        for lyt in aprx.listLayouts():
            for elm in lyt.listElements("TEXT_ELEMENT"):
                if elm.name == "FIN_DNK versions":
                    lastAIRAC = elm.text.replace("\n", " CRLF ")
                    newAIRAC = parameters[0].value + " CRLF " + parameters[1].value
                    elm.text = "AIRAC " + parameters[0].value + "\n" + "Ed " + parameters[1].value
                    arcpy.AddMessage("{0:<35} old:{1:<20} new:{2}".format(lyt.name, lastAIRAC, newAIRAC))
        return

class SetLayoutsSweAirac(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Set Layouts Swe AIRAC Number"
        self.description = "Changes AIRAC number for Sweden in several layouts."
        self.canRunInBackground = True


    def getParameterInfo(self):
        """Define parameter definitions"""

        # First parameter
        param0 = arcpy.Parameter(
            displayName="New AIRAC xx xxxx (e.g. 01 2019)",
            name="SweText",
            datatype="String",
            parameterType="Required",
            direction="Input")

        param0.value = "xx xxxx"

        params = [param0]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        aprx = arcpy.mp.ArcGISProject("CURRENT")



        arcpy.AddMessage("------------------------")
        arcpy.AddMessage("Basemap versions updated")
        arcpy.AddMessage("------------------------")
        for lyt in aprx.listLayouts():
            for elm in lyt.listElements("TEXT_ELEMENT"):
                if elm.name == "SWE version":
                    lastAIRAC = elm.text.replace("\n", " CRLF ")
                    newAIRAC = parameters[0].value
                    elm.text = "AIRAC " + newAIRAC
                    arcpy.AddMessage("{0:<35} old:{1:<20} new:{2}".format(lyt.name, lastAIRAC, newAIRAC))
        return

    
class Export330charts(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Export 330 charts"
        self.description = "Exports all charts for 330 squadron"
        self.canRunInBackground = True


    def getParameterInfo(self):
        """Define parameter definitions"""
        return

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        aprx = arcpy.mp.ArcGISProject("CURRENT")


        arcpy.AddMessage("---------------------------------------------------")
        arcpy.AddMessage("Exporting \"330sqn 250k RNAV Chart 36in\" as GeoTIFF")
        arcpy.AddMessage("---------------------------------------------------")
        for lyt in aprx.listLayouts():
            if lyt.name == "330sqn 250k RNAV Chart 36in":
                if lyt.mapSeries.enabled:
                    arcpy.AddMessage("Ready to export {0} charts".format(lyt.mapSeries.pageCount))
                    for elm in lyt.listElements("TEXT_ELEMENT"):
                        if elm.name == "AIRAC version":
                            lastAIRAC = elm.text
                            yyyy = lastAIRAC[9:13]
                            mm = lastAIRAC[6:8]
                    arcpy.AddMessage("AIRAC version is {0} {1}".format(mm, yyyy))
                    arcpy.AddMessage("---------------------------------------------------")

                    #for n in range(1, lyt.mapSeries.pageCount + 1):
                    for n in range(3, 4):
                        lyt.mapSeries.currentPageNumber = n
                        mapname = lyt.mapSeries.pageRow.Name
                        filename = yyyy + "_" + mm + " RNAV36_fra_python " + mapname + ".pdf"
                        arcpy.AddMessage(filename)
                        #lyt.exportToTIFF("D:\\Produkter\\250k RNAV Chart\\Print\\" + filename,resolution=400, color_mode="24-BIT_TRUE_COLOR", tiff_compression="DEFLATE")
                        lyt.mapSeries.exportToPDF("D:\\Produkter\\250k RNAV Chart\\Print\\" + filename, page_range_type="SELECTED", multiple_files="PDF_SINGLE_FILE", resolution=400, image_quality="BEST", compress_vector_graphics=True, image_compression="DEFLATE", embed_fonts=True, layers_attributes="NONE", georef_info=True, clip_to_elements=False, show_selection_symbology=False)
                else:
                    arcpy.AddMessage("The layout does not have Map Series enabled.")
        return
