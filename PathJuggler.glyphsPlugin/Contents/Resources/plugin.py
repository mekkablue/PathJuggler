# encoding: utf-8

###########################################################################################################
#
#	Path Tools plugin
#
#	Algorithms for improved handling of paths and compatibility
#
#	Author: Tamir Hassan, tamir@schriftlabor.at
#
#
###########################################################################################################

from __future__ import division, print_function, unicode_literals
import vanilla, math, objc, copy
from GlyphsApp import *
from GlyphsApp.plugins import *
from AppKit import NSAlternateKeyMask, NSContainsRect, NSMakePoint, NSMenuItem, NSNotificationCenter, NSPointInRect
from itertools import permutations

PATH_JUGGLER_PREFIX = "PathJuggler"

DEFAULT_TOLERANCE = 60
DEFAULT_HORIZ_TOLERANCE = 15
DEFAULT_MAX_MISMATCHES = 0
DEFAULT_SUPPRESS_OUTPUT = 20
DEFAULT_IGNORE_OVERLAP = True

DIR_NONE = -1
DIR_N = 0
DIR_NNE = 1
DIR_NE = 2
DIR_ENE = 3
DIR_E = 4
DIR_ESE = 5
DIR_SE = 6
DIR_SSE = 7
DIR_S = 8
DIR_SSW = 9
DIR_SW = 10
DIR_WSW = 11
DIR_W = 12
DIR_WNW = 13
DIR_NW = 14
DIR_NNW = 15

