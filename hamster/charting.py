"""Small charting library that enables you to draw simple bar and
horizontal bar charts. This library is not intended for scientific graphs.
More like some visual clues to the user.

Currently chart understands only list of two member lists, in label, value
fashion. Like:
    data = [
        ["Label1", value1],
        ["Label2", value2],
        ["Label3", value3],
    ]

Author: toms.baugis@gmail.com
Licensed under LGPL - do whatever you want, and send me some cookies, if you
feel like it.
Feel free to contribute - more info at Project Hamster web page:
http://projecthamster.wordpress.com/

Example:
    # create new chart object
    chart = Chart(max_bar_width = 40, collapse_whitespace = True) 
    
    eventBox = gtk.EventBox() # charts go into eventboxes, or windows
    place = self.get_widget("totals_by_day") #just some placeholder

    eventBox.add(chart);
    place.add(eventBox)

    #Let's imagine that we count how many apples we have gathered, by day
    data = [["Mon", 20], ["Tue", 12], ["Wed", 80],
            ["Thu", 60], ["Fri", 40], ["Sat", 0], ["Sun", 0]]
    self.day_chart.plot(data)

"""

import gtk
import gobject
import copy

# Tango colors
light = [(252, 233, 79),  (138, 226, 52),  (252, 175, 62),
         (114, 159, 207), (173, 127, 168), (233, 185, 110),
         (239, 41,  41),  (238, 238, 236), (136, 138, 133)]

medium = [(237, 212, 0),   (115, 210, 22),  (245, 121, 0),
          (52,  101, 164), (117, 80,  123), (193, 125, 17),
          (204, 0,   0),   (211, 215, 207), (85, 87, 83)]

dark = [(196, 160, 0), (78, 154, 6), (206, 92, 0),
        (32, 74, 135), (92, 53, 102), (143, 89, 2),
        (164, 0, 0), (186, 189, 182), (46, 52, 54)]

color_count = len(light)

def set_color(context, color):
    r,g,b = color[0] / 255.0, color[1] / 255.0, color[2] / 255.0
    context.set_source_rgb(r, g, b)
    
    
