# pythonGUIexperiments
tkinter work for little games and math visualization. 

General programming ideas that involve or have added some visualization/interactivity from the tkinter module

Some components of the programs in addition to gui handling include:

  From Pachinko
  - implementations of solutions to differential equations + simple physics models 
  
  From FourierAnimation
  - generating an interpolating polynomial to an arbitrary amount of points
  - performing analytic integration of a few classes of functions
  
  From DDR
  - Recording real-time input from the keyboard
  - Preventing accumulating lag in time sensitive programs including a visual update loop.
  
  From VocabularyPractise
  - Manipulating datasets in pandas


# Usage
-----
DDR/DDR recorder.py: Running the program launches a window. Focusing in on the window enables recording of keyboard arrow input.
The return key halts recording and saves it as a pandas DataFrame in a JSON file under a default filename 'Song.txt'.

DDR/DDRlike.py: pulls the DataFrame stored in JSON format from 'Song.txt'. Playback at desired speed can be set in the constructor to DdrFile

FourierDrawer/Fourier2D.py: Launches a blank canvas. The 'Add line' and 'Add curve' buttons add two and five points to the canvas, respectively.
Points may be dragged with the mouse. The return key or 'Interpolate' draws an interpolating curve through the full set of current points. The n key
or 'Fourier' generates an analytically dervies set of fourier components to for a default set of orders = -50:50, then regenerates the original curve
and draws to the canvas.

Pachinko/Pachinko.py: Run the file and click the window to drop balls.

SpacedVocabularyPractice.py: Run file and follow input prompts to launch specific gui.