class PathJuggler(GeneralPlugin):
	
	@objc.python_method
	def settings(self):
		self.name = 'Path Juggler'
	
	@objc.python_method
	def start(self):
		
		# constants (experimental settings not in settings window)
		self.USE_COMPASS = False
		self.IGNORE_CORNER = False
		
		if not self.loadPreferences():
			print("Note: 'Path Juggler' could not load preferences. Will resort to defaults")
		
		pathMenu = Glyphs.menu[PATH_MENU]	
		pathMenu.append(NSMenuItem.separatorItem())
		
		self.optionsItem = NSMenuItem("Path Juggler options...", self.showSettingsDialog)
		pathMenu.append(self.optionsItem)
		
		self.pathDirectionCompatibilityItem = NSMenuItem("Check paths for directional compatibility", self.runMenuCommand)
		pathMenu.append(self.pathDirectionCompatibilityItem)
		
		self.pathOrderingItem = NSMenuItem("Check path ordering", self.runMenuCommand)
		pathMenu.append(self.pathOrderingItem)
		
		#pathMenu.append(NSMenuItem.separatorItem())
		
		self.startingPointItem = NSMenuItem("Set starting points", self.runMenuCommand)
		pathMenu.append(self.startingPointItem)
		
		# ALT - all masters (not layers); w/o ALT just this master
		self.startingPointAllLayersItem = NSMenuItem("Set starting points for all layers", self.runMenuCommand)
		self.startingPointAllLayersItem.setKeyEquivalentModifierMask_(NSAlternateKeyMask)
		self.startingPointAllLayersItem.setAlternate_(True)
		pathMenu.append(self.startingPointAllLayersItem)
		
		self.startingPointCompatibilityItem = NSMenuItem("Reestablish starting point compatibility", self.runMenuCommand)
		pathMenu.append(self.startingPointCompatibilityItem)
		
		self.correctPathDirectionItem = NSMenuItem("Correct (only) path direction", self.runMenuCommand)
		pathMenu.append(self.correctPathDirectionItem)
		
		self.correctPathDirectionAllLayersItem = NSMenuItem("Correct (only) path direction for all layers", self.runMenuCommand)
		self.correctPathDirectionAllLayersItem.setKeyEquivalentModifierMask_(NSAlternateKeyMask)
		self.correctPathDirectionAllLayersItem.setAlternate_(True)
		pathMenu.append(self.correctPathDirectionAllLayersItem)
		
		self.correctPathOrderingItem = NSMenuItem("Correct path ordering", self.runMenuCommand)
		pathMenu.append(self.correctPathOrderingItem)
		
		self.correctPathOrderingMovingStartPointsItem = NSMenuItem("Correct path ordering, moving starting points if necessary", self.runMenuCommand)
		self.correctPathOrderingMovingStartPointsItem.setKeyEquivalentModifierMask_(NSAlternateKeyMask)
		self.correctPathOrderingMovingStartPointsItem.setAlternate_(True)
		pathMenu.append(self.correctPathOrderingMovingStartPointsItem)
		
		#pathMenu.append(NSMenuItem.separatorItem())
		
		self.allCorrectionsAllLayersItem = NSMenuItem("Run all corrections for all layers", self.runMenuCommand)
		pathMenu.append(self.allCorrectionsAllLayersItem)
		
	
	@objc.python_method
	def savePreferences( self, sender ):
		try:
			self.TOLERANCE = float(self.w.tolerance.get())
			self.HORIZ_TOLERANCE = float(self.w.horizTolerance.get())
			self.MAX_MISMATCHES = int(self.w.maxMismatches.get())
			self.SUPRESS_OUTPUT = int(self.w.suppressOutput.get())
			self.IGNORE_OVERLAP = bool(self.w.ignoreOverlap.get())
			Glyphs.defaults[PATH_JUGGLER_PREFIX + "Tolerance"] = self.TOLERANCE
			Glyphs.defaults[PATH_JUGGLER_PREFIX + "HorizTolerance"] = self.HORIZ_TOLERANCE
			Glyphs.defaults[PATH_JUGGLER_PREFIX + "MaxMismatches"] = self.MAX_MISMATCHES
			Glyphs.defaults[PATH_JUGGLER_PREFIX + "SuppressOutput"] = self.SUPPRESS_OUTPUT
			Glyphs.defaults[PATH_JUGGLER_PREFIX + "IgnoreOverlap"] = self.IGNORE_OVERLAP
			
			self.w.close()
		except:
			Message("Check that the entries are all valid.", "Error saving preferences")
			return False
			
		return True

	@objc.python_method
	def loadPreferences( self ):
		try:
			Glyphs.registerDefault(PATH_JUGGLER_PREFIX + "Tolerance", DEFAULT_TOLERANCE)
			Glyphs.registerDefault(PATH_JUGGLER_PREFIX + "HorizTolerance", DEFAULT_HORIZ_TOLERANCE)
			Glyphs.registerDefault(PATH_JUGGLER_PREFIX + "MaxMismatches", DEFAULT_MAX_MISMATCHES)
			Glyphs.registerDefault(PATH_JUGGLER_PREFIX + "SuppressOutput", DEFAULT_SUPPRESS_OUTPUT)
			Glyphs.registerDefault(PATH_JUGGLER_PREFIX + "IgnoreOverlap", DEFAULT_IGNORE_OVERLAP)
			self.TOLERANCE = float(Glyphs.defaults[PATH_JUGGLER_PREFIX + "Tolerance"])
			self.HORIZ_TOLERANCE = float(Glyphs.defaults[PATH_JUGGLER_PREFIX + "HorizTolerance"])
			self.MAX_MISMATCHES = int(Glyphs.defaults[PATH_JUGGLER_PREFIX + "MaxMismatches"])
			self.SUPPRESS_OUTPUT = int(Glyphs.defaults[PATH_JUGGLER_PREFIX + "SuppressOutput"])
			self.IGNORE_OVERLAP = bool(Glyphs.defaults[PATH_JUGGLER_PREFIX + "IgnoreOverlap"])
		except:
			return False
			
		return True
		
	@objc.python_method
	def resetDefaults( self, sender ):
		try:
			self.w.tolerance.set( DEFAULT_TOLERANCE )
			self.w.horizTolerance.set( DEFAULT_HORIZ_TOLERANCE )
			self.w.maxMismatches.set( DEFAULT_MAX_MISMATCHES )
			self.w.suppressOutput.set( DEFAULT_SUPPRESS_OUTPUT )
			self.w.ignoreOverlap.set( DEFAULT_IGNORE_OVERLAP )
		except:
			return False
			
		return True
	
	@objc.python_method
	def showSettingsDialog(self, sender):
		
		# Create new dialog window object. Once closed it cannot be re-opened
		windowWidth  = 325
		windowHeight = 225
		self.w = vanilla.FloatingWindow(
			( windowWidth, windowHeight ), # default window size
			"Path Juggler options", # window title
			autosaveName = PATH_JUGGLER_PREFIX + ".mainwindow" # stores last window position and size
		)
		
		# UI elements:
		linePos, inset, lineHeight = 12, 15, 22
		
		self.w.toleranceText = vanilla.TextBox( (inset, linePos+2, 250, 14), u"Angle tolerance (degrees):", sizeStyle='small', selectable=True )
		self.w.tolerance = vanilla.EditText( (inset+250, linePos-1, -inset, 19), "60", sizeStyle='small' )
		self.w.tolerance.getNSTextField().setToolTip_(u"Maximum angle difference for strokes to be considered directionally compatible.")
		linePos += lineHeight*1.5
		
		self.w.horizToleranceText = vanilla.TextBox( (inset, linePos+2, 250, 14), u"Tolerance for horizontal strokes (degrees):", sizeStyle='small', selectable=True )
		self.w.horizTolerance = vanilla.EditText( (inset+250, linePos-1, -inset, 19), "15", sizeStyle='small' )
		self.w.horizTolerance.getNSTextField().setToolTip_(u"This value applies when comparing strokes where at least one is perfectly horizontal.")
		linePos += lineHeight*1.5
		
		self.w.maxMismatchesText = vanilla.TextBox( (inset, linePos+2, 250, 14), u"Maximum mismatches in sequence:", sizeStyle='small', selectable=True )
		self.w.maxMismatches = vanilla.EditText( (inset+250, linePos-1, -inset, 19), "0", sizeStyle='small' )
		self.w.maxMismatches.getNSTextField().setToolTip_(u"Number of allowed mismatched segments in sequence before the glyph is deemed directionally incompatible.")
		linePos += lineHeight*1.5
		
		self.w.suppressOutputText = vanilla.TextBox( (inset, linePos+2, 250, 14), u"Suppress output when selection larger than:", sizeStyle='small', selectable=True )
		self.w.suppressOutput = vanilla.EditText( (inset+250, linePos-1, -inset, 19), "0", sizeStyle='small' )
		self.w.suppressOutput.getNSTextField().setToolTip_(u"Suppresses standard output in the macro fenster. Warnings will be shown after the function has completed.")
		linePos += lineHeight*1.5
		
		self.w.ignoreOverlap = vanilla.CheckBox( (inset, linePos-1, -inset, 20), u"Ignore corners in overlap", value=True, sizeStyle='small' )
		self.w.ignoreOverlap.getNSButton().setToolTip_(u"If enabled, ignores small segments in overlap regions of the glyph (e.g. corners). ")
		linePos += lineHeight*2
		
		# Save button:
		self.w.okButton = vanilla.Button( (-75-inset, -20-inset, -inset, -inset), "Save", sizeStyle='regular', callback=self.savePreferences )
		self.w.setDefaultButton( self.w.okButton )
		
		# Reset button:
		self.w.resetButton = vanilla.Button( (-220-inset, -20-inset, -inset-90, -inset), "Reset defaults", sizeStyle='regular', callback=self.resetDefaults )
		
		# Cancel button:
		#self.w.cancelButton = vanilla.Button( (-80-inset, -20-inset, -inset, -inset), "Cancel", sizeStyle='regular', callback=self.w.close() )
		#self.w.setDefaultButton( self.w.runButton )
		
		self.w.tolerance.set( self.TOLERANCE )
		self.w.horizTolerance.set( self.HORIZ_TOLERANCE )
		self.w.maxMismatches.set( self.MAX_MISMATCHES )
		self.w.suppressOutput.set( self.SUPPRESS_OUTPUT )
		self.w.ignoreOverlap.set( self.IGNORE_OVERLAP )
		
		# Open window and focus on it:
		self.w.open()
		self.w.makeKey()
	
	#@objc.python_method
	#def closeSettingsWindow(self):
	#	self.w.close()
		
	@objc.python_method
	def getDirection(self, pointFrom, pointTo):
		if pointTo.x == pointFrom.x:
			# north or south
			if pointTo.y == pointFrom.y:
				return DIR_NONE
			elif pointTo.y > pointFrom.y:
				return DIR_N
			elif pointTo.y < pointFrom.y:
				return DIR_S
		elif pointTo.x > pointFrom.x:
			# eastwards
			if pointTo.y == pointFrom.y:
				return DIR_E
			elif pointTo.y > pointFrom.y:
				return DIR_NE
			elif pointTo.y < pointFrom.y:
				return DIR_SE
		elif pointTo.x < pointFrom.x:
			# westwards
			if pointTo.y == pointFrom.y:
				return DIR_W
			elif pointTo.y > pointFrom.y:
				return DIR_NW
			elif pointTo.y < pointFrom.y:
				return DIR_SW
	
	@objc.python_method
	def getAngle(self, pointFrom, pointTo):
		dir = self.getDirection(pointFrom, pointTo)
		if dir != DIR_NONE:
			if dir < 4:
				opp = pointTo.x - pointFrom.x
				adj = pointTo.y - pointFrom.y # zero when east
				return math.degrees(math.atan(opp/adj))
			elif dir < 8:
				opp = pointFrom.y - pointTo.y
				adj = pointTo.x - pointFrom.x # zero when south
				return 90.0 + math.degrees(math.atan(opp/adj))
			elif dir < 12:
				opp = pointFrom.x - pointTo.x
				adj = pointFrom.y - pointTo.y # zero when west
				return 180.0 + math.degrees(math.atan(opp/adj))
			else:
				opp = pointTo.y - pointFrom.y
				adj = pointFrom.x - pointTo.x # zero when north
				return 270.0 + math.degrees(math.atan(opp/adj))
		else:
			return -1.0
		
	@objc.python_method
	def isHorizontal(self, dir1, dir2):
		return dir1==DIR_W or dir1==DIR_E or dir2==DIR_W or dir2==DIR_E
		
	@objc.python_method
	def isSimilarDirection(self, dir1, dir2):

		if self.isHorizontal(dir1, dir2):
			tolerance = 0 # horizontal
		else:
			tolerance = 2
		
		return abs(dir2 - dir1) <= tolerance or abs((dir2 + 16) - dir1) <= tolerance or abs(dir2 - (dir1 + 16)) <= tolerance
	
	@objc.python_method
	def isSimilarAngle(self, pointFrom1, pointTo1, pointFrom2, pointTo2, tolerance = False):
		dir1 = self.getDirection(pointFrom1, pointTo1)
		dir2 = self.getDirection(pointFrom2, pointTo2)
		
		if not tolerance:
			if self.isHorizontal(dir1, dir2):
				tolerance = self.HORIZ_TOLERANCE #2.0 # horizontal
			else:
				tolerance = self.TOLERANCE #60.0 # all other strokes, e.g. vertical
		
		angle1 = self.getAngle(pointFrom1, pointTo1)
		angle2 = self.getAngle(pointFrom2, pointTo2)
		
		return abs(angle2 - angle1) <= tolerance or abs(angle2 - angle1 + 360.0) <= tolerance or abs(angle2 - angle1 - 360.0) <= tolerance
	
	@objc.python_method
	def pathsCompatible(self, sourceLayer, targetLayer):
				
		if len(sourceLayer.paths) != len(targetLayer.paths):
			return False
		else:
			for pathIndex, sourcePath in enumerate(sourceLayer.paths):
				#sourcePath = sourceLayer.paths[pathIndex]
				targetPath = targetLayer.paths[pathIndex]
				if len(sourcePath.nodes) != len(targetPath.nodes):
					return False
				if len(sourcePath.segments) != len(targetPath.segments):
					return False
					
				for i, n1 in enumerate(sourcePath.nodes):
					n2 = targetPath.nodes[i]
					if n1.type != n2.type:
						return False
					
		return True
	
	
	@objc.python_method
	def isCorner(self, dirBefore, currDir, dirAfter):
		
		# check that both rotations in the same direction
		
		if currDir < dirBefore:
			beforeDiff = (currDir+16) - dirBefore
		else:
			beforeDiff = currDir - dirBefore
		
		print("in isCorner", dirBefore, currDir, beforeDiff)
		
		#if beforeDiff > 0 and beforeDiff != 8 and beforeDiff < 16:
		if beforeDiff >= 0 and beforeDiff < 16:
			
			if dirAfter < currDir:
				afterDiff = (dirAfter+16) - currDir
			else:
				afterDiff = dirAfter - currDir
			
			#if afterDiff > 0 and afterDiff != 8 and afterDiff < 16:
			if afterDiff >= 0 and afterDiff < 16:
			
				if beforeDiff <= 8 and afterDiff <= 8:
					
					# both directions are CW
					if dirAfter < dirBefore:
						totalDiff = (dirAfter+16) - dirBefore
					else:
						totalDiff = dirAfter - dirBefore
						
				elif beforeDiff >= 8 and afterDiff >= 8:
					
					# both directions are CCW
					if dirBefore < dirAfter:
						totalDiff = (dirBefore+16) - dirAfter
					else:
						totalDiff = dirBefore - dirAfter

				else:
					return False
			else:
				return False
		else:
			return False
		
		if totalDiff > 8 and totalDiff < 16:
			return True
		else:
			return False
	
		
	@objc.python_method
	def pathsDirectionallyCompatible(self, sourcePath, targetPath, roSourceCoords, roTargetCoords):
		
		if len(sourcePath.nodes) != len(targetPath.nodes):
			return False
		if len(sourcePath.segments) != len(targetPath.segments):
			return False
		
		mismatchedNodesInSequence = 0
		
		sourceNodes = []
		targetNodes = []
		
		for node in sourcePath.nodes:
			if node.type == LINE or node.type == CURVE:
				sourceNodes.append(node)
		for node in targetPath.nodes:
			if node.type == LINE or node.type == CURVE:
				targetNodes.append(node)		
		
		for i, n1 in enumerate(sourceNodes):
			#print("next node")
			n2 = targetNodes[i]
			if i == 0:
				prev_n1 = sourceNodes[len(sourceNodes)-1]
				prev_n2 = targetNodes[len(sourceNodes)-1]
			else:
				prev_n1 = sourceNodes[i-1]
				prev_n2 = targetNodes[i-1]
			
			if i != len(sourceNodes)-1:
				next_n1 = sourceNodes[i+1]
				next_n2 = targetNodes[i+1]
			else:
				next_n1 = sourceNodes[0]
				next_n2 = targetNodes[0]
			
			if i == 0:
				prev_prev_n1 = sourceNodes[len(sourceNodes)-2]
				prev_prev_n2 = targetNodes[len(sourceNodes)-2]
			elif i == 1:
				prev_prev_n1 = sourceNodes[len(sourceNodes)-1]
				prev_prev_n2 = targetNodes[len(sourceNodes)-1]
			else:
				prev_prev_n1 = sourceNodes[i-2]
				prev_prev_n2 = targetNodes[i-2]
			
			if n1.type != n2.type:
				return False
			
			# Overlap detection AND
			if False:
			#if self.IGNORE_OVERLAP:# and not prevSegInOverlap:
				if n1.type == LINE and n2.type == LINE:# or \

					if (prev_n1.position.x, prev_n1.position.y) not in roSourceCoords and (n1.position.x, n1.position.y) not in roSourceCoords:# \
							#and (int((prev_n1.position.x + n1.position.x)/2), int((prev_n1.position.y + n1.position.y)/2)) not in roSourceCoords:
						#print("sourcePath segment in overlap", prev_prev_n1.position, prev_n1.position, n1.position, prev_prev_n1.type, prev_n1.type, n1.type)
						if (prev_n2.position.x, prev_n2.position.y) not in roTargetCoords and (n2.position.x, n2.position.y) not in roTargetCoords:# \
								#and (int((prev_n2.position.x + n2.position.x)/2), int((prev_n2.position.y + n2.position.y)/2)) not in roTargetCoords:
							#print("targetPath segment in overlap\n", prev_prev_n2.position, prev_n2.position, n2.position, prev_prev_n2.type, prev_n2.type, n2.type)
							#prevSegInOverlap = True
							
							# check that this segment is shorter than the one before and after it
							dist1 = math.sqrt((n1.position.x - prev_n1.position.x) ** 2 + \
									(n1.position.y - prev_n1.position.y) ** 2)
							prev_dist1 = math.sqrt((prev_n1.position.x - prev_prev_n1.position.x) ** 2 + \
									(prev_n1.position.y - prev_prev_n1.position.y) ** 2)
							next_dist1 = math.sqrt((next_n1.position.x - n1.position.x) ** 2 + \
									(next_n1.position.y - n1.position.y) ** 2)
									
							dist2 = math.sqrt((n2.position.x - prev_n2.position.x) ** 2 + \
									(n2.position.y - prev_n2.position.y) ** 2)
							prev_dist2 = math.sqrt((prev_n2.position.x - prev_prev_n2.position.x) ** 2 + \
									(prev_n2.position.y - prev_prev_n2.position.y) ** 2)
							next_dist2 = math.sqrt((next_n2.position.x - n2.position.x) ** 2 + \
									(next_n2.position.y - n2.position.y) ** 2)
							
							if dist1 < prev_dist1 and dist1 < next_dist1 and dist2 < prev_dist2 and dist2 < next_dist2:
								continue
								
			# Overlap detection OR
			if self.IGNORE_OVERLAP:# and not prevSegInOverlap:
				if n1.type == LINE and n2.type == LINE:# or \

					if (prev_n1.position.x, prev_n1.position.y) not in roSourceCoords and (n1.position.x, n1.position.y) not in roSourceCoords \
							or (prev_n2.position.x, prev_n2.position.y) not in roTargetCoords and (n2.position.x, n2.position.y) not in roTargetCoords:
						
						# check that this segment is shorter than the one before and after it
						dist1 = math.sqrt((n1.position.x - prev_n1.position.x) ** 2 + \
								(n1.position.y - prev_n1.position.y) ** 2)
						prev_dist1 = math.sqrt((prev_n1.position.x - prev_prev_n1.position.x) ** 2 + \
								(prev_n1.position.y - prev_prev_n1.position.y) ** 2)
						next_dist1 = math.sqrt((next_n1.position.x - n1.position.x) ** 2 + \
								(next_n1.position.y - n1.position.y) ** 2)
								
						dist2 = math.sqrt((n2.position.x - prev_n2.position.x) ** 2 + \
								(n2.position.y - prev_n2.position.y) ** 2)
						prev_dist2 = math.sqrt((prev_n2.position.x - prev_prev_n2.position.x) ** 2 + \
								(prev_n2.position.y - prev_prev_n2.position.y) ** 2)
						next_dist2 = math.sqrt((next_n2.position.x - n2.position.x) ** 2 + \
								(next_n2.position.y - n2.position.y) ** 2)
						
						if dist1 < prev_dist1 and dist1 < next_dist1 and dist2 < prev_dist2 and dist2 < next_dist2:
							continue
			
			#Corner detection
			if self.IGNORE_CORNER:
				if n1.type == LINE and n2.type == LINE and len(sourcePath.nodes) >= 3:
					
					dirBefore1 = self.getDirection(prev_prev_n1, prev_n1)
					dirBefore2 = self.getDirection(prev_prev_n2, prev_n2)
					currDir1 = self.getDirection(prev_n1, n1)
					currDir2 = self.getDirection(prev_n2, n2)
					dirAfter1 = self.getDirection(n1, next_n1)
					dirAfter2 = self.getDirection(n2, next_n2)
					
					#if self.isCorner(dirBefore1, currDir1, dirAfter1) and self.isCorner(dirBefore2, currDir2, dirAfter2):
					c1 = self.isCorner(dirBefore1, currDir1, dirAfter1)
					c2 = self.isCorner(dirBefore2, currDir2, dirAfter2)
					
					if c1 and c2:
						continue	
				
			if self.isSimilarAngle(prev_n1, n1, prev_n2, n2):
				mismatchedNodesInSequence = 0
			else:
				mismatchedNodesInSequence += 1
				if mismatchedNodesInSequence > self.MAX_MISMATCHES: # default = 0
					return False
		return True

	@objc.python_method
	def generateOverlapCoords(self, thisLayer):
		testLayer = thisLayer.copy()
		testLayer.stopUpdates()
		testLayer.flattenOutlines()
		
		tempList = []
		for path in testLayer.paths:
			for node in path.nodes:
				(x, y) = node.position
				tempList.append((x, y))
					
			return set(tempList)

	@objc.python_method
	def allPathsDirectionallyCompatible(self, sourceLayer, targetLayer, roSourceCoords, roTargetCoords):
				
		if len(sourceLayer.paths) != len(targetLayer.paths):
			return False
		else:
			#roSourceCoords = self.generateOverlapCoords(sourceLayer)
			#roTargetCoords = self.generateOverlapCoords(targetLayer)
			
			for pathIndex, sourcePath in enumerate(sourceLayer.paths):
				#sourcePath = sourceLayer.paths[pathIndex]
				targetPath = targetLayer.paths[pathIndex]
				
				if not self.pathsDirectionallyCompatible(sourcePath, targetPath, roSourceCoords, roTargetCoords):
					return False
					
		return True
	
 
	@objc.python_method
	
	def findMatchingStartingNode(self, p1, p2, overlapNodes1, overlapNodes2): # TODO overlap nodes
		''' Finds, sets and returns new starting node of p1 to match p2 directionally '''
		oldStartingNode = p1.nodes[len(p1.nodes)-1]
		newStartingNode = None
		p1nodescopy = copy.copy(p1.nodes) # to avoid mutation error
		for n in p1nodescopy:
			if n.type == CURVE or n.type == LINE:
				n.makeNodeFirst()
				if self.pathsDirectionallyCompatible(p1, p2, overlapNodes1, overlapNodes2):
					newStartingNode = n
					break
		# reset starting node if unable to fix compatibility
		if not newStartingNode:
			oldStartingNode.makeNodeFirst()
		return newStartingNode

	@objc.python_method
	def reestablishStartingPointCompatibility(self, layer):
		''' Moves the starting points of the other layers to match those of layer '''
		glyph = layer.parent
		layerOverlapNodes = self.generateOverlapCoords(layer)
		changeMade = False
		
		for l in glyph.layers:
			if l != layer and (l.isMasterLayer or l.isBracketLayer() or l.isBraceLayer()):
				lOverlapNodes = self.generateOverlapCoords(l)
				# if l not _really_ compatible with layer
				if not self.allPathsDirectionallyCompatible(l, layer, lOverlapNodes, layerOverlapNodes):	
					
					# check if same number of paths
					if len(l.paths) != len(layer.paths):
						return("", "⚠️ Error: Layer" + l + " has " + len(l.paths) + " paths; layer " + layer + " has " + len(layer.paths) + " paths")
					else:
						# try with all different starting points until it is really compatible
						# if still not, then reset
						for i, p1 in enumerate(l.paths):
							p2 = layer.paths[i]
							if not self.pathsDirectionallyCompatible(p1, p2, lOverlapNodes, layerOverlapNodes):
								newStartingNode = self.findMatchingStartingNode(p1, p2, lOverlapNodes, layerOverlapNodes) # sets it too
								changeMade = True
								# reset starting node if unable to fix compatibility
								if not newStartingNode:
									#oldStartingNode.makeNodeFirst()
									return("", "⚠️ Unable to make layer " + l + " compatible by shifting starting points")
									
		if changeMade:
			return(glyph.name + ": Reestablished compatibility by moving starting points", "")
		else:
			return(glyph.name + ": No changes made", "")
						
	@objc.python_method
	def setStartingPoint(self, path):
		bottomLeftNode = None
		for node in path.nodes:
			if node.type == CURVE or node.type == LINE:
				if bottomLeftNode:
					if node.position.y < bottomLeftNode.position.y:
						bottomLeftNode = node
					elif node.position.y == bottomLeftNode.position.y:
						if node.position.x < bottomLeftNode.position.x:
							bottomLeftNode = node
				else:
					bottomLeftNode = node
		if bottomLeftNode:
			oldPos = bottomLeftNode.index
			bottomLeftNode.makeNodeFirst()
			newPos = bottomLeftNode.index
			if oldPos != newPos:
				return(str(path.parent) + ": " + str(path) + ": Setting starting point", "")
			else:
				return(str(path.parent) + ": " + str(path) + ": Starting point is already at the bottom left", "")
		return(str(path.parent) + ": " + str(path) + ": No bottom left node found", "")
				

	@objc.python_method
	def setStartingPoints(self, layer):
		output = []
		for p in layer.paths:
			output.append(self.setStartingPoint(p)[0])
		return("\n".join(output), "")
			
	@objc.python_method
	def getCentreOfMass(self, path):
		onCurveNodes = 0
		xsum, ysum = 0, 0
		for n in path.nodes:
			if n.type == CURVE or n.type == LINE:
				onCurveNodes += 1
				xsum += n.position.x
				ysum += n.position.y
		if onCurveNodes > 0:
			return NSMakePoint(xsum / onCurveNodes, ysum / onCurveNodes)
		else:
			return False
		
	# compares layer against all other layers in the glyph
	@objc.python_method
	def checkPathOrdering(self, glyph, layer):
		
		for i, p1 in enumerate(layer.paths):
			cm1 = self.getCentreOfMass(p1)
			for j, p2 in enumerate(layer.paths):
				if p1 != p2:
					cm2 = self.getCentreOfMass(p2)
					
					# check if centre of mass doesn't intersect the other's area
					if NSPointInRect(cm1, p2.bounds) or NSPointInRect(cm2, p1.bounds):
						continue
					
					if cm1 and cm2:
						pass
					else:
						return False
						
					for l in glyph.layers:
						if l != layer and (l.isMasterLayer or l.isBracketLayer() or l.isBraceLayer()):
							if len(l.paths) != len(layer.paths):
								return False
							
							lcm1 = self.getCentreOfMass(l.paths[i])
							lcm2 = self.getCentreOfMass(l.paths[j])
							
							if NSPointInRect(lcm1, l.paths[j].bounds) or NSPointInRect(lcm2, l.paths[i].bounds):
								continue
							
							if lcm1 and lcm2:
								if not self.isSimilarAngle(cm1, cm2, lcm1, lcm2, 45):
									return False
							else:
								return False
		return True
		
	@objc.python_method
	def checkPathOrderingLists(self, paths1, paths2):
				
		for i, p1 in enumerate(paths1):
			cm1 = self.getCentreOfMass(p1)
			for j, p2 in enumerate(paths1):
				if p1 != p2:
					cm2 = self.getCentreOfMass(p2)
				
					# check if centre of mass doesn't intersect the other's area
					if NSPointInRect(cm1, p2.bounds) or NSPointInRect(cm2, p1.bounds):
						continue
				
					if cm1 and cm2:
						pass
					else:
						return False
						
					lcm1 = self.getCentreOfMass(paths2[i])
					lcm2 = self.getCentreOfMass(paths2[j])
				
					if NSPointInRect(lcm1, paths2[j].bounds) or NSPointInRect(lcm2, paths2[i].bounds):
						continue
				
					if lcm1 and lcm2:
						if not self.isSimilarAngle(cm1, cm2, lcm1, lcm2, 45):
							return False
					
					else:
						return False
		return True
	
	@objc.python_method
	def correctPathOrdering(self, layer, startingPoints):
		'''
		reorders the paths in the glyph to make it compatible
		(automates the "Fix compatibility" filter)
		
		:param: layer: this layer remains the same and the others are adjusted to match it
		:startingPoints: if True, adjusts the starting points if necessary
		:return: none
		'''
		# paths in layer stay in the same order
		# iterate through the other layers
		# check if they are directionally compatible
		# if not, check if other orderings are directionally compatible and take the first
		
		reordered = False
		failed = False
		
		glyph = layer.parent
		layerOverlapNodes = self.generateOverlapCoords(layer)
		differentNumberOfPaths = False
		oneLayerIncompatible = False
		if not layer.paths:
			return("Original layer has no paths", "")
		
		layersToProcess = list([l for l in glyph.layers if l != layer \
				and (l.isMasterLayer or l.isBracketLayer() or l.isBraceLayer()) \
				and l.paths]) #\
				#and len(l.paths) == len(layer.paths)])
		
		layerOrderings = []
		for l in layersToProcess:
			if len(l.paths) == len(layer.paths):
				chosenOrdering = []
				layerIncompatible = False
				lOverlapNodes = self.generateOverlapCoords(l)
				matchingPermFound = False
				perms = permutations(l.paths)
				for perm in perms:
					newOrdering = []
					permIncompatible = False
					for i,p1 in enumerate(layer.paths): # iterates through paths
						newStartingNode = None
						p2 = perm[i]
						
						if self.pathsDirectionallyCompatible(p1, p2, layerOverlapNodes, lOverlapNodes):
							newOrdering.append((p2, False))
						elif startingPoints:# and type(p1) is GSPath:
							if len(p2.nodes) < 1:
								permIncompatible = True
								break
							if len(p1.nodes) != len(p2.nodes):
								permIncompatible = True
								break
							#if len(p1.segments) != len(p2.segments):
							#	permIncompatible/break
							oldStartingNode = p2.nodes[0]
							# following function also sets the node to the first
							newStartingNode = self.findMatchingStartingNode(p2, p1, lOverlapNodes, layerOverlapNodes)
							if newStartingNode:
								newOrdering.append((p2, newStartingNode))
								oldStartingNode.makeNodeFirst()
							else:
								permIncompatible = True
								break
						else:
							permIncompatible = True
							break
					if not permIncompatible:
						newPathList = list([p for (p, q) in newOrdering])
						if self.checkPathOrderingLists(layer.paths, newPathList):
							matchingPermFound = True
							chosenOrdering = newOrdering
							break
				if matchingPermFound:
					layerOrderings.append(chosenOrdering)
				else:
					layerIncompatible = True
					break
			else:
				differentNumberOfPaths = True
		
		errorString = ""
		if differentNumberOfPaths or oneLayerIncompatible:
			errorString += "\n" + glyph.name + ": cannot be made compatible."
			failed = True
		else:
			# if no errors encountered, reorder the layers
			# but first check whether the chosen combination is different to what's there
			for i, l in enumerate(layersToProcess):
				newOrdering = layerOrderings[i]
				layerPaths = []
				for p in l.paths: # geerate list of only paths in layer
					layerPaths.append(p)
				for j, (path, newStartingNode) in enumerate(newOrdering):
					if path != layerPaths[j]:
						reordered = True
					if newStartingNode and newStartingNode != layerPaths[j].nodes[0]:
						reordered = True
			if reordered:
				for i, l in enumerate(layersToProcess):
					newOrdering = layerOrderings[i]
					for i in range(len(l.shapes)-1,-1,-1): # reverse ordering
						if l.shapes[i].shapeType == GSShapeTypePath:
							del l.shapes[i]
					for path, newStartingNode in newOrdering:
						l.shapes.append(path)
						if newStartingNode:
							newStartingNode.makeNodeFirst()
						#reordered = True
			
		if differentNumberOfPaths:
			errorString += " Not all masters contain the same number of paths."
		if oneLayerIncompatible:
			errorString += " Could not find a matching compatible path."
						
		#if errorString:
		#	print(errorString)
		
		if reordered:
			if startingPoints:
				return(glyph.name + ": Reordered paths and/or starting points", errorString)
			else:
				return(glyph.name + ": Reordered paths", errorString)
		elif failed:
			return(glyph.name + ": Reordering failed", errorString)
		else:
			return(glyph.name + ": No changes made", errorString)
		
	
	@objc.python_method
	def correctPathDirection(self, layer):
		# make all paths anti-clockwise
		# except fully-enclosed paths inside another path that do not intersect it -> CW
		# if there are two such paths intersecting each other enclosed in an outer one,
		# make the one resulting in more whitespace (larger counter) anti-clockwise 
		
		changed = 0
		
		# generate table of intersections
		parentGlyph = layer.parent
		font = Glyphs.font
		
		# path is inside another
		# both paths intersect
		
		# Groups of fully enclosed paths
		
		innerPaths = []
		
		# STEP 1: Find all inner paths (and their respective outer paths)
		for i1, p1 in enumerate(layer.paths):
			for i2, p2 in enumerate(layer.paths):
				if p1 != p2:
					if NSContainsRect(p2.bounds, p1.bounds):
						if not p1.bezierPath.intersectWithPath_(p2.bezierPath):
							innerPaths.append((i2, i1))
		
		#print("innerPaths", innerPaths)
		
		pathGroups = []
		outerPaths = []
		
		for(outer, inner) in innerPaths:
			outerPaths.append(outer)
		
		# remove all enclosed paths from outerPaths
		for(outer, inner) in innerPaths:
			while inner in outerPaths:
				outerPaths.remove(inner)
		
		# TODO: set all (remaining) outerPaths to CCW
		
		for outerPath in outerPaths:
			if not layer.paths[outerPath].direction == -1: # CCW
				layer.paths[outerPath].reverse()
				changed = 1
		
		# set all innerPaths[1] to CW
		for(outer, inner) in innerPaths:
			if not inner in outerPaths:
				if not layer.paths[inner].direction == 1: # CW
					layer.paths[inner].reverse()
					changed = 2
			
		# group remaining paths inside an outer path
		for outerPath in outerPaths:
			outerGroup = [outerPath]
			for (outer, inner) in innerPaths:
				if outer == outerPath:
					outerGroup.append(inner)
			if len(outerGroup) > 2:
				pathGroups.append(outerGroup)
		
		for pathGroup in pathGroups:
			maxPath, maxArea = -1, -1
			for path in pathGroup[1:]:
				# inner path with largest area remains CW
				# other paths, if they intersect this inner path (but not the outer path)
				# are set to CCW
				#print ("path", path, "area", layer.paths[path].area())
				if layer.paths[path].area() > maxArea:
					maxPath = path
					maxArea = layer.paths[path].area()
			
			if maxPath >= 0:
				for path in pathGroup[1:]:
					if path != maxPath:
						if layer.paths[path].bezierPath.intersectWithPath_(layer.paths[maxPath].bezierPath):
							if not layer.paths[path].direction == -1: # CCW
								layer.paths[path].reverse()
								changed = 3
		
		if changed:
			return(str(layer) + ": Corrected path direction with intersection order " + str(changed), "")
		else:
			return(str(layer) + ": No changes made", "")

	@objc.python_method
	def runMenuCommand( self, sender ):
		
		# prepare macro output:
		Glyphs.clearLog()
		Glyphs.showMacroWindow()
		#print("Path Juggler log:")

		print("Running command: %s"%sender.title())

		try:
			Font = Glyphs.font
			if not Font.selectedLayers:
				print("⚠️ No glyphs selected")
				return
			
			selectedGlyphs = [ x.parent for x in Font.selectedLayers if x.parent.name is not None ]
			errors = ""
			successString = "Command generated no warnings."
			
			if not selectedGlyphs:
				print("⚠️ No glyphs selected")
				return
			
			for i, thisGlyph in enumerate(selectedGlyphs):
				
				output = ""
				error = ""
				
				containsPaths = False
				for l in thisGlyph.layers:
					if l.isMasterLayer or l.isBracketLayer() or l.isBraceLayer():
						if len(l.paths) > 0:
							containsPaths = True
							break
				
				if not containsPaths:
					output += thisGlyph.name + ": does not contain any paths in active layers"
				
				elif sender == self.pathDirectionCompatibilityItem:
					successString = "All glyphs in the selection are directionally compatible"
					
					if thisGlyph.mastersCompatible:
						pathsCompatible = True
						for l1 in thisGlyph.layers:
							if l1.isMasterLayer or l1.isBracketLayer() or l1.isBraceLayer():
								roSourceCoords = self.generateOverlapCoords(l1)
								for l2 in thisGlyph.layers:
									if l1 != l2:
										if l2.isMasterLayer or l2.isBracketLayer() or l2.isBraceLayer():
											roTargetCoords = self.generateOverlapCoords(l2)
											if not self.allPathsDirectionallyCompatible(l1, l2, roSourceCoords, roTargetCoords):
												pathsCompatible = False
						if pathsCompatible:
							output += thisGlyph.name + ": is directionally compatible"
						else:
							error += thisGlyph.name + ": ⚠️ has compatible masters, but they are not directionally compatible"
					else:
						error += thisGlyph.name+ ": ⚠️ does not have compatible masters"
						
				elif sender == self.pathOrderingItem:
					successString = "All glyphs in the selection have paths in the same order"
					
					for thisLayer in thisGlyph.layers:
						if thisLayer in Font.selectedLayers:
							if thisGlyph.mastersCompatible:
								if self.checkPathOrdering(thisGlyph, thisLayer):
									output += thisGlyph.name + ": has paths in the same order"
								else:
									error += thisGlyph.name + ": ⚠️ has compatible masters, but the paths appear to be switched"
							else:
								error += thisGlyph.name + ": ⚠️ does not have compatible masters"
							break # no need to check futher layers if multiple layers are selected
								
				elif sender == self.startingPointItem:
					
					for layer in thisGlyph.layers:
						if layer in Font.selectedLayers:
							text, error = self.setStartingPoints(layer) # error always blank
							if text:
								if output:
									output += "\n" + text
								else:
									output = text
							
				elif sender == self.startingPointAllLayersItem:
					
					for layer in thisGlyph.layers:
						text, error = self.setStartingPoints(layer) # error always blank
						if text:
							if output:
								output += "\n" + text
							else:
								output = text
							
				elif sender == self.startingPointCompatibilityItem:
					
					# uses the current layer as example of the "correct" setting
					thisLayer = Font.selectedLayers[0]
					if thisLayer.parent != thisGlyph:
						thisLayer = thisGlyph.layers[Font.selectedFontMaster.id]
					output, error = self.reestablishStartingPointCompatibility(thisLayer)
					
				elif sender == self.correctPathDirectionItem:
					
					for thisLayer in thisGlyph.layers:
						if thisLayer in Font.selectedLayers:
							text, error = self.correctPathDirection(thisLayer) # error always blank
							if text:
								if output:
									output += "\n" + text
								else:
									output = text
					
				elif sender == self.correctPathDirectionAllLayersItem:
					
					for thisLayer in thisGlyph.layers:
						text, error = self.correctPathDirection(thisLayer) # error always blank
						if text:
							if output:
								output += "\n" + text
							else:
								output = text
					
				elif sender == self.correctPathOrderingItem:
					
					# uses the current layer as example of the "correct" ordering
					thisLayer = Font.selectedLayers[0]
					if thisLayer.parent != thisGlyph:
						thisLayer = thisGlyph.layers[Font.selectedFontMaster.id]
					output, error = self.correctPathOrdering(thisLayer, False)
					
				elif sender == self.correctPathOrderingMovingStartPointsItem:
					
					# uses the current layer as example of the "correct" ordering
					thisLayer = Font.selectedLayers[0]
					if thisLayer.parent != thisGlyph:
						thisLayer = thisGlyph.layers[Font.selectedFontMaster.id]
					output, error = self.correctPathOrdering(thisLayer, True)
					
				elif sender == self.allCorrectionsAllLayersItem:
				
					output = ("Processing glyph " + thisGlyph.name)
						
					for layer in thisGlyph.layers:
						output += "\n" + self.correctPathDirection(layer)[0] # function returns no error
						output += "\n" + self.setStartingPoints(layer)[0] # function returns no error
					
					# uses the current layer as example of the "correct" ordering
					thisLayer = Font.selectedLayers[0]
					if thisLayer.parent != thisGlyph:
						thisLayer = thisGlyph.layers[Font.selectedFontMaster.id]
					text, error = self.correctPathOrdering(thisLayer, True)
					output += "\n" + text
					
					# TODO!!! if correctPathOrdering fails, repeat and try moving startpoints
					
					if len(selectedGlyphs) > 1:
						output += ("\n")
				
				else:
					print("⚠️ Error: Unrecognized command %s"%sender.title())
					
				if len(selectedGlyphs) > self.SUPPRESS_OUTPUT:
					if error:
						errors += "\n" + error
					if i % 10 == 0:
						print("Glyph %i of %i processed"%(i, len(selectedGlyphs)))
				else:
					if output:
						print(output)
					if error:
						print(error)
				
			if len(selectedGlyphs) > self.SUPPRESS_OUTPUT:
				if errors.strip() == "":
					print("✅ " + successString)
				else:
					print("Command generated following warnings: \n" + errors)
			
			self.updateGlyphsUI(Font)
		except Exception as e:
			Glyphs.showMacroWindow()
			print("\n⚠️ Script Error:\n")
			import traceback
			# Following line does not print the full stack
			print(traceback.format_exc())
			#traceback.print_stack()
	
	
	@objc.python_method
	def updateGlyphsUI(self, font):
		if font and font.currentTab:
			NSNotificationCenter.defaultCenter().postNotificationName_object_(
				"GSUpdateInterface",
				font.currentTab,
			)
			
	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
