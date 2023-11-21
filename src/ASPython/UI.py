'''
 * File: UI.py
 * Copyright (c) 2023 Loupe
 * https://loupe.team
 * 
 * This file is part of ASPython, licensed under the MIT License.
'''
import tkinter.filedialog # This NEEDS to come before tkinter? At least if you have an 'as' after tkinter
import tkinter
import ASTools


class Application(tkinter.Frame):
    def say_hi(self):
        print("hi there, everyone!")

    def createWidgets(self):
        self.columnconfigure(0, weight=1)
        # self.rowconfigure(2, weight=1)
        self.rowconfigure(4, weight=1)
        
        # Create a frame for the canvas with non-zero row&column weights
        frame_canvas = tkinter.Frame(self)
        frame_canvas.grid(row=4, column=0, columnspan=3, pady=(5, 0), sticky='ew')
        
        self.libraryScrollFrame = ScrollFrame(self)
        self.libraryScrollFrame.grid(row=4, columnspan=3,  sticky=tkinter.W+tkinter.E)
        
        self.libraryWidget = ChecklistBox(self.libraryScrollFrame.viewPort, bg="grey")
        self.libraryWidget.pack(fill=tkinter.X)
        
        self.QUIT = tkinter.Button(self)
        self.QUIT["text"] = "QUIT"
        self.QUIT["fg"]   = "red"
        self.QUIT["command"] =  self.quit

        # self.QUIT.pack({"side": "left"})
        self.QUIT.grid(column=0, row=0)

        self.hi_there = tkinter.Button(self)
        self.hi_there["text"] = "Select Project",
        self.hi_there["command"] = self.getProject 
        # self.hi_there.bind("<Enter>", lambda self, event: self.setColor(event.widget, "red"))
        # self.hi_there.pack({"side": "left"})
        self.hi_there.grid(column=1, row=0)
        
        configLabel = tkinter.Label(self)
        configLabel["text"] = "Configurations: "
        configLabel.grid(row=1, columnspan=3)
        
        
        self.configScrollFrame = ScrollFrame(self)
        self.configScrollFrame.grid(row=2, columnspan=3, ipady=10, sticky=tkinter.W+tkinter.E)
        
        self.configWidget = ChecklistBox(self.configScrollFrame.viewPort, bg="grey")
        self.configWidget.pack(fill=tkinter.X)
        
        configLabel = tkinter.Label(self)
        configLabel["text"] = "Libraries: "
        configLabel.grid(row=3, columnspan=1)
        
        configCheckAll = tkinter.Button(self)
        configCheckAll["text"] = "✓"
        configCheckAll.grid(row=3, column=1)
        configUnCheckAll = tkinter.Button(self)
        configUnCheckAll["text"] = "❌"
        configUnCheckAll.grid(row=3, column=2)
        
        # self.libraryWidget = ChecklistBox(self, bg="grey")
        # self.libraryWidget.pack(fill=tkinter.X, side=tkinter.TOP)
        # self.libraryWidget.grid(row=4, columnspan=3, ipady=10, sticky=tkinter.W+tkinter.E)
        
        configCheckAll["command"] = lambda : self.libraryWidget.setAll(True)
        configUnCheckAll["command"] = lambda : self.libraryWidget.setAll(0)
        
        self.buildButton = tkinter.Button(self)
        self.buildButton["text"] = "Build"
        self.buildButton["command"] = self.buildProject
        self.buildButton.grid(row=5, column=0, sticky=tkinter.W+tkinter.E)
        
        self.exportButton = tkinter.Button(self)
        self.exportButton["text"] = "Export Libs"
        self.exportButton["command"] = self.exportLibraries
        self.exportButton.grid(row=5, column=1, columnspan=2, pady=10, padx=10, sticky=tkinter.W+tkinter.E)

    
    
    
    def setColor(self, widget, color):
        widget["activeforeground"] = color
    
    def __init__(self, master=None):
        self.projectPath = ''
        self.project:ASTools.Project = None
        tkinter.Frame.__init__(self, master)
        self.pack(fill='both', expand=True)
        self.createWidgets()
        
        self.bind("<Configure>", self.on_resize)
        self.height = self.winfo_reqheight()
        self.width = self.winfo_reqwidth()

    def on_resize(self,event):
        # determine the ratio of old width/height to new width/height
        wscale = float(event.width)/self.width
        hscale = float(event.height)/self.height
        self.width = event.width
        self.height = event.height
        # resize the canvas 
        self.config(width=self.width, height=self.height)
        # rescale all the objects tagged with the "all" tag
        # self.scale("all",0,0,wscale,hscale)
        
    def getProject(self):
        potentialPath:str = tkinter.filedialog.askopenfilename(filetypes=[("AS Project","*.apj")])
        if not potentialPath: return
        
        self.busy(True)
        try:
            self.projectPath = potentialPath
            print(self.projectPath)
            self.project = ASTools.Project(self.projectPath)
            
            self.configWidget.addItems(self.projectConfigs())
            self.configWidget.setAll(0)
            
            self.libraryWidget.addItems(self.projectLibraries())
            self.libraryWidget.setAll(0)
            
            print(self.projectLibraries())
            print(self.projectConfigs())
        
        finally:
            self.busy(False)
    
    def projectLibraries(self):
        if not self.project: raise AttributeError()
        
        libNames:list = []
        
        for lib in self.project.libraries:
            libNames.append(lib.name)
            
        return libNames
    
    def projectConfigs(self):
        if not self.project: raise AttributeError()
        
        return self.project.buildConfigNames
    
    def buildProject(self):
        self.busy(True)
        try:
            status = self.project.build(*self.configWidget.getCheckedItems())
            if status.returncode < ASTools.ASReturnCodes["Errors"]:
                self.buildButton["text"] = "Build " + "✓"
            else:
                self.buildButton["text"] = "Build " + "❌"
        finally:
            self.busy(False)
        
            
    def exportLibraries(self):
        dest:str = tkinter.filedialog.askdirectory()
        if not dest: return
        
        
        buildConfigs = []
        for configName in self.configWidget.getCheckedItems():
            buildConfigs.append(configName)
            
        if len(buildConfigs) == 0: raise IndexError()
        
        ignoreLibraries = list(set(self.projectLibraries()).difference(self.libraryWidget.getCheckedItems()))
        ignoreLibraries = ['*{0}*'.format(element) for element in ignoreLibraries]
        
        status = self.project.exportLibraries(dest, overwrite=True, buildConfigs=buildConfigs, ignores=ignoreLibraries, includeVersion=True)
        
        if len(status.failed) == 0:
            self.exportButton["text"] = "Export Libs " + "✓"
        else:
            self.exportButton["text"] = "Export Libs " + "❌"
    
    def busy(self, setValue:bool) -> bool:
        if(setValue != None):
            self._busy = setValue
            
            if(setValue):
                self.config(cursor='wait')
            else:
                self.config(cursor='')
            self.update()
        return self._busy
            