class Chart(gtk.DrawingArea):
    """Chart constructor. Optional arguments:
        cycle_colors = [True|False] - should every bar get it's own color.
                                      Defaults to False
        orient_vertical = [True|False] - Chart orientation.
                                         Defaults to vertical
        max_bar_width = pixels - Maximal width of bar. If not specified,
                                 bars will stretch to fill whole area
        collapse_whitespace = [True|False] - If max_bar_width is set, should
                                             we still fill the graph area with
                                             the white stuff and grids and such.
                                             Defaults to false
        stretch_grid = [True|False] - Should the grid be of fixed or flex
                                      size. If set to true, graph will be split
                                      in 4 parts, which will stretch on resize.
                                      Defaults to False.
        animate = [True|False] - Should the bars grow/shrink on redrawing.
                                 Animation happens only if labels and their
                                 order match.
                                 Defaults to True.

        Then there are some defaults, you can override:
        default_grid_stride - If stretch_grid is set to false, this allows you
                              to choose granularity of grid. Defaults to 50
        animation_frames - in how many steps should the animation be done
        animation_timeout - after how many miliseconds should we draw next frame
    """
    def __init__(self, **args):
        """here is init"""
        gtk.DrawingArea.__init__(self)
        self.connect("expose_event", self.expose)
        self.data, self.prev_data = None, None #start off with an empty hand
        
        """now see what we have in args!"""
        self.cycle_colors = "cycle_colors" in args and args["cycle_colors"] # defaults to false
        self.orient_vertical = "orient" not in args or args["orient"] == "vertical" # defaults to true
        
        self.max_bar_width = None
        if "max_bar_width" in args: self.max_bar_width = args["max_bar_width"]        
        self.collapse_whitespace = "collapse_whitespace" in args and args["collapse_whitespace"] #defaults to false
        
        self.stretch_grid = "stretch_grid" in args and args["stretch_grid"] == True #defaults to false

        self.animate = "animate" not in args or args["animate"] # defaults to true
        
        #and some defaults
        self.default_grid_stride = 50
        
        self.animation_frames = 20
        self.animation_timeout = 10 #in miliseconds
        
    def expose(self, widget, event): # expose is when drawing's going on
        context = widget.window.cairo_create()
        context.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
        context.clip()
        
        if self.orient_vertical:
            self.bar_chart(context) 
        else:
            self.horizontal_bar_chart(context)

        return False

    def plot(self, data):
        self.data, self.max = self.get_factors(data)

        if self.animate:
            """chart animation means gradually moving from previous data set
               to the new one. prev_data will be the previous set, new_data
               is copy of the data we have been asked to plot, and data itself
               will be the moving thing"""
               
            # but first we have to check that keys match - otherwise we will
            # get hell knows what
            if self.prev_data:
                if len(self.prev_data) != len(self.data):
                    self.invalidate()
                    return
                for i in range(len(self.prev_data)):
                    if self.data[i][0] != self.prev_data[i][0]:
                        self.invalidate()
                        return #here we go home
                
            
            self.current_frame = 0
            self.new_data = copy.deepcopy(self.data)

            if not self.prev_data: #if there is no previous data, set it to zero, so we get a growing animation
                self.prev_data = copy.deepcopy(self.data)
                for i in range(len(self.prev_data)):
                    self.prev_data[i][1] = 0
                    self.prev_data[i][2] = 0
                    
            self.data = copy.deepcopy(self.prev_data)


            gobject.timeout_add(self.animation_timeout, self.replot)
        else:
            self.invalidate()

    
    def replot(self):
        if self.window:    #this can get called before expose    
            self.current_frame = self.current_frame + 1
            
            # here we do the magic - go from prev to new
            # we are fiddling with the calculated sizes instead of raw data - that's much safer
            for i in range(len(self.data)):
                self.data[i][2] = self.data[i][2] - ((self.prev_data[i][2] - self.new_data[i][2]) / float(self.animation_frames))
                
            self.invalidate()
            
        if self.current_frame < self.animation_frames:
            return True
        else:
            self.prev_data = self.new_data
            return False

    def invalidate(self):
        if self.window:    #this can get called before expose    
            alloc = self.get_allocation()
            rect = gtk.gdk.Rectangle(alloc.x, alloc.y, alloc.width, alloc.height)
            self.window.invalidate_rect(rect, True)
            self.window.process_updates(True)
            
    
    def get_factors(self, data):
        """get's max value out of data and calculates each record's factor
           against it"""
        max_value = 0
        
        for i in range(len(data)):
            max_value = max(max_value, data[i][1])
        
        res = []
        for i in range(len(data)):
            factor = data[i][1] / float(max_value) if max_value > 0 else 0
            res.append([data[i][0], data[i][1], factor])
        
        return res, max_value
    
    
    def bar_chart(self, context):
        rect = self.get_allocation()  #x, y, width, height        
        data, records = self.data, len(self.data)

        if not data:
            return

        # graph box dimensions
        graph_x = rect.x + 50  #give some space to scale labels
        graph_width = rect.width + rect.x - graph_x
        
        step = graph_width / records
        if self.max_bar_width:
            step = min(step, self.max_bar_width)
            if self.collapse_whitespace:
                graph_width = step * records #no need to have that white stuff

        graph_y = rect.y
        graph_height = graph_y - rect.x + rect.height - 15
        
        max_size = graph_height - 15



        context.set_line_width(1)
        
        # TODO put this somewhere else - drawing background and some grid
        context.rectangle(graph_x - 1, graph_y, graph_width, graph_height)
        context.set_source_rgb(1, 1, 1)
        context.fill_preserve()
        context.stroke()

        context.set_line_width(1)
        context.set_dash ([1, 3]);

        set_color(context, dark[8])
        
        # scale lines
        stride = self.default_grid_stride if self.stretch_grid == False else int(graph_height / 4)
            
        for y in range(graph_y, graph_y + graph_height, stride):
            context.move_to(graph_x - 10, y)
            context.line_to(graph_x + graph_width, y)

        # and borders on both sides, so the graph doesn't fall out
        context.move_to(graph_x - 1, graph_y)
        context.line_to(graph_x - 1, graph_y + graph_height + 1)
        context.move_to(graph_x + graph_width, graph_y)
        context.line_to(graph_x + graph_width, graph_y + graph_height + 1)
        

        context.stroke()
        
        
        context.set_dash ([]);
        # bars themselves
        for i in range(records):
            context.rectangle(graph_x + (step * i),
                              graph_y + graph_height - (graph_height * data[i][2]),
                              step * 0.8,
                              (graph_height * data[i][2]))

            color = 1
            if self.cycle_colors:
                if color_count < records:
                    color = (i + 1) % color_count
                else:
                    color = i
                
            set_color(context, light[color])
            context.fill_preserve()    
            set_color(context, dark[color]);
            context.stroke()
        
        # labels
        set_color(context, dark[8]);
        for i in range(records):
            context.move_to(graph_x + 5 + (step * i), graph_y + graph_height + 15)
            context.show_text(data[i][0])

        # values for max min and average
        context.move_to(rect.x + 10, rect.y + 10)
        context.show_text(str(int(self.max)))




    def horizontal_bar_chart(self, context):
        rect = self.get_allocation()  #x, y, width, height
        data, records = self.data, len(self.data)
        
        # ok, start with labels - get the longest now
        # TODO - figure how to wrap text
        max_extent = 0
        for i in range(records):
            extent = context.text_extents(data[i][0]) #x, y, width, height
            max_extent = max(max_extent, extent[2])
            
        
        #push graph to the right, so it doesn't overlap, and add little padding aswell
        graph_x = int(rect.x + max_extent + 10)
        graph_width = int(rect.width + rect.x - graph_x - 40)

        graph_y = rect.y
        graph_height = graph_y - rect.x + rect.height
        
        
        step = graph_height / records if records > 0 else 30
        if self.max_bar_width:
            step = min(step, self.max_bar_width)
            if self.collapse_whitespace:
                graph_height = step * records #resize graph accordingly
        
        max_size = graph_width - 15


        #now let's put the labels and align them right
        set_color(context, dark[8]);
        for i in range(records):
            extent = context.text_extents(data[i][0]) #x, y, width, height
            
            context.move_to(rect.x + max_extent - extent[2], rect.y + (step * i) + (step + extent[3]) / 2)
            context.show_text(data[i][0])
        
        context.stroke()        
        
        


        context.set_line_width(1)
        
        
        # TODO put this somewhere else - drawing background and some grid
        context.rectangle(graph_x - 1, rect.y, graph_width, graph_height)
        context.set_source_rgb(1, 1, 1)
        context.fill_preserve()
        context.stroke()


        context.set_line_width(1)
        context.set_dash ([1, 3]);

        set_color(context, dark[8])

        # scale lines        
        grid_stride = self.default_grid_stride if self.stretch_grid == False else int(graph_width / 4)
        for x in range(graph_x, graph_x + graph_width, grid_stride):
            context.move_to(x-1, graph_y)
            context.line_to(x-1, graph_y + graph_height)

        # and borders on both sides, so the graph doesn't fall out
        context.move_to(graph_x, graph_y)
        context.line_to(graph_x + graph_width, graph_y)
        context.move_to(graph_x, graph_y + graph_height)
        context.line_to(graph_x + graph_width, graph_y + graph_height)


        context.stroke()
        
        
        context.set_dash ([]);
        # bars themselves
        for i in range(records):
            context.rectangle(graph_x,
                              graph_y + (step * i) + step * 0.1,
                              (max_size * data[i][2]),
                              step * 0.8)

            color = 1
            if self.cycle_colors:
                if color_count < records:
                    color = (i + 1) % color_count
                else:
                    color = i
                
            set_color(context, light[color])
            context.fill_preserve()    
            set_color(context, dark[color]);
            context.stroke()
        

        # values for max min and average
        set_color(context, dark[8])
        context.move_to(graph_x + graph_width + 10, graph_y + 10)
        context.show_text(str(int(self.max)))
        
        