# ************************
# Scrollable Frame Class
# ************************
class ScrollFrame(tkinter.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs) # create a frame (self)
        self.config(height=100)

        self.canvas = tkinter.Canvas(self, borderwidth=0, background="#ffffff")          #place canvas on self
        self.viewPort = tkinter.Frame(self.canvas, background="#ffffff")                    #place a frame on the canvas, this frame will hold the child widgets 
        self.vsb = tkinter.Scrollbar(self, orient="vertical", command=self.canvas.yview) #place a scrollbar on self 
        self.canvas.configure(yscrollcommand=self.vsb.set)                          #attach scrollbar action to scroll of canvas

        self.vsb.pack(side="right", fill="y")                                       #pack scrollbar to right of self
        self.canvas.pack(side="left", fill="both", expand=True)                     #pack canvas to left of self and expand to fil
        self.canvas_window = self.canvas.create_window((4,4), window=self.viewPort, anchor="nw",            #add view port frame to canvas
            tags="self.viewPort")

        self.viewPort.bind("<Configure>", self.onFrameConfigure)                       #bind an event whenever the size of the viewPort frame changes.
        self.canvas.bind("<Configure>", self.onCanvasConfigure)                       #bind an event whenever the size of the viewPort frame changes.

        self.onFrameConfigure(None)                                                 #perform an initial stretch on render, otherwise the scroll region has a tiny border until the first resize

    def onFrameConfigure(self, event):                                              
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))                 #whenever the size of the frame changes, alter the scroll region respectively.

    def onCanvasConfigure(self, event):
        '''Reset the canvas window to encompass inner frame when required'''
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width = canvas_width)            #whenever the size of the canvas changes alter the window region respectively.


class ChecklistBox(tkinter.Frame):
    def __init__(self, parent, choices=None, **kwargs):
        tkinter.Frame.__init__(self, parent, **kwargs)

        self.vars = []
        self.items = []
        
        if choices:
            self.addItems(choices)

    def clearItems(self):
        for item in self.items:
            item.pack_forget()
            
        self.items.clear()
        self.vars.clear()
        
    def setAll(self, value):
        for i, var in enumerate(self.vars):
            if value:
                var.set(self.items[i].cget('text'))
            else:
                var.set('')
        
    def addItems(self, choices):
        bg = self.cget("background")
        for choice in choices:
            var = tkinter.StringVar(value=choice)
            cb = tkinter.Checkbutton(self, var=var, text=choice,
                                onvalue=choice, offvalue="",
                                anchor="w", width=20, background=bg,
                                relief="flat", highlightthickness=0
            )
            cb.pack(side="top", fill="x", anchor="w")
            self.vars.append(var)
            self.items.append(cb)

    def getCheckedItems(self):
        values = []
        for var in self.vars:
            value =  var.get()
            if value:
                values.append(value)
        return values
    


if __name__ == "__main__":
    # filediag = tkinter.filedialog.FileDialog(root)
    root = tkinter.Tk()
    root.title("AS Tools")
    app = Application(master=root)
    app.mainloop()
    root.destroy()
